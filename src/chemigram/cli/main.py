"""Chemigram CLI entry point (RFC-020).

Typer root app + global-options callback. Registers individual command
modules from :mod:`chemigram.cli.commands`. Sub-apps for grouped verbs
(``vocab``, ``masks``).
"""

from __future__ import annotations

from pathlib import Path

import typer

from chemigram.cli._context import CliContext
from chemigram.cli.commands import context, edit, lifecycle, status, vocab
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

# Lifecycle
app.command(name="ingest", help="Bootstrap a per-image workspace from a raw file.")(
    lifecycle.ingest
)

# Edit / state
app.command(name="apply-primitive", help="Apply a vocabulary entry; snapshot the result.")(
    edit.apply_primitive
)
app.command(name="remove-module", help="Strip all history entries for an operation.")(
    edit.remove_module
)
app.command(name="reset", help="Rewind the current branch to baseline (ADR-062).")(edit.reset)
app.command(name="get-state", help="Print a summary of the workspace's current XMP.")(
    edit.get_state
)

# Context
app.command(name="read-context", help="Print the agent's first-turn context (RFC-011).")(
    context.read_context
)
app.command(name="log-vocabulary-gap", help="Append a gap record to vocabulary_gaps.jsonl.")(
    context.log_vocabulary_gap
)
# CLI-only direct verbs — propose/confirm in MCP is conversational and
# requires per-process state; the CLI's subprocess shape doesn't fit
# (parallel invocations would race on a shared proposal store).
app.command(
    name="apply-taste-update",
    help="Append directly to a taste file (CLI-only; MCP uses propose/confirm).",
)(context.apply_taste_update)
app.command(
    name="apply-notes-update",
    help="Append directly to per-image notes (CLI-only; MCP uses propose/confirm).",
)(context.apply_notes_update)


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
        help="Describe what would happen without writing any files. (Currently a "
        "no-op for v1.3.0 foundation; verbs that mutate filesystem state will "
        "honor it as they ship in #54..#59.)",
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


if __name__ == "__main__":
    # Allows `python -m chemigram.cli.main` (used by the e2e session test).
    app()
