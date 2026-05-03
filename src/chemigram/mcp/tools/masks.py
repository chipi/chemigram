"""Mask tools.

- ``generate_mask`` / ``regenerate_mask`` — produce raster masks via the
  configured :class:`~chemigram.core.masking.MaskingProvider` (default:
  :class:`CoarseAgentProvider`); register the result in the per-image
  registry. Returns ``MASKING_ERROR`` if no masker is configured on the
  server (the production wiring lives in :func:`build_server`).
- ``list_masks`` / ``tag_mask`` / ``invalidate_mask`` — real wrappers over
  :mod:`chemigram.core.versioning.masks`.
"""

from __future__ import annotations

from typing import Any

from chemigram.core.helpers import ensure_preview_render, serialize_mask_entry
from chemigram.core.masking import MaskingError
from chemigram.core.versioning.masks import (
    MaskError,
    MaskNotFoundError,
    get_mask,
    invalidate_mask,
    list_masks,
    register_mask,
    tag_mask,
)
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
)
from chemigram.mcp.registry import ToolContext, register_tool


def _default_mask_name(target: str) -> str:
    """``target='manta' → 'current_manta_mask'`` for default-name convention."""
    safe = target.strip().replace(" ", "_") or "subject"
    return f"current_{safe}_mask"


def _no_masker_error() -> ToolError:
    return ToolError(
        code=ErrorCode.MASKING_ERROR,
        message=(
            "no masker configured on this server "
            "(set via build_server(masker=CoarseAgentProvider(...)))"
        ),
        recoverable=False,
    )


# --- generate_mask ------------------------------------------------------


async def _generate_mask(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    target = args["target"]
    prompt = args.get("prompt")
    name = args.get("name") or _default_mask_name(target)

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    if ctx.masker is None:
        return ToolResult.fail(_no_masker_error())

    try:
        preview = ensure_preview_render(workspace)
    except RuntimeError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.STATE_ERROR, message=str(exc)))

    try:
        result = ctx.masker.generate(target=target, render_path=preview, prompt=prompt)
    except MaskingError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.MASKING_ERROR, message=str(exc)))
    except Exception as exc:
        # MaskingProvider is BYOA (ADR-007) — third-party code. Any
        # unexpected exception from a provider is the provider's
        # concern; convert it to a structured masking_error so the
        # agent never sees a raw stack trace.
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.MASKING_ERROR,
                message=f"masker raised {type(exc).__name__}: {exc}",
            )
        )

    entry = register_mask(
        workspace.repo,
        name,
        result.png_bytes,
        generator=result.generator,
        prompt=result.prompt,
    )
    return ToolResult.ok(serialize_mask_entry(entry))


register_tool(
    name="generate_mask",
    description=(
        "Generate a raster mask for a target on the current XMP state. "
        "Auto-renders a preview if needed; registers the PNG and returns "
        "the mask registry entry."
    ),
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


# --- regenerate_mask ----------------------------------------------------


async def _regenerate_mask(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    name = args["name"]
    target_arg = args.get("target")
    prompt = args.get("prompt")

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    if ctx.masker is None:
        return ToolResult.fail(_no_masker_error())

    try:
        _prior_entry, prior_bytes = get_mask(workspace.repo, name)
    except MaskNotFoundError as exc:
        return ToolResult.fail(error_not_found(str(exc)))
    except MaskError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.MASKING_ERROR, message=str(exc)))

    effective_target = target_arg or _target_from_name(name)
    if not effective_target:
        return ToolResult.fail(
            error_invalid_input(f"cannot infer target for mask {name!r}; pass `target=` explicitly")
        )

    try:
        preview = ensure_preview_render(workspace)
    except RuntimeError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.STATE_ERROR, message=str(exc)))

    try:
        result = ctx.masker.regenerate(
            target=effective_target,
            render_path=preview,
            prior_mask=prior_bytes,
            prompt=prompt,
        )
    except MaskingError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.MASKING_ERROR, message=str(exc)))
    except Exception as exc:
        # See _generate_mask: provider is BYOA, any unexpected
        # exception becomes a structured masking_error.
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.MASKING_ERROR,
                message=f"masker raised {type(exc).__name__}: {exc}",
            )
        )

    entry = register_mask(
        workspace.repo,
        name,
        result.png_bytes,
        generator=result.generator,
        prompt=result.prompt,
    )
    return ToolResult.ok(serialize_mask_entry(entry))


register_tool(
    name="regenerate_mask",
    description=(
        "Refine an existing mask with an updated target/prompt. The prior "
        "mask is passed to the provider as guidance."
    ),
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


def _target_from_name(name: str) -> str:
    """Recover ``target`` from the default-name convention.

    ``"current_manta_mask"`` → ``"manta"``. Returns ``""`` if the name
    doesn't match the convention; caller treats that as "no inferred
    target — caller must pass one explicitly".
    """
    if name.startswith("current_") and name.endswith("_mask"):
        middle = name[len("current_") : -len("_mask")]
        return middle.replace("_", " ")
    return ""


# --- list_masks (real) --------------------------------------------------


async def _list_masks(args: dict[str, Any], ctx: ToolContext) -> ToolResult[list[dict[str, Any]]]:
    image_id = args["image_id"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    entries = list_masks(workspace.repo)
    return ToolResult.ok([serialize_mask_entry(e) for e in entries])


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
    return ToolResult.ok(serialize_mask_entry(entry))


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
