"""Chemigram CLI entry point (RFC-020).

Typer root app + global-options callback. Registers individual command
modules from :mod:`chemigram.cli.commands`. Sub-apps for grouped verbs
(``vocab``, ``masks``).
"""

from __future__ import annotations

from pathlib import Path

import typer

from chemigram.cli._context import CliContext
from chemigram.cli.commands import (
    binding,
    context,
    edit,
    export,
    lifecycle,
    masks,
    render,
    status,
    versioning,
    vocab,
)
from chemigram.cli.output import make_writer

app = typer.Typer(
    name="chemigram",
    help="Agent-driven photo editing on darktable. Subprocess adapter "
    "mirroring the MCP tool surface (RFC-020).",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    # add_completion=True surfaces Typer's --install-completion /
    # --show-completion (bash/zsh/fish/PowerShell). Closes RFC-020 §Q1.
    add_completion=True,
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

# Versioning
app.command(name="snapshot", help="Snapshot the current XMP; return the new content hash.")(
    versioning.snapshot
)
app.command(name="branch", help="Create a branch at HEAD (or --from <ref>).")(versioning.branch)
app.command(name="tag", help="Create an immutable tag at HEAD (or --hash <h>).")(versioning.tag)
app.command(name="checkout", help="Move HEAD to a ref or hash.")(versioning.checkout)
app.command(name="log", help="Print the operation log (newest first).")(versioning.log)
app.command(name="diff", help="Diff two snapshots — added/removed/changed primitives.")(
    versioning.diff
)

# Layer binding (no unbind — MCP doesn't have one either)
app.command(name="bind-layers", help="Apply L1/L2 vocabulary templates onto the current XMP.")(
    binding.bind_layers
)

# Render / export
app.command(name="render-preview", help="Render a snapshot to a JPEG preview.")(
    render.render_preview
)
app.command(name="compare", help="Render two snapshots and stitch them side-by-side.")(
    render.compare
)
app.command(name="export-final", help="High-quality export to the workspace's exports/ dir.")(
    export.export_final
)

# Masks (sub-app)
app.add_typer(masks.app, name="masks", help="Inspect / tag / invalidate raster masks.")

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
    configdir: Path | None = typer.Option(
        None,
        "--configdir",
        help="darktable-cli configdir for renders (must be pre-bootstrapped per ADR-005). "
        "When omitted, a temp dir is created per render — only useful for non-render verbs.",
        envvar="CHEMIGRAM_DT_CONFIGDIR",
    ),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress informational events; errors still surface."
    ),
    verbose: int = typer.Option(
        0, "--verbose", "-v", count=True, help="Increase log verbosity (stackable)."
    ),
) -> None:
    """Set up the per-invocation context (writer, flags). Runs before any subcommand.

    A ``--dry-run`` global flag was prototyped during v1.3.0 development but
    removed before ship: no verb actually checked it, so it was a silent
    no-op (a footgun for users who'd assume their write was suppressed).
    A future RFC will reintroduce ``--dry-run`` once a verb-by-verb
    semantics is decided (does ``ingest --dry-run`` short-circuit before
    EXIF read? before symlink? etc.).
    """
    obj: CliContext = {
        "json": json,
        "workspace": workspace,
        "configdir": configdir,
        "quiet": quiet,
        "verbose": verbose,
        "writer": make_writer(json_mode=json, quiet=quiet, verbose=verbose),
    }
    ctx.obj = obj


if __name__ == "__main__":
    # Allows `python -m chemigram.cli.main` (used by the e2e session test).
    app()
