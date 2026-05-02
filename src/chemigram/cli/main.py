"""Chemigram CLI entry point (RFC-020).

Typer root app + global-options callback. Registers individual command
modules from :mod:`chemigram.cli.commands`. Sub-apps for grouped verbs
(``vocab``, ``masks``).
"""

from __future__ import annotations

from pathlib import Path

import typer

from chemigram.cli._context import CliContext
from chemigram.cli.commands import status, vocab
from chemigram.cli.output import make_writer

app = typer.Typer(
    name="chemigram",
    help="Agent-driven photo editing on darktable. Subprocess adapter "
    "mirroring the MCP tool surface (RFC-020).",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    add_completion=False,
)

app.add_typer(vocab.app, name="vocab", help="Inspect installed vocabulary.")
app.command(
    name="status",
    help="Print runtime diagnostics: chemigram + darktable-cli versions, "
    "configured packs, workspace root, prompt store version, output schema.",
)(status.status)


@app.callback()
def _global_options(
    ctx: typer.Context,
    json: bool = typer.Option(
        False,
        "--json",
        help="Emit newline-delimited JSON to stdout instead of human-readable text.",
    ),
    workspace: Path | None = typer.Option(
        None,
        "--workspace",
        help="Workspace root (defaults to ~/Pictures/Chemigram).",
        envvar="CHEMIGRAM_WORKSPACE",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational events; errors still surface."
    ),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase log verbosity (stackable)."
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Describe what would happen without writing any files.",
    ),
) -> None:
    """Set up the per-invocation context (writer, flags). Runs before any subcommand."""
    obj: CliContext = {
        "json": json,
        "workspace": workspace,
        "quiet": quiet,
        "verbose": verbose,
        "dry_run": dry_run,
        "writer": make_writer(json_mode=json, quiet=quiet, verbose=verbose),
    }
    ctx.obj = obj
