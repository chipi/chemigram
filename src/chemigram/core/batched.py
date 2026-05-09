"""Batched per-region adjustment (RFC-031).

Provides :func:`apply_per_region` — apply one vocabulary primitive to N
mask-bound regions of an image as a single atomic operation. The
canonical use case is dodge-and-burn: brighten cheekbones, brighten nose
bridge, deepen jaw shadow, etc. — one move from the photographer's
perspective, N region-specific applications underneath.

Design highlights (per RFC-031):

- **Single-primitive restriction.** All regions must use the same
  ``primitive_name``. Mixed-op batching is deferred (the agent emits
  separate batched calls per primitive instead).
- **Atomic semantics.** All regions validate first; if any region's
  parameters or mask reference is invalid, none are applied.
- **Stack via ``multi_priority``.** Per ADR-002 / ADR-051 / Path B in
  ``synthesize_xmp``, same-op stacking is keyed on
  ``(operation, multi_priority)``. Each region is assigned a unique
  ``multi_priority`` so they all coexist as separate masked instances
  in the synthesized XMP.
- **One snapshot, one op-log entry.** Caller (MCP / CLI) snapshots the
  final XMP once; the structured op-log payload reflects the batch shape.

Soft cap: 32 regions per call. Empty batch is a hard error.
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
