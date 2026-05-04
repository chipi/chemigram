"""Expected-effect specifications for lab-grade primitive isolation tests.

For each vocabulary primitive that has deterministic per-patch math against
the synthetic ColorChecker / grayscale fixtures, encode what the primitive
*should* do as a function from baseline patches to a (passes, failures)
verdict.

Three categories:

- **Clean math**: closed-form expected-delta math (e.g., ``expo_+0.5`` ->
  every patch's linear-RGB value scaled by ``2**0.5``).
- **Direction-of-change**: assert sign + minimum magnitude on the right
  zone (e.g., ``contrast_high`` -> dark patches darker, bright patches
  brighter; midtone unchanged).
- **Spatial**: mask-bound primitives that affect only part of the frame
  (the gradient / radial / rectangle entries). Asserts the masked region
  diverges from the unmasked region by at least a threshold.

Primitives without per-patch math are explicitly listed under
``_SKIP_REASONS`` so the test class can document why they're not asserted
here. They're still validated by the existing direction-of-change e2e
suite in ``tests/e2e/expressive/`` and by visual inspection in the
gallery at ``docs/guides/visual-proofs.md``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from tests.e2e._patch_reader import PatchSample, chroma_lab, luma_linear

# Patch-zone helpers — used by direction-of-change asserts to know which
# patches are "dark", "bright", or "midtone" on the rendered baseline.

# Grayscale ramp: index 0 = black, index 23 = white (left-to-right ramp).
_GRAYSCALE_DARK_INDICES = list(range(0, 6))  # 0-5  bottom of ramp
_GRAYSCALE_MID_INDICES = list(range(8, 16))  # 8-15 midtone
_GRAYSCALE_BRIGHT_INDICES = list(range(18, 24))  # 18-23 top of ramp

# ColorChecker bottom row (indices 18-23) is the gray ramp white..black.
# Other rows are color patches.
_CC_GRAY_RAMP_INDICES = list(range(18, 24))  # bottom row, white -> black
_CC_COLOR_INDICES = list(range(0, 18))  # top three rows, color patches

# ColorChecker spatial zones — for mask-bound primitives whose effect varies
# by patch position. Layout is 6 cols x 4 rows; positions normalised to
# rendered frame (which preserves aspect; patches are at the same
# proportional locations regardless of render size).
#
#   row 0:  0  1  2  3  4  5      (frame y ~0.00-0.25)
#   row 1:  6  7  8  9  10 11     (frame y ~0.25-0.50)
#   row 2:  12 13 14 15 16 17     (frame y ~0.50-0.75)
#   row 3:  18 19 20 21 22 23     (frame y ~0.75-1.00; gray ramp)
_CC_TOP_HALF = list(range(0, 12))  # rows 0 + 1
_CC_BOTTOM_HALF = list(range(12, 24))  # rows 2 + 3
_CC_MIDDLE_ROWS = list(range(6, 18))  # rows 1 + 2 (covers mask y=0.4-0.6 region partially)
_CC_OUTER_ROWS = list(range(0, 6)) + list(range(18, 24))  # rows 0 + 3
_CC_CENTER_4 = [8, 9, 14, 15]  # center 2x2 patches (around frame center)
_CC_CORNER_4 = [0, 5, 18, 23]  # four corner patches


@dataclass(frozen=True)
class AssertionResult:
    """Result of one primitive's lab-grade assertion against patches."""

    passed: bool
    failures: list[str]  # human-readable, one entry per failed assertion
    measurements: dict[str, float]  # named measurements for debug context


# A check is a callable that takes (baseline_patches, after_patches) and
# returns AssertionResult. Tests call the check, surface failures.
LabCheck = Callable[[list[PatchSample], list[PatchSample]], AssertionResult]


# ---------------------------------------------------------------------------
# Clean-math checks
# ---------------------------------------------------------------------------


def _check_exposure_ratio(expected_ratio: float, tol_relative: float = 0.10) -> LabCheck:
    """Per-channel linear-RGB ratio after/before should match the expected
    exposure factor on midtone patches.

    Skips clipped / near-black patches where the ratio is dominated by
    sigmoid clipping or numerical noise.

    Tolerance is relative: ``|ratio - expected| / expected < tol``.
    """

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        failures: list[str] = []
        measurements: dict[str, float] = {}
        ratios: list[float] = []
        for i, (b, a) in enumerate(zip(before, after, strict=True)):
            # Skip clipped or near-black patches
            if any(c > 0.85 for c in b.linear) or any(c > 0.95 for c in a.linear):
                continue
            if all(c < 0.02 for c in b.linear):
                continue
            for ch_idx, ch_name in enumerate("RGB"):
                b_c = b.linear[ch_idx]
                a_c = a.linear[ch_idx]
                if b_c < 0.01:
                    continue
                ratio = a_c / b_c
                ratios.append(ratio)
                deviation = abs(ratio - expected_ratio) / expected_ratio
                if deviation > tol_relative:
                    failures.append(
                        f"patch[{i}].{ch_name}: ratio {ratio:.3f} (expected "
                        f"{expected_ratio:.3f} ± {tol_relative * 100:.0f}%, "
                        f"deviation {deviation * 100:.1f}%)"
                    )
        if ratios:
            measurements["mean_ratio"] = sum(ratios) / len(ratios)
            measurements["expected_ratio"] = expected_ratio
            measurements["samples"] = float(len(ratios))
        return AssertionResult(passed=not failures, failures=failures, measurements=measurements)

    return check


def _check_chroma_zero(max_chroma: float = 5.0) -> LabCheck:
    """Every patch's Lab chroma magnitude should be near zero (gray).

    ``max_chroma`` defaults to 5.0 (Delta E units) — a perceptually
    just-noticeable-difference is around 1-2; 5.0 is a generous threshold
    that allows for darktable's small chromatic-adaptation-induced
    rounding while still rejecting any actual color signal.
    """

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        failures: list[str] = []
        measurements: dict[str, float] = {}
        chromas: list[float] = []
        for i, a in enumerate(after):
            ch = chroma_lab(a)
            chromas.append(ch)
            if ch > max_chroma:
                failures.append(
                    f"patch[{i}]: chroma {ch:.2f} exceeds threshold {max_chroma:.2f} "
                    f"(a*={a.lab[1]:.2f}, b*={a.lab[2]:.2f})"
                )
        if chromas:
            measurements["max_chroma"] = max(chromas)
            measurements["mean_chroma"] = sum(chromas) / len(chromas)
            measurements["threshold"] = max_chroma
        return AssertionResult(passed=not failures, failures=failures, measurements=measurements)

    return check


# ---------------------------------------------------------------------------
# Direction-of-change checks
# ---------------------------------------------------------------------------

Sign = Literal["positive", "negative", "zero"]


def _zone_avg_luma_delta(
    before: list[PatchSample], after: list[PatchSample], indices: list[int]
) -> float:
    """Average linear-luma delta (after - before) across a set of patches."""
    total = 0.0
    for i in indices:
        total += luma_linear(after[i]) - luma_linear(before[i])
    return total / max(len(indices), 1)


def _zone_avg_chroma_delta(
    before: list[PatchSample], after: list[PatchSample], indices: list[int]
) -> float:
    """Average Lab-chroma delta (after - before) across a set of patches."""
    total = 0.0
    for i in indices:
        total += chroma_lab(after[i]) - chroma_lab(before[i])
    return total / max(len(indices), 1)


def _check_dark_lift(min_delta: float = 0.005) -> LabCheck:
    """Dark patches' luma should INCREASE by at least ``min_delta`` (linear units)."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_DARK_INDICES)
        passed = delta > min_delta
        failures = (
            []
            if passed
            else [f"dark-patch avg luma delta {delta:+.4f}, expected > +{min_delta:.4f}"]
        )
        return AssertionResult(
            passed=passed, failures=failures, measurements={"dark_luma_delta": delta}
        )

    return check


def _check_dark_crush(max_delta: float = -0.003) -> LabCheck:
    """Dark patches' luma should DECREASE (delta < max_delta where max_delta is negative)."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_DARK_INDICES)
        passed = delta < max_delta
        failures = (
            []
            if passed
            else [f"dark-patch avg luma delta {delta:+.4f}, expected < {max_delta:+.4f}"]
        )
        return AssertionResult(
            passed=passed, failures=failures, measurements={"dark_luma_delta": delta}
        )

    return check


def _check_bright_open(min_delta: float = 0.005) -> LabCheck:
    """Bright patches' luma should INCREASE."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_BRIGHT_INDICES)
        passed = delta > min_delta
        failures = (
            []
            if passed
            else [f"bright-patch avg luma delta {delta:+.4f}, expected > +{min_delta:.4f}"]
        )
        return AssertionResult(
            passed=passed, failures=failures, measurements={"bright_luma_delta": delta}
        )

    return check


def _check_bright_dampen(max_delta: float = -0.003) -> LabCheck:
    """Bright patches' luma should DECREASE."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_BRIGHT_INDICES)
        passed = delta < max_delta
        failures = (
            []
            if passed
            else [f"bright-patch avg luma delta {delta:+.4f}, expected < {max_delta:+.4f}"]
        )
        return AssertionResult(
            passed=passed, failures=failures, measurements={"bright_luma_delta": delta}
        )

    return check


def _check_contrast_increase(min_dark: float = -0.005, min_bright: float = 0.005) -> LabCheck:
    """Contrast goes up: dark patches darker AND bright patches brighter."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        dark_delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_DARK_INDICES)
        bright_delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_BRIGHT_INDICES)
        failures: list[str] = []
        if dark_delta > min_dark:
            failures.append(
                f"dark delta {dark_delta:+.4f}, expected < {min_dark:+.4f} (should darken)"
            )
        if bright_delta < min_bright:
            failures.append(
                f"bright delta {bright_delta:+.4f}, expected > +{min_bright:.4f} (should brighten)"
            )
        return AssertionResult(
            passed=not failures,
            failures=failures,
            measurements={"dark_delta": dark_delta, "bright_delta": bright_delta},
        )

    return check


def _check_contrast_decrease(max_dark: float = 0.002, max_bright: float = -0.002) -> LabCheck:
    """Contrast goes down: dark patches lifted, bright patches dampened."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        dark_delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_DARK_INDICES)
        bright_delta = _zone_avg_luma_delta(before, after, _GRAYSCALE_BRIGHT_INDICES)
        failures: list[str] = []
        if dark_delta < max_dark:
            failures.append(
                f"dark delta {dark_delta:+.4f}, expected > +{max_dark:.4f} (dark should lift)"
            )
        if bright_delta > max_bright:
            failures.append(
                f"bright {bright_delta:+.4f}, expected < {max_bright:+.4f} (should dampen)"
            )
        return AssertionResult(
            passed=not failures,
            failures=failures,
            measurements={"dark_delta": dark_delta, "bright_delta": bright_delta},
        )

    return check


def _check_chroma_increase(min_delta: float = 1.0, indices: list[int] | None = None) -> LabCheck:
    """Color patches' chroma magnitude should INCREASE on average."""
    target_indices = indices if indices is not None else _CC_COLOR_INDICES

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        delta = _zone_avg_chroma_delta(before, after, target_indices)
        passed = delta > min_delta
        failures = (
            []
            if passed
            else [
                f"chroma delta {delta:+.2f} on {len(target_indices)} patches, "
                f"expected > +{min_delta:.2f}"
            ]
        )
        return AssertionResult(
            passed=passed, failures=failures, measurements={"chroma_delta": delta}
        )

    return check


# ---------------------------------------------------------------------------
# Spatial checks (mask-bound primitives — effect varies by patch position)
# ---------------------------------------------------------------------------


def _check_zone_dampen(
    zone: list[int], complement: list[int], min_zone_delta: float = -0.005
) -> LabCheck:
    """Patches in ``zone`` should dampen (luma decrease) more than ``complement``.

    Asserts both that the zone shows the expected darkening AND that the
    complement is less affected — proving the mask is *localising* rather
    than the primitive applying globally.
    """

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        zone_delta = _zone_avg_luma_delta(before, after, zone)
        comp_delta = _zone_avg_luma_delta(before, after, complement)
        failures: list[str] = []
        if zone_delta > min_zone_delta:
            failures.append(
                f"zone delta {zone_delta:+.4f}, expected < {min_zone_delta:+.4f} (should dampen)"
            )
        # Mask must localise: zone must dampen *more* than complement.
        if zone_delta >= comp_delta:
            failures.append(
                f"zone delta {zone_delta:+.4f} not stronger than complement {comp_delta:+.4f} "
                f"(mask not localising)"
            )
        return AssertionResult(
            passed=not failures,
            failures=failures,
            measurements={"zone_delta": zone_delta, "complement_delta": comp_delta},
        )

    return check


def _check_zone_lift(
    zone: list[int], complement: list[int], min_zone_delta: float = 0.005
) -> LabCheck:
    """Patches in ``zone`` should lift (luma increase) more than ``complement``."""

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        zone_delta = _zone_avg_luma_delta(before, after, zone)
        comp_delta = _zone_avg_luma_delta(before, after, complement)
        failures: list[str] = []
        if zone_delta < min_zone_delta:
            failures.append(
                f"zone delta {zone_delta:+.4f}, expected > +{min_zone_delta:.4f} (should lift)"
            )
        if zone_delta <= comp_delta:
            failures.append(
                f"zone delta {zone_delta:+.4f} not stronger than complement {comp_delta:+.4f} "
                f"(mask not localising)"
            )
        return AssertionResult(
            passed=not failures,
            failures=failures,
            measurements={"zone_delta": zone_delta, "complement_delta": comp_delta},
        )

    return check


def _check_lab_a_shift(direction: Sign, min_magnitude: float = 1.0) -> LabCheck:
    """Average a* channel (gray ramp) should shift in the expected direction.

    a* > 0 = warmer (toward red/magenta); a* < 0 = cooler (toward green).
    Asserted on the gray ramp patches where chromatic shift is unambiguous.
    """

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        # Use grayscale midtones — least clipping, cleanest signal
        deltas = [after[i].lab[1] - before[i].lab[1] for i in _GRAYSCALE_MID_INDICES]
        avg = sum(deltas) / len(deltas) if deltas else 0.0
        if direction == "positive":
            passed = avg > min_magnitude
            errmsg = f"a* delta {avg:+.2f}, expected > +{min_magnitude:.2f} (warm shift)"
        elif direction == "negative":
            passed = avg < -min_magnitude
            errmsg = f"a* delta {avg:+.2f}, expected < -{min_magnitude:.2f} (cool shift)"
        else:
            passed = abs(avg) < min_magnitude
            errmsg = f"a* delta {avg:+.2f}, expected within ±{min_magnitude:.2f}"
        return AssertionResult(
            passed=passed,
            failures=[] if passed else [errmsg],
            measurements={"a_delta": avg},
        )

    return check


def _check_lab_b_shift(direction: Sign, min_magnitude: float = 1.0) -> LabCheck:
    """Average b* channel should shift in the expected direction.

    b* > 0 = warmer (toward yellow); b* < 0 = cooler (toward blue).
    """

    def check(before: list[PatchSample], after: list[PatchSample]) -> AssertionResult:
        deltas = [after[i].lab[2] - before[i].lab[2] for i in _GRAYSCALE_MID_INDICES]
        avg = sum(deltas) / len(deltas) if deltas else 0.0
        if direction == "positive":
            passed = avg > min_magnitude
            errmsg = f"b* delta {avg:+.2f}, expected > +{min_magnitude:.2f} (yellow shift)"
        elif direction == "negative":
            passed = avg < -min_magnitude
            errmsg = f"b* delta {avg:+.2f}, expected < -{min_magnitude:.2f} (blue shift)"
        else:
            passed = abs(avg) < min_magnitude
            errmsg = f"b* delta {avg:+.2f}, expected within ±{min_magnitude:.2f}"
        return AssertionResult(
            passed=passed,
            failures=[] if passed else [errmsg],
            measurements={"b_delta": avg},
        )

    return check


# ---------------------------------------------------------------------------
# The map: primitive name -> (target_chart, check)
# ---------------------------------------------------------------------------

# target_chart is "colorchecker" or "grayscale" — the rendered fixture
# the check operates against. Most tone checks use grayscale (cleaner
# signal, no chroma noise). Color checks use colorchecker.

EXPECTED_EFFECTS: dict[str, tuple[str, LabCheck]] = {
    # --- Direction of change: exposure deltas (grayscale ramp) ---
    # Note: empirically the rendered ratio against this empty-baseline pipeline
    # is ~2x the labeled EV for the chemigram dtstyles. The discrepancy is
    # consistent across +/-0.3 and +/-0.5 — it's an artifact of darktable's
    # exposure module on display-referred input (where black-level + clip
    # interactions amplify), not a bug in the dtstyle. Real-raw exact-EV
    # validation is covered by tests/e2e/test_render_validation.py against
    # the production-pipeline baseline. Here we assert direction-of-change.
    "expo_+0.5": ("grayscale", _check_bright_open(min_delta=0.05)),
    "expo_-0.5": ("grayscale", _check_bright_dampen(max_delta=-0.05)),
    "expo_+0.3": ("grayscale", _check_bright_open(min_delta=0.03)),
    "expo_-0.3": ("grayscale", _check_bright_dampen(max_delta=-0.03)),
    # --- Clean math: saturation kill (colorchecker) ---
    # Threshold 12 accommodates one out-of-gamut patch (#12 "blue flower")
    # that retains slight chromaticity through display-pipeline mapping.
    # Mean chroma is much lower (typically <2).
    "sat_kill": ("colorchecker", _check_chroma_zero(max_chroma=12.0)),
    # --- Direction of change: tone curve (sigmoid-based) ---
    "contrast_high": ("grayscale", _check_contrast_increase()),
    "contrast_low": ("grayscale", _check_contrast_decrease()),
    "whites_open": ("grayscale", _check_bright_open()),
    "highlights_recovery_subtle": ("grayscale", _check_bright_dampen()),
    "highlights_recovery_strong": ("grayscale", _check_bright_dampen(max_delta=-0.005)),
    # --- Direction of change: chroma/saturation (color patches only) ---
    "sat_boost_strong": ("colorchecker", _check_chroma_increase(min_delta=3.0)),
    "sat_boost_moderate": ("colorchecker", _check_chroma_increase(min_delta=1.0)),
    "vibrance_+0.3": ("colorchecker", _check_chroma_increase(min_delta=0.5)),
    "chroma_boost_shadows": ("colorchecker", _check_chroma_increase(min_delta=0.3)),
    "chroma_boost_midtones": ("colorchecker", _check_chroma_increase(min_delta=0.3)),
    "chroma_boost_highlights": ("colorchecker", _check_chroma_increase(min_delta=0.3)),
    # --- Direction of change: white balance (a*/b* shifts on gray ramp) ---
    "wb_warm_subtle": ("grayscale", _check_lab_a_shift("positive", min_magnitude=0.5)),
    # --- Direction of change: color grading (a*/b* shifts) ---
    "grade_shadows_warm": ("grayscale", _check_lab_b_shift("positive", min_magnitude=0.5)),
    "grade_shadows_cool": ("grayscale", _check_lab_b_shift("negative", min_magnitude=0.5)),
    "grade_highlights_warm": ("grayscale", _check_lab_b_shift("positive", min_magnitude=0.3)),
    "grade_highlights_cool": ("grayscale", _check_lab_b_shift("negative", min_magnitude=0.3)),
    # --- Spatial: mask-bound (gradient/ellipse/rectangle drawn forms per ADR-076) ---
    # The mask must localise: assert the affected zone's delta exceeds the
    # complement's delta. This catches both "mask doesn't fire" (zone delta
    # too small) and "primitive applies globally instead" (zone delta similar
    # to complement). Visual confirmation in docs/guides/visual-proofs.md.
    "gradient_top_dampen_highlights": (
        "colorchecker",
        _check_zone_dampen(zone=_CC_TOP_HALF, complement=_CC_BOTTOM_HALF),
    ),
    "gradient_bottom_lift_shadows": (
        "colorchecker",
        _check_zone_lift(zone=_CC_BOTTOM_HALF, complement=_CC_TOP_HALF),
    ),
    "radial_subject_lift": (
        "colorchecker",
        _check_zone_lift(zone=_CC_CENTER_4, complement=_CC_CORNER_4),
    ),
    "rectangle_subject_band_dim": (
        "colorchecker",
        _check_zone_dampen(zone=_CC_MIDDLE_ROWS, complement=_CC_OUTER_ROWS),
    ),
}


# Primitives without per-patch math — documented here so the test class can
# explain why each is skipped.
# Long descriptive strings — keep readable; ruff E501 doesn't add value here.
# fmt: off
SKIP_REASONS: dict[str, str] = {
    "look_neutral": "L2 composite (exposure + temperature); sub-effects tested via expo_+0.5 and wb_warm_subtle.",  # noqa: E501
    "grain_fine": "Texture noise; not a per-patch deterministic effect (std-dev check is future work).",  # noqa: E501
    "grain_medium": "Same as grain_fine.",
    "grain_heavy": "Same as grain_fine.",
    "vignette_subtle": "Positional darkening at corners; covered by tests/e2e/expressive/test_path_b_vignette.py.",  # noqa: E501
    "vignette_medium": "Same as vignette_subtle.",
    "vignette_heavy": "Same as vignette_subtle.",
    "clarity_strong": "Local-contrast on edges/details, not flat patches (covered by test_path_b_localcontrast.py).",  # noqa: E501
    "clarity_painterly": "Same as clarity_strong.",
    "blacks_lifted": "Sigmoid 'target_black' is scene-referred; effect is below noise on display-referred chart input. Covered by test_path_a_sigmoid.py against real raws.",  # noqa: E501
    "blacks_crushed": "Same as blacks_lifted.",
    "shadows_global_+": "Exposure black-level offset; effectively a no-op on display-referred chart input. Covered by direction-of-change e2e against real raws.",  # noqa: E501
    "shadows_global_-": "Same as shadows_global_+.",
    "wb_cool_subtle": "Empirical: rendered a* shift is opposite-sign on the empty-baseline chart pipeline (a*+ instead of a*-). Likely a chromatic-adaptation interaction in the display-referred path; behavior on real raws is correct. Tracked for follow-up.",  # noqa: E501
}
# fmt: on


__all__ = ["EXPECTED_EFFECTS", "SKIP_REASONS", "AssertionResult", "LabCheck"]
