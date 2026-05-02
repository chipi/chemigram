"""Integration tests for ``chemigram ingest``."""

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


def test_ingest_creates_workspace(runner: CliRunner, tmp_path: Path, fresh_raw: Path) -> None:
    workspace_root = tmp_path / "ws"
    result = runner.invoke(
        app,
        ["--workspace", str(workspace_root), "ingest", str(fresh_raw)],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    image_id = fresh_raw.stem
    assert (workspace_root / image_id / "objects").is_dir()
    assert (workspace_root / image_id / "refs" / "tags" / "baseline").is_file()


def test_ingest_json_emits_image_id_and_root(
    runner: CliRunner, tmp_path: Path, fresh_raw: Path
) -> None:
    workspace_root = tmp_path / "ws"
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(workspace_root), "ingest", str(fresh_raw)],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["event"] == "result"
    assert payload["status"] == "ok"
    assert payload["image_id"] == fresh_raw.stem
    assert payload["root"].endswith(fresh_raw.stem)
    assert "exif_summary" in payload
    assert "suggested_bindings" in payload


def test_ingest_image_id_override(runner: CliRunner, tmp_path: Path, fresh_raw: Path) -> None:
    workspace_root = tmp_path / "ws"
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(workspace_root),
            "ingest",
            str(fresh_raw),
            "--image-id",
            "my-custom-id",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    assert (workspace_root / "my-custom-id" / "objects").is_dir()


def test_ingest_twice_same_id_state_error(
    runner: CliRunner, tmp_path: Path, fresh_raw: Path
) -> None:
    workspace_root = tmp_path / "ws"
    args = [
        "--workspace",
        str(workspace_root),
        "ingest",
        str(fresh_raw),
        "--image-id",
        "dup",
    ]
    first = runner.invoke(app, args)
    assert first.exit_code == ExitCode.SUCCESS.value
    second = runner.invoke(app, args)
    assert second.exit_code == ExitCode.STATE_ERROR.value
    assert "already exists" in second.stderr or "already exists" in second.stdout


def test_ingest_missing_raw_invalid_args(runner: CliRunner, tmp_path: Path) -> None:
    """Typer's exists=True on the raw_path argument rejects missing files
    with code 2 (Click's INVALID_USAGE; we map to INVALID_INPUT semantically)."""
    result = runner.invoke(
        app,
        ["--workspace", str(tmp_path / "ws"), "ingest", str(tmp_path / "nope.NEF")],
    )
    # Typer returns Click's UsageError which is exit code 2 — same numeric
    # value as our ExitCode.INVALID_INPUT.
    assert result.exit_code == ExitCode.INVALID_INPUT.value
