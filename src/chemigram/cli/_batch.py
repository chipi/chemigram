"""Batch-input helpers for the CLI (B3 / RFC-020 §Q2).

`--stdin` lets a verb read image_ids from stdin and apply itself once
per line, emitting one NDJSON event per image and a final aggregate
exit code (= max across iterations, so any failure surfaces).

Used by ``get-state``, ``apply-primitive``, ``render-preview``, and
``export-final``. Other verbs (mutating multi-step ones, mask
generation, etc.) can opt in later.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator

import typer

from chemigram.cli.exit_codes import ExitCode


def iter_image_ids(stdin: bool, image_id: str | None) -> Iterator[str]:
    """Yield image_ids from stdin (one per line, stripped, skipping blanks)
    when ``stdin`` is set, else yield the single ``image_id``.

    Raises ``typer.BadParameter`` if neither stdin nor an explicit
    ``image_id`` is provided — equivalent to Typer's "missing argument"
    error but raised at our boundary so the writer can format it
    consistently.
    """
    if stdin:
        for raw in sys.stdin:
            line = raw.strip()
            if line:
                yield line
        return
    if image_id is None:
        raise typer.BadParameter("image_id is required (or pass --stdin to read from stdin)")
    yield image_id


def aggregate_exit_code(codes: Iterable[int]) -> int:
    """Return the worst (= max) exit code from the iterable.

    Per RFC-020 §Q2: any single-image failure surfaces in the batch's
    final exit code. ``SUCCESS`` (0) is the default if the iterable is
    empty.
    """
    worst = ExitCode.SUCCESS.value
    for code in codes:
        if code > worst:
            worst = code
    return worst
