"""Typed context object passed via Typer's ``ctx.obj``.

Typer's context is ``Any`` by default; this module gives the global
options a typed shape so mypy stays strict across the CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from chemigram.cli.output import OutputWriter


class CliContext(TypedDict):
    """Shape of ``ctx.obj`` after the global-options callback runs."""

    json: bool
    workspace: Path | None
    configdir: Path | None
    quiet: bool
    verbose: int
    writer: OutputWriter
