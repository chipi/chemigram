"""Edit / state CLI verbs (issue #54).

Mirrors MCP ``apply_primitive``, ``remove_module``, ``reset``,
``get_state`` (per ADR-033/056). Each verb calls the underlying
:mod:`chemigram.core` API directly (per ADR-071); none of them go
through ``chemigram.mcp.tools.*``.

Mask-override semantics for raster-mask-bound primitives are honored
(materialization runs through the masking provider). For v1.3.0
foundation, raster-mask paths route via the same
``chemigram.mcp.tools._masks_apply.materialize_mask_for_dt`` helper
the MCP server uses; that helper lives in mcp/ today and is genuine
shared infrastructure (a future refactor lifts it to core).
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.versioning import (
    MaskNotFoundError,
    RefNotFoundError,
    RepoError,
    VersioningError,
    snapshot,
)
from chemigram.core.versioning.ops import reset_to
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import synthesize_xmp

# Pure helpers — same shape both adapters need; pragmatic shared import
# until they move to core.
from chemigram.mcp._state import current_xmp, summarize_state

# ---------------------------------------------------------------------------
# get-state (read-only)
# ---------------------------------------------------------------------------


def get_state(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
) -> None:
    """Read-only: summarize the current HEAD XMP."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
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
        return

    summary = summarize_state(xmp)
    writer.result(message=f"state for {image_id}", image_id=image_id, **summary)


# ---------------------------------------------------------------------------
# apply-primitive
# ---------------------------------------------------------------------------


def apply_primitive(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    entry: str = typer.Option(..., "--entry", help="Vocabulary entry name."),
    mask_override: str | None = typer.Option(
        None,
        "--mask-override",
        help="Raster-mask-bound primitives: registered mask name to use instead of entry.mask_ref.",
    ),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Vocabulary pack(s). Defaults to ['starter'].",
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

    workspace = resolve_workspace_or_fail(ctx, image_id)

    if vocab_entry.mask_kind == "raster":
        target_name = mask_override or vocab_entry.mask_ref
        if target_name is None:
            writer.error(
                f"primitive {entry!r} is raster-mask-bound but no mask_ref or --mask-override set",
                ExitCode.INVALID_INPUT,
                entry=entry,
            )
            raise typer.Exit(code=ExitCode.INVALID_INPUT.value)
        try:
            from chemigram.mcp.tools._masks_apply import materialize_mask_for_dt

            materialize_mask_for_dt(workspace, target_name)
        except MaskNotFoundError as exc:
            # Mirror the MCP tool: a missing mask is NOT_FOUND, not
            # MASKING_ERROR (which is reserved for provider failures).
            writer.error(str(exc), ExitCode.NOT_FOUND, mask=target_name)
            raise typer.Exit(code=ExitCode.NOT_FOUND.value) from exc
        except Exception as exc:
            writer.error(
                f"mask materialization failed: {exc}",
                ExitCode.MASKING_ERROR,
                mask=target_name,
            )
            raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc
    elif mask_override is not None:
        writer.error(
            f"primitive {entry!r} (mask_kind={vocab_entry.mask_kind!r}) "
            "doesn't accept --mask-override",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        writer.error(
            "workspace has no baseline snapshot to apply onto",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value)

    new_xmp = synthesize_xmp(baseline_xmp, [vocab_entry.dtstyle])
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=f"apply: {entry}")
    except VersioningError as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"applied {entry} to {image_id}",
        image_id=image_id,
        entry=entry,
        snapshot_hash=new_hash,
        state_after=summarize_state(new_xmp),
    )


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
