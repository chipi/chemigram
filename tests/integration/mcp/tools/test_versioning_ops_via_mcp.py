"""Integration: per-tool coverage for the versioning MCP tools.

Each tool gets dedicated happy-path + error-path coverage through
``in_memory_session``. The pre-existing :file:`test_versioning_rendering_via_mcp.py`
covers the multi-tool happy-path session; this file covers the
shape-of-the-error-envelope contract per tool.

Part of GH #31 / v1.1.0 capability matrix.
"""

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
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    ws = Workspace(image_id="img-1", root=root, repo=repo, raw_path=raw_path)
    ctx.workspaces[ws.image_id] = ws

    yield server, ctx
    clear_registry()


def _decode(call_result: Any) -> dict:
    return json.loads(call_result.content[0].text)


# ---------- branch -----------------------------------------------------


def test_branch_happy_path(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "branch",
                    arguments={
                        "image_id": "img-1",
                        "name": "experiment",
                        "from_": "baseline",
                    },
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")
    assert out["data"]["ref"] == "refs/heads/experiment"


def test_branch_default_from_is_head(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "branch", arguments={"image_id": "img-1", "name": "from-head"}
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")


def test_branch_already_exists_raises_versioning_error(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            await session.call_tool("branch", arguments={"image_id": "img-1", "name": "dup"})
            return _decode(
                await session.call_tool("branch", arguments={"image_id": "img-1", "name": "dup"})
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"
    assert "already exists" in out["error"]["message"]


def test_branch_from_unknown_ref_raises(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "branch",
                    arguments={
                        "image_id": "img-1",
                        "name": "from-nowhere",
                        "from_": "refs/heads/no-such-branch",
                    },
                )
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"


def test_branch_unknown_image_raises_not_found(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "branch",
                    arguments={"image_id": "no-such-image", "name": "x"},
                )
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "not_found"


# ---------- tag --------------------------------------------------------


def test_tag_default_at_head(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool("tag", arguments={"image_id": "img-1", "name": "v0"})
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")
    assert out["data"]["ref"] == "refs/tags/v0"


def test_tag_immutability_re_tag_rejects(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            await session.call_tool("tag", arguments={"image_id": "img-1", "name": "v0"})
            return _decode(
                await session.call_tool("tag", arguments={"image_id": "img-1", "name": "v0"})
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"
    assert "immutable" in out["error"]["message"]


def test_tag_empty_name_rejected_as_invalid_input(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool("tag", arguments={"image_id": "img-1", "name": ""})
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "invalid_input"


def test_tag_explicit_hash(server_and_ctx: Any) -> None:
    server, ctx = server_and_ctx
    h = ctx.workspaces["img-1"].repo.resolve_ref("refs/tags/baseline")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "tag",
                    arguments={"image_id": "img-1", "name": "explicit", "hash": h},
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")


def test_tag_unknown_hash_raises_versioning_error(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "tag",
                    arguments={
                        "image_id": "img-1",
                        "name": "ghost",
                        "hash": "0" * 64,
                    },
                )
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"


# ---------- checkout ---------------------------------------------------


def test_checkout_to_branch_returns_state_summary(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": "img-1", "ref_or_hash": "main"},
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")
    assert "head_hash" in out["data"]


def test_checkout_to_tag_succeeds(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": "img-1", "ref_or_hash": "baseline"},
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")


def test_checkout_to_hash_succeeds(server_and_ctx: Any) -> None:
    server, ctx = server_and_ctx
    h = ctx.workspaces["img-1"].repo.resolve_ref("refs/tags/baseline")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": "img-1", "ref_or_hash": h},
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")


def test_checkout_unknown_ref_raises(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": "img-1", "ref_or_hash": "no-such-thing"},
                )
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"


# ---------- log --------------------------------------------------------


def test_log_after_several_ops_newest_first(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> list[dict]:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )
            await session.call_tool("tag", arguments={"image_id": "img-1", "name": "v1"})
            return _decode(
                await session.call_tool("log", arguments={"image_id": "img-1", "limit": 10})
            )["data"]

    entries = anyio.run(_go)
    # Newest first — tag, then snapshot (apply), then earlier setup
    ops = [e["op"] for e in entries]
    assert ops[0] == "tag"
    assert "snapshot" in ops


def test_log_limit_respected(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> list[dict]:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )
            return _decode(
                await session.call_tool("log", arguments={"image_id": "img-1", "limit": 1})
            )["data"]

    entries = anyio.run(_go)
    assert len(entries) == 1


def test_log_unknown_image_raises_not_found(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("log", arguments={"image_id": "no-such"}))

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "not_found"


# ---------- diff -------------------------------------------------------


def test_diff_equal_snapshots_returns_empty_list(server_and_ctx: Any) -> None:
    server, ctx = server_and_ctx
    h = ctx.workspaces["img-1"].repo.resolve_ref("refs/tags/baseline")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "diff",
                    arguments={"image_id": "img-1", "hash_a": h, "hash_b": h},
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")
    assert out["data"] == []


def test_diff_after_apply_shows_change(server_and_ctx: Any) -> None:
    server, ctx = server_and_ctx
    base = ctx.workspaces["img-1"].repo.resolve_ref("refs/tags/baseline")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            applied = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
                )
            )
            return _decode(
                await session.call_tool(
                    "diff",
                    arguments={
                        "image_id": "img-1",
                        "hash_a": base,
                        "hash_b": applied["data"]["snapshot_hash"],
                    },
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")
    diffs = out["data"]
    assert len(diffs) >= 1
    assert any(d["operation"] == "exposure" for d in diffs)


def test_diff_unknown_hash_raises(server_and_ctx: Any) -> None:
    server, ctx = server_and_ctx
    base = ctx.workspaces["img-1"].repo.resolve_ref("refs/tags/baseline")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "diff",
                    arguments={
                        "image_id": "img-1",
                        "hash_a": base,
                        "hash_b": "0" * 64,
                    },
                )
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"


# ---------- snapshot from detached HEAD --------------------------------


def test_snapshot_from_detached_head_raises_versioning_error(server_and_ctx: Any) -> None:
    """The protective error in versioning.ops.snapshot is preserved even
    after ADR-062 — reset no longer detaches HEAD, but a direct checkout
    to a tag still does, and the next snapshot must refuse cleanly.
    """
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "checkout",
                arguments={"image_id": "img-1", "ref_or_hash": "baseline"},
            )
            return _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
                )
            )

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "versioning_error"
    assert "detached" in out["error"]["message"].lower()


# ---------- snapshot tool (explicit) -----------------------------------


def test_snapshot_tool_happy_path(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "snapshot",
                    arguments={"image_id": "img-1", "label": "manual save"},
                )
            )

    out = anyio.run(_go)
    assert out["success"], out.get("error")
    assert "hash" in out["data"]


# ---------- get_state error path ---------------------------------------


def test_get_state_unknown_image_raises_not_found(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("get_state", arguments={"image_id": "no-such"}))

    out = anyio.run(_go)
    assert out["success"] is False
    assert out["error"]["code"] == "not_found"


# ---------- list_vocabulary input validation ---------------------------
#
# Note: the layer-enum check in `_list_vocabulary` is reachable only
# from direct in-process calls — through MCP, the schema layer rejects
# out-of-enum values at the transport layer (no JSON envelope returned).
# That belt-and-suspenders runtime check has unit-tier coverage; the
# integration tier covers the happy path in test_vocab_edit_via_mcp.
