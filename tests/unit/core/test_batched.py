"""Unit tests for chemigram.core.batched (RFC-031).

Validates the apply_per_region core function:

- Atomic semantics — empty / oversized / unknown-primitive / unresolved-mask
  / out-of-range parameter all hard-reject before any region applies
- Multi-instance stacking — N regions produce N module instances in the
  synthesized XMP, each with unique multi_priority (so Path B in
  synthesize_xmp appends rather than replaces)
- Mask binding — each region's mask_spec ends up on its own instance
- Named-mask resolution — RFC-032 named masks compose with batched apply
- Parameter validation — required when entry has parameters declared

These tests don't render through darktable; they verify XMP structure.
The e2e tier exercises real darktable rendering of batched XMPs.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.batched import (
    MAX_REGIONS_PER_BATCH,
    BatchedApplyError,
    RegionSpec,
    apply_per_region,
)
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE_XMP_PATH = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    """Empty-history baseline so the synthesizer's only output is the
    entries we apply in the test."""
    template = parse_xmp(_BASELINE_XMP_PATH)
    return dataclasses.replace(template, history=())


def _ellipse(cx: float, cy: float, rx: float = 0.1, ry: float = 0.1) -> dict:
    return {
        "dt_form": "ellipse",
        "dt_params": {
            "center_x": cx,
            "center_y": cy,
            "radius_x": rx,
            "radius_y": ry,
            "border": 0.02,
        },
    }


# --- atomic-validation hard-rejects -------------------------------------


def test_empty_regions_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    with pytest.raises(BatchedApplyError, match="regions list is empty"):
        apply_per_region(empty_baseline, "exposure", [], vocab=vocab)


def test_too_many_regions_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    regions = [
        RegionSpec(mask_spec=_ellipse(0.5, 0.5), parameter_values={"ev": 0.1})
        for _ in range(MAX_REGIONS_PER_BATCH + 1)
    ]
    with pytest.raises(BatchedApplyError, match="exceeds soft cap"):
        apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)


def test_unknown_primitive_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    regions = [RegionSpec(mask_spec=_ellipse(0.5, 0.5))]
    with pytest.raises(BatchedApplyError, match="not found in loaded packs"):
        apply_per_region(empty_baseline, "totally_made_up_primitive", regions, vocab=vocab)


def test_unresolved_named_mask_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    regions = [
        RegionSpec(
            mask_spec={"kind": "named", "name": "mask_does_not_exist"},
            parameter_values={"ev": 0.5},
        )
    ]
    with pytest.raises(BatchedApplyError, match="not found"):
        apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)


def test_none_mask_spec_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Per RFC-031, every region must have a mask binding — global apply is
    apply_primitive's job, not apply_per_region's."""
    bad_region = RegionSpec(mask_spec={}, parameter_values={"ev": 0.5})  # type: ignore[arg-type]
    object.__setattr__(bad_region, "mask_spec", None)  # frozen dataclass workaround
    regions = [bad_region]
    with pytest.raises(BatchedApplyError, match="mask_spec must not be None"):
        apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)


def test_out_of_range_parameter_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Atomic — second region has out-of-range value; the first region must
    not be applied either."""
    regions = [
        RegionSpec(mask_spec=_ellipse(0.3, 0.3), parameter_values={"ev": 0.5}),
        RegionSpec(mask_spec=_ellipse(0.7, 0.7), parameter_values={"ev": 999.0}),
    ]
    with pytest.raises(BatchedApplyError, match="out of range"):
        apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)


def test_unknown_parameter_name_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    regions = [RegionSpec(mask_spec=_ellipse(0.5, 0.5), parameter_values={"not_a_param": 0.5})]
    with pytest.raises(BatchedApplyError, match="unknown parameter"):
        apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)


def test_parameter_values_on_unparameterized_entry_raises(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """Find any non-parameterized entry and supply parameter_values — must
    hard-reject."""
    non_parameterized = [
        e for e in vocab.list_all() if e.parameters is None and e.mask_spec is None
    ]
    if not non_parameterized:
        pytest.skip("expressive-baseline has no non-parameterized entries to exercise this case")
    entry = non_parameterized[0]
    regions = [RegionSpec(mask_spec=_ellipse(0.5, 0.5), parameter_values={"foo": 1.0})]
    with pytest.raises(BatchedApplyError, match="has no 'parameters' declaration"):
        apply_per_region(empty_baseline, entry.name, regions, vocab=vocab)


# --- multi-instance stacking -------------------------------------------


def test_n_regions_produce_n_history_instances(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Six dodge-and-burn regions on exposure → six exposure history
    entries in the synthesized XMP, each with unique multi_priority."""
    regions = [
        RegionSpec(mask_spec=_ellipse(0.2, 0.3), parameter_values={"ev": 0.3}),
        RegionSpec(mask_spec=_ellipse(0.5, 0.3), parameter_values={"ev": 0.3}),
        RegionSpec(mask_spec=_ellipse(0.8, 0.3), parameter_values={"ev": 0.3}),
        RegionSpec(mask_spec=_ellipse(0.2, 0.7), parameter_values={"ev": -0.4}),
        RegionSpec(mask_spec=_ellipse(0.5, 0.7), parameter_values={"ev": -0.4}),
        RegionSpec(mask_spec=_ellipse(0.8, 0.7), parameter_values={"ev": -0.4}),
    ]
    result = apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 6, (
        f"expected 6 exposure history entries, got {len(exposure_entries)}: "
        f"{[(h.operation, h.multi_priority) for h in result.history]}"
    )
    multi_priorities = sorted(h.multi_priority for h in exposure_entries)
    assert multi_priorities == [1, 2, 3, 4, 5, 6], (
        f"multi_priorities should be unique 1..6; got {multi_priorities}"
    )


def test_each_region_carries_its_mask_binding(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Each region's masked instance has its own blendop_params (different
    mask_id encoded). Quick proxy: the blendop_params strings should all
    differ between instances."""
    regions = [
        RegionSpec(mask_spec=_ellipse(0.25, 0.5), parameter_values={"ev": 0.2}),
        RegionSpec(mask_spec=_ellipse(0.75, 0.5), parameter_values={"ev": 0.2}),
    ]
    result = apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 2
    blendop_a = exposure_entries[0].blendop_params
    blendop_b = exposure_entries[1].blendop_params
    assert blendop_a != blendop_b, "two different masks should produce different blendop_params"


def test_stacks_above_existing_baseline_instances(
    vocab: VocabularyIndex,
) -> None:
    """If the baseline already has an exposure entry at multi_priority=0,
    the batched regions should stack above (multi_priority >= 1)."""
    template = parse_xmp(_BASELINE_XMP_PATH)
    # Baseline already has exposure history; verify our additions don't
    # collide with it.
    pre_exposure = [h for h in template.history if h.operation == "exposure"]
    pre_max_mp = max((h.multi_priority for h in pre_exposure), default=0)

    regions = [
        RegionSpec(mask_spec=_ellipse(0.3, 0.5), parameter_values={"ev": 0.2}),
        RegionSpec(mask_spec=_ellipse(0.7, 0.5), parameter_values={"ev": 0.2}),
    ]
    result = apply_per_region(template, "exposure", regions, vocab=vocab)
    post_exposure = [h for h in result.history if h.operation == "exposure"]
    new_mps = sorted(h.multi_priority for h in post_exposure)
    # Existing baseline entries preserved + 2 new ones above the previous max
    assert len(post_exposure) == len(pre_exposure) + 2
    expected_new = {pre_max_mp + 1, pre_max_mp + 2}
    actual_mps = set(new_mps) - {h.multi_priority for h in pre_exposure}
    assert actual_mps == expected_new, (
        f"new regions should occupy multi_priority {sorted(expected_new)}; got {sorted(actual_mps)}"
    )


# --- named-mask composition (RFC-032 + RFC-031) ------------------------


def test_named_mask_resolves_in_batch(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """A region with mask_spec={"kind": "named", "name": "mask_skin_region"}
    resolves correctly during batch validation and produces a parametric
    instance in the synthesized XMP."""
    regions = [
        RegionSpec(
            mask_spec={"kind": "named", "name": "mask_skin_region"},
            parameter_values={"ev": 0.2},
        )
    ]
    result = apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 1
    # Resolved spec is parametric (range_filter), so the instance carries
    # parametric mask binding in blendop_params (no masks_history needed).
    assert exposure_entries[0].blendop_params  # non-empty


def test_mixed_named_and_drawn_masks(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Some regions named, some inline drawn. Both should resolve and stack."""
    regions = [
        RegionSpec(
            mask_spec={"kind": "named", "name": "mask_luminosity_brightest_quartile"},
            parameter_values={"ev": -0.3},
        ),
        RegionSpec(
            mask_spec=_ellipse(0.5, 0.5),
            parameter_values={"ev": 0.2},
        ),
    ]
    result = apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 2
    multi_priorities = sorted(h.multi_priority for h in exposure_entries)
    assert multi_priorities == [1, 2]


# --- single-region edge case -------------------------------------------


def test_single_region_works(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """One-region batch is valid (and useful for atomic semantics on a
    single masked move). Should produce one history entry."""
    regions = [RegionSpec(mask_spec=_ellipse(0.5, 0.5), parameter_values={"ev": 0.3})]
    result = apply_per_region(empty_baseline, "exposure", regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 1
    assert exposure_entries[0].multi_priority == 1
