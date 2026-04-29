"""Integration: context tools through the in-memory MCP harness."""

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
def server_and_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    tastes = tmp_path / "tastes"
    tastes.mkdir()
    monkeypatch.setenv("CHEMIGRAM_TASTES_DIR", str(tastes))

    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts)

    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw = root / "raw" / "x.NEF"
    raw.touch()
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    ws = Workspace(image_id="img-1", root=root, repo=repo, raw_path=raw)
    ctx.workspaces[ws.image_id] = ws

    yield server, ctx, tastes, ws
    clear_registry()


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_read_context_via_mcp(server_and_workspace: Any) -> None:
    server, _, tastes, ws = server_and_workspace
    (tastes / "_default.md").write_text("calm tones\n")
    (ws.root / "brief.md").write_text("Tastes: [underwater]\n\nIntent: blue\n")

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool("read_context", arguments={"image_id": "img-1"})
            return _decode(r)

    payload = anyio.run(_exercise)
    assert payload["success"] is True
    assert "calm tones" in payload["data"]["tastes"]["default"]
    assert payload["data"]["brief"]["tastes"] == ["underwater"]


def test_propose_confirm_taste_via_mcp(server_and_workspace: Any) -> None:
    server, _, tastes, _ = server_and_workspace

    async def _exercise() -> tuple[dict, dict]:
        async with in_memory_session(server) as session:
            propose = await session.call_tool(
                "propose_taste_update",
                arguments={
                    "content": "prefer cool tones for pelagic",
                    "category": "appearance",
                    "file": "underwater",
                },
            )
            propose_payload = _decode(propose)
            confirm = await session.call_tool(
                "confirm_taste_update",
                arguments={"proposal_id": propose_payload["data"]["proposal_id"]},
            )
            return propose_payload, _decode(confirm)

    propose, confirm = anyio.run(_exercise)
    assert propose["success"]
    assert confirm["success"]
    written = (tastes / "underwater.md").read_text()
    assert "cool tones for pelagic" in written


def test_propose_confirm_notes_via_mcp(server_and_workspace: Any) -> None:
    server, _, _, ws = server_and_workspace

    async def _exercise() -> tuple[dict, dict]:
        async with in_memory_session(server) as session:
            propose = await session.call_tool(
                "propose_notes_update",
                arguments={
                    "image_id": "img-1",
                    "content": "session: lifted shadows; warmth on subject",
                },
            )
            propose_payload = _decode(propose)
            confirm = await session.call_tool(
                "confirm_notes_update",
                arguments={"proposal_id": propose_payload["data"]["proposal_id"]},
            )
            return propose_payload, _decode(confirm)

    propose, confirm = anyio.run(_exercise)
    assert propose["success"]
    assert confirm["success"]
    notes = (ws.root / "notes.md").read_text()
    assert "lifted shadows" in notes


def test_read_context_empty_workspace_returns_sane_structure(
    server_and_workspace: Any,
) -> None:
    """No tastes/brief/notes → read_context returns the documented
    sections with empty values; doesn't fail.
    """
    server, _, _, _ = server_and_workspace

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("read_context", arguments={"image_id": "img-1"}))

    payload = anyio.run(_go)
    assert payload["success"], payload.get("error")
    data = payload["data"]
    # Structured-top sections per ADR-059
    for section in ("tastes", "brief", "notes", "recent_log", "recent_gaps"):
        assert section in data


def test_read_context_multi_scope_tastes(server_and_workspace: Any) -> None:
    """_default.md is always loaded; brief's `Tastes: [genre]` adds
    that genre file to the merge per ADR-048.
    """
    server, _, tastes, ws = server_and_workspace
    (tastes / "_default.md").write_text("default-line\n")
    (tastes / "underwater.md").write_text("underwater-line\n")
    (ws.root / "brief.md").write_text("Tastes: [underwater]\n")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("read_context", arguments={"image_id": "img-1"}))

    payload = anyio.run(_go)
    assert payload["success"]
    tastes_data = payload["data"]["tastes"]
    # Both default and the genre file appear in the loaded set.
    assert "default-line" in tastes_data["default"]
    assert any(
        "underwater-line" in v for v in tastes_data.get("genres", {}).values()
    ) or "underwater-line" in tastes_data.get("merged", "")


def test_read_context_long_notes_summarized(server_and_workspace: Any) -> None:
    """Notes longer than 40 lines (10 head + 30 tail threshold) → the
    response includes the elision marker.
    """
    server, _, _, ws = server_and_workspace
    long_notes = "\n".join(f"line {i}" for i in range(1, 60))
    (ws.root / "notes.md").write_text(long_notes)

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("read_context", arguments={"image_id": "img-1"}))

    payload = anyio.run(_go)
    assert payload["success"]
    notes = payload["data"]["notes"]
    # Notes section reports the truncation flag and contains the elision marker
    assert notes.get("truncated") is True
    body = notes.get("summary", "") or notes.get("body", "")
    assert "elided" in body
    assert "line 1" in body  # head present
    assert "line 59" in body  # tail present


def test_read_context_brief_no_tastes_field(server_and_workspace: Any) -> None:
    """Brief without `Tastes:` line → only _default.md loads, no error."""
    server, _, tastes, ws = server_and_workspace
    (tastes / "_default.md").write_text("default-only\n")
    (ws.root / "brief.md").write_text("Intent: get the shot\n")

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("read_context", arguments={"image_id": "img-1"}))

    payload = anyio.run(_go)
    assert payload["success"]
    assert payload["data"]["brief"]["tastes"] == []
    assert "default-only" in payload["data"]["tastes"]["default"]


def test_confirm_taste_unknown_proposal_returns_not_found(
    server_and_workspace: Any,
) -> None:
    server, _, _, _ = server_and_workspace

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "confirm_taste_update",
                    arguments={"proposal_id": "no-such-proposal-id"},
                )
            )

    payload = anyio.run(_go)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_confirm_notes_unknown_proposal_returns_not_found(
    server_and_workspace: Any,
) -> None:
    server, _, _, _ = server_and_workspace

    async def _go() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "confirm_notes_update",
                    arguments={"proposal_id": "no-such-proposal-id"},
                )
            )

    payload = anyio.run(_go)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_proposal_in_transcript_when_configured(server_and_workspace: Any, tmp_path: Path) -> None:
    """Build a fresh server with transcript wired; verify proposal/confirmation entries."""
    from chemigram.core.session import start_session

    _, _, _tastes, ws = server_and_workspace
    clear_registry()

    transcript = start_session(ws, session_id="ctx-int")
    server, ctx = build_server(
        vocabulary=VocabularyIndex(VOCAB_TEST_PACK),
        prompts=PromptStore(SHIPPED_PROMPTS),
        transcript=transcript,
    )
    ctx.workspaces[ws.image_id] = ws

    async def _exercise() -> None:
        async with in_memory_session(server) as session:
            propose = _decode(
                await session.call_tool(
                    "propose_taste_update",
                    arguments={"content": "x", "category": "appearance"},
                )
            )
            await session.call_tool(
                "confirm_taste_update",
                arguments={"proposal_id": propose["data"]["proposal_id"]},
            )

    try:
        anyio.run(_exercise)
    finally:
        transcript.close()
        clear_registry()

    lines = [json.loads(line) for line in transcript.path.read_text(encoding="utf-8").splitlines()]
    kinds = [line.get("kind") for line in lines]
    assert "proposal" in kinds
    assert "confirmation" in kinds
