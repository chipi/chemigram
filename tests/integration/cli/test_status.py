"""Integration tests for ``chemigram status``.

`status` is a diagnostic — it ALWAYS exits 0 and reports missing
components as fields + ``warnings`` entries. Scripts that need a hard
check for darktable can branch on ``payload["darktable_cli_path"] is
None`` in the JSON output. Erroring out would defeat the discoverability
use case (you can't ask "is darktable installed?" if the answer is to
fail when it isn't). Tested in both directions — present and absent.
"""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app
from chemigram.cli.output import OUTPUT_SCHEMA_VERSION


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_status_always_succeeds(runner: CliRunner) -> None:
    """Whether or not darktable is installed, status exits 0."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr


def test_status_human_output_contains_all_fields(runner: CliRunner) -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == ExitCode.SUCCESS.value
    out = result.stdout
    for key in (
        "chemigram_version",
        "darktable_cli_path",
        "darktable_cli_version",
        "workspace_root",
        "configured_packs",
        "prompt_store_active",
        "output_schema_version",
    ):
        assert key in out, f"missing {key} in status human output"


def test_status_json_output_one_summary_line(runner: CliRunner) -> None:
    """Without warnings, --json status emits exactly one NDJSON line.

    When darktable is missing or another component is misconfigured,
    additional `event: warning` lines precede the summary; the summary
    is always last. This test runs whichever path the runner is on
    (with or without darktable).
    """
    result = runner.invoke(app, ["--json", "status"])
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines
    payloads = [json.loads(line) for line in lines]
    summary = payloads[-1]
    assert summary["event"] == "result"
    assert summary["status"] == "ok"
    assert summary["schema_version"] == OUTPUT_SCHEMA_VERSION
    for key in (
        "chemigram_version",
        "darktable_cli_path",
        "darktable_cli_version",
        "workspace_root",
        "configured_packs",
        "prompt_store_active",
        "output_schema_version",
        "warnings",
    ):
        assert key in summary, f"missing {key} in status JSON"
    assert isinstance(summary["warnings"], list)


def test_status_reports_darktable_absent_in_fields(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When darktable-cli is missing, status still exits 0 and reports
    the absence in ``darktable_cli_path: null`` plus a ``warnings`` entry.
    """
    monkeypatch.setenv("DARKTABLE_CLI", "/nonexistent/darktable-cli")
    monkeypatch.setenv("PATH", "")
    result = runner.invoke(app, ["--json", "status"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    summary = payloads[-1]
    assert summary["event"] == "result"
    assert summary["darktable_cli_path"] is None
    assert summary["darktable_cli_version"] is None
    assert any("darktable-cli not found" in w for w in summary["warnings"])


def test_status_human_warns_when_darktable_absent(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Human mode emits a warning event before the result summary."""
    monkeypatch.setenv("DARKTABLE_CLI", "/nonexistent/darktable-cli")
    monkeypatch.setenv("PATH", "")
    result = runner.invoke(app, ["status"])
    assert result.exit_code == ExitCode.SUCCESS.value
    assert "darktable-cli not found" in result.stdout
