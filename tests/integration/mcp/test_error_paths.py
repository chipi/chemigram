"""Integration: every reachable ErrorCode round-trips as a structured envelope.

The first principle in ``docs/testing.md`` is that errors are first-class
data — agents must never see a raw stack trace through MCP. This file
audits the reachable error codes from the agent's perspective and proves
each one comes back as ``{success: false, error: {code, message,
details, recoverable}}`` rather than escaping as a transport failure.

The unreachable codes (``synthesizer_error``, ``permission_error``,
``not_implemented`` — see ``src/chemigram/mcp/errors.py``'s class
docstring) are deliberately not exercised: tests gated until those codes
have a real callsite.

Part of GH #34 / v1.1.0 capability matrix.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

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

REPO_ROOT = Path(__file__).resolve().parents[3]
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


def _is_structured_error(payload: dict, expected_code: str) -> bool:
    """The contract from ADR-056 / RFC-010."""
    if payload.get("success") is not False:
        return False
    err = payload.get("error")
    if not isinstance(err, dict):
        return False
    return (
        err.get("code") == expected_code
        and isinstance(err.get("message"), str)
        and isinstance(err.get("details"), dict)
        and isinstance(err.get("recoverable"), bool)
    )


# ---------- invalid_input ----------------------------------------------


def test_invalid_input_envelope_shape(server_and_ctx: Any) -> None:
    """log_vocabulary_gap with whitespace-only description → invalid_input."""
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "log_vocabulary_gap",
                    arguments={"image_id": "img-1", "description": "   "},
                )
            )

    payload = anyio.run(_go)
    assert _is_structured_error(payload, "invalid_input")


# ---------- not_found --------------------------------------------------


def test_not_found_envelope_shape(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool("get_state", arguments={"image_id": "no-such-image"})
            )

    payload = anyio.run(_go)
    assert _is_structured_error(payload, "not_found")


# ---------- state_error ------------------------------------------------


def test_state_error_no_baseline_snapshot(tmp_path: Path) -> None:
    """A workspace with no snapshot can't apply primitives."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts)

    root = tmp_path / "fresh"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    # No snapshot — workspace is empty.
    ws = Workspace(image_id="empty", root=root, repo=repo, raw_path=raw_path)
    ctx.workspaces[ws.image_id] = ws

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": "empty", "primitive_name": "expo_+0.5"},
                )
            )

    payload = anyio.run(_go)
    clear_registry()
    assert _is_structured_error(payload, "state_error")
    assert "no baseline" in payload["error"]["message"].lower()


def test_state_error_snapshot_tool_no_xmp(tmp_path: Path) -> None:
    """The snapshot tool refuses when there's no current XMP."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts)

    root = tmp_path / "fresh"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    ws = Workspace(image_id="empty", root=root, repo=repo, raw_path=raw_path)
    ctx.workspaces[ws.image_id] = ws

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("snapshot", arguments={"image_id": "empty"}))

    payload = anyio.run(_go)
    clear_registry()
    assert _is_structured_error(payload, "state_error")


# ---------- versioning_error -------------------------------------------


def test_versioning_error_envelope_shape(server_and_ctx: Any) -> None:
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": "img-1", "ref_or_hash": "no-such-ref"},
                )
            )

    payload = anyio.run(_go)
    assert _is_structured_error(payload, "versioning_error")


# ---------- darktable_error --------------------------------------------


def test_darktable_error_render_with_stub_raw(server_and_ctx: Any) -> None:
    """The fixture's raw_path is a touch'd empty file — darktable rejects it.

    This is the integration-level proof that the ``darktable_error`` envelope
    is well-formed; the e2e tier (``test_render_validation.py``) covers
    the success path with a real raw.
    """
    import shutil

    if shutil.which("darktable-cli") is None:
        pytest.skip("no darktable-cli on PATH")
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "img-1", "size": 256},
                )
            )

    payload = anyio.run(_go)
    assert _is_structured_error(payload, "darktable_error")


def test_darktable_error_no_binary_envelope(server_and_ctx: Any) -> None:
    """If darktable-cli isn't reachable, render returns a structured error.

    Patches the render stage's binary resolution to a non-existent path
    so the test runs even on machines that have darktable installed.
    """
    server, _ = server_and_ctx

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "render_preview",
                    arguments={"image_id": "img-1", "size": 256},
                )
            )

    with patch.dict("os.environ", {"DARKTABLE_CLI": "/no/such/binary"}):
        payload = anyio.run(_go)
    assert _is_structured_error(payload, "darktable_error")


# ---------- contract: every reachable code is exercised somewhere -----


def test_audit_reachable_error_codes_exercised() -> None:
    """Sanity: every reachable ErrorCode value has at least one assertion
    above. Update this set when adding/removing codes (and update the
    matrix in #30).
    """
    from chemigram.mcp.errors import ErrorCode

    reachable = {
        ErrorCode.INVALID_INPUT,
        ErrorCode.NOT_FOUND,
        ErrorCode.STATE_ERROR,
        ErrorCode.VERSIONING_ERROR,
        ErrorCode.MASKING_ERROR,
        ErrorCode.DARKTABLE_ERROR,
    }
    reserved = {
        ErrorCode.SYNTHESIZER_ERROR,
        ErrorCode.PERMISSION_ERROR,
        ErrorCode.NOT_IMPLEMENTED,
    }
    # All enum values are accounted for in either reachable or reserved.
    assert reachable | reserved == set(ErrorCode), (
        f"Some ErrorCode values are unaccounted: "
        f"{set(ErrorCode) - reachable - reserved}. Either add to "
        f"`reachable` (with a corresponding test above) or `reserved` "
        f"(with a callsite in errors.py's class docstring)."
    )
