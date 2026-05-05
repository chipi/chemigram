"""Integration tests for ``chemigram vocab list / show``."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.main import app


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


# ----- vocab list ----------------------------------------------------------


def test_vocab_list_returns_starter_entries(runner: CliRunner) -> None:
    """Starter pack ships 2 entries post-v1.6.0: ``wb_warm_subtle`` and
    ``look_neutral``. The discrete ``expo_+0.5`` / ``expo_-0.5`` entries
    were removed in favor of the parameterized ``exposure`` entry that
    lives in ``expressive-baseline`` (RFC-021)."""
    result = runner.invoke(app, ["vocab", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    out = result.stdout
    assert "wb_warm_subtle" in out
    assert "look_neutral" in out
    assert "2 entries" in out


def test_vocab_list_json_emits_one_line_per_entry_plus_summary(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "vocab", "list"])
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    payloads = [json.loads(line) for line in lines]
    events = [p for p in payloads if p["event"] == "vocabulary_entry"]
    summaries = [p for p in payloads if p["event"] == "result"]
    assert len(events) == 2  # post-v1.6.0 starter (RFC-021)
    assert len(summaries) == 1
    assert summaries[0]["count"] == 2
    assert summaries[0]["status"] == "ok"
    # Summary is the last line (per RFC-020 §C convention).
    assert payloads[-1]["event"] == "result"


def test_vocab_list_layer_filter(runner: CliRunner) -> None:
    """``--layer L2`` should narrow to just the L2 entries (1 in starter)."""
    result = runner.invoke(app, ["--json", "vocab", "list", "--layer", "L2"])
    assert result.exit_code == ExitCode.SUCCESS.value
    payloads = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    entries = [p for p in payloads if p["event"] == "vocabulary_entry"]
    assert all(e["layer"] == "L2" for e in entries)
    assert len(entries) >= 1


# ----- vocab show ---------------------------------------------------------


def test_vocab_show_returns_entry_fields(runner: CliRunner) -> None:
    result = runner.invoke(app, ["vocab", "show", "wb_warm_subtle"])
    assert result.exit_code == ExitCode.SUCCESS.value, result.stdout + result.stderr
    out = result.stdout
    assert "wb_warm_subtle" in out
    assert ".dtstyle" in out
    assert "L3" in out


def test_vocab_show_json_returns_full_record(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "vocab", "show", "wb_warm_subtle"])
    assert result.exit_code == ExitCode.SUCCESS.value
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["event"] == "result"
    assert payload["name"] == "wb_warm_subtle"
    assert payload["layer"] == "L3"
    assert payload["path"].endswith(".dtstyle")
    assert "modversions" in payload


def test_vocab_show_unknown_entry_exits_three(runner: CliRunner) -> None:
    result = runner.invoke(app, ["vocab", "show", "no_such_entry_exists"])
    assert result.exit_code == ExitCode.NOT_FOUND.value
    assert "not found" in result.stderr.lower()


def test_vocab_show_unknown_json_emits_error_event(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--json", "vocab", "show", "no_such_entry"])
    assert result.exit_code == ExitCode.NOT_FOUND.value
    err_lines = [line for line in result.stderr.splitlines() if line.strip()]
    payload = json.loads(err_lines[-1])
    assert payload["event"] == "error"
    assert payload["status"] == "error"
    assert payload["exit_code"] == ExitCode.NOT_FOUND.value
