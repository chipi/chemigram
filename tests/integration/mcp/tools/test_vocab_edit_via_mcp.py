"""Integration: tool batch 1 round-trips through the in-memory MCP harness."""

from __future__ import annotations

import json
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
    baseline_xmp = parse_xmp(BASELINE_XMP)
    h = snapshot(repo, baseline_xmp, label="baseline")
    tag(repo, "baseline", h)
    ws = Workspace(image_id="img-1", root=root, repo=repo, raw_path=raw_path)
    ctx.workspaces[ws.image_id] = ws

    yield server, ctx
    clear_registry()


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_list_vocabulary_via_mcp(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool("list_vocabulary", arguments={})
            return _decode(r)

    payload = anyio.run(_exercise)
    assert payload["success"] is True
    names = {e["name"] for e in payload["data"]}
    assert "expo_+0.5" in names


def test_apply_primitive_via_mcp(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _exercise() -> tuple[dict, dict]:
        async with in_memory_session(server) as session:
            apply_r = await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )
            state_r = await session.call_tool("get_state", arguments={"image_id": "img-1"})
            return _decode(apply_r), _decode(state_r)

    apply_payload, state_payload = anyio.run(_exercise)
    assert apply_payload["success"] is True
    assert "snapshot_hash" in apply_payload["data"]
    assert state_payload["success"] is True
    assert state_payload["data"]["head_hash"] == apply_payload["data"]["snapshot_hash"]


def test_apply_primitive_with_ad_hoc_mask_spec_via_mcp(server_and_ctx: Any) -> None:
    """Closes #78: any-primitive ad-hoc masking through the MCP tool surface.

    Pass an explicit mask_spec alongside a global primitive (expo_+0.5);
    verify the snapshot's XMP carries masks_history (proof the apply path
    routed through apply_with_drawn_mask).
    """
    server, ctx = server_and_ctx
    mask_spec = {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": 0.5,
            "center_y": 0.5,
            "radius_x": 0.3,
            "radius_y": 0.3,
            "border": 0.05,
        },
    }

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": "img-1",
                        "primitive_name": "expo_+0.5",
                        "mask_spec": mask_spec,
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is True
    snapshot_hash = payload["data"]["snapshot_hash"]

    # Verify the snapshot XMP carries masks_history (= drawn-mask path ran).
    workspace = ctx.workspaces["img-1"]
    raw = workspace.repo.read_object(snapshot_hash)
    assert b"masks_history" in raw, (
        "ad-hoc mask_spec via MCP should inject darktable:masks_history via apply_with_drawn_mask"
    )


def test_reset_via_mcp(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _exercise() -> tuple[dict, dict, dict]:
        async with in_memory_session(server) as session:
            baseline_state = _decode(
                await session.call_tool("get_state", arguments={"image_id": "img-1"})
            )
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )
            after_apply = _decode(
                await session.call_tool("get_state", arguments={"image_id": "img-1"})
            )
            reset_r = _decode(await session.call_tool("reset", arguments={"image_id": "img-1"}))
            return baseline_state, after_apply, reset_r

    baseline, applied, after_reset = anyio.run(_exercise)
    assert applied["data"]["head_hash"] != baseline["data"]["head_hash"]
    assert after_reset["data"]["head_hash"] == baseline["data"]["head_hash"]


def test_remove_module_via_mcp(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _exercise() -> tuple[dict, dict]:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )
            before = _decode(await session.call_tool("get_state", arguments={"image_id": "img-1"}))
            r = await session.call_tool(
                "remove_module",
                arguments={"image_id": "img-1", "module_name": "exposure"},
            )
            return before, _decode(r)

    before, removed = anyio.run(_exercise)
    assert removed["success"] is True
    assert removed["data"]["state_after"]["entry_count"] < before["data"]["entry_count"]


def test_read_context_via_vocab_session(server_and_ctx: Any) -> None:
    """Slice 5 shipped read_context for real; verify it works in this fixture."""
    server, _ = server_and_ctx

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool("read_context", arguments={"image_id": "img-1"})
            return _decode(r)

    payload = anyio.run(_exercise)
    assert payload["success"] is True
    assert "tastes" in payload["data"]
    assert "brief" in payload["data"]
