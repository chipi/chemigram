"""Unit tests for chemigram.core.session.SessionTranscript."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chemigram.core.session import SessionHeader, SessionTranscript, start_session
from chemigram.core.versioning import ImageRepo
from chemigram.core.workspace import Workspace, init_workspace_root


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw = root / "raw" / "x.NEF"
    raw.touch()
    return Workspace(image_id="img", root=root, repo=repo, raw_path=raw)


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_start_session_writes_header(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.close()
    lines = _read_lines(t.path)
    assert lines[0]["kind"] == "header"
    assert lines[0]["image_id"] == "img"
    assert lines[0]["mode"] == "A"


def test_session_id_auto_generated(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.close()
    assert len(t.session_id) == 32  # uuid4 hex


def test_session_id_explicit_used(workspace: Workspace) -> None:
    t = start_session(workspace, session_id="abc123")
    t.close()
    assert t.session_id == "abc123"
    assert t.path.name == "abc123.jsonl"


def test_append_writes_jsonl_line(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.append({"kind": "note", "msg": "hello"})
    t.close()
    lines = _read_lines(t.path)
    # header, note, footer
    assert len(lines) == 3
    assert lines[1]["kind"] == "note"
    assert lines[1]["msg"] == "hello"
    assert "timestamp" in lines[1]


def test_append_tool_call_shape(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.append_tool_call("apply_primitive", {"image_id": "x", "primitive_name": "expo_+0.5"})
    t.close()
    lines = _read_lines(t.path)
    entry = lines[1]
    assert entry["kind"] == "tool_call"
    assert entry["tool"] == "apply_primitive"
    assert entry["args"] == {"image_id": "x", "primitive_name": "expo_+0.5"}


def test_append_tool_result_shape(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.append_tool_result("apply_primitive", success=True)
    t.append_tool_result("missing_thing", success=False, error_code="not_found")
    t.close()
    lines = _read_lines(t.path)
    assert lines[1]["success"] is True
    assert "error_code" not in lines[1]
    assert lines[2]["error_code"] == "not_found"


def test_append_proposal_and_confirmation(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.append_proposal("taste", "p1", "prefer cool tones for pelagic")
    t.append_confirmation("p1", accepted=True)
    t.close()
    lines = _read_lines(t.path)
    assert lines[1]["kind"] == "proposal"
    assert lines[1]["proposal_kind"] == "taste"
    assert lines[2]["kind"] == "confirmation"
    assert lines[2]["accepted"] is True


def test_close_writes_footer(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.append({"kind": "note"})
    t.append({"kind": "note"})
    t.close()
    lines = _read_lines(t.path)
    assert lines[-1]["kind"] == "footer"
    assert lines[-1]["entry_count"] == 2
    assert "ended_at" in lines[-1]


def test_close_with_summary_merges_into_footer(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.close(summary={"snapshots_taken": 3})
    lines = _read_lines(t.path)
    assert lines[-1]["snapshots_taken"] == 3


def test_close_idempotent(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.close()
    t.close()  # should not raise
    # Only one footer line written
    lines = _read_lines(t.path)
    footers = [line for line in lines if line.get("kind") == "footer"]
    assert len(footers) == 1


def test_append_after_close_raises(workspace: Workspace) -> None:
    t = start_session(workspace)
    t.close()
    with pytest.raises(RuntimeError, match="closed"):
        t.append({"kind": "note"})


def test_transcript_path_is_under_sessions_dir(workspace: Workspace) -> None:
    t = start_session(workspace, session_id="x")
    t.close()
    assert t.path == workspace.sessions_dir / "x.jsonl"


def test_session_header_dataclass_shape() -> None:
    h = SessionHeader(session_id="x", started_at="t", image_id="i", mode="A")
    assert h.prompt_versions == {}
    assert h.vocab_pack == "starter"


def test_transcript_continues_after_serialize_failure(workspace: Workspace, tmp_path: Path) -> None:
    """A non-serializable entry surfaces as 'write_failure' but doesn't kill
    the transcript."""

    class NotSerializable:
        pass

    t = start_session(workspace)
    t.append({"kind": "weird", "obj": NotSerializable()})  # default=str makes this work
    t.append({"kind": "note", "msg": "still alive"})
    t.close()
    lines = _read_lines(t.path)
    # default=str converts NotSerializable to its repr — line written
    assert any(line.get("kind") == "weird" for line in lines)
    assert any(line.get("kind") == "note" for line in lines)


def test_isinstance_session_transcript(workspace: Workspace) -> None:
    t = start_session(workspace)
    assert isinstance(t, SessionTranscript)
    t.close()
