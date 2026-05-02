"""Unit tests for ``chemigram.cli.output``: HumanWriter + JsonWriter.

Both writers go through stdout/stderr; ``capsys`` captures the streams.
The Human path uses ``typer.echo`` which writes to ``stdout`` (or
``stderr`` when ``err=True``); JsonWriter writes via the ``sys`` module.
"""

from __future__ import annotations

import json

import pytest

from chemigram.cli.exit_codes import ExitCode
from chemigram.cli.output import (
    OUTPUT_SCHEMA_VERSION,
    HumanWriter,
    JsonWriter,
    make_writer,
)

# ----- HumanWriter --------------------------------------------------------


def test_human_writer_event_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    HumanWriter().event("did_something", message="hello", count=3)
    out = capsys.readouterr().out
    assert "hello" in out
    assert "count=3" in out


def test_human_writer_quiet_suppresses_events(capsys: pytest.CaptureFixture[str]) -> None:
    HumanWriter(quiet=True).event("noisy", message="should not appear")
    out = capsys.readouterr().out
    assert out == ""


def test_human_writer_error_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    HumanWriter().error("boom", ExitCode.NOT_FOUND, what="image_x")
    captured = capsys.readouterr()
    assert "boom" in captured.err
    assert "NOT_FOUND" in captured.err
    assert "what=image_x" in captured.err
    assert captured.out == ""


def test_human_writer_result_to_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    HumanWriter().result(message="done", count=5)
    out = capsys.readouterr().out
    assert "done" in out
    assert "count: 5" in out


def test_human_writer_verbose_threshold_gates_events(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Events tagged ``_verbose_min=2`` only appear at -vv or higher."""
    w = HumanWriter(verbose=1)
    w.event("debug", message="should hide", _verbose_min=2)
    assert capsys.readouterr().out == ""

    w = HumanWriter(verbose=2)
    w.event("debug", message="should show", _verbose_min=2)
    assert "should show" in capsys.readouterr().out


# ----- JsonWriter ---------------------------------------------------------


def test_json_writer_event_emits_one_ndjson_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    JsonWriter().event("xmp_change", key="exposure", before=0.0, after=0.5)
    out = capsys.readouterr().out.strip().splitlines()
    assert len(out) == 1
    payload = json.loads(out[0])
    assert payload["event"] == "xmp_change"
    assert payload["key"] == "exposure"
    assert payload["before"] == 0.0
    assert payload["after"] == 0.5
    assert payload["schema_version"] == OUTPUT_SCHEMA_VERSION


def test_json_writer_error_to_stderr_with_exit_code_fields(
    capsys: pytest.CaptureFixture[str],
) -> None:
    JsonWriter().error("boom", ExitCode.DARKTABLE_ERROR, hint="not on PATH")
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err.strip())
    assert payload["event"] == "error"
    assert payload["status"] == "error"
    assert payload["exit_code"] == ExitCode.DARKTABLE_ERROR.value
    assert payload["exit_code_name"] == "DARKTABLE_ERROR"
    assert payload["hint"] == "not on PATH"


def test_json_writer_result_is_summary_with_status_ok(
    capsys: pytest.CaptureFixture[str],
) -> None:
    JsonWriter().result(message="status", chemigram_version="1.2.0")
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["event"] == "result"
    assert payload["status"] == "ok"
    assert payload["chemigram_version"] == "1.2.0"


def test_json_writer_quiet_suppresses_events_but_not_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    w = JsonWriter(quiet=True)
    w.event("hidden")
    w.error("loud", ExitCode.INVALID_INPUT)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err  # error still emitted


# ----- make_writer --------------------------------------------------------


def test_make_writer_picks_json_when_flag_set() -> None:
    assert isinstance(make_writer(json_mode=True), JsonWriter)


def test_make_writer_picks_human_when_flag_unset() -> None:
    assert isinstance(make_writer(json_mode=False), HumanWriter)
