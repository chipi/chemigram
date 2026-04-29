"""Integration: batch-2 versioning + rendering tools through the harness.

Real-render tests skip when darktable isn't present.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import anyio
import pytest

from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.vocab import VocabularyIndex
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import clear_registry
from chemigram.mcp.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[4]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"
BASELINE_XMP = REPO_ROOT / "tests" / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"


@pytest.fixture
def server_and_ctx(tmp_path: Path) -> Any:
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts)

    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    ws = Workspace(image_id="img-1", root=root, repo=repo, raw_path=raw_path)
    ctx.workspaces[ws.image_id] = ws

    yield server, ctx
    clear_registry()


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_full_versioning_session_via_mcp(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            apply_a = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
                )
            )
            assert apply_a["success"]
            br = _decode(
                await session.call_tool(
                    "branch",
                    arguments={"image_id": "img-1", "name": "exp", "from_": "HEAD"},
                )
            )
            chk = _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": "img-1", "ref_or_hash": "exp"},
                )
            )
            apply_b = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": "img-1",
                        "primitive_name": "wb_warm_subtle",
                    },
                )
            )
            df = _decode(
                await session.call_tool(
                    "diff",
                    arguments={
                        "image_id": "img-1",
                        "hash_a": apply_a["data"]["snapshot_hash"],
                        "hash_b": apply_b["data"]["snapshot_hash"],
                    },
                )
            )
            tg = _decode(
                await session.call_tool(
                    "tag",
                    arguments={"image_id": "img-1", "name": "v1-export"},
                )
            )
            lg = _decode(
                await session.call_tool(
                    "log",
                    arguments={"image_id": "img-1", "limit": 50},
                )
            )
            return {
                "apply_a": apply_a,
                "branch": br,
                "checkout": chk,
                "apply_b": apply_b,
                "diff": df,
                "tag": tg,
                "log": lg,
            }

    out = anyio.run(_exercise)
    for step in ("apply_a", "branch", "checkout", "apply_b", "diff", "tag", "log"):
        assert out[step]["success"], f"{step} failed: {out[step].get('error')}"
    assert isinstance(out["diff"]["data"], list)
    assert any(e["op"] == "tag" for e in out["log"]["data"])


@pytest.mark.skipif(shutil.which("darktable-cli") is None, reason="no darktable-cli")
def test_render_preview_via_mcp_with_darktable(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool(
                "render_preview",
                arguments={"image_id": "img-1", "size": 256},
            )
            return _decode(r)

    payload = anyio.run(_exercise)
    # Darktable will fail because raw_path is a stub; expect DARKTABLE_ERROR
    assert payload["success"] is False
    assert payload["error"]["code"] == "darktable_error"
