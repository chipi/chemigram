"""Integration tests for ``chemigram status``."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app
from chemigram.cli.output import OUTPUT_SCHEMA_VERSION


@pytest.fixture
def runner() -> CliRunner:
    # Newer Click splits stderr from stdout by default — no mix_stderr kwarg needed.
    return CliRunner()


def test_status_human_output(runner: CliRunner) -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    out = result.stdout
    assert "chemigram_version" in out
    assert "darktable_cli_version" in out
    assert "configured_packs" in out
    assert "prompt_store_active" in out
    assert "output_schema_version" in out


def test_status_json_output_one_summary_line(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "status"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "result"
    assert payload["status"] == "ok"
    assert payload["schema_version"] == OUTPUT_SCHEMA_VERSION
    # All six fields per RFC-020 §H present.
    for key in (
        "chemigram_version",
        "darktable_cli_path",
        "darktable_cli_version",
        "workspace_root",
        "configured_packs",
        "prompt_store_active",
        "output_schema_version",
    ):
        assert key in payload, f"missing {key} in status JSON"


def test_status_exits_six_when_darktable_missing(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``DARKTABLE_CLI=/nonexistent`` (and PATH stripped) exits 6."""
    monkeypatch.setenv("DARKTABLE_CLI", "/nonexistent/darktable-cli")
    monkeypatch.setenv("PATH", "")
    result = runner.invoke(app, ["status"])
    assert result.exit_code == ExitCode.DARKTABLE_ERROR.value
    assert "darktable-cli" in result.stderr


def test_status_json_error_when_darktable_missing(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DARKTABLE_CLI", "/nonexistent/darktable-cli")
    monkeypatch.setenv("PATH", "")
    result = runner.invoke(app, ["--json", "status"])
    assert result.exit_code == ExitCode.DARKTABLE_ERROR.value
    err_lines = [line for line in result.stderr.splitlines() if line.strip()]
    assert err_lines
    payload = json.loads(err_lines[-1])
    assert payload["event"] == "error"
    assert payload["status"] == "error"
    assert payload["exit_code"] == ExitCode.DARKTABLE_ERROR.value
    assert payload["exit_code_name"] == "DARKTABLE_ERROR"
