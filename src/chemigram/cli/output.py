"""Output writer abstraction for the CLI (RFC-020 §C).

Two implementations behind one Protocol. Command modules call the
writer; they never call ``print``, ``sys.stdout``, or ``typer.echo``
directly. This keeps the human/JSON branch isolated and lets the
audit test at ``tests/integration/cli/test_audit_imports.py`` flag
direct-output regressions.

Output schema is versioned independently of package SemVer (same
pattern as prompt versioning per ADR-045). The constant lives here
and is surfaced via ``chemigram status``. ADR-072 (closing at v1.3.0
ship) codifies the bump rules.
"""

from __future__ import annotations

import json
import sys
from typing import Any, Protocol

import typer

from chemigram.cli.exit_codes import ExitCode

OUTPUT_SCHEMA_VERSION = "1.0"
"""Semantic version of the CLI's NDJSON output schema (ADR-072)."""


class OutputWriter(Protocol):
    """How a command emits events, errors, and the final result."""

    def event(self, kind: str, **fields: Any) -> None:
        """Emit a non-final event (progress, intermediate state)."""

    def error(self, message: str, code: ExitCode, **fields: Any) -> None:
        """Emit a terminal error. Goes to stderr in both modes."""

    def result(self, **fields: Any) -> None:
        """Emit the final summary event for a successful invocation."""


# ---------------------------------------------------------------------------
# Human writer
# ---------------------------------------------------------------------------


class HumanWriter:
    """Render to a terminal. Results to stdout, errors to stderr.

    Uses Typer's ``echo`` (which falls back gracefully when stdout
    isn't a TTY). Prefixes: ``✓`` for success, ``⚠`` for warning,
    ``✗`` for error.
    """

    def __init__(self, *, quiet: bool = False, verbose: int = 0) -> None:
        self._quiet = quiet
        self._verbose = verbose

    def event(self, kind: str, **fields: Any) -> None:
        if self._quiet:
            return
        # Verbose-only events are gated by --verbose count.
        threshold = int(fields.pop("_verbose_min", 0))
        if self._verbose < threshold:
            return
        message = fields.pop("message", None) or kind
        details = " ".join(f"{k}={v}" for k, v in fields.items())
        typer.echo(f"  {message}{(' ' + details) if details else ''}")

    def error(self, message: str, code: ExitCode, **fields: Any) -> None:
        prefix = "✗"
        details = " ".join(f"{k}={v}" for k, v in fields.items())
        typer.echo(
            f"{prefix} {message}{(' (' + details + ')') if details else ''}",
            err=True,
        )
        typer.echo(f"  exit code: {code.value} ({code.name})", err=True)

    def result(self, **fields: Any) -> None:
        if self._quiet:
            return
        message = fields.pop("message", "ok")
        typer.echo(f"✓ {message}")
        for k, v in fields.items():
            typer.echo(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# JSON writer (NDJSON)
# ---------------------------------------------------------------------------


class JsonWriter:
    """Newline-delimited JSON to stdout. Errors as NDJSON to stderr.

    The final emitted line on a successful invocation is always a
    ``result`` event with ``status: "ok"``. On failure the final stderr
    line is an ``error`` event with ``status: "error"``. Consumers that
    don't stream can ``splitlines()`` and parse the last line to get a
    summary.
    """

    def __init__(self, *, quiet: bool = False, verbose: int = 0) -> None:
        self._quiet = quiet
        self._verbose = verbose

    def _emit(self, payload: dict[str, Any], *, stream: Any) -> None:
        line = json.dumps(payload, ensure_ascii=False, default=str)
        stream.write(line + "\n")
        stream.flush()

    def event(self, kind: str, **fields: Any) -> None:
        if self._quiet:
            return
        threshold = int(fields.pop("_verbose_min", 0))
        if self._verbose < threshold:
            return
        self._emit(
            {
                "schema_version": OUTPUT_SCHEMA_VERSION,
                "event": kind,
                **fields,
            },
            stream=sys.stdout,
        )

    def error(self, message: str, code: ExitCode, **fields: Any) -> None:
        self._emit(
            {
                "schema_version": OUTPUT_SCHEMA_VERSION,
                "event": "error",
                "status": "error",
                "exit_code": code.value,
                "exit_code_name": code.name,
                "message": message,
                **fields,
            },
            stream=sys.stderr,
        )

    def result(self, **fields: Any) -> None:
        self._emit(
            {
                "schema_version": OUTPUT_SCHEMA_VERSION,
                "event": "result",
                "status": "ok",
                **fields,
            },
            stream=sys.stdout,
        )


def make_writer(*, json_mode: bool, quiet: bool = False, verbose: int = 0) -> OutputWriter:
    """Pick a writer based on the ``--json`` global flag."""
    if json_mode:
        return JsonWriter(quiet=quiet, verbose=verbose)
    return HumanWriter(quiet=quiet, verbose=verbose)
