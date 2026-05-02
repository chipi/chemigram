"""Integration tests for the CLI bind-layers verb (#56)."""

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


def test_bind_layers_with_no_flags_returns_current_state(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """The MCP tool returns the current state when neither template is passed.

    The CLI mirrors that behavior — exits 0 with applied=[] and a state summary.
    """
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "bind-layers",
            "test-image",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "ok"
    assert payload["applied"] == []
    assert "state_after" in payload


def test_bind_layers_with_l2_template(runner: CliRunner, cli_workspace_root: Path) -> None:
    """The starter pack ships `look_neutral` at L2."""
    result = runner.invoke(
        app,
        [
            "--json",
            "--workspace",
            str(cli_workspace_root),
            "bind-layers",
            "test-image",
            "--l2",
            "look_neutral",
        ],
    )
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["applied"] == ["look_neutral"]
    assert payload["snapshot_hash"]


def test_bind_layers_unknown_entry_not_found(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "bind-layers",
            "test-image",
            "--l2",
            "no_such_l2_template",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value


def test_bind_layers_layer_mismatch_invalid_input(
    runner: CliRunner, cli_workspace_root: Path
) -> None:
    """Pass an L3 entry to --l2 → INVALID_INPUT (layer mismatch)."""
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "bind-layers",
            "test-image",
            "--l2",
            "expo_+0.5",  # this is L3
        ],
    )
    assert result.exit_code == ExitCode.INVALID_INPUT.value


def test_bind_layers_unknown_image(runner: CliRunner, cli_workspace_root: Path) -> None:
    result = runner.invoke(
        app,
        [
            "--workspace",
            str(cli_workspace_root),
            "bind-layers",
            "no-image",
            "--l2",
            "look_neutral",
        ],
    )
    assert result.exit_code == ExitCode.NOT_FOUND.value
