"""Unit tests for chemigram.core.batched.apply_per_region_mixed (RFC-036).

Validates the mixed-op batched apply core function:

- Atomic semantics: empty / oversized / no-ops / unknown-primitive / out-of-range
  all hard-reject before any region applies.
- Multi-instance stacking with per-op multi_priority allocation.
- Composition of ops on the same mask (composed-skin-retouch shape).
- Composition of ops across different regions (eye-detail shape).
- Named-mask resolution + RFC-034 invert flag.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.batched import (
    BatchedApplyError,
    MixedRegionSpec,
    OpSpec,
    apply_per_region_mixed,
)
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"


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


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    return dataclasses.replace(parse_xmp(_BASELINE), history=())


# --- atomic-validation hard-rejects -------------------------------------


def test_empty_regions_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    with pytest.raises(BatchedApplyError, match="regions list is empty"):
        apply_per_region_mixed(empty_baseline, [], vocab=vocab)


def test_all_empty_ops_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """A batch where every region has empty ops list — total pairs = 0."""
    regions = [
        MixedRegionSpec(mask_spec=_ellipse(0.5, 0.5), ops=()),
        MixedRegionSpec(mask_spec=_ellipse(0.3, 0.3), ops=()),
    ]
    with pytest.raises(BatchedApplyError, match="empty 'ops' lists"):
        apply_per_region_mixed(empty_baseline, regions, vocab=vocab)


def test_too_many_op_region_pairs_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Exceed MAX_OP_REGION_PAIRS (64) — soft cap rejection."""
    # 8 regions * 9 ops = 72 pairs (> 64)
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(i * 0.1, 0.5),
            ops=tuple(
                OpSpec(primitive_name="exposure", parameter_values={"ev": 0.1}) for _ in range(9)
            ),
        )
        for i in range(8)
    ]
    with pytest.raises(BatchedApplyError, match="exceeds soft cap"):
        apply_per_region_mixed(empty_baseline, regions, vocab=vocab)


def test_unknown_primitive_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(0.5, 0.5),
            ops=(OpSpec(primitive_name="totally_made_up"),),
        )
    ]
    with pytest.raises(BatchedApplyError, match="not found in loaded packs"):
        apply_per_region_mixed(empty_baseline, regions, vocab=vocab)


def test_unresolved_named_mask_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    regions = [
        MixedRegionSpec(
            mask_spec={"kind": "named", "name": "mask_does_not_exist"},
            ops=(OpSpec(primitive_name="exposure", parameter_values={"ev": 0.5}),),
        )
    ]
    with pytest.raises(BatchedApplyError, match="not found"):
        apply_per_region_mixed(empty_baseline, regions, vocab=vocab)


def test_out_of_range_parameter_raises(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Atomic — second op has out-of-range value; first op must NOT apply."""
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(0.5, 0.5),
            ops=(
                OpSpec(primitive_name="exposure", parameter_values={"ev": 0.3}),
                OpSpec(primitive_name="exposure", parameter_values={"ev": 999.0}),
            ),
        )
    ]
    with pytest.raises(BatchedApplyError, match="out of range"):
        apply_per_region_mixed(empty_baseline, regions, vocab=vocab)


# --- multi-instance stacking (composed-skin-retouch shape) ------------


def test_two_ops_same_mask_both_apply(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Composed skin retouch: skin_uniformity + skin_smooth_painterly on
    one mask. Both should produce history entries; they touch different
    operations (colorequal vs bilat) so they don't collide."""
    regions = [
        MixedRegionSpec(
            mask_spec={"kind": "named", "name": "mask_skin_region"},
            ops=(
                OpSpec(primitive_name="skin_uniformity", parameter_values={"sat_orange": -0.3}),
                OpSpec(
                    primitive_name="skin_smooth_painterly",
                    parameter_values={"clarity_strength": -0.4},
                ),
            ),
        )
    ]
    result = apply_per_region_mixed(empty_baseline, regions, vocab=vocab)
    ops = {h.operation for h in result.history}
    assert "colorequal" in ops  # from skin_uniformity
    assert "bilat" in ops  # from skin_smooth_painterly


def test_same_op_across_regions_stacks(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Eye-detail-style mixed-op: exposure on each iris (2 regions, same op).
    Both should produce exposure history entries with unique multi_priority."""
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(0.4, 0.5),
            ops=(OpSpec(primitive_name="exposure", parameter_values={"ev": 0.3}),),
        ),
        MixedRegionSpec(
            mask_spec=_ellipse(0.6, 0.5),
            ops=(OpSpec(primitive_name="exposure", parameter_values={"ev": 0.3}),),
        ),
    ]
    result = apply_per_region_mixed(empty_baseline, regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 2
    multi_priorities = sorted(h.multi_priority for h in exposure_entries)
    assert len(set(multi_priorities)) == 2, (
        f"both exposure regions should have unique multi_priorities; got {multi_priorities}"
    )


def test_three_ops_per_region_two_regions_creates_six_instances(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """Eye-detail full pattern: exposure + sharpen + saturation across
    2 regions = 6 history entries total."""
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(0.4, 0.5),
            ops=(
                OpSpec(primitive_name="exposure", parameter_values={"ev": 0.3}),
                OpSpec(primitive_name="sharpen", parameter_values={"amount": 1.5}),
                OpSpec(primitive_name="hsl_saturation", parameter_values={"sat_blue": 0.2}),
            ),
        ),
        MixedRegionSpec(
            mask_spec=_ellipse(0.6, 0.5),
            ops=(
                OpSpec(primitive_name="exposure", parameter_values={"ev": 0.3}),
                OpSpec(primitive_name="sharpen", parameter_values={"amount": 1.5}),
                OpSpec(primitive_name="hsl_saturation", parameter_values={"sat_blue": 0.2}),
            ),
        ),
    ]
    result = apply_per_region_mixed(empty_baseline, regions, vocab=vocab)
    # 2 regions * 3 ops = 6 instances; each op appears twice with different
    # multi_priorities.
    counts = {}
    for h in result.history:
        counts[h.operation] = counts.get(h.operation, 0) + 1
    # The 3 touched ops (exposure, sharpen, colorequal) should each have 2
    # instances. (hsl_saturation touches colorequal.)
    assert counts.get("exposure") == 2
    assert counts.get("sharpen") == 2
    assert counts.get("colorequal") == 2


def test_named_mask_with_invert_resolves(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """RFC-032 + RFC-034 named-mask + invert in mixed-op batch."""
    regions = [
        MixedRegionSpec(
            mask_spec={"kind": "named", "name": "mask_subject", "invert": True},
            ops=(
                OpSpec(primitive_name="exposure", parameter_values={"ev": -0.4}),
                OpSpec(
                    primitive_name="bilat_clarity_strength",
                    parameter_values={"clarity_strength": -0.5},
                ),
            ),
        )
    ]
    result = apply_per_region_mixed(empty_baseline, regions, vocab=vocab)
    ops = {h.operation for h in result.history}
    assert "exposure" in ops
    assert "bilat" in ops


# --- single-region edge case --------------------------------------------


def test_single_region_single_op_works(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """One region, one op — degenerate mixed-op equivalent to single-op
    apply_per_region. Should work; both APIs produce equivalent results."""
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(0.5, 0.5),
            ops=(OpSpec(primitive_name="exposure", parameter_values={"ev": 0.3}),),
        )
    ]
    result = apply_per_region_mixed(empty_baseline, regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 1


def test_op_appearing_twice_in_one_region_stacks(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """Same primitive twice in one region's ops list — both apply with
    distinct multi_priorities (the cap of MAX_OP_REGION_PAIRS counts both)."""
    regions = [
        MixedRegionSpec(
            mask_spec=_ellipse(0.5, 0.5),
            ops=(
                OpSpec(primitive_name="exposure", parameter_values={"ev": 0.2}),
                OpSpec(primitive_name="exposure", parameter_values={"ev": 0.4}),
            ),
        )
    ]
    result = apply_per_region_mixed(empty_baseline, regions, vocab=vocab)
    exposure_entries = [h for h in result.history if h.operation == "exposure"]
    assert len(exposure_entries) == 2
    multi_priorities = sorted(h.multi_priority for h in exposure_entries)
    assert len(set(multi_priorities)) == 2
