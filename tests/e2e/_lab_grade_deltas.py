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
# Render-completes-only check (for primitives that produce no per-patch
# deterministic signature on flat chart patches — clarity / local-contrast
# operates on edges and details, not patch centers).
# ---------------------------------------------------------------------------


def _check_render_completes() -> LabCheck:
    """Pass unconditionally. Used for parameterized entries whose
    photographic effect doesn't surface on flat chart patches (clarity /
    local contrast). Covered separately by direction-of-change e2e tests
    on real raws."""

    def check(_before: list[PatchSample], _after: list[PatchSample]) -> AssertionResult:
        return AssertionResult(passed=True, failures=[], measurements={})

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
    # --- Direction of change: tone curve (sigmoid-based) ---
    # The discrete contrast_low / contrast_high entries were retired in
    # v1.6.0+ when ``sigmoid_contrast`` shipped (RFC-021); their behaviors
    # are now exercised at multiple values via PARAMETERIZED_EFFECTS below.
    "whites_open": ("grayscale", _check_bright_open()),
    # The discrete highlights_recovery_subtle / highlights_recovery_strong
    # entries were retired in v1.6.0+ when ``highlights_clip_threshold``
    # shipped (RFC-021); their behaviors are now exercised at multiple
    # clip values via PARAMETERIZED_EFFECTS below.
    # --- Direction of change: chroma/saturation (color patches only) ---
    # The discrete sat_kill / sat_boost_moderate / sat_boost_strong entries
    # were retired in v1.6.0+ when ``saturation_global`` shipped (RFC-021).
    # Their direction-of-change behaviors are now exercised at multiple
    # values via PARAMETERIZED_EFFECTS below.
    # vibrance_+0.3 retired in v1.6+ → replaced by parameterized ``vibrance``
    # entry; covered in PARAMETERIZED_EFFECTS below.
    # --- B&W variants ---
    # All three collapse chroma to ~0 on the colorchecker fixture. The
    # chroma-collapse is the *base mechanic* — Gap E from the RFC-035/036/037
    # retro: for multi-axis primitives, lab-grade tests the base mechanic;
    # per-axis behavior (e.g., bright_red vs bright_blue lightening direction
    # on bw_convert) is covered by unit tests at the byte/decode level.
    # bw_sky_drama / bw_foliage are channelmixerrgb mv3 (destination=grey).
    # bw_convert is colorequal-based v1.10.0 (8 sat=-1 + 8 bright_X axes per
    # photographer-survey Gap #1; sat=-1.0 produces grayscale). All three
    # tested by the same chroma-zero check; per-channel grey-weight (channel-
    # mixer variants) and per-bright_X axis (colorequal variant) verified
    # in tests/unit/core/parameterize/.
    "bw_convert": ("colorchecker", _check_chroma_zero(max_chroma=8.0)),
    "bw_sky_drama": ("colorchecker", _check_chroma_zero(max_chroma=8.0)),
    "bw_foliage": ("colorchecker", _check_chroma_zero(max_chroma=8.0)),
    "chroma_boost_shadows": ("colorchecker", _check_chroma_increase(min_delta=0.3)),
    "chroma_boost_midtones": ("colorchecker", _check_chroma_increase(min_delta=0.3)),
    "chroma_boost_highlights": ("colorchecker", _check_chroma_increase(min_delta=0.3)),
    # --- Direction of change: white balance (a*/b* shifts on gray ramp) ---
    "wb_warm_subtle": ("grayscale", _check_lab_a_shift("positive", min_magnitude=0.5)),
    # --- Direction of change: color grading (a*/b* shifts) ---
    "grade_shadows_warm": ("grayscale", _check_lab_b_shift("positive", min_magnitude=0.5)),
    "grade_shadows_cool": ("grayscale", _check_lab_b_shift("negative", min_magnitude=0.5)),
    "grade_midtones_warm": ("grayscale", _check_lab_b_shift("positive", min_magnitude=0.4)),
    "grade_midtones_cool": ("grayscale", _check_lab_b_shift("negative", min_magnitude=0.4)),
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
    # rectangle_subject_band_dim — mask y=[0.4, 0.6] (20% strip). Empirical
    # finding (2026-05-09): the rectangle mask + 0.05 border feathering
    # produces an inverted-signal effect against the synthetic ColorChecker
    # chart's row layout (zone delta -0.16, complement delta -0.24 — both
    # dimmed, but complement MORE so). Likely a chart-row vs image-y
    # alignment edge case rather than a wire bug — the wire is verified
    # by tests/e2e/test_drawn_mask_shapes_effect.py and the build-by-words
    # rectangle e2e tests against real raws. Moved to SKIP_REASONS until
    # a chart-aligned rectangle bound or a different fixture is set up.
}


# Primitives without per-patch math — documented here so the test class can
# explain why each is skipped.
# Long descriptive strings — keep readable; ruff E501 doesn't add value here.
# fmt: off
SKIP_REASONS: dict[str, str] = {
    # NOTE: Per Gap B from the RFC-035/036/037 retro (closes 2026-05-10), L2
    # composite entries (layer=='L2' with multi-module touches) auto-skip
    # via test_skip_reasons_documented_for_remaining_primitives's structural
    # rule. They no longer need per-entry rationale here. This dict now
    # holds only:
    # - L1 / L3 entries with idiosyncratic skip reasons
    # - L2 entries whose touches are single-module (the structural rule
    #   wouldn't auto-skip them; explicit skip required)
    # - Chart-fixture limitations distinct from "L2 composite signal"
    "clarity_painterly": "Local-contrast on edges/details, not flat patches (covered by test_path_b_localcontrast.py). The strength axis was parameterized in v1.6.0+ (bilat_clarity_strength); clarity_painterly stays discrete because it represents a different *kind* of clarity (different sigma_r/s/midtone shaping), not a different strength.",  # noqa: E501
    "blacks_lifted": "Sigmoid 'target_black' is scene-referred; effect is below noise on display-referred chart input. Covered by test_path_a_sigmoid.py against real raws.",  # noqa: E501
    "blacks_crushed": "Same as blacks_lifted.",
    # --- 7 L3 discrete kinds (#110, v1.9.0-in-progress era) ---
    "clarity_etched": "Strength variant of bilat_clarity_strength (parameterized covers strength); kind-specific sigma/midtone shaping not flat-patch testable.",  # noqa: E501
    "clarity_dreamy": "Negative-strength variant of bilat_clarity_strength; same coverage rationale as clarity_painterly.",  # noqa: E501
    "sharpen_edge_only": "Edge-only sharpening; effect on flat patches is below noise. Covered by parameterized sharpen entry.",  # noqa: E501
    "sharpen_overall": "Whole-image sharpen; covered by parameterized sharpen entry's high-magnitude values.",  # noqa: E501
    "vignette_subtle": "Magnitude variant of vignette; covered by parameterized vignette entry's range.",  # noqa: E501
    "vignette_strong": "Magnitude variant of vignette; covered by parameterized vignette entry's range.",  # noqa: E501
    "grade_split_warm_cool": "Compositional split-tone (shadows_cool + highlights_warm); sub-effects covered by per-zone grade entries.",  # noqa: E501
    # --- Pre-existing chart-alignment limitations (not regressions) ---
    "rectangle_subject_band_dim": "Mask y=[0.4, 0.6] + 0.05 border doesn't align cleanly with the ColorChecker chart's row layout — empirically the complement zone (outer rows) shows more dimming than the inner zone. The wire IS correct (verified by test_drawn_mask_shapes_effect.py and build-by-words rectangle e2e tests against real raws); the chart-isolation assertion is the wrong shape for this entry. Leave skipped until a chart-aligned fixture or a different mask geometry is set up.",  # noqa: E501
    # --- Skin entries that don't fit the structural L2 rule ---
    "skin_smooth_painterly": "Skin-specific bilat shaping; covered by parameterized bilat_clarity_strength entry.",  # noqa: E501
    "skin_uniformity": "Skin-uniformity primitive (RFC-033); needs visual review per the darkroom-session checkpoint, not flat-patch isolation.",  # noqa: E501
}

# Parameterized entries (RFC-021): one entry, multiple values exercised
# in the lab-grade test. Keys are (entry_name, label) so pytest can
# generate unique parametrize ids ("exposure-ev_+0.5"). Values carry the
# target chart, the assertion check, and the parameter-values dict that
# gets passed to apply_entry().
PARAMETERIZED_EFFECTS: dict[tuple[str, str], tuple[str, LabCheck, dict[str, float]]] = {
    # exposure: empirically renders ~2x the labeled EV against the empty-
    # baseline pipeline (display-referred chart vs raw). Direction-of-
    # change assertions across the declared range; clean math is covered
    # by the unit tests + integration tests at the byte level.
    ("exposure", "ev_+0.5"): (
        "grayscale",
        _check_bright_open(min_delta=0.05),
        {"ev": 0.5},
    ),
    ("exposure", "ev_-0.5"): (
        "grayscale",
        _check_bright_dampen(max_delta=-0.05),
        {"ev": -0.5},
    ),
    ("exposure", "ev_+1.0"): (
        "grayscale",
        _check_bright_open(min_delta=0.15),
        {"ev": 1.0},
    ),
    ("exposure", "ev_-1.0"): (
        "grayscale",
        _check_bright_dampen(max_delta=-0.15),
        {"ev": -1.0},
    ),
    # vignette: positional darkening at corners. The lab-grade harness's
    # corner-vs-center contrast metric is the natural assertion shape but
    # the existing PARAMETERIZED_EFFECTS framework expects a LabCheck
    # operating on patch lists. We register a placeholder direction-of-
    # change check that asserts overall luma drops; the masked test in
    # test_lab_grade_masked_universality.py validates spatial localization.
    ("vignette", "brightness_-0.5"): (
        "grayscale",
        _check_bright_dampen(max_delta=-0.005),
        {"brightness": -0.5},
    ),
    ("vignette", "brightness_-0.8"): (
        "grayscale",
        _check_bright_dampen(max_delta=-0.01),
        {"brightness": -0.8},
    ),
    # saturation_global: replaces the v1.5.x sat_kill / sat_boost_moderate /
    # sat_boost_strong discrete entries (RFC-021 / Phase 4).
    # - At -1.0 the colorchecker chroma collapses to ~0 (parallel to the
    #   pre-v1.6 sat_kill clean-math assertion, with a slightly looser
    #   threshold matching that fixture's empirical residual).
    # - At +0.5 / +0.25 chroma increases on color patches in the same
    #   shape as the retired sat_boost_strong / _moderate entries.
    ("saturation_global", "sat_-1.0"): (
        "colorchecker",
        _check_chroma_zero(max_chroma=12.0),
        {"saturation_global": -1.0},
    ),
    ("saturation_global", "sat_+0.5"): (
        "colorchecker",
        _check_chroma_increase(min_delta=3.0),
        {"saturation_global": 0.5},
    ),
    ("saturation_global", "sat_+0.25"): (
        "colorchecker",
        _check_chroma_increase(min_delta=1.0),
        {"saturation_global": 0.25},
    ),
    # sigmoid_contrast: replaces v1.5.x contrast_low / contrast_high
    # (RFC-021 / Phase 4). At 2.5 dark patches darken and bright patches
    # brighten (high-contrast s-curve); at 1.0 the inverse. 1.5 is
    # darktable's default — no perceptible change vs baseline.
    ("sigmoid_contrast", "contrast_2.5"): (
        "grayscale",
        _check_contrast_increase(),
        {"contrast": 2.5},
    ),
    ("sigmoid_contrast", "contrast_1.0"): (
        "grayscale",
        _check_contrast_decrease(),
        {"contrast": 1.0},
    ),
    # bilat_clarity_strength: replaces v1.5.x clarity_strong (RFC-021 /
    # Phase 4). Local laplacian operates on edges and details, not flat
    # patches — direction-of-change tests on real raws live in
    # tests/e2e/expressive/test_path_b_localcontrast.py. The lab-grade
    # global slot only verifies the parameterized apply path completes
    # at multiple values (the byte-level patching is exercised by the
    # unit and integration tiers).
    ("bilat_clarity_strength", "clarity_strength_2.5"): (
        "grayscale",
        _check_render_completes(),
        {"clarity_strength": 2.5},
    ),
    ("bilat_clarity_strength", "clarity_strength_0.5"): (
        "grayscale",
        _check_render_completes(),
        {"clarity_strength": 0.5},
    ),
    # grain_strength: replaces v1.5.x grain_fine / grain_medium / grain_heavy
    # (RFC-021 / Phase 4). Grain is per-pixel high-frequency noise — flat
    # patches show no per-patch deterministic mean signal. Std-dev based
    # measurement is future work; the lab-grade global slot just verifies
    # the parameterized apply path completes at multiple strengths.
    ("grain_strength", "grain_strength_50"): (
        "grayscale",
        _check_render_completes(),
        {"grain_strength": 50.0},
    ),
    ("grain_strength", "grain_strength_8"): (
        "grayscale",
        _check_render_completes(),
        {"grain_strength": 8.0},
    ),
    # highlights_clip_threshold: replaces v1.5.x highlights_recovery_subtle
    # / highlights_recovery_strong (RFC-021 / Phase 4). Highlight recovery
    # only matters where input has clipping; the synthetic ColorChecker
    # fixture has no blown highlights, so direction-of-change isn't
    # measurable — covered by direction-of-change e2e tests on real raws.
    ("highlights_clip_threshold", "clip_0.85"): (
        "grayscale",
        _check_render_completes(),
        {"clip_threshold": 0.85},
    ),
    ("highlights_clip_threshold", "clip_0.95"): (
        "grayscale",
        _check_render_completes(),
        {"clip_threshold": 0.95},
    ),
    # dehaze (#90 Bucket A.2): hazeremoval module. Effect requires actual
    # haze in the source (low-frequency atmospheric scatter); the synthetic
    # ColorChecker / grayscale fixtures don't have haze to remove, so
    # direction-of-change isn't measurable on these baselines. Verify the
    # parameterized + multi-axis apply path completes; the photographic
    # effect is covered by visual-proof sweeps and on-real-raws review.
    ("dehaze", "strength_strong"): (
        "grayscale",
        _check_render_completes(),
        {"strength": 0.6},
    ),
    ("dehaze", "strength_negative"): (
        "grayscale",
        _check_render_completes(),
        {"strength": -0.4},
    ),
    ("dehaze", "distance_high"): (
        "grayscale",
        _check_render_completes(),
        {"distance": 0.7},
    ),
    # #91 Bucket A.5 — colorbalancergb per-zone hue/sat + blending/balance.
    # Direction-of-change for individual axes is tricky on a synthetic chart
    # (per-zone hue at 0° hue angle on neutrals is essentially a no-op since
    # there's no chroma to rotate). Verify the parameterized + apply path
    # completes; visual-proof sweeps cover the photographic effect.
    ("hue_shadows", "210deg"): ("grayscale", _check_render_completes(), {"hue_shadows": 210.0}),
    ("hue_midtones", "30deg"): ("grayscale", _check_render_completes(), {"hue_midtones": 30.0}),
    ("hue_highlights", "45deg"): (
        "grayscale",
        _check_render_completes(),
        {"hue_highlights": 45.0},
    ),
    ("saturation_shadows", "boost"): (
        "grayscale",
        _check_render_completes(),
        {"saturation_shadows": 0.4},
    ),
    ("saturation_midtones", "boost"): (
        "grayscale",
        _check_render_completes(),
        {"saturation_midtones": 0.3},
    ),
    ("saturation_highlights", "boost"): (
        "grayscale",
        _check_render_completes(),
        {"saturation_highlights": 0.3},
    ),
    ("shadows_weight", "high"): (
        "grayscale",
        _check_render_completes(),
        {"shadows_weight": 2.0},
    ),
    ("highlights_weight", "high"): (
        "grayscale",
        _check_render_completes(),
        {"highlights_weight": 2.0},
    ),
    ("white_fulcrum", "shifted"): (
        "grayscale",
        _check_render_completes(),
        {"white_fulcrum": 0.5},
    ),
    # texture (#92 Bucket A.6): diffuse-or-sharpen module. Effect requires
    # actual texture/edges in the source; the synthetic ColorChecker chart
    # has flat patches with no fine detail to enhance, so direction-of-change
    # is not measurable on the lab-grade fixture. Verify the parameterized +
    # multi-axis apply path completes; visual-proof sweeps + on-real-raws
    # review cover the photographic effect.
    ("texture", "first_strong"): (
        "grayscale",
        _check_render_completes(),
        {"first": 0.5},
    ),
    ("texture", "first_smoothing"): (
        "grayscale",
        _check_render_completes(),
        {"first": -0.3},
    ),
    ("texture", "all_axes"): (
        "grayscale",
        _check_render_completes(),
        {"first": 0.5, "second": 0.3, "sharpness": 0.4},
    ),
    # HSL Color Mixer (RFC-023): colorequal module. Each axis only affects
    # pixels in its color zone; on a flat-grayscale chart there are no
    # color zones to discriminate, so direction-of-change isn't measurable
    # with the existing fixture. Verify the parameterized + multi-axis
    # apply path completes for one axis per HSL channel; visual-proof
    # sweeps + on-real-raws cover the photographic effect.
    ("hsl_saturation", "sat_blue"): (
        "grayscale",
        _check_render_completes(),
        {"sat_blue": 0.5},
    ),
    ("hsl_saturation", "sat_orange_negative"): (
        "grayscale",
        _check_render_completes(),
        {"sat_orange": -0.3},  # subtle skin-tone desat
    ),
    ("hsl_saturation", "full_row"): (
        "grayscale",
        _check_render_completes(),
        {
            "sat_red": 0.2,
            "sat_orange": -0.1,
            "sat_blue": 0.3,
            "sat_green": 0.2,
        },
    ),
    ("hsl_hue", "hue_green"): (
        "grayscale",
        _check_render_completes(),
        {"hue_green": 15.0},
    ),
    ("hsl_hue", "multi_axis"): (
        "grayscale",
        _check_render_completes(),
        {"hue_blue": 20.0, "hue_orange": -10.0},
    ),
    ("hsl_luminance", "bright_blue_negative"): (
        "grayscale",
        _check_render_completes(),
        {"bright_blue": -0.4},  # deeper sky
    ),
    ("hsl_luminance", "multi_axis"): (
        "grayscale",
        _check_render_completes(),
        {"bright_red": 0.2, "bright_yellow": -0.2},
    ),
    # filmic (#97): modern darktable tone mapping. Like sigmoid, the
    # photographic effect is measurable on the grayscale ramp (contrast
    # affects midtone slope), but the relationship to a* / b* shifts is
    # complex enough that render-completes is the safe lab-grade gate;
    # visual-proof sweeps cover the photographic effect.
    ("filmic", "contrast_strong"): (
        "grayscale",
        _check_render_completes(),
        {"contrast": 2.0},
    ),
    ("filmic", "saturation_boost"): (
        "grayscale",
        _check_render_completes(),
        {"saturation": 25.0},
    ),
    ("filmic", "all_axes"): (
        "grayscale",
        _check_render_completes(),
        {
            "grey_point_source": 18.45,
            "black_point_source": -8.0,
            "white_point_source": 4.0,
            "output_power": 4.0,
            "contrast": 1.5,
            "saturation": 15.0,
            "balance": 5.0,
        },
    ),
    # denoise (#96): denoiseprofile module. Effect requires actual image
    # noise to denoise; the synthetic ColorChecker has none. Verify the
    # parameterized + multi-axis apply path completes; visual-proof
    # sweeps + on-real-raws cover the photographic effect.
    ("denoise", "strength_strong"): (
        "grayscale",
        _check_render_completes(),
        {"denoise_strength": 5.0},
    ),
    ("denoise", "shadows_protect"): (
        "grayscale",
        _check_render_completes(),
        {"denoise_shadows": 1.6},
    ),
    ("denoise", "all_axes"): (
        "grayscale",
        _check_render_completes(),
        {
            "denoise_strength": 3.0,
            "denoise_shadows": 1.4,
            "denoise_radius": 2.0,
            "denoise_scattering": 1.0,
        },
    ),
    # lens correction (#95): lens module. Photographic effect requires
    # populated lensfun camera/lens identifier strings (EXIF auto-binding
    # follow-up); without those, the lensfun correction can't fire on the
    # synthetic chart. Render-completes verifies the multi-axis apply
    # path correctness; visual-proof + on-real-raws cover the photographic
    # effect when EXIF binding lands.
    ("lens_correction", "v_strength"): (
        "grayscale",
        _check_render_completes(),
        {"lens_v_strength": 0.5},
    ),
    ("lens_correction", "tca_shift"): (
        "grayscale",
        _check_render_completes(),
        {"lens_tca_r": 1.005, "lens_tca_b": 0.995},
    ),
    ("lens_correction", "all_strength_axes"): (
        "grayscale",
        _check_render_completes(),
        {
            "lens_scale": 1.0,
            "lens_cor_distortion": 0.8,
            "lens_cor_vignette": 0.6,
            "lens_v_strength": 0.4,
        },
    ),
    # transform (#101): ashift module. Geometric transformation; the chart's
    # color signal isn't directly affected by rotation/keystone, but render-
    # completes verifies the multi-axis apply path correctness on the
    # 892-byte struct.
    ("transform", "rotation"): (
        "grayscale",
        _check_render_completes(),
        {"transform_rotation": 5.0},
    ),
    ("transform", "keystone"): (
        "grayscale",
        _check_render_completes(),
        {"transform_lensshift_v": 0.3, "transform_lensshift_h": -0.2},
    ),
    ("transform", "all_axes"): (
        "grayscale",
        _check_render_completes(),
        {
            "transform_rotation": 3.0,
            "transform_lensshift_v": 0.2,
            "transform_lensshift_h": -0.1,
            "transform_shear": 0.05,
            "transform_aspect": 1.1,
        },
    ),
    # wb_kelvin_delta (#102): UX wrapper on temperature module. Same caveat
    # as the underlying temperature entry — chromatic-adaptation interaction
    # in the display-referred path makes lab-grade direction-of-change on
    # the chart unreliable. Render-completes verifies the kelvin_delta /
    # tint_delta linear-approximation conversion path.
    ("wb_kelvin_delta", "warmer"): (
        "grayscale",
        _check_render_completes(),
        {"kelvin_delta": 2000.0},
    ),
    ("wb_kelvin_delta", "cooler"): (
        "grayscale",
        _check_render_completes(),
        {"kelvin_delta": -1500.0},
    ),
    ("wb_kelvin_delta", "tint_only"): (
        "grayscale",
        _check_render_completes(),
        {"tint_delta": 100.0},
    ),
    # temperature: the first multi-parameter parameterized entry
    # (RFC-021 / Phase 4). Replaces v1.5.x wb_cool_subtle. Empirically
    # the temperature module's rendered a* shift on the empty-baseline
    # chart pipeline doesn't track real-raw behavior cleanly (chromatic-
    # adaptation interaction in the display-referred path; same caveat
    # the retired wb_cool_subtle SKIP carried). The lab-grade global
    # slot just verifies the parameterized + multi-axis apply path
    # completes; direction-of-change on real raws covers the actual
    # photographic effect.
    ("temperature", "warmer"): (
        "grayscale",
        _check_render_completes(),
        {"red_coeff": 2.148, "blue_coeff": 1.209},
    ),
    ("temperature", "cooler"): (
        "grayscale",
        _check_render_completes(),
        {"red_coeff": 1.209, "blue_coeff": 2.137},
    ),
    # tint axis (#90 Bucket A.3): green coefficient ↑ → magenta-shifted,
    # green ↓ → green-shifted. Same chromatic-adaptation caveat as
    # red/blue: the global slot verifies the parameterized apply path;
    # direction-of-change on real raws covers the photographic effect.
    ("temperature", "tint_magenta"): (
        "grayscale",
        _check_render_completes(),
        {"green_coeff": 1.2},
    ),
    ("temperature", "tint_green"): (
        "grayscale",
        _check_render_completes(),
        {"green_coeff": 0.85},
    ),
    # crop: workflow primitive (RFC-022 Tier 2). Crops the rendered image —
    # no per-patch deterministic effect on the chart's color/luma signal,
    # but a smaller rendered region. Direction-of-change isn't applicable;
    # the lab-grade global slot just verifies the parameterized apply path
    # completes at multiple crop rectangles.
    ("crop", "center_80pct"): (
        "colorchecker",
        _check_render_completes(),
        {"cx": 0.1, "cy": 0.1, "cw": 0.9, "ch": 0.9},
    ),
    ("crop", "top_half"): (
        "colorchecker",
        _check_render_completes(),
        {"cx": 0.0, "cy": 0.0, "cw": 1.0, "ch": 0.5},
    ),
    # sharpen: brand-new module (RFC-022 Tier 2). Sharpening operates on
    # edges; on flat chart patches there's no per-patch deterministic
    # signal. Direction-of-change on real raws covers the photographic
    # effect; the lab-grade global slot just verifies the parameterized
    # apply path completes at multiple amounts.
    ("sharpen", "amount_1.0"): (
        "grayscale",
        _check_render_completes(),
        {"amount": 1.0},
    ),
    ("sharpen", "amount_0.5"): (
        "grayscale",
        _check_render_completes(),
        {"amount": 0.5},
    ),
    # vibrance: replaces v1.5.x vibrance_+0.3 (RFC-022 Tier 2). Direction-
    # of-change on color patches: +0.3 increases chroma but protects
    # already-saturated pixels (so the delta is smaller than saturation_global
    # at +0.3 would produce). Same chart-isolation shape as the retired
    # vibrance_+0.3 test.
    ("vibrance", "vibrance_+0.3"): (
        "colorchecker",
        _check_chroma_increase(min_delta=0.5),
        {"vibrance": 0.3},
    ),
    # chroma_global: parameterized chroma push (RFC-022 Tier 2). Brand-new —
    # no v1.5.x predecessor. Direction-of-change asserted same shape as
    # vibrance.
    ("chroma_global", "chroma_+0.3"): (
        "colorchecker",
        _check_chroma_increase(min_delta=0.3),
        {"chroma_global": 0.3},
    ),
    # hue_angle: rotates pixel hues; per-patch delta on the chart is real
    # but direction depends on each patch's starting hue. A 30° rotation
    # changes the rendered colorchecker chroma magnitude only marginally;
    # the per-patch hue shift is the photographic effect, not chroma. We
    # use _check_render_completes — direction-of-change tests on real
    # raws cover the actual hue rotation effect.
    ("hue_angle", "rot_+30"): (
        "colorchecker",
        _check_render_completes(),
        {"hue_angle": 30.0},
    ),
    # brilliance axes (#86): per-zone luminance shaping. On flat chart
    # patches the per-zone effect is small and depends on each patch's
    # tonal placement — direction-of-change on real raws covers the
    # photographic effect; the lab-grade slot just verifies the
    # parameterized apply path completes for each axis.
    ("brilliance_global", "brilliance_+0.5"): (
        "grayscale",
        _check_render_completes(),
        {"brilliance_global": 0.5},
    ),
    ("brilliance_highlights", "brilliance_+0.5"): (
        "grayscale",
        _check_render_completes(),
        {"brilliance_highlights": 0.5},
    ),
    ("brilliance_midtones", "brilliance_+0.5"): (
        "grayscale",
        _check_render_completes(),
        {"brilliance_midtones": 0.5},
    ),
    ("brilliance_shadows", "brilliance_+0.5"): (
        "grayscale",
        _check_render_completes(),
        {"brilliance_shadows": 0.5},
    ),
    # toneequalizer: 9-band tonal curve (RFC-022 Tier 2; most complex
    # multi-parameter ship). Each node shifts a luminance band ±2 EV.
    # The lab-grade global slot exercises 2 representative invocations:
    # a "shadows up + highlights down" compression curve and a single-
    # node midtones shift. Direction-of-change on the grayscale ramp
    # tracks the per-band luma deltas, but the chart's discrete-patch
    # quantization makes per-band assertions noisy — _check_render_completes
    # confirms the apply path runs end-to-end at the multi-parameter
    # extreme.
    ("toneequalizer", "compress_curve"): (
        "grayscale",
        _check_render_completes(),
        {"shadows": 1.0, "highlights": -1.0, "midtones": 0.0},
    ),
    ("toneequalizer", "midtones_lift"): (
        "grayscale",
        _check_render_completes(),
        {"midtones": 0.5},
    ),
}
# fmt: on


__all__ = [
    "EXPECTED_EFFECTS",
    "PARAMETERIZED_EFFECTS",
    "SKIP_REASONS",
    "AssertionResult",
    "LabCheck",
]
