"""Shape tests for render-preview / compare / export-final.

These don't invoke real darktable (that's the e2e tier — see
``tests/e2e/test_cli_session.py``). They check argument validation,
error mapping for bad refs/hashes, and the NOT_FOUND path for missing
image_id. Real-bytes assertions live in the e2e suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ----- render-preview ---------------------------------------------------


def test_render_preview_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(cli_workspace_root), "render-preview", "no-image"]
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_render_preview_unknown_ref_versioning_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """Unknown ref → VERSIONING_ERROR (mirrors MCP)."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "render-preview",
            "test-image",
            "--ref",
            "no-such-ref",
        ],
    )
    assert result.exit_code == ExitCode.VERSIONING_ERROR.value


# ----- compare ----------------------------------------------------------


def test_compare_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "compare",
            "no-image",
            "0" * 64,
            "1" * 64,
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_compare_unknown_first_hash_versioning_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "compare",
            "test-image",
            "0" * 64,
            "1" * 64,
        ],
    )
    assert result.exit_code == ExitCode.VERSIONING_ERROR.value


# ----- export-final -----------------------------------------------------


def test_export_final_invalid_format(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "export-final",
            "test-image",
            "--format",
            "tiff",
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


def test_export_final_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app, ["--workspace", str(cli_workspace_root), "export-final", "no-image"]
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_export_final_unknown_ref_versioning_error(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "export-final",
            "test-image",
            "--ref",
            "no-such-ref",
        ],
    )
    assert result.exit_code == ExitCode.VERSIONING_ERROR.value
