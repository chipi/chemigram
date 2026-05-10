"""Batched per-region adjustment (RFC-031, RFC-036).

Provides two related functions:

- :func:`apply_per_region` — RFC-031 single-primitive batched apply.
  Apply ONE vocabulary primitive to N mask-bound regions atomically.
  Canonical use case: dodge-and-burn (single primitive `exposure`,
  varied across regions).
- :func:`apply_per_region_mixed` — RFC-036 mixed-op batched apply.
  Apply MULTIPLE primitives to (possibly multiple) mask-bound regions
  atomically. Each region carries its own ``ops`` list. Canonical use
  cases: composed skin retouch (skin_uniformity + skin_smooth_painterly
  on mask_skin_region in one move) and eye-detail lift (exposure +
  sharpening + saturation on the eye region).

Design highlights (shared across both):

- **Atomic semantics.** All regions / ops validate first; any failure
  aborts the entire batch (no partial state).
- **Stack via ``multi_priority``.** Per ADR-002 / ADR-051 / Path B in
  ``synthesize_xmp``, same-op stacking is keyed on
  ``(operation, multi_priority)``. Each (op, region) pair is assigned
  a unique ``multi_priority`` so all instances coexist as separate
  masked entries in the synthesized XMP.
- **One snapshot per call.** Caller (MCP / CLI) snapshots the final
  XMP once; the structured op-log payload reflects the batch shape.

Soft caps:
- :func:`apply_per_region` — 32 regions per call (RFC-031).
- :func:`apply_per_region_mixed` — 64 (op * region) pairs total (RFC-036),
  bounded to catch agent bugs while leaving room for "5 regions * 3 ops"
  composed-skin-retouch patterns.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from chemigram.core.helpers import apply_with_mask
from chemigram.core.vocab import VocabError, VocabularyIndex, resolve_named_mask_spec
from chemigram.core.xmp import Xmp

# Soft cap on regions per batch (RFC-031 §Open questions). Real workflows
# top out at ~15-20 regions; 32 is a generous-but-finite upper bound that
# catches obviously-broken agent output (e.g. emitting 200 regions).
MAX_REGIONS_PER_BATCH = 32

# Soft cap on (op * region) pairs in a mixed-op batch (RFC-036). 5 regions
# * 3 ops = 15 typical eye-detail or composed-skin shape; 64 leaves
# significant headroom while bounding obviously-broken agent emission.
MAX_OP_REGION_PAIRS = 64


class BatchedApplyError(Exception):
    """Raised when an :func:`apply_per_region` call fails validation."""


@dataclasses.dataclass(frozen=True)
class RegionSpec:
    """One region in an :func:`apply_per_region` batch.

    ``mask_spec`` is the apply-time mask spec (drawn / parametric / named
    via RFC-032). ``parameter_values`` is optional per-region parameter
    overrides; required when the primitive declares parameters.
    """

    mask_spec: dict[str, Any]
    parameter_values: dict[str, float] | None = None


@dataclasses.dataclass(frozen=True)
class OpSpec:
    """One operation in a mixed-op region (RFC-036).

    Each region in :func:`apply_per_region_mixed` carries an ``ops`` list
    where each element is an OpSpec — primitive name + optional parameter
    values. Order within a region is preserved at apply time (ops are
    applied in list order against the same mask).
    """

    primitive_name: str
    parameter_values: dict[str, float] | None = None


@dataclasses.dataclass(frozen=True)
class MixedRegionSpec:
    """One region in an :func:`apply_per_region_mixed` batch (RFC-036).

    ``mask_spec`` scopes the region (drawn / parametric / named via
    RFC-032). ``ops`` is the ordered list of primitives applied to that
    region. Same op may appear twice in one region's ops list (each gets
    its own multi_priority); same primitive across multiple regions also
    stacks via per-(op, region) multi_priority allocation.
    """

    mask_spec: dict[str, Any]
    ops: tuple[OpSpec, ...]


def apply_per_region(
    baseline: Xmp,
    primitive_name: str,
    regions: list[RegionSpec],
    *,
    vocab: VocabularyIndex,
) -> Xmp:
    """Apply ``primitive_name`` to N mask-bound regions atomically.

    Args:
        baseline: The current XMP to apply onto.
        primitive_name: Name of the vocabulary entry to apply; must
            exist in ``vocab``.
        regions: One or more :class:`RegionSpec`. Each describes a
            mask + (optional) parameter override pair.
        vocab: The :class:`VocabularyIndex` to resolve the primitive
            and any named-mask references against.

    Returns:
        A new :class:`Xmp` with N module instances of the primitive's
        operation(s) — one per region — each bound to its own mask.
        Each instance carries a unique ``multi_priority`` so the
        synthesizer's same-op detector treats them as distinct (Path B).

    Raises:
        BatchedApplyError: regions list is empty, exceeds the soft cap,
            references an unknown primitive, supplies parameter_values
            without parameters declared, or any region's mask
            resolution / parameter validation fails. Atomic — if any
            region fails validation, no regions are applied.
    """
    _validate_batch_shape(primitive_name, regions, vocab)
    entry = vocab.lookup_by_name(primitive_name)
    assert entry is not None  # validated above

    # Resolve named masks + validate parameter values for every region
    # BEFORE applying any (atomic semantics).
    resolved = []
    for idx, region in enumerate(regions):
        try:
            resolved_spec = resolve_named_mask_spec(region.mask_spec, vocab)
        except VocabError as exc:
            raise BatchedApplyError(f"region {idx}: {exc}") from exc
        if resolved_spec is None:
            raise BatchedApplyError(
                f"region {idx}: mask_spec must not be None — every region "
                f"in a batched apply needs a mask binding"
            )
        _validate_region_parameters(entry, region, idx)
        resolved.append((resolved_spec, region.parameter_values))

    # Find the highest multi_priority for this primitive's operations in
    # the baseline; new regions stack above. This gives stable ordering
    # against an existing per-image edit and avoids colliding with any
    # prior masked instances (e.g. from a previous apply_per_region call).
    base_max_mp = _max_multi_priority_for_ops(baseline, entry.touches)

    # Apply each region in sequence, threading the previous result as the
    # next baseline. Each gets a unique multi_priority so Path B in
    # synthesize_xmp appends rather than replaces.
    new_xmp = baseline
    for region_idx, (resolved_spec, parameter_values) in enumerate(resolved):
        per_region_mp = base_max_mp + 1 + region_idx
        dtstyle = _prepare_dtstyle_for_region(
            entry,
            parameter_values,
            multi_priority=per_region_mp,
        )
        new_xmp = apply_with_mask(new_xmp, dtstyle, resolved_spec)

    return new_xmp


def _validate_batch_shape(
    primitive_name: str,
    regions: list[RegionSpec],
    vocab: VocabularyIndex,
) -> None:
    """Hard-reject empty batches, oversized batches, and unknown primitives."""
    if not regions:
        raise BatchedApplyError(
            "regions list is empty; apply_per_region requires at least one region "
            "(use apply_primitive for a global apply)"
        )
    if len(regions) > MAX_REGIONS_PER_BATCH:
        raise BatchedApplyError(
            f"regions count ({len(regions)}) exceeds soft cap "
            f"({MAX_REGIONS_PER_BATCH}); split the batch or revisit the workflow"
        )
    entry = vocab.lookup_by_name(primitive_name)
    if entry is None:
        raise BatchedApplyError(f"primitive {primitive_name!r} not found in loaded packs")


def _validate_region_parameters(
    entry: Any,  # VocabEntry
    region: RegionSpec,
    region_idx: int,
) -> None:
    """Validate parameter_values match the entry's declared parameter shape.

    Hard-rejects: caller passed parameter_values for a non-parameterized
    entry, or values fall outside the declared range. Mirrors the same
    validation that ``apply_entry`` does in the single-region path so
    the batched path doesn't bypass the contract.
    """
    if region.parameter_values is None:
        return
    if entry.parameters is None:
        raise BatchedApplyError(
            f"region {region_idx}: entry {entry.name!r} has no 'parameters' "
            f"declaration but parameter_values were supplied: "
            f"{region.parameter_values!r}"
        )
    declared = {p.name: p for p in entry.parameters}
    for name, value in region.parameter_values.items():
        if name not in declared:
            raise BatchedApplyError(
                f"region {region_idx}: unknown parameter {name!r} for entry "
                f"{entry.name!r}; declared parameters: {sorted(declared)}"
            )
        spec = declared[name]
        lo, hi = spec.range
        if not (lo <= float(value) <= hi):
            raise BatchedApplyError(
                f"region {region_idx}: parameter {name!r} value {value} "
                f"out of range [{lo}, {hi}] for entry {entry.name!r}"
            )


def _max_multi_priority_for_ops(baseline: Xmp, ops: tuple[str, ...]) -> int:
    """Highest ``multi_priority`` among baseline history entries whose
    operation appears in ``ops``. Returns 0 if nothing matches — the
    baseline either has no entries for these ops, or the entries are at
    the default priority. Either way, the next free slot is 1.
    """
    op_set = set(ops)
    highest = 0
    for entry in baseline.history:
        if entry.operation in op_set and entry.multi_priority > highest:
            highest = entry.multi_priority
    return highest


def _prepare_dtstyle_for_region(
    entry: Any,  # VocabEntry
    parameter_values: dict[str, float] | None,
    *,
    multi_priority: int,
) -> Any:
    """Return a fresh dtstyle with parameter values applied (if any) and
    every plugin's ``multi_priority`` set to the per-region value.

    The multi_priority assignment is what makes regions stack rather than
    replace (per Path B in :func:`synthesize_xmp` — keyed on the
    ``(operation, multi_priority)`` tuple).
    """
    from chemigram.core.helpers import _apply_parameter_values_to_dtstyle

    dtstyle = entry.dtstyle
    if parameter_values:
        dtstyle = _apply_parameter_values_to_dtstyle(dtstyle, entry.parameters, parameter_values)
    new_plugins = tuple(
        dataclasses.replace(p, multi_priority=multi_priority) for p in dtstyle.plugins
    )
    return dataclasses.replace(dtstyle, plugins=new_plugins)


# ---------------------------------------------------------------------------
# RFC-036 — mixed-op batched apply
# ---------------------------------------------------------------------------


def apply_per_region_mixed(
    baseline: Xmp,
    regions: list[MixedRegionSpec],
    *,
    vocab: VocabularyIndex,
) -> Xmp:
    """Apply N (op * region) pairs atomically (RFC-036).

    Extension of :func:`apply_per_region` — each region carries its own
    ``ops`` list. Canonical use cases: composed skin retouch
    (skin_uniformity + skin_smooth_painterly on one mask) and eye-detail
    lift (exposure + sharpening + saturation on the eye region).

    Args:
        baseline: The current XMP to apply onto.
        regions: One or more :class:`MixedRegionSpec`. Each carries a
            mask + an ordered list of ops. Soft cap: total (op * region)
            pairs ≤ MAX_OP_REGION_PAIRS.
        vocab: The :class:`VocabularyIndex` to resolve primitives + named
            masks against.

    Returns:
        A new :class:`Xmp` with one masked instance per (op, region) pair.
        Per-op multi_priority allocation is independent (exposure regions
        stack among themselves; sigmoid regions stack among themselves;
        cross-op pairs don't collide because the synthesizer keys on the
        (operation, multi_priority) tuple).

    Raises:
        BatchedApplyError: validation fails. Atomic — no region applied
        on any failure.
    """
    _validate_mixed_batch_shape(regions, vocab)

    # Resolve named masks + validate parameter values for every (op, region)
    # pair BEFORE applying any (atomic semantics).
    resolved: list[tuple[dict[str, Any], list[tuple[Any, dict[str, float] | None]]]] = []
    for region_idx, region in enumerate(regions):
        try:
            resolved_spec = resolve_named_mask_spec(region.mask_spec, vocab)
        except VocabError as exc:
            raise BatchedApplyError(f"region {region_idx}: {exc}") from exc
        if resolved_spec is None:
            raise BatchedApplyError(
                f"region {region_idx}: mask_spec must not be None — every region "
                f"in a mixed-op batched apply needs a mask binding"
            )
        ops_resolved: list[tuple[Any, dict[str, float] | None]] = []
        for op_idx, op in enumerate(region.ops):
            entry = vocab.lookup_by_name(op.primitive_name)
            if entry is None:
                raise BatchedApplyError(
                    f"region {region_idx} op {op_idx}: primitive "
                    f"{op.primitive_name!r} not found in loaded packs"
                )
            _validate_mixed_op_parameters(entry, op, region_idx, op_idx)
            ops_resolved.append((entry, op.parameter_values))
        resolved.append((resolved_spec, ops_resolved))

    # Allocate multi_priority per op independently. For each (op, region),
    # the multi_priority is op_baseline_max + 1 + (region_index_for_this_op).
    # Keeps operations of different types from colliding while stacking
    # same-op regions.
    op_baseline_max: dict[str, int] = {}
    op_region_counter: dict[str, int] = {}

    new_xmp = baseline
    from chemigram.core.helpers import apply_with_mask

    for resolved_spec, ops_resolved in resolved:
        for entry, parameter_values in ops_resolved:
            for op_name in entry.touches:
                if op_name not in op_baseline_max:
                    op_baseline_max[op_name] = _max_multi_priority_for_ops(baseline, (op_name,))
                    op_region_counter[op_name] = 0
                op_region_counter[op_name] += 1
            # Use the entry's primary touched op to allocate a single
            # multi_priority per (op, region) pair. For multi-touch
            # entries (rare in mixed-op contexts), all plugins get the
            # same per-pair priority.
            primary_op = entry.touches[0]
            per_pair_mp = op_baseline_max[primary_op] + op_region_counter[primary_op]

            dtstyle = _prepare_dtstyle_for_region(
                entry,
                parameter_values,
                multi_priority=per_pair_mp,
            )
            new_xmp = apply_with_mask(new_xmp, dtstyle, resolved_spec)

    return new_xmp


def _validate_mixed_batch_shape(
    regions: list[MixedRegionSpec],
    vocab: VocabularyIndex,
) -> None:
    """Hard-reject empty / oversized mixed-op batches and unknown primitives."""
    if not regions:
        raise BatchedApplyError(
            "regions list is empty; apply_per_region_mixed requires at least one region"
        )
    total_pairs = sum(len(r.ops) for r in regions)
    if total_pairs == 0:
        raise BatchedApplyError(
            "all regions have empty 'ops' lists; apply_per_region_mixed requires "
            "at least one op per region (use apply_per_region for region-only "
            "single-op batches)"
        )
    if total_pairs > MAX_OP_REGION_PAIRS:
        raise BatchedApplyError(
            f"total (op * region) pair count ({total_pairs}) exceeds soft cap "
            f"({MAX_OP_REGION_PAIRS}); split the batch or revisit the workflow"
        )


def _validate_mixed_op_parameters(
    entry: Any,  # VocabEntry
    op: OpSpec,
    region_idx: int,
    op_idx: int,
) -> None:
    """Validate parameter_values match the entry's parameter shape."""
    if op.parameter_values is None:
        return
    if entry.parameters is None:
        raise BatchedApplyError(
            f"region {region_idx} op {op_idx}: entry {entry.name!r} has no "
            f"'parameters' declaration but parameter_values were supplied: "
            f"{op.parameter_values!r}"
        )
    declared = {p.name: p for p in entry.parameters}
    for name, value in op.parameter_values.items():
        if name not in declared:
            raise BatchedApplyError(
                f"region {region_idx} op {op_idx}: unknown parameter "
                f"{name!r} for entry {entry.name!r}; declared parameters: "
                f"{sorted(declared)}"
            )
        spec = declared[name]
        lo, hi = spec.range
        if not (lo <= float(value) <= hi):
            raise BatchedApplyError(
                f"region {region_idx} op {op_idx}: parameter {name!r} "
                f"value {value} out of range [{lo}, {hi}] for entry "
                f"{entry.name!r}"
            )
