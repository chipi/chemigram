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
from chemigram.core.vocab import MaskdefEntry, VocabEntry
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
        "parameters": _serialize_parameters(e),
    }


def _serialize_parameters(e: VocabEntry) -> list[dict[str, Any]] | None:
    """Serialize an entry's parameter specs for MCP / CLI introspection.

    Returns ``None`` for non-parameterized entries (closes #89's
    discoverability gap — the agent or user can tell at a glance whether
    an entry takes ``--value V`` / ``value`` and what the parameter
    shape is).

    Each parameter is rendered as: ``{name, type, range: [min, max],
    default, module, modversion, offset}``. The byte-level ``field``
    block from ADR-078 is flattened into the parameter dict for terser
    consumption; full reconstruction is possible from the entry's
    ParameterSpec if needed.
    """
    if e.parameters is None:
        return None
    return [
        {
            "name": p.name,
            "type": p.type,
            "range": list(p.range),
            "default": p.default,
            "module": p.field.module,
            "modversion": p.field.modversion,
            "offset": p.field.offset,
        }
        for p in e.parameters
    ]


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


# --- list_masks_vocabulary (RFC-032) ------------------------------------


def _serialize_maskdef(m: MaskdefEntry) -> dict[str, Any]:
    return {
        "name": m.name,
        "kind": "mask",
        "description": m.description,
        "tags": list(m.tags),
        "spec": m.spec,
        "llm_vision_prompt": m.llm_vision_prompt,
        "darktable_version": m.darktable_version,
        "source": m.source,
    }


async def _list_masks_vocabulary(
    args: dict[str, Any], ctx: ToolContext
) -> ToolResult[list[dict[str, Any]]]:
    tags = args.get("tags")
    masks = ctx.vocabulary.list_masks(tags=tags)
    return ToolResult.ok([_serialize_maskdef(m) for m in masks])


register_tool(
    name="list_masks_vocabulary",
    description=(
        "List available named masks (RFC-032). Each entry's 'spec' field is "
        "the apply-time mask_spec — drawn-form, parametric range_filter, or "
        "both. Reference a named mask in apply_primitive's mask_spec arg as "
        "{'kind': 'named', 'name': '<maskdef-name>'}. Optional tags filter "
        "(OR — any tag in the list matches)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    },
    handler=_list_masks_vocabulary,
)


# --- wb_from_gray_card (survey Gap #20) ---------------------------------


async def _wb_from_gray_card(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    """Sample a gray-card region of a rendered image and return the
    temperature-primitive coefficients that would correct it to neutral."""
    from pathlib import Path

    from chemigram.core.gray_card import GrayCardError, wb_from_gray_card

    image_path = args["image_path"]
    x = int(args["x"])
    y = int(args["y"])
    sample_radius = int(args.get("sample_radius", 5))

    try:
        coeffs = wb_from_gray_card(Path(image_path), x=x, y=y, sample_radius=sample_radius)
    except GrayCardError as exc:
        return ToolResult.fail(error_invalid_input(str(exc)))

    return ToolResult.ok(
        {
            "red_coeff": coeffs.red_coeff,
            "green_coeff": coeffs.green_coeff,
            "blue_coeff": coeffs.blue_coeff,
            "sampled_r": coeffs.sampled_r,
            "sampled_g": coeffs.sampled_g,
            "sampled_b": coeffs.sampled_b,
            "sample_radius": coeffs.sample_radius,
            "parameter_values": coeffs.as_parameter_values(),
        }
    )


register_tool(
    name="wb_from_gray_card",
    description=(
        "Sample a gray-card region of a rendered image at pixel coordinates "
        "(x, y) and return the temperature-primitive coefficients that "
        "correct the sample to neutral gray. Typical workflow: call "
        "render_preview to get a JPEG, examine for the gray-card region, "
        "call this tool with the sampled coordinates, then call "
        "apply_primitive(image_id, 'temperature', parameter_values=<...>) "
        "with the returned coefficients. Per RFC-postponed / survey Gap #20."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to a rendered image (typically from render_preview).",
            },
            "x": {"type": "integer", "minimum": 0, "description": "Pixel x coordinate."},
            "y": {"type": "integer", "minimum": 0, "description": "Pixel y coordinate."},
            "sample_radius": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "default": 5,
                "description": "Half-side of square sample region (default 5 → 11x11).",
            },
        },
        "required": ["image_path", "x", "y"],
        "additionalProperties": False,
    },
    handler=_wb_from_gray_card,
)


# --- propagate_state (RFC-037) ------------------------------------------


async def _propagate_state(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    """Propagate the source workspace's edit state to N targets atomically
    (RFC-037 / wedding-defining anchor-and-sync workflow)."""
    from chemigram.core.propagate import PropagateError, propagate_state

    source_id = args["source_image_id"]
    target_ids = args.get("target_image_ids", [])
    exclude_ops = args.get("exclude_ops")
    include_per_image = bool(args.get("include_per_image", False))
    label = args.get("label")

    source_ws = resolve_workspace(ctx, source_id)
    if source_ws is None:
        return ToolResult.fail(error_not_found(f"source image {source_id!r}"))

    if not isinstance(target_ids, list):
        return ToolResult.fail(error_invalid_input("target_image_ids must be a list"))

    target_workspaces = []
    for tid in target_ids:
        ws = resolve_workspace(ctx, tid)
        if ws is None:
            return ToolResult.fail(error_not_found(f"target image {tid!r}"))
        target_workspaces.append(ws)

    try:
        batch = propagate_state(
            source_ws,
            target_workspaces,
            exclude_ops=exclude_ops,
            include_per_image=include_per_image,
            label=label,
        )
    except PropagateError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))

    return ToolResult.ok(
        {
            "n_succeeded": batch.n_succeeded,
            "n_failed": batch.n_failed,
            "results": [
                {
                    "image_id": r.image_id,
                    "snapshot_hash": r.snapshot_hash,
                    "applied_ops": list(r.applied_ops),
                }
                for r in batch.results
            ],
            "source_image_id": source_id,
        }
    )


register_tool(
    name="propagate_state",
    description=(
        "Propagate the source image's edit state (everything in its current "
        "history) to N target images atomically. Same mental model as "
        "Lightroom's Sync function — edit one anchor, sync to many. "
        "Default: inherit everything except framing-bound ops (drawn masks, "
        "retouch, crop, lens corrections); these don't propagate cleanly "
        "across different framings. Override via include_per_image=true for "
        "tripod-fixed series. Optional exclude_ops list for fine-grained "
        "opt-out (e.g., keep each target's individual exposure). Atomic — "
        "all targets receive propagated state or none do. Soft cap at 200 "
        "targets per call. Per RFC-037 / survey Gap #4 (wedding-defining)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "source_image_id": {"type": "string", "description": "Anchor image."},
            "target_image_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1,
                "maxItems": 200,
                "description": "Images to propagate state TO.",
            },
            "exclude_ops": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Optional list of operation names to skip. Default: empty (inherit everything)."
                ),
            },
            "include_per_image": {
                "type": "boolean",
                "default": False,
                "description": (
                    "Override the framing-bound auto-exclusion (drawn masks, "
                    "retouch, crop, lens). Use for tripod-fixed series."
                ),
            },
            "label": {"type": "string", "description": "Optional snapshot label."},
        },
        "required": ["source_image_id", "target_image_ids"],
        "additionalProperties": False,
    },
    handler=_propagate_state,
)


# --- apply_per_region (RFC-031) -----------------------------------------


async def _apply_per_region(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    from chemigram.core.batched import (
        BatchedApplyError,
        MixedRegionSpec,
        OpSpec,
        RegionSpec,
        apply_per_region,
        apply_per_region_mixed,
    )

    image_id = args["image_id"]
    primitive_name = args.get("primitive_name")
    regions_raw = args.get("regions", [])
    label = args.get("label")

    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.INVALID_INPUT,
                message="workspace has no baseline snapshot to apply onto",
            )
        )

    if not isinstance(regions_raw, list):
        return ToolResult.fail(error_invalid_input("regions must be a list"))

    # RFC-036 dispatch: presence of "ops" on any region signals mixed-op shape.
    has_ops = any("ops" in r for r in regions_raw)
    if has_ops and primitive_name is not None:
        return ToolResult.fail(
            error_invalid_input(
                "cannot specify both top-level 'primitive_name' (single-op shape) "
                "and per-region 'ops' (mixed-op shape) — pick one"
            )
        )
    if not has_ops and primitive_name is None:
        return ToolResult.fail(
            error_invalid_input(
                "must specify either top-level 'primitive_name' (single-op) or "
                "per-region 'ops' (mixed-op)"
            )
        )

    if has_ops:
        # Mixed-op shape (RFC-036)
        mixed_regions = [
            MixedRegionSpec(
                mask_spec=r.get("mask_spec"),
                ops=tuple(
                    OpSpec(
                        primitive_name=op["primitive_name"],
                        parameter_values=op.get("parameter_values"),
                    )
                    for op in r.get("ops", [])
                ),
            )
            for r in regions_raw
        ]
        try:
            new_xmp = apply_per_region_mixed(baseline_xmp, mixed_regions, vocab=ctx.vocabulary)
        except BatchedApplyError as exc:
            return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))
        n_regions = len(mixed_regions)
        n_pairs = sum(len(r.ops) for r in mixed_regions)
        snapshot_label = (
            label if label else f"apply_per_region_mixed: {n_regions} regions, {n_pairs} ops"
        )
    else:
        # Single-op shape (RFC-031)
        regions = [
            RegionSpec(
                mask_spec=r.get("mask_spec"),
                parameter_values=r.get("parameter_values"),
            )
            for r in regions_raw
        ]
        # primitive_name guaranteed non-None here by the dispatch above.
        assert primitive_name is not None
        try:
            new_xmp = apply_per_region(baseline_xmp, primitive_name, regions, vocab=ctx.vocabulary)
        except BatchedApplyError as exc:
            return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))
        n_regions = len(regions)
        n_pairs = n_regions
        snapshot_label = (
            label if label else f"apply_per_region: {primitive_name} ({n_regions} regions)"
        )

    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=snapshot_label)
    except VersioningError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc)))

    return ToolResult.ok(
        {
            "state_after": summarize_state(new_xmp),
            "snapshot_hash": new_hash,
            "n_regions": n_regions,
            "n_op_region_pairs": n_pairs,
            "primitive_name": primitive_name,
            "shape": "mixed" if has_ops else "single",
        }
    )


register_tool(
    name="apply_per_region",
    description=(
        "Apply vocabulary primitives to N mask-bound regions atomically. "
        "Two shapes:\n"
        "(1) **Single-op (RFC-031)** — supply top-level `primitive_name`; "
        "each region applies that one primitive. Canonical use: dodge-and-"
        "burn (one primitive `exposure`, varied across regions).\n"
        "(2) **Mixed-op (RFC-036)** — supply per-region `ops: [{primitive_name, "
        "parameter_values?}, ...]` instead. Canonical uses: composed skin "
        "retouch (skin_uniformity + skin_smooth_painterly on mask_skin_region "
        "in one move) and eye-detail lift (exposure + sharpening + saturation "
        "on the eye region).\n"
        "Pick one shape — can't mix `primitive_name` and per-region `ops`. "
        "Either way, all regions validate first; any failure aborts the batch "
        "(atomic). Soft caps: 32 regions (single-op) or 64 (op * region) "
        "pairs (mixed-op)."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "primitive_name": {
                "type": "string",
                "description": (
                    "Single-op shape (RFC-031). Specify together with regions "
                    "where each region carries optional parameter_values."
                ),
            },
            "regions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 64,
                "items": {
                    "type": "object",
                    "properties": {
                        "mask_spec": {
                            "type": "object",
                            "description": (
                                "Apply-time mask spec — drawn-form "
                                "(dt_form/dt_params), parametric "
                                "(range_filter), or named ({kind: 'named', "
                                "name: '<maskdef>'}). Per-region mandatory."
                            ),
                        },
                        "parameter_values": {
                            "type": "object",
                            "description": (
                                "Single-op shape only — per-region parameter "
                                "overrides for the top-level primitive_name."
                            ),
                        },
                        "ops": {
                            "type": "array",
                            "description": (
                                "Mixed-op shape (RFC-036) — ordered list of "
                                "{primitive_name, parameter_values?} pairs "
                                "applied to this region's mask. Same primitive "
                                "may appear twice; each gets its own "
                                "multi_priority."
                            ),
                            "items": {
                                "type": "object",
                                "properties": {
                                    "primitive_name": {"type": "string"},
                                    "parameter_values": {"type": "object"},
                                },
                                "required": ["primitive_name"],
                            },
                        },
                    },
                    "required": ["mask_spec"],
                },
            },
            "label": {
                "type": "string",
                "description": "Optional snapshot label.",
            },
        },
        "required": ["image_id", "regions"],
        "additionalProperties": False,
    },
    handler=_apply_per_region,
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


def _resolve_value_arg(value_arg: Any, entry: Any) -> dict[str, float] | None:
    """Normalize the MCP ``value`` argument into a name->float dict.

    Per ADR-079, ``value`` is shape-polymorphic by entry's parameters
    cardinality:
    - ``None`` → no parameter override (entry uses dtstyle defaults).
    - scalar (int/float) on a single-parameter entry → wraps as
      ``{<the parameter's name>: scalar}``.
    - dict on a multi-parameter (or single-parameter) entry → keys must
      match declared parameter names.

    Validation: out-of-range values, unknown names, and shape mismatches
    raise :class:`ValueError` mapped to ``INVALID_INPUT`` by the caller.
    """
    if value_arg is None:
        return None
    if entry.parameters is None:
        raise ValueError(
            f"entry {entry.name!r} has no parameters declared; 'value' argument cannot be supplied"
        )
    declared_by_name = {p.name: p for p in entry.parameters}
    declared_names = list(declared_by_name.keys())

    if isinstance(value_arg, (int, float)):
        if len(declared_names) != 1:
            raise ValueError(
                f"scalar 'value' is only valid for single-parameter entries; "
                f"{entry.name!r} declares {len(declared_names)} parameters: "
                f"{declared_names}. Pass a dict instead."
            )
        out: dict[str, float] = {declared_names[0]: float(value_arg)}
    elif isinstance(value_arg, dict):
        out = {}
        for name, v in value_arg.items():
            if name not in declared_by_name:
                raise ValueError(
                    f"unknown parameter {name!r} for entry {entry.name!r}; "
                    f"declared: {declared_names}"
                )
            try:
                out[name] = float(v)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"parameter {name!r} value {v!r} is not numeric") from exc
    else:
        raise ValueError(f"'value' must be a number or dict, got {type(value_arg).__name__}")

    # Range validation (hard reject per ADR-079)
    for name, v in out.items():
        spec = declared_by_name[name]
        lo, hi = spec.range
        if not (lo <= v <= hi):
            raise ValueError(
                f"parameter {name!r} value {v} outside declared range "
                f"[{lo}, {hi}] for entry {entry.name!r}"
            )
    return out


async def _apply_primitive(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    primitive_name = args["primitive_name"]
    mask_spec_override = args.get("mask_spec")
    value_arg = args.get("value")

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

    # Resolve parameter values (per ADR-079; raises on shape / range error).
    try:
        parameter_values = _resolve_value_arg(value_arg, entry)
    except ValueError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))

    # Mask resolution: caller-supplied mask_spec override > manifest mask_spec.
    effective_mask = mask_spec_override if mask_spec_override is not None else entry.mask_spec

    # RFC-032 named-mask resolution: if effective_mask is a {"kind": "named",
    # "name": "..."} reference, look it up in the vocab and substitute the
    # maskdef's spec. No-op for already-resolved drawn / parametric specs.
    from chemigram.core.vocab import VocabError, resolve_named_mask_spec

    try:
        effective_mask = resolve_named_mask_spec(effective_mask, ctx.vocabulary)
    except VocabError as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))

    # Route: parameterized OR non-parameterized.
    has_parameters = parameter_values is not None or entry.parameters is not None
    if has_parameters:
        from chemigram.core.helpers import apply_entry
        from chemigram.core.parameterize import PatchError

        try:
            new_xmp = apply_entry(
                baseline_xmp,
                entry,
                parameter_values=parameter_values,
                mask_spec=effective_mask,
            )
        except (ValueError, TypeError, PatchError) as exc:
            return ToolResult.fail(ToolError(code=ErrorCode.INVALID_INPUT, message=str(exc)))
    elif effective_mask is not None:
        from chemigram.core.helpers import apply_with_mask

        try:
            new_xmp = apply_with_mask(baseline_xmp, entry.dtstyle, effective_mask)
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


_MASK_SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "dt_form": {
            "type": "string",
            "enum": ["gradient", "ellipse", "rectangle", "path"],
            "description": (
                "Drawn-form kind (spatial mask). 'gradient' for smooth "
                "top/bottom/left/right transitions; 'ellipse' for circular "
                "subject regions; 'rectangle' for hard-edged rectangular "
                "regions; 'path' for arbitrary N-vertex closed polygons "
                "(AI subject silhouettes per RFC-026, programmatic outlines, "
                "etc.). See docs/guides/mask-shapes-from-words.md for the "
                "spatial-English-to-parameter mapping (RFC-029 / ADR-084). "
                "Optional when range_filter is set; together they "
                "intersect (drawn AND parametric)."
            ),
        },
        "dt_params": {
            "type": "object",
            "description": (
                "Form-specific parameters. Coordinates are normalized "
                "image coords [0, 1]. gradient: anchor_x, anchor_y, "
                "rotation (deg, 0=horizontal-light-on-top, 90=vertical), "
                "compression, state. ellipse: center_x, center_y, "
                "radius_x, radius_y, border. rectangle: x0, y0, x1, y1, "
                "border. path: vertices=[[x,y],...], border. See "
                "docs/guides/mask-shapes-from-words.md for example phrases."
            ),
        },
        "range_filter": {
            "type": "object",
            "description": (
                "Pixel-level refinement (RFC-024 / ADR-085). Filters the "
                "spatial mask down to pixels matching a luminance or "
                "color-channel range. Examples: 'in this gradient, only "
                "the dark pixels' = drawn gradient + range_filter "
                "{kind: 'luminance', min: 0.0, max: 0.3}. 'only the blue "
                "hues' = range_filter {kind: 'color_h', min: 0.55, max: "
                "0.7}. Used alone (no dt_form) for global content-derived "
                "masks; combined with dt_form for spatial+content "
                "intersection."
            ),
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["luminance", "color_h", "color_s", "color_l"],
                    "description": (
                        "Channel selector. 'luminance' = brightness "
                        "(universal, works in any color space). "
                        "'color_h' = HSL hue [0..1]. 'color_s' = HSL "
                        "saturation. 'color_l' = HSL lightness. Color "
                        "kinds set blend_cst to HSL automatically."
                    ),
                },
                "min": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Band lower bound, [0..1].",
                },
                "max": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0,
                    "description": "Band upper bound, [0..1].",
                },
                "feather": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 0.5,
                    "description": (
                        "Ramp width applied to both edges of the band. "
                        "Default 0.05 (small soft transition)."
                    ),
                },
                "invert": {
                    "type": "boolean",
                    "description": (
                        "If true, OUTSIDE the range becomes the mask "
                        "(useful for SUBTRACT semantics)."
                    ),
                },
            },
            "required": ["kind", "min", "max"],
        },
    },
    "additionalProperties": False,
    "description": (
        "Mask spec. Must have at least one of 'dt_form' (spatial) or "
        "'range_filter' (parametric). Three valid combinations: drawn "
        "only, parametric only, drawn+parametric (intersection)."
    ),
}


register_tool(
    name="apply_primitive",
    description=(
        "Apply a vocabulary primitive to the current XMP and snapshot the "
        "result. Composes three orthogonal axes: (1) entry's manifest "
        "mask_spec is honored automatically; (2) caller-supplied mask_spec "
        "overrides the manifest one (ADR-076) — use this for build-by-words "
        "mask construction (e.g., 'bottom third', 'circle on subject'); "
        "see docs/guides/mask-shapes-from-words.md for the "
        "spatial-vocabulary-to-parameter mapping (RFC-029 / ADR-084); "
        "(3) caller-supplied value patches the entry's op_params per its "
        "parameters declaration (RFC-021 / ADR-077). Scalar value is "
        "shorthand for single-parameter entries; dict value "
        '(e.g., {"temp": 0.4, "tint": -0.1}) for multi-parameter. '
        "Tip: same mask_spec across multiple apply_primitive calls binds to "
        "the same mask_id in darktable (deterministic hash) — no need to "
        "track mask handles."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "primitive_name": {"type": "string"},
            "mask_spec": {
                **_MASK_SPEC_SCHEMA,
                "description": (
                    "Optional drawn-mask spec applied at apply time. "
                    "Overrides the entry's manifest mask_spec when both "
                    "are present. Schema matches the manifest mask_spec "
                    "field; see docs/guides/mask-applicable-controls.md "
                    "for the per-module compatibility matrix and parameter "
                    "semantics."
                ),
            },
            "value": {
                "oneOf": [
                    {"type": "number"},
                    {"type": "object"},
                ],
                "description": (
                    "Optional parameter value(s) for parameterized entries "
                    "(per RFC-021 / ADR-079). Number for single-parameter "
                    "entries (shorthand); object {name: value, ...} for "
                    "multi-parameter entries. Out-of-range values and "
                    "unknown parameter names fail with INVALID_INPUT."
                ),
            },
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
