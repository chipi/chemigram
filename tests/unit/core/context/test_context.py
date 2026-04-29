"""Unit tests for chemigram.core.context loaders."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from chemigram.core.context import (
    NOTES_HEAD_LINES,
    NOTES_TAIL_LINES,
    Brief,
    Notes,
    RecentGaps,
    RecentLog,
    Tastes,
)
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


@pytest.fixture
def tastes_root(tmp_path: Path) -> Path:
    """Isolated tastes root via CHEMIGRAM_TASTES_DIR."""
    root = tmp_path / "tastes"
    root.mkdir()
    return root


# --- Tastes -------------------------------------------------------------


def test_tastes_default_only(tastes_root: Path) -> None:
    (tastes_root / "_default.md").write_text("calm tones\nlow contrast\n")
    out = Tastes.load(brief_genres=None, tastes_root=tastes_root)
    assert "calm tones" in out.default
    assert out.genres == {}
    assert out.conflicts == []


def test_tastes_with_genres(tastes_root: Path) -> None:
    (tastes_root / "_default.md").write_text("base\n")
    (tastes_root / "underwater.md").write_text("slate-blue over cyan\n")
    (tastes_root / "wildlife.md").write_text("eye contrast lifted\n")
    out = Tastes.load(brief_genres=["underwater", "wildlife"], tastes_root=tastes_root)
    assert out.default == "base\n"
    assert "underwater" in out.genres
    assert "wildlife" in out.genres


def test_tastes_missing_genre_file_skipped(tastes_root: Path) -> None:
    (tastes_root / "_default.md").write_text("base\n")
    out = Tastes.load(brief_genres=["nonexistent"], tastes_root=tastes_root)
    assert out.genres == {}


def test_tastes_conflicts_surfaced(tastes_root: Path) -> None:
    (tastes_root / "_default.md").write_text("")
    (tastes_root / "a.md").write_text("warm tones\nshallow shadows\n")
    (tastes_root / "b.md").write_text("warm tones\nbig contrast\n")
    out = Tastes.load(brief_genres=["a", "b"], tastes_root=tastes_root)
    assert len(out.conflicts) == 1
    assert out.conflicts[0]["point"] == "warm tones"
    assert set(out.conflicts[0]["files"]) == {"a", "b"}


def test_tastes_dir_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    custom = tmp_path / "custom-tastes"
    custom.mkdir()
    (custom / "_default.md").write_text("custom\n")
    monkeypatch.setenv("CHEMIGRAM_TASTES_DIR", str(custom))
    out = Tastes.load()
    assert "custom" in out.default


def test_tastes_missing_default_returns_empty(tastes_root: Path) -> None:
    out = Tastes.load(brief_genres=None, tastes_root=tastes_root)
    assert out.default == ""


# --- Brief --------------------------------------------------------------


def test_brief_load_parses_tastes_line(workspace: Workspace) -> None:
    (workspace.root / "brief.md").write_text(
        "# Manta photo\n\nTastes: [underwater, wildlife]\n\nIntent: clean blue water\n"
    )
    out = Brief.load(workspace)
    assert out.tastes == ["underwater", "wildlife"]
    assert "clean blue water" in out.intent


def test_brief_load_parses_unbracketed_tastes(workspace: Workspace) -> None:
    (workspace.root / "brief.md").write_text("Tastes: portrait, studio\n")
    out = Brief.load(workspace)
    assert out.tastes == ["portrait", "studio"]


def test_brief_missing_returns_empty(workspace: Workspace) -> None:
    out = Brief.load(workspace)
    assert out.raw == ""
    assert out.tastes == []


# --- Notes --------------------------------------------------------------


def test_notes_short_no_truncation(workspace: Workspace) -> None:
    (workspace.root / "notes.md").write_text("a\nb\nc\n")
    out = Notes.load(workspace)
    assert out.summary == "a\nb\nc\n"
    assert out.truncated is False


def test_notes_long_truncated_correctly(workspace: Workspace) -> None:
    big = "\n".join(f"line {i}" for i in range(100))
    (workspace.root / "notes.md").write_text(big)
    out = Notes.load(workspace)
    assert out.truncated is True
    assert "line 0" in out.summary  # head present
    assert "line 99" in out.summary  # tail present
    assert "lines elided" in out.summary
    head_lines = out.summary.split("... [")[0].splitlines()
    assert len([line for line in head_lines if line.strip()]) == NOTES_HEAD_LINES


def test_notes_summarize_false_returns_raw(workspace: Workspace) -> None:
    big = "\n".join(f"line {i}" for i in range(100))
    (workspace.root / "notes.md").write_text(big)
    out = Notes.load(workspace, summarize=False)
    assert out.summary == big
    assert out.truncated is False


def test_notes_truncation_threshold_boundary(workspace: Workspace) -> None:
    """At exactly the threshold (head+tail), no truncation."""
    lines = [f"l{i}" for i in range(NOTES_HEAD_LINES + NOTES_TAIL_LINES)]
    (workspace.root / "notes.md").write_text("\n".join(lines))
    out = Notes.load(workspace)
    assert out.truncated is False


def test_notes_missing_returns_empty(workspace: Workspace) -> None:
    out = Notes.load(workspace)
    assert out.summary == ""
    assert out.truncated is False


# --- RecentLog ----------------------------------------------------------


def test_recent_log_returns_newest_first(workspace: Workspace) -> None:
    log_path = workspace.root / "log.jsonl"
    log_path.write_text(
        "\n".join(
            json.dumps({"timestamp": f"2026-04-29T10:{i:02d}:00+00:00", "op": f"op_{i}"})
            for i in range(5)
        )
    )
    out = RecentLog.load(workspace)
    assert out[0].op == "op_4"
    assert out[-1].op == "op_0"


def test_recent_log_respects_limit(workspace: Workspace) -> None:
    log_path = workspace.root / "log.jsonl"
    log_path.write_text(
        "\n".join(json.dumps({"timestamp": "t", "op": f"op_{i}"}) for i in range(10))
    )
    out = RecentLog.load(workspace, limit=3)
    assert len(out) == 3


def test_recent_log_handles_partial_last_line(workspace: Workspace) -> None:
    log_path = workspace.root / "log.jsonl"
    log_path.write_text(json.dumps({"timestamp": "t", "op": "good"}) + "\n{not valid json\n")
    out = RecentLog.load(workspace)
    assert len(out) == 1
    assert out[0].op == "good"


def test_recent_log_missing_returns_empty(workspace: Workspace) -> None:
    out = RecentLog.load(workspace)
    assert out == []


def test_recent_log_details_capture_extras(workspace: Workspace) -> None:
    log_path = workspace.root / "log.jsonl"
    log_path.write_text(
        json.dumps({"timestamp": "t", "op": "snapshot", "hash": "abc", "label": "x"})
    )
    out = RecentLog.load(workspace)
    assert out[0].details == {"hash": "abc", "label": "x"}


# --- RecentGaps ---------------------------------------------------------


def test_recent_gaps_v0_3_0_minimal_record(workspace: Workspace) -> None:
    """Minimal 4-field records (v0.3.0) parse with defaults."""
    workspace.vocabulary_gaps_path.parent.mkdir(parents=True, exist_ok=True)
    workspace.vocabulary_gaps_path.write_text(
        json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "image_id": "img",
                "description": "no smoothing primitive",
                "workaround": "skipped",
            }
        )
    )
    out = RecentGaps.load(workspace)
    assert len(out) == 1
    assert out[0].description == "no smoothing primitive"
    assert out[0].intent_category == "uncategorized"
    assert out[0].operations_involved == []


def test_recent_gaps_full_rfc_013_record(workspace: Workspace) -> None:
    workspace.vocabulary_gaps_path.parent.mkdir(parents=True, exist_ok=True)
    workspace.vocabulary_gaps_path.write_text(
        json.dumps(
            {
                "timestamp": "t",
                "image_id": "img",
                "description": "needs gradient warmth",
                "workaround": "wb_warm_subtle",
                "session_id": "abc123",
                "snapshot_hash": "deadbeef" * 8,
                "intent": "warm gradient highlights",
                "intent_category": "tone",
                "missing_capability": "parametric warm gradient",
                "operations_involved": ["temperature"],
                "vocabulary_used": ["wb_warm_subtle"],
                "satisfaction": 0,
                "notes": "approximation only",
            }
        )
    )
    out = RecentGaps.load(workspace)
    assert out[0].session_id == "abc123"
    assert out[0].satisfaction == 0
    assert out[0].operations_involved == ["temperature"]


def test_recent_gaps_missing_returns_empty(workspace: Workspace) -> None:
    out = RecentGaps.load(workspace)
    assert out == []
