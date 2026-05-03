"""Layer-binding CLI verb (issue #56).

Mirrors MCP ``bind_layers`` (per ADR-033/056). The MCP tool is
unilateral — there's no ``unbind_layers`` counterpart in the engine
(layer removal is via ``remove-module``). RFC-020 §F amendment in #61
removes the originally-listed ``unbind-layers`` verb.
"""

from __future__ import annotations

from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import default_workspace_root, load_workspace
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.helpers import current_xmp, summarize_state
from chemigram.core.versioning import VersioningError, snapshot
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import synthesize_xmp


def bind_layers(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    l1: str | None = typer.Option(
        None, "--l1", help="L1 vocabulary template name (camera/lens binding)."
    ),
    l2: str | None = typer.Option(
        None, "--l2", help="L2 vocabulary template name (look baseline)."
    ),
    pack: list[str] = typer.Option(
        None, "--pack", "-p", help="Vocabulary pack(s). Defaults to ['starter']."
    ),
) -> None:
    """Apply L1 and/or L2 templates onto the current XMP; snapshot the result.

    With both flags omitted, prints the current state and exits 0
    (matches the MCP tool's no-op behavior).
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    pack_names = pack if pack else ["starter"]

    workspace_root = obj["workspace"] or default_workspace_root()
    workspace = load_workspace(workspace_root, image_id)
    if workspace is None:
        writer.error(
            f"workspace not found: {image_id}",
            ExitCode.NOT_FOUND,
            image_id=image_id,
            workspace_root=str(workspace_root),
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    baseline = current_xmp(workspace)
    if baseline is None:
        writer.error(
            "cannot bind_layers: workspace has no current XMP",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value)

    try:
        vocabulary = load_packs(pack_names)
    except Exception as exc:
        writer.error(
            f"failed to load packs {pack_names}: {exc}",
            ExitCode.INVALID_INPUT,
            packs=pack_names,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    entries = []
    applied: list[str] = []
    for name, layer_label in ((l1, "L1"), (l2, "L2")):
        if name is None:
            continue
        entry = vocabulary.lookup_by_name(name)
        if entry is None:
            writer.error(
                f"vocabulary entry {name!r} for {layer_label} not found",
                ExitCode.NOT_FOUND,
                entry=name,
                layer=layer_label,
                packs=pack_names,
            )
            raise typer.Exit(code=ExitCode.NOT_FOUND.value)
        if entry.layer != layer_label:
            writer.error(
                f"{name!r} is layer {entry.layer}, expected {layer_label}",
                ExitCode.INVALID_INPUT,
                entry=name,
                expected_layer=layer_label,
                actual_layer=entry.layer,
            )
            raise typer.Exit(code=ExitCode.INVALID_INPUT.value)
        entries.append(entry.dtstyle)
        applied.append(name)

    if not entries:
        # No-op path — return the current state summary.
        writer.result(
            message=f"no templates passed; current state for {image_id}",
            image_id=image_id,
            state_after=summarize_state(baseline),
            applied=[],
        )
        return

    new_xmp = synthesize_xmp(baseline, entries)
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label="bind_layers")
    except VersioningError as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"bound {applied} for {image_id}",
        image_id=image_id,
        snapshot_hash=new_hash,
        state_after=summarize_state(new_xmp),
        applied=applied,
    )
