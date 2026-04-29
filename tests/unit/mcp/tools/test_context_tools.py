"""Unit tests for chemigram.mcp.tools.context."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


@pytest.fixture
def isolated_tastes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "tastes"
    root.mkdir()
    monkeypatch.setenv("CHEMIGRAM_TASTES_DIR", str(root))
    return root


# --- read_context -------------------------------------------------------


def test_read_context_minimal_workspace(context: ToolContext, isolated_tastes: Path) -> None:
    """Empty tastes/brief/notes/log/gaps → empty structures, no error."""
    result = _call("read_context", {"image_id": "test-image"}, context)
    assert result.success is True
    data = result.data
    assert data["tastes"] == {"default": "", "genres": {}, "conflicts": []}
    assert data["brief"]["intent"] == ""
    assert data["notes"]["summary"] == ""
    assert isinstance(data["recent_log"], list)
    assert data["recent_gaps"] == []


def test_read_context_with_tastes_and_brief(context: ToolContext, isolated_tastes: Path) -> None:
    (isolated_tastes / "_default.md").write_text("calm tones\n")
    (isolated_tastes / "underwater.md").write_text("slate-blue over cyan\n")
    workspace = context.workspaces["test-image"]
    (workspace.root / "brief.md").write_text("Tastes: [underwater]\n\nIntent: clean blue\n")

    result = _call("read_context", {"image_id": "test-image"}, context)
    assert result.success is True
    assert "calm tones" in result.data["tastes"]["default"]
    assert "underwater" in result.data["tastes"]["genres"]
    assert result.data["brief"]["tastes"] == ["underwater"]
    assert "clean blue" in result.data["brief"]["intent"]


def test_read_context_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call("read_context", {"image_id": "ghost"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_read_context_after_apply_includes_recent_log(
    context: ToolContext, isolated_tastes: Path
) -> None:
    _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "expo_+0.5"},
        context,
    )
    result = _call("read_context", {"image_id": "test-image"}, context)
    assert result.success is True
    ops = [e["op"] for e in result.data["recent_log"]]
    assert "snapshot" in ops


# --- propose_taste_update / confirm_taste_update ------------------------


def test_propose_taste_returns_proposal_id(context: ToolContext) -> None:
    result = _call(
        "propose_taste_update",
        {"content": "prefer cool tones", "category": "appearance"},
        context,
    )
    assert result.success is True
    pid = result.data["proposal_id"]
    assert len(pid) == 32  # uuid hex
    assert pid in context.proposals
    assert context.proposals[pid].kind == "taste"


def test_propose_taste_invalid_category_rejected(context: ToolContext) -> None:
    result = _call(
        "propose_taste_update",
        {"content": "x", "category": "weather"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_propose_taste_empty_content_rejected(context: ToolContext) -> None:
    result = _call(
        "propose_taste_update",
        {"content": "   ", "category": "appearance"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_propose_taste_default_target_is_default_md(context: ToolContext) -> None:
    result = _call(
        "propose_taste_update",
        {"content": "a", "category": "appearance"},
        context,
    )
    assert result.data["target_file"] == "_default.md"


def test_propose_taste_explicit_file_used(context: ToolContext) -> None:
    result = _call(
        "propose_taste_update",
        {"content": "a", "category": "appearance", "file": "underwater"},
        context,
    )
    # extension auto-added
    assert result.data["target_file"] == "underwater.md"


def test_confirm_taste_writes_to_target_file(context: ToolContext, isolated_tastes: Path) -> None:
    propose = _call(
        "propose_taste_update",
        {
            "content": "prefer cool tones for pelagic",
            "category": "appearance",
            "file": "underwater",
        },
        context,
    )
    pid = propose.data["proposal_id"]

    confirm = _call("confirm_taste_update", {"proposal_id": pid}, context)
    assert confirm.success is True
    written = isolated_tastes / "underwater.md"
    assert written.exists()
    assert "prefer cool tones for pelagic" in written.read_text()
    # Proposal cleared
    assert pid not in context.proposals


def test_confirm_taste_unknown_proposal_returns_not_found(context: ToolContext) -> None:
    result = _call("confirm_taste_update", {"proposal_id": "nope"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_confirm_taste_double_confirm_returns_not_found(
    context: ToolContext, isolated_tastes: Path
) -> None:
    propose = _call(
        "propose_taste_update",
        {"content": "x", "category": "value"},
        context,
    )
    pid = propose.data["proposal_id"]
    _call("confirm_taste_update", {"proposal_id": pid}, context)

    result = _call("confirm_taste_update", {"proposal_id": pid}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_confirm_taste_separator_between_appends(
    context: ToolContext, isolated_tastes: Path
) -> None:
    """Second confirm gets a blank-line separator."""
    p1 = _call(
        "propose_taste_update",
        {"content": "first line", "category": "appearance"},
        context,
    ).data["proposal_id"]
    _call("confirm_taste_update", {"proposal_id": p1}, context)
    p2 = _call(
        "propose_taste_update",
        {"content": "second line", "category": "appearance"},
        context,
    ).data["proposal_id"]
    _call("confirm_taste_update", {"proposal_id": p2}, context)
    written = (isolated_tastes / "_default.md").read_text()
    assert "first line" in written
    assert "second line" in written
    # blank line between
    assert "first line\n\nsecond line" in written or "first line\n" in written


# --- propose_notes_update / confirm_notes_update ------------------------


def test_propose_notes_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call(
        "propose_notes_update",
        {"image_id": "ghost", "content": "x"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_propose_notes_empty_content_rejected(context: ToolContext) -> None:
    result = _call(
        "propose_notes_update",
        {"image_id": "test-image", "content": "   "},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_propose_and_confirm_notes_round_trip(context: ToolContext) -> None:
    propose = _call(
        "propose_notes_update",
        {"image_id": "test-image", "content": "session: lifted shadows on subject"},
        context,
    )
    assert propose.success is True
    pid = propose.data["proposal_id"]

    confirm = _call("confirm_notes_update", {"proposal_id": pid}, context)
    assert confirm.success is True
    notes = (context.workspaces["test-image"].root / "notes.md").read_text()
    assert "lifted shadows on subject" in notes
    assert pid not in context.proposals


def test_confirm_notes_unknown_proposal_returns_not_found(context: ToolContext) -> None:
    result = _call("confirm_notes_update", {"proposal_id": "nope"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_confirm_notes_with_taste_proposal_id_returns_not_found(
    context: ToolContext, isolated_tastes: Path
) -> None:
    """Cross-kind proposal IDs are isolated — a taste pid can't confirm via notes."""
    p = _call(
        "propose_taste_update",
        {"content": "x", "category": "appearance"},
        context,
    )
    result = _call("confirm_notes_update", {"proposal_id": p.data["proposal_id"]}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


# --- transcript integration ---------------------------------------------


def test_propose_records_to_transcript(
    context: ToolContext, isolated_tastes: Path, tmp_path: Path
) -> None:
    from chemigram.core.session import start_session

    workspace = context.workspaces["test-image"]
    transcript = start_session(workspace, session_id="t1")
    context.transcript = transcript

    p = _call(
        "propose_taste_update",
        {"content": "x", "category": "appearance"},
        context,
    )
    _call("confirm_taste_update", {"proposal_id": p.data["proposal_id"]}, context)
    transcript.close()

    import json

    lines = [json.loads(line) for line in transcript.path.read_text(encoding="utf-8").splitlines()]
    kinds = [line.get("kind") for line in lines]
    assert "proposal" in kinds
    assert "confirmation" in kinds
