"""Vocabulary + edit tools (batch 1 of Slice 3).

Wraps the v0.1.0/v0.2.0 engine into MCP-callable tools:

- ``list_vocabulary`` — wraps :meth:`VocabularyIndex.list_all`
- ``get_state`` — current ``state_after`` summary for an image
- ``apply_primitive`` — synthesize a vocabulary entry, snapshot
- ``remove_module`` — strip entries by operation, snapshot
- ``reset`` — rewind the workspace's current branch to the baseline ref (per ADR-062)

All tools follow the RFC-010 contract: structured ``ToolResult`` returns,
``ErrorCode`` taxonomy, no exceptions across the MCP boundary.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from chemigram.core.helpers import current_xmp, summarize_state
from chemigram.core.versioning import RefNotFoundError, RepoError
from chemigram.core.versioning.ops import VersioningError, reset_to, snapshot
from chemigram.core.vocab import VocabEntry
from chemigram.core.xmp import synthesize_xmp
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
)
from chemigram.mcp.registry import ToolContext, register_tool


def _serialize_entry(e: VocabEntry) -> dict[str, Any]:
    return {
        "name": e.name,
        "layer": e.layer,
        "subtype": e.subtype,
        "description": e.description,
        "tags": list(e.tags),
        "touches": list(e.touches),
        "mask_spec": e.mask_spec,
        "global_variant": e.global_variant,
    }


# --- list_vocabulary ----------------------------------------------------


async def _list_vocabulary(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[list[dict[str, Any]]]:
    layer = args.get("layer")
    tags = args.get("tags")
    if layer is not None and layer not in ("L1", "L2", "L3"):
        return ToolResult.fail(
            error_invalid_input(f"layer must be L1/L2/L3, got {layer!r}", got=layer)
        )
    entries = ctx.vocabulary.list_all(layer=layer, tags=tags)
    return ToolResult.ok([_serialize_entry(e) for e in entries])


register_tool(
    name="list_vocabulary",
    description=(
        "List available .dtstyle primitives. Optional layer filter (L1/L2/L3) "
        "and tags filter (OR — any tag in the list matches)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "layer": {"type": "string", "enum": ["L1", "L2", "L3"]},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    },
    handler=_list_vocabulary,
)


# --- get_state ----------------------------------------------------------


async def _get_state(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    xmp = current_xmp(workspace)
    if xmp is None:
        # Fresh workspace, no snapshot yet — return baseline-ish empty summary.
        return ToolResult.ok(
            {
                "head_hash": None,
                "entry_count": 0,
                "enabled_count": 0,
                "layers_present": {"L1": False, "L2": False, "L3": False},
                "note": "no snapshot yet on this workspace",
            }
        )
    return ToolResult.ok(summarize_state(xmp))


register_tool(
    name="get_state",
    description="Return the current XMP state summary for an image.",
    input_schema={
        "type": "object",
        "properties": {"image_id": {"type": "string"}},
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_get_state,
)


# --- apply_primitive ----------------------------------------------------


async def _apply_primitive(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    primitive_name = args["primitive_name"]

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    entry = ctx.vocabulary.lookup_by_name(primitive_name)
    if entry is None:
        return ToolResult.fail(error_not_found(f"primitive {primitive_name!r}"))

    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message="workspace has no baseline snapshot to apply onto",
                recoverable=True,
            )
        )

    if entry.mask_spec is not None:
        from chemigram.core.helpers import apply_with_drawn_mask

        try:
            new_xmp = apply_with_drawn_mask(baseline_xmp, entry.dtstyle, entry.mask_spec)
        except (ValueError, TypeError) as exc:
            return ToolResult.fail(ToolError(code=ErrorCode.MASKING_ERROR, message=str(exc)))
    else:
        new_xmp = synthesize_xmp(baseline_xmp, [entry.dtstyle])
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=f"apply: {primitive_name}")
    except VersioningError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc)))

    return ToolResult.ok(
        {
            "state_after": summarize_state(new_xmp),
            "snapshot_hash": new_hash,
        }
    )


register_tool(
    name="apply_primitive",
    description=(
        "Apply a vocabulary primitive to the current XMP and snapshot the "
        "result. Mask-bound entries (mask_spec set) route through the "
        "drawn-mask apply path automatically."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "primitive_name": {"type": "string"},
        },
        "required": ["image_id", "primitive_name"],
        "additionalProperties": False,
    },
    handler=_apply_primitive,
)


# --- remove_module ------------------------------------------------------


async def _remove_module(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    module_name = args["module_name"]

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message="workspace has no snapshot to remove from",
                recoverable=True,
            )
        )

    new_history = tuple(p for p in baseline_xmp.history if p.operation != module_name)
    if len(new_history) == len(baseline_xmp.history):
        return ToolResult.fail(
            error_not_found(
                f"module {module_name!r} (no history entries match)",
                module_name=module_name,
            )
        )

    new_xmp = replace(baseline_xmp, history=new_history)
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=f"remove_module: {module_name}")
    except VersioningError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc)))

    return ToolResult.ok(
        {
            "state_after": summarize_state(new_xmp),
            "snapshot_hash": new_hash,
        }
    )


register_tool(
    name="remove_module",
    description="Remove all history entries for an operation; snapshot the result.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "module_name": {"type": "string"},
        },
        "required": ["image_id", "module_name"],
        "additionalProperties": False,
    },
    handler=_remove_module,
)


# --- reset --------------------------------------------------------------


async def _reset(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    try:
        baseline_xmp = reset_to(workspace.repo, workspace.baseline_ref)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message=f"baseline ref {workspace.baseline_ref!r} not resolvable: {exc}",
            )
        )
    return ToolResult.ok(summarize_state(baseline_xmp))


register_tool(
    name="reset",
    description=(
        "Rewind the workspace's current branch to its baseline ref (per "
        "ADR-062). Destructive on the current branch's tip — capture a tag "
        "or branch first if you need to keep the prior state. After reset, "
        "HEAD is attached and apply_primitive can resume immediately."
    ),
    input_schema={
        "type": "object",
        "properties": {"image_id": {"type": "string"}},
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_reset,
)
