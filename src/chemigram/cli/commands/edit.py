"""Edit / state CLI verbs (issue #54).

Mirrors MCP ``apply_primitive``, ``remove_module``, ``reset``,
``get_state`` (per ADR-033/056). Each verb calls the underlying
:mod:`chemigram.core` API directly (per ADR-071); none of them go
through ``chemigram.mcp.tools.*``.

Mask binding paths (closes #78):

- An entry with ``mask_spec`` in its manifest auto-routes through
  :func:`chemigram.core.helpers.apply_with_mask`. This is the
  v1.5.0 behavior, generalized in v1.9.0 (ADR-085) to handle drawn
  masks, parametric range_filter, and drawn+parametric composition.
- ``--mask-spec '<json>'`` on ``apply-primitive`` overrides at apply
  time (or supplies a mask for an entry that doesn't have one).
  This is the v1.6.0 addition — lets a photographer mask any
  primitive ad-hoc without authoring a vocabulary entry.

The JSON shape matches the manifest's ``mask_spec`` field
(``{"dt_form": "gradient"|"ellipse"|"rectangle", "dt_params": {...}}``);
schema reference and parameter semantics live in
``docs/guides/mask-applicable-controls.md``.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any, cast

import typer

from chemigram.cli._batch import aggregate_exit_code, iter_image_ids
from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.helpers import (
    apply_entry,
    apply_with_mask,
    current_xmp,
    summarize_state,
)
from chemigram.core.parameterize import PatchError
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


def _resolve_effective_mask(
    vocab_entry: Any, mask_spec_override: dict[str, Any] | None
) -> dict[str, Any] | None:
    """Pick the mask_spec to apply, preferring the CLI override.

    Returns the dict that should be passed to ``apply_with_mask``,
    or None if the entry should be applied globally. The CLI override
    takes precedence over the manifest's ``mask_spec`` so a photographer
    can re-mask a shipped masked entry on the fly.
    """
    if mask_spec_override is not None:
        return mask_spec_override
    return vocab_entry.mask_spec


def _do_apply_primitive(
    ctx: typer.Context,
    image_id: str,
    *,
    vocab_entry: object,
    entry_name: str,
    vocabulary: object | None = None,
    mask_spec_override: dict[str, Any] | None = None,
    parameter_values: dict[str, float] | None = None,
    strength: float | None = None,
) -> int:
    """Per-image core for apply-primitive; returns exit code."""
    from chemigram.core.vocab import VocabEntry, VocabError, VocabularyIndex
    from chemigram.core.vocab import resolve_named_mask_spec as _resolve_named_mask_spec

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

    effective_mask = _resolve_effective_mask(vocab_entry, mask_spec_override)

    # RFC-032 named-mask resolution: substitute {"kind": "named", "name": ...}
    # references with the maskdef's spec. No-op for already-resolved specs.
    if vocabulary is not None and effective_mask is not None:
        assert isinstance(vocabulary, VocabularyIndex)
        try:
            effective_mask = _resolve_named_mask_spec(effective_mask, vocabulary)
        except VocabError as exc:
            writer.error(str(exc), ExitCode.NOT_FOUND, entry=entry_name)
            return ExitCode.NOT_FOUND.value

    has_parameters = parameter_values is not None or vocab_entry.parameters is not None
    has_strength = strength is not None

    # Route through apply_entry when parameter axis OR strength axis is in
    # play. apply_entry handles the parameter-only / mask-only / strength /
    # composition shapes.
    if has_parameters or has_strength:
        try:
            new_xmp = apply_entry(
                baseline_xmp,
                vocab_entry,
                parameter_values=parameter_values,
                mask_spec=effective_mask,
                strength=strength,
            )
        except (ValueError, TypeError) as exc:
            writer.error(str(exc), ExitCode.INVALID_INPUT, entry=entry_name)
            return ExitCode.INVALID_INPUT.value
        except PatchError as exc:
            writer.error(str(exc), ExitCode.INVALID_INPUT, entry=entry_name)
            return ExitCode.INVALID_INPUT.value
    elif effective_mask is not None:
        # Legacy mask-only path (no parameters / strength axis).
        try:
            new_xmp = apply_with_mask(baseline_xmp, vocab_entry.dtstyle, effective_mask)
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


def _parse_value_or_params(
    value: str | None,
    params: list[str] | None,
    entry: Any,
) -> dict[str, float] | None:
    """Resolve ``--value V`` and/or ``--param NAME=V`` flags into a single
    {name: float} dict suitable for :func:`apply_entry`.

    Routing per ADR-079:
    - Neither flag set: returns None (apply uses the entry's default param
      values, or no parameter axis if the entry isn't parameterized).
    - ``--value V`` only: shorthand for the single-parameter case. Resolves
      to ``{<entry's only parameter name>: V}``. Rejects multi-parameter
      entries with :class:`typer.BadParameter` (use ``--param`` instead).
    - ``--param NAME=V`` only (repeatable): explicit name-keyed; required
      for multi-parameter entries.
    - Both: must agree for any name they both set; conflicting values
      fail with :class:`typer.BadParameter`.

    Validation done here:
    - Numeric coercion of value strings.
    - Unknown parameter name (not declared by the entry's ``parameters``):
      :class:`typer.BadParameter` naming the entry's declared params.
    - Out-of-range value (per the parameter spec's ``range``):
      :class:`typer.BadParameter` naming the parameter, value, and range.

    Returns ``None`` when the entry has no ``parameters`` declaration AND
    neither flag was set; raises if the caller passed a value flag against
    a non-parameterized entry.
    """
    from chemigram.core.vocab import VocabEntry

    assert isinstance(entry, VocabEntry)
    has_value = value is not None and value != ""
    has_params = bool(params)

    if not has_value and not has_params:
        return None

    if entry.parameters is None:
        raise typer.BadParameter(
            f"entry {entry.name!r} has no parameters declared; "
            f"--value / --param cannot be used here"
        )

    declared_names = [p.name for p in entry.parameters]
    declared_by_name = {p.name: p for p in entry.parameters}

    out: dict[str, float] = {}

    # --value V (single-parameter shorthand)
    if has_value:
        if len(declared_names) != 1:
            raise typer.BadParameter(
                f"--value V is only valid for single-parameter entries; "
                f"entry {entry.name!r} declares {len(declared_names)} parameters "
                f"({declared_names}). Use --param NAME=V (repeatable) instead."
            )
        try:
            v = float(value)  # type: ignore[arg-type]
        except ValueError as exc:
            raise typer.BadParameter(f"--value must be a number, got {value!r}") from exc
        out[declared_names[0]] = v

    # --param NAME=V (repeatable)
    if has_params:
        for raw in params:  # type: ignore[union-attr]
            if "=" not in raw:
                raise typer.BadParameter(
                    f"--param expects NAME=VALUE, got {raw!r} (missing '=' separator)"
                )
            name, _, vstr = raw.partition("=")
            name = name.strip()
            if name not in declared_by_name:
                raise typer.BadParameter(
                    f"unknown parameter {name!r} for entry {entry.name!r}; "
                    f"declared: {declared_names}"
                )
            try:
                v = float(vstr)
            except ValueError as exc:
                raise typer.BadParameter(
                    f"--param {name}=... must be a number, got {vstr!r}"
                ) from exc
            if name in out and out[name] != v:
                raise typer.BadParameter(
                    f"conflicting values for parameter {name!r}: "
                    f"--value supplied {out[name]}, --param supplied {v}"
                )
            out[name] = v

    # Range validation (hard reject per ADR-079)
    for name, v in out.items():
        spec = declared_by_name[name]
        lo, hi = spec.range
        if not (lo <= v <= hi):
            raise typer.BadParameter(
                f"parameter {name!r} value {v} outside declared range "
                f"[{lo}, {hi}] for entry {entry.name!r}"
            )

    return out


def _parse_mask_spec_flag(value: str | None) -> dict[str, Any] | None:
    """Parse the ``--mask-spec`` flag value (JSON string) into a dict.

    Empty / unset returns None. Raises ``typer.BadParameter`` with a
    helpful message on invalid JSON or wrong shape.
    """
    if value is None or value == "":
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(
            f"--mask-spec must be valid JSON (got {exc.msg} at pos {exc.pos}). "
            f'Example: \'{{"dt_form":"ellipse","dt_params":{{"center_x":0.5,'
            f'"center_y":0.5,"radius_x":0.3,"radius_y":0.3,"border":0.05}}}}\''
        ) from exc
    if not isinstance(parsed, dict):
        raise typer.BadParameter(f"--mask-spec must be a JSON object, got {type(parsed).__name__}")
    if "dt_form" not in parsed:
        raise typer.BadParameter(
            "--mask-spec missing required key 'dt_form' "
            "(one of: gradient, ellipse, rectangle). "
            "See docs/guides/mask-applicable-controls.md for the schema."
        )
    return parsed


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
    mask_spec: str = typer.Option(
        None,
        "--mask-spec",
        help=(
            "Optional JSON mask spec to apply this primitive through a drawn "
            "mask region. Schema: "
            '\'{"dt_form":"gradient|ellipse|rectangle","dt_params":{...}}\'. '
            "Overrides the entry's manifest mask_spec when both are present. "
            "See docs/guides/mask-applicable-controls.md for parameter "
            "semantics and the per-module compatibility matrix."
        ),
    ),
    value: str = typer.Option(
        None,
        "--value",
        help=(
            "Single-parameter shorthand for parameterized entries (e.g. "
            "'exposure --value 0.7'). For multi-parameter entries, use "
            "--param NAME=V instead. See docs/guides/recipes.md."
        ),
    ),
    param: list[str] = typer.Option(
        None,
        "--param",
        help=(
            "Repeatable NAME=VALUE for multi-parameter entries "
            "(e.g. '--param temp=+0.4 --param tint=-0.1'). May be combined "
            "with --value if values agree."
        ),
    ),
    strength: float = typer.Option(
        None,
        "--strength",
        help=(
            "RFC-035 Path B — interpolate the entry's authored parameterized "
            "fields toward identity by this factor [0.0, 1.0]. 1.0 preserves "
            "authored (default); 0.0 = identity / no-op; 0.5 = halfway. "
            "Useful for L2 looks: '--strength 0.5' produces a softer variant."
        ),
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

    mask_spec_override = _parse_mask_spec_flag(mask_spec)

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

    # Resolve --value / --param into a single name->value dict, with all
    # validation (unknown name, out-of-range, scalar-on-multi) performed
    # up front. typer.BadParameter raises a clean exit-2 / INVALID_INPUT.
    parameter_values = _parse_value_or_params(value, param, vocab_entry)

    codes = [
        _do_apply_primitive(
            ctx,
            img,
            vocab_entry=vocab_entry,
            entry_name=entry,
            vocabulary=vocabulary,
            mask_spec_override=mask_spec_override,
            parameter_values=parameter_values,
            strength=strength,
        )
        for img in iter_image_ids(stdin, image_id)
    ]
    final = aggregate_exit_code(codes)
    if final != ExitCode.SUCCESS.value:
        raise typer.Exit(code=final)


# ---------------------------------------------------------------------------
# apply-per-region (RFC-031)
# ---------------------------------------------------------------------------


def apply_per_region_cli(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    entry: str | None = typer.Option(
        None,
        "--entry",
        help=(
            "Vocabulary entry name (single-op shape per RFC-031). Omit to use "
            "mixed-op shape where each region carries its own 'ops' list."
        ),
    ),
    regions_json: str = typer.Option(
        ...,
        "--regions",
        help=(
            "JSON array of regions. Single-op shape: each region is "
            '{"mask_spec": {...}, "parameter_values": {...}}. '
            "Mixed-op shape (RFC-036): each region is "
            '{"mask_spec": {...}, "ops": [{"primitive_name": "...", '
            '"parameter_values": {...}}, ...]}. '
            "mask_spec accepts drawn / parametric / named-mask shapes."
        ),
    ),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack name (repeatable). Defaults to ['starter'].",
    ),
    label: str = typer.Option(None, "--label", help="Optional snapshot label."),
) -> None:
    """Apply primitives to N mask-bound regions atomically (RFC-031 single-op
    OR RFC-036 mixed-op)."""
    from chemigram.core.batched import (
        BatchedApplyError,
        MixedRegionSpec,
        OpSpec,
        RegionSpec,
        apply_per_region,
        apply_per_region_mixed,
    )

    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    pack_names = pack if pack else ["starter"]

    try:
        regions_raw = json.loads(regions_json)
    except json.JSONDecodeError as exc:
        writer.error(
            f"--regions must be valid JSON: {exc.msg} at pos {exc.pos}",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc
    if not isinstance(regions_raw, list):
        writer.error("--regions must be a JSON array", ExitCode.INVALID_INPUT)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    # RFC-036 dispatch.
    has_ops = any("ops" in r for r in regions_raw)
    if has_ops and entry is not None:
        writer.error(
            "cannot specify both --entry (single-op) and per-region 'ops' "
            "(mixed-op) — pick one shape",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)
    if not has_ops and entry is None:
        writer.error(
            "must specify either --entry (single-op) or per-region 'ops' (mixed-op) in --regions",
            ExitCode.INVALID_INPUT,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    try:
        vocabulary = load_packs(pack_names)
    except Exception as exc:
        writer.error(
            f"failed to load packs {pack_names}: {exc}",
            ExitCode.INVALID_INPUT,
            packs=pack_names,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    workspace = resolve_workspace_or_fail(ctx, image_id)
    baseline_xmp = current_xmp(workspace)
    if baseline_xmp is None:
        writer.error(
            "workspace has no baseline snapshot to apply onto",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value)

    try:
        if has_ops:
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
            new_xmp = apply_per_region_mixed(baseline_xmp, mixed_regions, vocab=vocabulary)
            n_regions = len(mixed_regions)
            n_pairs = sum(len(r.ops) for r in mixed_regions)
            snapshot_label = (
                label if label else f"apply_per_region_mixed: {n_regions} regions, {n_pairs} ops"
            )
            shape = "mixed"
        else:
            regions = [
                RegionSpec(
                    mask_spec=r.get("mask_spec"),
                    parameter_values=r.get("parameter_values"),
                )
                for r in regions_raw
            ]
            # entry guaranteed non-None here by the dispatch validation above.
            assert entry is not None
            new_xmp = apply_per_region(baseline_xmp, entry, regions, vocab=vocabulary)
            n_regions = len(regions)
            n_pairs = n_regions
            snapshot_label = label if label else f"apply_per_region: {entry} ({n_regions} regions)"
            shape = "single"
    except BatchedApplyError as exc:
        writer.error(str(exc), ExitCode.INVALID_INPUT, entry=entry)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    try:
        new_hash = snapshot(workspace.repo, new_xmp, label=snapshot_label)
    except VersioningError as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"applied to {n_regions} regions of {image_id} ({shape}-op shape)",
        image_id=image_id,
        entry=entry,
        n_regions=n_regions,
        n_op_region_pairs=n_pairs,
        shape=shape,
        snapshot_hash=new_hash,
        state_after=summarize_state(new_xmp),
    )


# ---------------------------------------------------------------------------
# propagate-state (RFC-037)
# ---------------------------------------------------------------------------


def propagate_state_cli(
    ctx: typer.Context,
    source_image_id: str = typer.Argument(..., help="Anchor image (state propagates FROM)."),
    target: list[str] = typer.Option(
        ...,
        "--to",
        help="Target image_id (repeatable; state propagates TO).",
    ),
    exclude_op: list[str] = typer.Option(
        None,
        "--exclude-op",
        help="Operation name to skip (repeatable). Default: inherit everything.",
    ),
    include_per_image: bool = typer.Option(
        False,
        "--include-per-image",
        help=(
            "Override framing-bound auto-exclusion (drawn masks, retouch, "
            "crop, lens). Use for tripod-fixed series."
        ),
    ),
    label: str = typer.Option(None, "--label", help="Optional snapshot label."),
) -> None:
    """Propagate the source image's edit state to N target images atomically (RFC-037)."""
    from chemigram.core.propagate import PropagateError, propagate_state

    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    try:
        source_ws = resolve_workspace_or_fail(ctx, source_image_id)
    except typer.Exit as exc:
        raise typer.Exit(code=int(exc.exit_code)) from exc

    target_workspaces = []
    for tid in target:
        try:
            target_workspaces.append(resolve_workspace_or_fail(ctx, tid))
        except typer.Exit as exc:
            raise typer.Exit(code=int(exc.exit_code)) from exc

    try:
        batch = propagate_state(
            source_ws,
            target_workspaces,
            exclude_ops=exclude_op if exclude_op else None,
            include_per_image=include_per_image,
            label=label,
        )
    except PropagateError as exc:
        writer.error(str(exc), ExitCode.INVALID_INPUT, source=source_image_id)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    for r in batch.results:
        writer.event(
            "propagated",
            image_id=r.image_id,
            snapshot_hash=r.snapshot_hash,
            n_ops=len(r.applied_ops),
        )

    writer.result(
        message=(f"propagated state from {source_image_id} to {batch.n_succeeded} target(s)"),
        source_image_id=source_image_id,
        n_succeeded=batch.n_succeeded,
        n_failed=batch.n_failed,
    )


# ---------------------------------------------------------------------------
# wb-from-gray-card (survey Gap #20)
# ---------------------------------------------------------------------------


def wb_from_gray_card_cli(
    ctx: typer.Context,
    image_path: str = typer.Argument(
        ..., help="Path to rendered image (e.g., from render-preview)."
    ),
    x: int = typer.Option(..., "--x", help="Pixel x coordinate of gray-card sample."),
    y: int = typer.Option(..., "--y", help="Pixel y coordinate of gray-card sample."),
    sample_radius: int = typer.Option(
        5, "--sample-radius", help="Half-side of square sample region (default 5 → 11x11 pixels)."
    ),
) -> None:
    """Sample a gray-card region; print the temperature-primitive coefficients."""
    from pathlib import Path

    from chemigram.core.gray_card import GrayCardError, wb_from_gray_card

    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    try:
        coeffs = wb_from_gray_card(Path(image_path), x=x, y=y, sample_radius=sample_radius)
    except GrayCardError as exc:
        writer.error(str(exc), ExitCode.INVALID_INPUT)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    writer.result(
        message=(
            f"gray-card-pick at ({x}, {y}) → "
            f"red_coeff={coeffs.red_coeff:.3f}, "
            f"green_coeff={coeffs.green_coeff:.3f}, "
            f"blue_coeff={coeffs.blue_coeff:.3f}"
        ),
        red_coeff=coeffs.red_coeff,
        green_coeff=coeffs.green_coeff,
        blue_coeff=coeffs.blue_coeff,
        sampled_r=coeffs.sampled_r,
        sampled_g=coeffs.sampled_g,
        sampled_b=coeffs.sampled_b,
        sample_radius=coeffs.sample_radius,
        next_step=(
            f"chemigram apply-primitive <image_id> --entry temperature "
            f"--param red_coeff={coeffs.red_coeff:.3f} "
            f"--param green_coeff={coeffs.green_coeff:.3f} "
            f"--param blue_coeff={coeffs.blue_coeff:.3f}"
        ),
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
