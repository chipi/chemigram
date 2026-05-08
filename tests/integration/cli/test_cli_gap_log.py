"""Integration tests for ``chemigram gap-log {list,rank,show,clear}``."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.commands.gap_log import (
    _aggregation_key,
    _iter_image_ids,
    _parse_since,
)
from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app
from chemigram.core.context import GapEntry


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _write_gap(workspace_root: Path, image_id: str, **fields) -> None:
    """Append one gap record to <root>/<image_id>/vocabulary_gaps.jsonl."""
    image_root = workspace_root / image_id
    # Create the per-image-repo signature so _iter_image_ids picks it up.
    (image_root / "objects").mkdir(parents=True, exist_ok=True)
    (image_root / "raw").mkdir(parents=True, exist_ok=True)
    path = image_root / "vocabulary_gaps.jsonl"
    record = {"image_id": image_id, **fields}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# ---------------------------------------------------------------------------
# Helpers — pure-function unit tests embedded in the integration test file
# (the helpers are simple enough that a separate unit file isn't worth it)
# ---------------------------------------------------------------------------


def test_parse_since_relative_days() -> None:
    result = _parse_since("7d")
    assert result is not None
    assert (datetime.now(UTC) - result).days == 7


def test_parse_since_relative_hours() -> None:
    result = _parse_since("24h")
    assert result is not None
    delta = datetime.now(UTC) - result
    assert 23 * 3600 <= delta.total_seconds() <= 25 * 3600


def test_parse_since_iso_date() -> None:
    result = _parse_since("2026-05-01")
    assert result is not None
    assert result.year == 2026 and result.month == 5 and result.day == 1


def test_parse_since_iso_datetime_z() -> None:
    result = _parse_since("2026-05-01T12:00:00Z")
    assert result is not None
    assert result.tzinfo is not None
    assert result.hour == 12


def test_parse_since_invalid_raises() -> None:
    import typer

    with pytest.raises(typer.BadParameter):
        _parse_since("not-a-date")


def test_parse_since_none_returns_none() -> None:
    assert _parse_since(None) is None


def test_aggregation_key_normalizes() -> None:
    g1 = GapEntry(
        timestamp="t",
        image_id="i",
        description="  Wanted dehaze  ",
        missing_capability="hazeremoval",
    )
    g2 = GapEntry(
        timestamp="t2",
        image_id="i2",
        description="wanted dehaze",
        missing_capability="HAZEREMOVAL",
    )
    assert _aggregation_key(g1) == _aggregation_key(g2)


def test_iter_image_ids_finds_image_root(tmp_path: Path) -> None:
    (tmp_path / "img1" / "objects").mkdir(parents=True)
    (tmp_path / "img1" / "raw").mkdir()
    (tmp_path / "img2" / "objects").mkdir(parents=True)
    (tmp_path / "img2" / "raw").mkdir()
    (tmp_path / "not-an-image").mkdir()  # missing objects/raw
    assert _iter_image_ids(tmp_path) == ["img1", "img2"]


def test_iter_image_ids_empty_workspace(tmp_path: Path) -> None:
    assert _iter_image_ids(tmp_path) == []


def test_iter_image_ids_missing_root() -> None:
    assert _iter_image_ids(Path("/does/not/exist")) == []


# ---------------------------------------------------------------------------
# gap-log list
# ---------------------------------------------------------------------------


def test_list_no_gaps(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "0 gap(s)" in result.stdout


def test_list_returns_all_gaps_across_images(runner: CliRunner, tmp_path: Path) -> None:
    _write_gap(
        tmp_path,
        "img1",
        timestamp="2026-05-01T10:00:00Z",
        description="dehaze missing",
        missing_capability="hazeremoval",
    )
    _write_gap(
        tmp_path,
        "img2",
        timestamp="2026-05-02T10:00:00Z",
        description="lens correction missing",
        missing_capability="lens",
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "dehaze missing" in result.stdout
    assert "lens correction missing" in result.stdout
    assert "2 gap(s)" in result.stdout
    assert "2 image(s)" in result.stdout


def test_list_image_filter(runner: CliRunner, tmp_path: Path) -> None:
    _write_gap(tmp_path, "img1", timestamp="2026-05-01T10:00:00Z", description="a-only")
    _write_gap(tmp_path, "img2", timestamp="2026-05-02T10:00:00Z", description="b-only")
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "gap-log", "list", "--image", "img1"]
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "1 gap(s)" in result.stdout
    assert "a-only" in result.stdout
    assert "b-only" not in result.stdout


def test_list_module_filter(runner: CliRunner, tmp_path: Path) -> None:
    _write_gap(
        tmp_path,
        "img1",
        timestamp="2026-05-01T10:00:00Z",
        description="dehaze missing",
        missing_capability="hazeremoval",
    )
    _write_gap(
        tmp_path,
        "img2",
        timestamp="2026-05-02T10:00:00Z",
        description="lens correction missing",
        missing_capability="lens",
    )
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "gap-log", "list", "--module", "lens"]
    )
    assert "1 gap(s)" in result.stdout
    assert "lens correction missing" in result.stdout
    assert "dehaze missing" not in result.stdout


def test_list_since_relative_filters_old(runner: CliRunner, tmp_path: Path) -> None:
    """Use a far-past timestamp; --since 1d should filter it out."""
    _write_gap(tmp_path, "img1", timestamp="2020-01-01T00:00:00Z", description="old")
    _write_gap(
        tmp_path,
        "img2",
        timestamp=datetime.now(UTC).isoformat(),
        description="recent",
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "list", "--since", "1d"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "1 gap(s)" in result.stdout
    assert "recent" in result.stdout


def test_list_since_invalid_format_errors(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "gap-log", "list", "--since", "not-a-date"]
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


# ---------------------------------------------------------------------------
# gap-log rank
# ---------------------------------------------------------------------------


def test_rank_aggregates_by_description(runner: CliRunner, tmp_path: Path) -> None:
    """Three gaps with the same description = one ranked row, count=3."""
    for i in range(3):
        _write_gap(
            tmp_path,
            f"img{i}",
            timestamp=f"2026-05-0{i + 1}T10:00:00Z",
            description="wanted dehaze",
            missing_capability="hazeremoval",
        )
    _write_gap(
        tmp_path,
        "imgX",
        timestamp="2026-05-04T10:00:00Z",
        description="wanted lens correction",
        missing_capability="lens",
    )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "rank"])
    assert result.exit_code == ExitCode.SUCCESS.value
    # 2 unique patterns, 4 total
    assert "2 unique gap pattern(s)" in result.stdout
    assert "total_gaps: 4" in result.stdout
    # The dehaze row should be ranked first (count 3)
    assert "wanted dehaze" in result.stdout


def test_rank_top_limit(runner: CliRunner, tmp_path: Path) -> None:
    for n in range(5):
        _write_gap(
            tmp_path,
            f"img{n}",
            timestamp=f"2026-05-0{n + 1}T10:00:00Z",
            description=f"gap-{n}",
        )
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "rank", "--top", "2"])
    # 5 unique patterns total; top=2 limits the displayed rows.
    assert "2 unique gap pattern(s) (top 2)" in result.stdout
    assert "total_gaps: 5" in result.stdout


# ---------------------------------------------------------------------------
# gap-log show
# ---------------------------------------------------------------------------


def test_show_returns_chronological(runner: CliRunner, tmp_path: Path) -> None:
    _write_gap(tmp_path, "img1", timestamp="2026-05-02T10:00:00Z", description="second")
    _write_gap(tmp_path, "img1", timestamp="2026-05-01T10:00:00Z", description="first")
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "show", "img1"])
    assert result.exit_code == ExitCode.SUCCESS.value
    # "first" should appear before "second" in stdout (oldest first)
    out = result.stdout
    assert out.find("first") < out.find("second"), out


def test_show_missing_image(runner: CliRunner, tmp_path: Path) -> None:
    """No gap log file = 0 gaps + a warning, no error."""
    (tmp_path / "no-gaps" / "objects").mkdir(parents=True)
    (tmp_path / "no-gaps" / "raw").mkdir()
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "show", "no-gaps"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "0 gaps" in result.stdout


# ---------------------------------------------------------------------------
# gap-log clear
# ---------------------------------------------------------------------------


def test_clear_with_yes_deletes_file(runner: CliRunner, tmp_path: Path) -> None:
    _write_gap(tmp_path, "img1", timestamp="2026-05-01T10:00:00Z", description="x")
    path = tmp_path / "img1" / "vocabulary_gaps.jsonl"
    assert path.exists()
    result = runner.invoke(app, ["--workspace", str(tmp_path), "gap-log", "clear", "img1", "--yes"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "cleared 1 gap(s)" in result.stdout
    assert not path.exists()


def test_clear_with_n_confirmation_keeps_file(runner: CliRunner, tmp_path: Path) -> None:
    _write_gap(tmp_path, "img1", timestamp="2026-05-01T10:00:00Z", description="x")
    path = tmp_path / "img1" / "vocabulary_gaps.jsonl"
    result = runner.invoke(
        app,
        ["--workspace", str(tmp_path), "gap-log", "clear", "img1"],
        input="n\n",
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "cancelled" in result.stdout
    assert path.exists(), "user said no — file must be preserved"


def test_clear_missing_image(runner: CliRunner, tmp_path: Path) -> None:
    (tmp_path / "no-gaps" / "objects").mkdir(parents=True)
    (tmp_path / "no-gaps" / "raw").mkdir()
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "gap-log", "clear", "no-gaps", "--yes"]
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "nothing to clear" in result.stdout
