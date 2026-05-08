"""Retouch (spot heal/clone) tool — RFC-025 / ADR-087.

Wraps :func:`chemigram.core.helpers.apply_spot_retouch` into an
MCP-callable tool. Sister to ``apply_primitive`` for the structurally
different primitive class of spot correction (replaces pixels via a
darktable algorithm rather than filtering an effect through parameters).

v1.9.0 scope: HEAL + CLONE algorithms, CIRCLE geometry, single-form
per call. AI auto-spot detection (multi-form batched calls) routes to
RFC-030 when that unfreezes.
"""

from __future__ import annotations

from typing import Any

from chemigram.core.helpers import apply_spot_retouch, current_xmp, summarize_state
from chemigram.core.versioning.ops import VersioningError, snapshot
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_not_found,
)
from chemigram.mcp.registry import ToolContext, register_tool


async def _apply_spot(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    kind = args["kind"]
    x = float(args["x"])
    y = float(args["y"])
    radius = float(args["radius"])
    source_x = args.get("source_x")
    source_y = args.get("source_y")
    opacity = float(args.get("opacity", 100.0))
    border = float(args.get("border", 0.02))

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message="workspace has no baseline snapshot to apply onto",
                recoverable=True,
            )
        )

    try:
        new_xmp = apply_spot_retouch(
            baseline_xmp,
            kind=kind,
            x=x,
            y=y,
            radius=radius,
            source_x=float(source_x) if source_x is not None else None,
            source_y=float(source_y) if source_y is not None else None,
            opacity=opacity,
            border=border,
        )
    except (ValueError, TypeError) as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))

    label = f"apply_spot: {kind} at ({x:.3f},{y:.3f}) r={radius:.3f}"
    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=label)
    except VersioningError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc)))

    return ToolResult.ok(
        {
            "state_after": summarize_state(new_xmp),
            "snapshot_hash": new_hash,
            "kind": kind,
            "coordinates": {"x": x, "y": y, "radius": radius},
        }
    )


register_tool(
    name="apply_spot",
    description=(
        "Apply a spot retouch (heal or clone) at the given coordinate and "
        "snapshot. Use 'heal' for blemishes, sensor dust, distracting "
        "elements (darktable picks the source via wavelet decomposition). "
        "Use 'clone' to mirror features or copy texture from a specific "
        "source point (caller specifies source_x, source_y). Coordinates "
        "are normalized image coords [0, 1]; radius is also normalized "
        "(typical: 0.01-0.10). Sister to apply_primitive for the "
        "structurally different spot-correction primitive class. "
        "RFC-025 / ADR-087. v1.9.0 scope: heal + clone, single form per "
        "call; AI auto-detection of multiple spots is RFC-030."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "kind": {
                "type": "string",
                "enum": ["heal", "clone"],
                "description": (
                    "'heal' (auto-source via wavelet decomposition) or "
                    "'clone' (caller specifies source_x, source_y)."
                ),
            },
            "x": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Spot center x in normalized [0, 1] coords.",
            },
            "y": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": "Spot center y in normalized [0, 1] coords.",
            },
            "radius": {
                "type": "number",
                "exclusiveMinimum": 0.0,
                "maximum": 1.0,
                "description": (
                    "Spot radius in normalized [0, 1] coords. Typical: "
                    "0.01-0.10 for blemishes / dust spots."
                ),
            },
            "source_x": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": (
                    "Source center x for 'clone' (required for clone, ignored for heal)."
                ),
            },
            "source_y": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 1.0,
                "description": (
                    "Source center y for 'clone' (required for clone, ignored for heal)."
                ),
            },
            "opacity": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 100.0,
                "description": "Effect opacity (0-100, default 100).",
            },
            "border": {
                "type": "number",
                "minimum": 0.0,
                "maximum": 0.5,
                "description": (
                    "Mask falloff width in normalized coords (default "
                    "0.02 = subtle soft edge for natural blending)."
                ),
            },
        },
        "required": ["image_id", "kind", "x", "y", "radius"],
        "additionalProperties": False,
    },
    handler=_apply_spot,
)
