"""Integration tests for ``chemigram cache`` sub-app (v1.9.0)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _build_fake_workspace(tmp_path: Path, *, image_id: str, n_previews: int) -> Path:
    """Build a minimal per-image workspace with N preview JPEG files.

    The cache sub-app keys off the per-image-repo signature
    (objects/ + raw/ both present) so we touch those alongside the
    previews/ directory."""
    img_root = tmp_path / image_id
    (img_root / "objects").mkdir(parents=True)
    (img_root / "raw").mkdir(parents=True)
    previews = img_root / "previews"
    previews.mkdir()
    for i in range(n_previews):
        (previews / f"preview_aaaa{i}_1024.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)
    return tmp_path


def test_cache_list_empty_workspace(runner: CliRunner, tmp_path: Path) -> None:
    """Empty workspace: list returns 0 entries cleanly."""
    result = runner.invoke(app, ["--workspace", str(tmp_path), "cache", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "0 cached preview" in result.stdout


def test_cache_list_finds_previews(runner: CliRunner, tmp_path: Path) -> None:
    """Build a fake workspace with 3 previews; cache list reports 3."""
    _build_fake_workspace(tmp_path, image_id="DSCF0001", n_previews=3)
    result = runner.invoke(app, ["--workspace", str(tmp_path), "cache", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "3 cached preview" in result.stdout


def test_cache_list_json_per_entry_event(runner: CliRunner, tmp_path: Path) -> None:
    """JSON mode emits one cache_entry event per file."""
    _build_fake_workspace(tmp_path, image_id="DSCF0001", n_previews=2)
    result = runner.invoke(app, ["--json", "--workspace", str(tmp_path), "cache", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    entries = [p for p in payloads if p["event"] == "cache_entry"]
    assert len(entries) == 2
    for e in entries:
        assert e["image_id"] == "DSCF0001"
        assert "size_bytes" in e
        assert "modified" in e


def test_cache_size_aggregates_across_images(runner: CliRunner, tmp_path: Path) -> None:
    """Size command sums bytes across multiple images."""
    _build_fake_workspace(tmp_path, image_id="A", n_previews=2)
    _build_fake_workspace(tmp_path, image_id="B", n_previews=3)
    result = runner.invoke(app, ["--json", "--workspace", str(tmp_path), "cache", "size"])
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    per_image = [p for p in payloads if p["event"] == "cache_size"]
    assert len(per_image) == 2
    summary = next(p for p in payloads if p["event"] == "result")
    assert summary["file_count"] == 5  # 2 + 3
    assert summary["total_bytes"] > 0


def test_cache_clear_dry_run_without_yes(runner: CliRunner, tmp_path: Path) -> None:
    """clear without --yes should print what would be removed and not delete."""
    _build_fake_workspace(tmp_path, image_id="A", n_previews=2)
    result = runner.invoke(app, ["--workspace", str(tmp_path), "cache", "clear"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "would remove" in result.stdout
    # Files should still exist
    previews = tmp_path / "A" / "previews"
    assert len(list(previews.glob("*.jpg"))) == 2


def test_cache_clear_with_yes_actually_removes(runner: CliRunner, tmp_path: Path) -> None:
    """clear --yes deletes the cached previews."""
    _build_fake_workspace(tmp_path, image_id="A", n_previews=2)
    result = runner.invoke(app, ["--workspace", str(tmp_path), "cache", "clear", "--yes"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    assert "removed 2" in result.stdout
    previews = tmp_path / "A" / "previews"
    assert len(list(previews.glob("*.jpg"))) == 0
    # The previews/ directory itself should remain
    assert previews.is_dir()


def test_cache_list_image_filter(runner: CliRunner, tmp_path: Path) -> None:
    """--image filter restricts to one image_id."""
    _build_fake_workspace(tmp_path, image_id="A", n_previews=2)
    _build_fake_workspace(tmp_path, image_id="B", n_previews=3)
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(tmp_path), "cache", "list", "--image", "A"],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    entries = [p for p in payloads if p["event"] == "cache_entry"]
    assert len(entries) == 2
    assert all(e["image_id"] == "A" for e in entries)


def test_cache_list_since_filter_rejects_bad_format(runner: CliRunner, tmp_path: Path) -> None:
    """--since with an unrecognized format returns INVALID_INPUT."""
    _build_fake_workspace(tmp_path, image_id="A", n_previews=1)
    result = runner.invoke(
        app, ["--workspace", str(tmp_path), "cache", "list", "--since", "yesterday"]
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value
