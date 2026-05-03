"""Edit / state CLI verbs (issue #54).

Mirrors MCP ``apply_primitive``, ``remove_module``, ``reset``,
``get_state`` (per ADR-033/056). Each verb calls the underlying
:mod:`chemigram.core` API directly (per ADR-071); none of them go
through ``chemigram.mcp.tools.*``.

Mask-bound primitives (``mask_spec`` set on the vocabulary entry) route
through :func:`chemigram.core.helpers.apply_with_drawn_mask`, which
encodes the form into the XMP's ``masks_history`` and patches each
plugin's ``blendop_params`` to bind it.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import typer

from chemigram.cli._batch import aggregate_exit_code, iter_image_ids
from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.helpers import (
    apply_with_drawn_mask,
    current_xmp,
    summarize_state,
)
from chemigram.core.versioning import (
    RefNotFoundError,
    RepoError,
    VersioningError,
    snapshot,
)
from chemigram.core.versioning.ops import reset_to
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import synthesize_xmp

# ---------------------------------------------------------------------------
# get-state (read-only)
# ---------------------------------------------------------------------------


def _do_get_state(ctx: typer.Context, image_id: str) -> int:
    """Per-image core; returns exit code rather than raising. Used both
    by the single-image and ``--stdin`` batch paths."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    try:
        workspace = resolve_workspace_or_fail(ctx, image_id)
    except typer.Exit as exc:
        return int(exc.exit_code)
    xmp = current_xmp(workspace)
    if xmp is None:
        writer.result(
            message="no snapshot yet",
            image_id=image_id,
            head_hash=None,
            entry_count=0,
            enabled_count=0,
            layers_present={"L1": False, "L2": False, "L3": False},
            note="no snapshot yet on this workspace",
        )
        return ExitCode.SUCCESS.value
    summary = summarize_state(xmp)
    writer.result(message=f"state for {image_id}", image_id=image_id, **summary)
    return ExitCode.SUCCESS.value


def get_state(
    ctx: typer.Context,
    image_id: str = typer.Argument(None, help="Image ID (or '-' with --stdin for batch)."),
    stdin: bool = typer.Option(
        False, "--stdin", help="Read image_ids from stdin (one per line); aggregate exit code."
    ),
) -> None:
    """Read-only: summarize the current HEAD XMP."""
    codes = [_do_get_state(ctx, img) for img in iter_image_ids(stdin, image_id)]
    final = aggregate_exit_code(codes)
    if final != ExitCode.SUCCESS.value:
        raise typer.Exit(code=final)


# ---------------------------------------------------------------------------
# apply-primitive
# ---------------------------------------------------------------------------


def _do_apply_primitive(
    ctx: typer.Context,
    image_id: str,
    *,
    vocab_entry: object,
    entry_name: str,
) -> int:
    """Per-image core for apply-primitive; returns exit code."""
    from chemigram.core.vocab import VocabEntry

    assert isinstance(vocab_entry, VocabEntry)
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    try:
        workspace = resolve_workspace_or_fail(ctx, image_id)
    except typer.Exit as exc:
        return int(exc.exit_code)

    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        writer.error(
            "workspace has no baseline snapshot to apply onto",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        return ExitCode.STATE_ERROR.value

    if vocab_entry.mask_spec is not None:
        try:
            new_xmp = apply_with_drawn_mask(
                baseline_xmp, vocab_entry.dtstyle, vocab_entry.mask_spec
            )
        except (ValueError, TypeError) as exc:
            writer.error(str(exc), ExitCode.MASKING_ERROR, entry=entry_name)
            return ExitCode.MASKING_ERROR.value
    else:
        new_xmp = synthesize_xmp(baseline_xmp, [vocab_entry.dtstyle])
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=f"apply: {entry_name}")
    except VersioningError as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        return ExitCode.VERSIONING_ERROR.value

    writer.result(
        message=f"applied {entry_name} to {image_id}",
        image_id=image_id,
        entry=entry_name,
        snapshot_hash=new_hash,
        state_after=summarize_state(new_xmp),
    )
    return ExitCode.SUCCESS.value


def apply_primitive(
    ctx: typer.Context,
    image_id: str = typer.Argument(None, help="Image ID (or '-' with --stdin for batch)."),
    entry: str = typer.Option(..., "--entry", help="Vocabulary entry name."),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Vocabulary pack(s). Defaults to ['starter'].",
    ),
    stdin: bool = typer.Option(
        False,
        "--stdin",
        help="Read image_ids from stdin (one per line); same entry applied to each.",
    ),
) -> None:
    """Apply a vocabulary entry; snapshot the result."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    pack_names = pack if pack else ["starter"]

    try:
        vocabulary = load_packs(pack_names)
    except Exception as exc:
        writer.error(
            f"failed to load packs {pack_names}: {exc}",
            ExitCode.INVALID_INPUT,
            packs=pack_names,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    vocab_entry = vocabulary.lookup_by_name(entry)
    if vocab_entry is None:
        writer.error(
            f"vocabulary entry not found: {entry}",
            ExitCode.NOT_FOUND,
            entry=entry,
            packs=pack_names,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    codes = [
        _do_apply_primitive(
            ctx,
            img,
            vocab_entry=vocab_entry,
            entry_name=entry,
        )
        for img in iter_image_ids(stdin, image_id)
    ]
    final = aggregate_exit_code(codes)
    if final != ExitCode.SUCCESS.value:
        raise typer.Exit(code=final)


# ---------------------------------------------------------------------------
# remove-module
# ---------------------------------------------------------------------------


def remove_module(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    operation: str = typer.Option(
        ...,
        "--operation",
        help="darktable operation name to strip from history (e.g. exposure, channelmixerrgb).",
    ),
) -> None:
    """Strip all history entries for ``operation``; snapshot the result."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        writer.error(
            "workspace has no snapshot to remove from",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value)

    new_history = tuple(p for p in baseline_xmp.history if p.operation != operation)
    if len(new_history) == len(baseline_xmp.history):
        writer.error(
            f"operation {operation!r}: no history entries match",
            ExitCode.NOT_FOUND,
            operation=operation,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    new_xmp = replace(baseline_xmp, history=new_history)
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=f"remove_module: {operation}")
    except VersioningError as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"removed operation {operation} from {image_id}",
        image_id=image_id,
        operation=operation,
        snapshot_hash=new_hash,
        state_after=summarize_state(new_xmp),
    )


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------


def reset(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
) -> None:
    """Rewind the current branch to the workspace's baseline ref (ADR-062)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        baseline_xmp = reset_to(workspace.repo, workspace.baseline_ref)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        writer.error(
            f"baseline ref {workspace.baseline_ref!r} not resolvable: {exc}",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value) from exc

    summary = summarize_state(baseline_xmp)
    writer.result(message=f"reset {image_id} to baseline", image_id=image_id, **summary)
