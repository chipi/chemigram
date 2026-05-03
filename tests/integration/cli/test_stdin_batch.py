"""Integration tests for ``--stdin`` batch mode (B3 / RFC-020 §Q2).

Covers the four verbs that opt in: ``get-state``, ``apply-primitive``,
``render-preview``, ``export-final``. Render/export aren't exercised
end-to-end here because they invoke darktable; their stdin plumbing is
covered by the get-state and apply-primitive cases (same shared helper
in chemigram.cli._batch).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.workspace import init_workspace_root
from chemigram.core.xmp import parse_xmp


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def two_image_workspace_root(tmp_path: Path) -> Path:
    """Workspace root with two image_ids, both with baseline snapshots."""
    from tests.integration.cli.conftest import BASELINE_XMP, TEST_RAW_NAME

    root = tmp_path / "ws_root"
    for image_id in ("img-a", "img-b"):
        image_root = root / image_id
        init_workspace_root(image_root)
        repo = ImageRepo.init(image_root)
        raw_dir = image_root / "raw"
        raw_dir.mkdir(exist_ok=True)
        (raw_dir / TEST_RAW_NAME).touch()
        baseline_xmp = parse_xmp(BASELINE_XMP)
        baseline_hash = snapshot(repo, baseline_xmp, label="baseline")
        tag(repo, "baseline", baseline_hash)
    return root


def test_get_state_stdin_processes_each_image(
    runner: CliRunner, two_image_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(two_image_workspace_root), "get-state", "-", "--stdin"],
        input="img-a\nimg-b\n",
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    image_ids = {p["image_id"] for p in payloads if "image_id" in p}
    assert "img-a" in image_ids and "img-b" in image_ids


def test_get_state_stdin_skips_blank_lines(
    runner: CliRunner, two_image_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(two_image_workspace_root), "get-state", "-", "--stdin"],
        input="\nimg-a\n\n\nimg-b\n",
    )
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    image_ids = {p["image_id"] for p in payloads if "image_id" in p}
    assert image_ids == {"img-a", "img-b"}


def test_get_state_stdin_aggregates_worst_exit_code(
    runner: CliRunner, two_image_workspace_root: Path
) -> None:
    """One missing image_id surfaces NOT_FOUND in the final exit code,
    but the other one still gets processed."""
    result = runner.invoke(
        app,
        ["--json", "--workspace", str(two_image_workspace_root), "get-state", "-", "--stdin"],
        input="img-a\nghost\nimg-b\n",
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
    # Both real images still emitted result events
    success_payloads = [
        json.loads(line) for line in result.stdout.strip().splitlines() if line.strip()
    ]
    image_ids = {p["image_id"] for p in success_payloads if p.get("event") == "result"}
    assert image_ids == {"img-a", "img-b"}


def test_get_state_no_image_id_no_stdin_errors(
    runner: CliRunner, two_image_workspace_root: Path
) -> None:
    """Missing both image_id and --stdin should error cleanly."""
    result = runner.invoke(
        app,
        ["--workspace", str(two_image_workspace_root), "get-state"],
    )
    # Typer's BadParameter exits with code 2 (Click's UsageError default).
    assert result.exit_code != 0


def test_apply_primitive_stdin_applies_to_each(
    runner: CliRunner, two_image_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(two_image_workspace_root),
            "apply-primitive",
            "-",
            "--entry",
            "expo_+0.5",
            "--stdin",
        ],
        input="img-a\nimg-b\n",
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    lines = [line for line in result.stdout.strip().splitlines() if line.strip()]
    results = [json.loads(line) for line in lines if json.loads(line).get("event") == "result"]
    image_ids = {r["image_id"] for r in results}
    assert image_ids == {"img-a", "img-b"}
    # Both should have produced a snapshot_hash
    assert all("snapshot_hash" in r for r in results)


def test_apply_primitive_stdin_aggregates_failures(
    runner: CliRunner, two_image_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(two_image_workspace_root),
            "apply-primitive",
            "-",
            "--entry",
            "expo_+0.5",
            "--stdin",
        ],
        input="img-a\nghost\n",
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
    # img-a should have succeeded
    payloads = [json.loads(line) for line in result.stdout.strip().splitlines() if line.strip()]
    success = [p for p in payloads if p.get("event") == "result"]
    assert any(p["image_id"] == "img-a" for p in success)
