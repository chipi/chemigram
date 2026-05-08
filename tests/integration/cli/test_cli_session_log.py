"""Integration tests for ``chemigram session-log {list,show,find,replay}``.

Sister test file to ``test_cli_gap_log.py``; same workspace-fixture
pattern, but each sub-test seeds session JSONL transcripts under
<root>/<image_id>/sessions/<session_id>.jsonl.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _seed_session(
    workspace_root: Path,
    image_id: str,
    session_id: str,
    *,
    started_at: str = "2026-05-01T10:00:00Z",
    mode: str = "mode_a",
    vocab_pack: str = "starter",
    entries: list[dict] | None = None,
    summary: dict | None = None,
) -> Path:
    """Seed one transcript at <root>/<image_id>/sessions/<session_id>.jsonl."""
    image_root = workspace_root / image_id
    (image_root / "objects").mkdir(parents=True, exist_ok=True)
    (image_root / "raw").mkdir(parents=True, exist_ok=True)
    sessions_dir = image_root / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    path = sessions_dir / f"{session_id}.jsonl"

    lines: list[dict] = [
        {
            "kind": "header",
            "session_id": session_id,
            "started_at": started_at,
            "image_id": image_id,
            "mode": mode,
            "prompt_versions": {},
            "vocab_pack": vocab_pack,
        }
    ]
    if entries:
        lines.extend(entries)
    if summary is not None:
        lines.append({"kind": "footer", "summary": summary})

    with path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")
    return path


# ---------------------------------------------------------------------------
# session-log list
# ---------------------------------------------------------------------------


def test_list_no_sessions(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "0 session(s)" in result.stdout


def test_list_returns_all_sessions(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(tmp_path, "img1", "s1", started_at="2026-05-01T10:00:00Z")
    _seed_session(tmp_path, "img2", "s2", started_at="2026-05-02T10:00:00Z")
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "2 session(s)" in result.stdout
    assert "s1" in result.stdout
    assert "s2" in result.stdout


def test_list_image_filter(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(tmp_path, "img1", "s1")
    _seed_session(tmp_path, "img2", "s2")
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "session-log", "list", "--image", "img1"]
    )
    assert "1 session(s)" in result.stdout
    assert "s1" in result.stdout
    assert "s2" not in result.stdout


def test_list_since_relative_filters_old(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(tmp_path, "img1", "old", started_at="2020-01-01T00:00:00Z")
    _seed_session(
        tmp_path,
        "img2",
        "new",
        started_at=datetime.now(UTC).isoformat(),
    )
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "session-log", "list", "--since", "1d"]
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "1 session(s)" in result.stdout
    assert "new" in result.stdout


def test_list_since_invalid_format_errors(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "session-log", "list", "--since", "not-a-date"]
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


def test_list_includes_entry_count(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {"timestamp": "t", "kind": "tool_call", "tool": "apply_primitive", "args": {}},
            {"timestamp": "t", "kind": "tool_result", "tool": "apply_primitive", "success": True},
        ],
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "list"])
    assert "entry_count" in result.stdout
    # 1 header + 2 entries = 3
    assert "3" in result.stdout


# ---------------------------------------------------------------------------
# session-log show
# ---------------------------------------------------------------------------


def test_show_prints_chronological_entries(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {
                "timestamp": "t1",
                "kind": "tool_call",
                "tool": "apply_primitive",
                "args": {"name": "exposure"},
            },
            {"timestamp": "t2", "kind": "tool_result", "tool": "apply_primitive", "success": True},
            {"timestamp": "t3", "kind": "note", "text": "looks good"},
        ],
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "show", "s1"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "exposure" in result.stdout
    assert "looks good" in result.stdout
    assert "4 entries" in result.stdout  # 1 header + 3 entries


def test_show_unknown_session_exits_three(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "session-log", "show", "no_such_session"]
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
    assert "session not found" in result.stderr.lower()


# ---------------------------------------------------------------------------
# session-log find
# ---------------------------------------------------------------------------


def test_find_requires_a_filter(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "find"])
    assert result.exit_code == ExitCode.INVALID_INPUT.value
    assert "at least one filter" in result.stderr.lower()


def test_find_by_primitive(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {
                "timestamp": "t",
                "kind": "tool_call",
                "tool": "apply_primitive",
                "args": {"name": "exposure", "value": 0.5},
            },
            {
                "timestamp": "t",
                "kind": "tool_call",
                "tool": "apply_primitive",
                "args": {"name": "vibrance", "value": 0.3},
            },
        ],
    )
    result = runner.invoke(
        app,
        ["--workspace", str(tmp_path), "session-log", "find", "--primitive", "exposure"],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "1 match(es)" in result.stdout
    assert "exposure" in result.stdout
    assert '"name": "vibrance"' not in result.stdout


def test_find_by_tool(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {"timestamp": "t", "kind": "tool_call", "tool": "apply_primitive", "args": {}},
            {"timestamp": "t", "kind": "tool_call", "tool": "snapshot", "args": {}},
        ],
    )
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "session-log", "find", "--tool", "snapshot"]
    )
    assert "1 match(es)" in result.stdout


def test_find_by_module_substring(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {
                "timestamp": "t",
                "kind": "note",
                "text": "wanted to apply colorbalancergb but it didn't work",
            },
            {"timestamp": "t", "kind": "note", "text": "applied vignette successfully"},
        ],
    )
    result = runner.invoke(
        app,
        ["--workspace", str(tmp_path), "session-log", "find", "--module", "colorbalancergb"],
    )
    assert "1 match(es)" in result.stdout
    assert "colorbalancergb" in result.stdout


# ---------------------------------------------------------------------------
# session-log replay
# ---------------------------------------------------------------------------


def test_replay_renders_apply_primitive_as_cli(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {
                "timestamp": "t",
                "kind": "tool_call",
                "tool": "apply_primitive",
                "args": {"name": "exposure", "image_id": "img1", "value": 0.5},
            },
        ],
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "replay", "s1"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "chemigram apply-primitive" in result.stdout
    assert "exposure" in result.stdout
    assert "--value 0.5" in result.stdout


def test_replay_renders_versioning_verbs(runner: CliRunner, tmp_path: Path) -> None:
    _seed_session(
        tmp_path,
        "img1",
        "s1",
        entries=[
            {
                "timestamp": "t",
                "kind": "tool_call",
                "tool": "snapshot",
                "args": {"image_id": "img1"},
            },
        ],
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "session-log", "replay", "s1"])
    assert "chemigram snapshot img1" in result.stdout


def test_replay_unknown_session_exits_three(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "session-log", "replay", "no_such_session"]
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
