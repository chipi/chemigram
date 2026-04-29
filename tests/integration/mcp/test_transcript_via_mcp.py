"""Integration: transcript wires into MCP server dispatch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
import pytest

from chemigram.core.session import start_session
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
def workspace_with_baseline(tmp_path: Path) -> Workspace:
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw = root / "raw" / "x.NEF"
    raw.touch()
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    return Workspace(image_id="img-1", root=root, repo=repo, raw_path=raw)


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_mcp_session_writes_tool_call_entries(workspace_with_baseline: Workspace) -> None:
    """Every MCP tool call → tool_call + tool_result entries on the transcript."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)

    transcript = start_session(workspace_with_baseline, session_id="testsess")
    server, ctx = build_server(vocabulary=vocab, prompts=prompts, transcript=transcript)
    ctx.workspaces[workspace_with_baseline.image_id] = workspace_with_baseline

    async def _exercise() -> None:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )
            await session.call_tool("get_state", arguments={"image_id": "img-1"})

    try:
        anyio.run(_exercise)
    finally:
        transcript.close()
        clear_registry()

    lines = [json.loads(line) for line in transcript.path.read_text(encoding="utf-8").splitlines()]
    kinds = [line["kind"] for line in lines]
    assert kinds[0] == "header"
    assert kinds[-1] == "footer"
    tool_calls = [line for line in lines if line["kind"] == "tool_call"]
    tool_results = [line for line in lines if line["kind"] == "tool_result"]
    assert {entry["tool"] for entry in tool_calls} == {"apply_primitive", "get_state"}
    assert all(entry["success"] for entry in tool_results)


def test_transcript_header_shape(workspace_with_baseline: Workspace) -> None:
    """Header's first line carries the documented metadata: session_id,
    started_at, image_id, mode, prompt_versions, vocab_pack.
    """
    clear_registry()
    transcript = start_session(
        workspace_with_baseline,
        session_id="hdr",
        mode="A",
        vocab_pack="starter",
        prompt_versions={"mode_a": "v1"},
    )
    transcript.close()
    clear_registry()
    lines = [json.loads(line) for line in transcript.path.read_text(encoding="utf-8").splitlines()]
    header = lines[0]
    assert header["kind"] == "header"
    assert header["session_id"] == "hdr"
    assert header["image_id"] == "img-1"
    assert header["mode"] == "A"
    assert header["vocab_pack"] == "starter"
    assert header["prompt_versions"] == {"mode_a": "v1"}
    assert "started_at" in header


def test_transcript_footer_shape(workspace_with_baseline: Workspace) -> None:
    """Footer carries ended_at + entry_count; close is idempotent."""
    clear_registry()
    transcript = start_session(workspace_with_baseline, session_id="ftr")
    transcript.append({"kind": "note", "text": "marker"})
    transcript.close(summary={"final_tag": "v1"})
    transcript.close()  # idempotent — second call is a no-op
    clear_registry()
    lines = [json.loads(line) for line in transcript.path.read_text(encoding="utf-8").splitlines()]
    footer = lines[-1]
    assert footer["kind"] == "footer"
    assert footer["entry_count"] == 1
    assert "ended_at" in footer
    assert footer["final_tag"] == "v1"


def test_transcript_orders_calls_results_proposals(
    workspace_with_baseline: Workspace,
) -> None:
    """Multi-kind sequence is recorded in call order."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    transcript = start_session(workspace_with_baseline, session_id="order")
    server, ctx = build_server(vocabulary=vocab, prompts=prompts, transcript=transcript)
    ctx.workspaces[workspace_with_baseline.image_id] = workspace_with_baseline
    transcript.append_proposal("taste", "p1", "test proposal")
    transcript.append_confirmation("p1", accepted=True)

    async def _exercise() -> None:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "expo_+0.5"},
            )

    try:
        anyio.run(_exercise)
    finally:
        transcript.close()
        clear_registry()

    kinds = [
        json.loads(line)["kind"]
        for line in transcript.path.read_text(encoding="utf-8").splitlines()
    ]
    # Header → proposal → confirmation → tool_call → tool_result → footer
    assert kinds[0] == "header"
    assert kinds[-1] == "footer"
    proposal_idx = kinds.index("proposal")
    confirm_idx = kinds.index("confirmation")
    call_idx = kinds.index("tool_call")
    result_idx = kinds.index("tool_result")
    assert proposal_idx < confirm_idx < call_idx < result_idx
    # Each tool_call has a matching tool_result immediately after.
    assert call_idx + 1 == result_idx


def test_transcript_records_failed_tool_with_error_code(
    workspace_with_baseline: Workspace,
) -> None:
    """A tool that fails records the structured error_code."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    transcript = start_session(workspace_with_baseline, session_id="fail")
    server, ctx = build_server(vocabulary=vocab, prompts=prompts, transcript=transcript)
    ctx.workspaces[workspace_with_baseline.image_id] = workspace_with_baseline

    async def _exercise() -> None:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "apply_primitive",
                arguments={"image_id": "img-1", "primitive_name": "no_such_primitive"},
            )

    try:
        anyio.run(_exercise)
    finally:
        transcript.close()
        clear_registry()

    results = [
        json.loads(line)
        for line in transcript.path.read_text(encoding="utf-8").splitlines()
        if json.loads(line).get("kind") == "tool_result"
    ]
    assert results, "expected at least one tool_result"
    assert results[0]["success"] is False
    assert results[0]["error_code"] == "not_found"


def test_mcp_session_transcript_failure_does_not_abort(
    workspace_with_baseline: Workspace,
) -> None:
    """Transcript I/O failure → the tool call still completes."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)

    class BrokenTranscript:
        def append_tool_call(self, *_args: Any, **_kw: Any) -> None:
            raise RuntimeError("disk full")

        def append_tool_result(self, *_args: Any, **_kw: Any) -> None:
            raise RuntimeError("disk full")

    server, ctx = build_server(vocabulary=vocab, prompts=prompts, transcript=BrokenTranscript())
    ctx.workspaces[workspace_with_baseline.image_id] = workspace_with_baseline

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool("get_state", arguments={"image_id": "img-1"})
            return _decode(r)

    try:
        payload = anyio.run(_exercise)
    finally:
        clear_registry()

    # The tool call still succeeded despite transcript failures
    assert payload["success"] is True
