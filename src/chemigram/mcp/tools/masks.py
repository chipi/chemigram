"""Mask tools (batch 3 of Slice 3).

Mix of stubs and real implementations:

- ``generate_mask`` / ``regenerate_mask`` — stubs returning
  ``NOT_IMPLEMENTED`` with ``slice=4`` (real masking provider lands then).
- ``list_masks`` / ``tag_mask`` / ``invalidate_mask`` — real wrappers over
  :mod:`chemigram.core.versioning.masks`. Useful in v0.3.0 for any masks
  registered out-of-band (e.g., a developer dropping a PNG via Python).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from chemigram.core.versioning.masks import (
    MaskError,
    MaskNotFoundError,
    invalidate_mask,
    list_masks,
    tag_mask,
)
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
    error_not_implemented,
)
from chemigram.mcp.registry import ToolContext, register_tool

_SLICE_4 = "real masking provider lands in Slice 4"


# --- generate_mask (stub) -----------------------------------------------


async def _generate_mask(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_SLICE_4, slice=4))


register_tool(
    name="generate_mask",
    description="(Stub — Slice 4) Generate a raster mask from a target description.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "target": {"type": "string"},
            "prompt": {"type": "string"},
            "name": {"type": "string"},
        },
        "required": ["image_id", "target"],
        "additionalProperties": False,
    },
    handler=_generate_mask,
)


# --- regenerate_mask (stub) ---------------------------------------------


async def _regenerate_mask(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    return ToolResult.fail(error_not_implemented(_SLICE_4, slice=4))


register_tool(
    name="regenerate_mask",
    description="(Stub — Slice 4) Regenerate an existing mask with refined target/prompt.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "name": {"type": "string"},
            "target": {"type": "string"},
            "prompt": {"type": "string"},
        },
        "required": ["image_id", "name"],
        "additionalProperties": False,
    },
    handler=_regenerate_mask,
)


# --- list_masks (real) --------------------------------------------------


def _serialize_entry(e: Any) -> dict[str, Any]:
    raw = asdict(e)
    if "timestamp" in raw and raw["timestamp"] is not None:
        raw["timestamp"] = raw["timestamp"].isoformat()
    return raw


async def _list_masks(args: dict[str, Any], ctx: ToolContext) -> ToolResult[list[dict[str, Any]]]:
    image_id = args["image_id"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    entries = list_masks(workspace.repo)
    return ToolResult.ok([_serialize_entry(e) for e in entries])


register_tool(
    name="list_masks",
    description="List registered masks for an image (newest first).",
    input_schema={
        "type": "object",
        "properties": {"image_id": {"type": "string"}},
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_list_masks,
)


# --- tag_mask (real) ----------------------------------------------------


async def _tag_mask(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    source = args["source"]
    new_name = args["new_name"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    if not new_name:
        return ToolResult.fail(error_invalid_input("new_name must be non-empty"))
    try:
        entry = tag_mask(workspace.repo, source, new_name)
    except MaskNotFoundError as exc:
        return ToolResult.fail(error_not_found(str(exc)))
    except MaskError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.MASKING_ERROR, message=str(exc)))
    return ToolResult.ok(_serialize_entry(entry))


register_tool(
    name="tag_mask",
    description="Copy a mask registry entry under a new name (snapshot before regeneration).",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "source": {"type": "string"},
            "new_name": {"type": "string"},
        },
        "required": ["image_id", "source", "new_name"],
        "additionalProperties": False,
    },
    handler=_tag_mask,
)


# --- invalidate_mask (real) ---------------------------------------------


async def _invalidate_mask(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    name = args["name"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    try:
        invalidate_mask(workspace.repo, name)
    except MaskNotFoundError as exc:
        return ToolResult.fail(error_not_found(str(exc)))
    except MaskError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.MASKING_ERROR, message=str(exc)))
    return ToolResult.ok({"ok": True})


register_tool(
    name="invalidate_mask",
    description="Drop a mask from the registry (PNG bytes remain content-addressed).",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "name": {"type": "string"},
        },
        "required": ["image_id", "name"],
        "additionalProperties": False,
    },
    handler=_invalidate_mask,
)
