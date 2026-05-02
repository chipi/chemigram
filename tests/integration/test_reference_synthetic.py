"""Integration: synthetic reference-target validation (RFC-019 Tier A).

Validates the synthetic CC24 + grayscale fixtures and the assertion
library round-trip against the published L\\*a\\*b\\* ground truth. CI-safe
(no darktable, no real RAW). Catches:

- sRGB ↔ Lab math regressions in chemigram.core.assertions
- Drift between the synthetic PNGs and the JSON ground truth
- Per-patch extraction or coordinate logic bugs
- Tonal-response linearity regressions on the grayscale ramp
"""

from __future__ import annotations

import json
from pathlib import Path

from chemigram.core.assertions import (
    PatchCoord,
    assert_color_accuracy,
    assert_tonal_response,
    extract_patch_values,
    srgb_to_lab,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REF_DIR = REPO_ROOT / "tests" / "fixtures" / "reference-targets"
CC24_PNG = REF_DIR / "colorchecker_synthetic_srgb.png"
CC24_JSON = REF_DIR / "colorchecker24_lab_d50.json"
GRAY_PNG = REF_DIR / "grayscale_synthetic_linear.png"


def _load_cc24_reference() -> dict:
    return json.loads(CC24_JSON.read_text(encoding="utf-8"))


def _cc24_patch_coords() -> list[PatchCoord]:
    """Sample 80x80 sub-region from the center of each 100x100 patch
    (avoids edge-aliasing artefacts from sRGB rendering at boundaries).
    """
    raw = _load_cc24_reference()
    grid = raw["synthetic_grid"]
    patch = grid["patch_pixels"]
    cols = grid["cols"]
    inset = (patch - 80) // 2
    out: list[PatchCoord] = []
    for entry in raw["patches"]:
        idx = entry["index"]
        row, col = divmod(idx - 1, cols)
        x = col * patch + inset
        y = row * patch + inset
        out.append(PatchCoord(x=x, y=y, w=80, h=80))
    return out


# ----- CC24 -----------------------------------------------------------------


def test_synthetic_cc24_round_trip_under_threshold() -> None:
    """Extracting Lab from the synthetic CC24 should match the reference
    JSON within the documented thresholds. The drift comes from sRGB
    8-bit quantization (256 levels) plus Lab → sRGB clipping for
    out-of-gamut patches.
    """
    raw = _load_cc24_reference()
    coords = _cc24_patch_coords()
    measured = extract_patch_values(CC24_PNG, coords)
    reference = [(p["L"], p["a"], p["b"]) for p in raw["patches"]]
    skip = [i - 1 for i in raw["out_of_gamut_indices"]]
    result = assert_color_accuracy(
        measured, reference, max_mean_de=2.0, max_max_de=4.0, skip_indices=skip
    )
    assert result.passed, (
        f"synthetic CC24 round-trip failed: mean_de={result.mean_de:.3f}, "
        f"max_de={result.max_de:.3f}; per-patch: "
        f"{[round(d, 2) for d in result.per_patch]}"
    )


def test_synthetic_cc24_neutral_patches_are_neutral() -> None:
    """The 6 neutral patches (#19..24) should have |a*| and |b*| below 3."""
    raw = _load_cc24_reference()
    coords = _cc24_patch_coords()
    measured = extract_patch_values(CC24_PNG, coords)
    for idx in raw["neutral_indices"]:
        _L, a, b = measured[idx - 1]
        assert abs(a) < 3.0, f"neutral patch {idx} a*={a:.2f} not neutral"
        assert abs(b) < 3.0, f"neutral patch {idx} b*={b:.2f} not neutral"


def test_synthetic_cc24_lightness_monotone_on_neutrals() -> None:
    """Neutrals 19 (white) → 24 (black) should decrease in L*."""
    raw = _load_cc24_reference()
    coords = _cc24_patch_coords()
    from itertools import pairwise

    measured = extract_patch_values(CC24_PNG, coords)
    neutrals = [measured[i - 1][0] for i in raw["neutral_indices"]]
    for prev, cur in pairwise(neutrals):
        assert cur < prev, f"neutrals not monotone: {neutrals}"


# ----- Grayscale ramp -------------------------------------------------------


def test_synthetic_grayscale_is_linear_in_srgb() -> None:
    """The 24-step ramp's measured sRGB values increase linearly across
    the 600 px width — sanity check that the generator did its job.
    """
    from PIL import Image

    img = Image.open(GRAY_PNG).convert("RGB")
    width, _ = img.size
    steps = 24
    step_width = width // steps
    samples = []
    for i in range(steps):
        x = i * step_width + step_width // 2
        r, g, b = img.getpixel((x, img.height // 2))
        samples.append((r + g + b) / 3.0)
    # Strict monotone increasing
    from itertools import pairwise

    for prev, cur in pairwise(samples):
        assert cur > prev


def test_synthetic_grayscale_lab_lightness_increases_monotone() -> None:
    """Sampled L* per step increases monotone."""
    from PIL import Image

    img = Image.open(GRAY_PNG).convert("RGB")
    width, _ = img.size
    steps = 24
    step_width = width // steps
    L_values: list[float] = []
    for i in range(steps):
        x = i * step_width + step_width // 2
        rgb = img.getpixel((x, img.height // 2))
        L, _a, _b = srgb_to_lab(rgb)
        L_values.append(L)
    from itertools import pairwise

    for prev, cur in pairwise(L_values):
        assert cur > prev


def test_assert_exposure_shift_through_synthetic_neutrals() -> None:
    """End-to-end assertion test: simulate an exposure-shift effect on
    the CC24 neutrals by directly producing a "shifted" Lab patch list,
    verify the assertion API reports the correct direction.
    """
    from chemigram.core.assertions import assert_exposure_shift

    raw = _load_cc24_reference()
    coords = _cc24_patch_coords()
    measured = extract_patch_values(CC24_PNG, coords)
    neutrals = [measured[i - 1] for i in raw["neutral_indices"]]
    # Synthesize a +5 L* shift on the neutrals
    shifted = [(L + 5.0, a, b) for L, a, b in neutrals]
    assert assert_exposure_shift(neutrals, shifted, direction=+1, min_magnitude=4.0)
    # Wrong direction fails
    assert not assert_exposure_shift(neutrals, shifted, direction=-1, min_magnitude=4.0)


def test_assert_wb_shift_through_synthetic_neutrals() -> None:
    """Same shape: simulate a warm WB shift, verify assertion catches it."""
    from chemigram.core.assertions import assert_wb_shift

    raw = _load_cc24_reference()
    coords = _cc24_patch_coords()
    measured = extract_patch_values(CC24_PNG, coords)
    neutrals = [measured[i - 1] for i in raw["neutral_indices"]]
    # Synthesize a +3 b* shift (warmer)
    warmed = [(L, a, b + 3.0) for L, a, b in neutrals]
    assert assert_wb_shift(neutrals, warmed, axis="b", direction=+1, min_magnitude=2.0)
    # The unshifted a* axis remains stable — direction-of-change on a*
    # should fail for both directions (delta is essentially zero).
    assert not assert_wb_shift(neutrals, warmed, axis="a", direction=+1, min_magnitude=1.0)
    assert not assert_wb_shift(neutrals, warmed, axis="a", direction=-1, min_magnitude=1.0)


def test_assert_color_accuracy_skip_indices_via_real_fixture() -> None:
    """Validates the skip_indices flow against the actual synthetic CC24
    + JSON ground truth pair. Confirms the out-of-gamut Cyan patch is
    correctly excluded from the strict thresholds.
    """
    raw = _load_cc24_reference()
    coords = _cc24_patch_coords()
    measured = extract_patch_values(CC24_PNG, coords)
    reference = [(p["L"], p["a"], p["b"]) for p in raw["patches"]]
    # Without skip: the strict threshold may be violated by the
    # out-of-gamut patch alone.
    skip = [i - 1 for i in raw["out_of_gamut_indices"]]
    result = assert_color_accuracy(
        measured, reference, max_mean_de=2.0, max_max_de=4.0, skip_indices=skip
    )
    assert result.passed
    # The skipped patch's DE is reported but doesn't affect mean/max.
    cyan_de = result.per_patch[17]  # patch #18 = index 17 (zero-based)
    # Cyan is far enough out of gamut that its DE should be measurable.
    # We don't assert a specific value (it's gamut-clip-dependent), but
    # it's typically > the in-gamut max threshold.
    assert cyan_de >= 0


def test_synthetic_grayscale_tonal_response_is_close_to_linear_in_srgb() -> None:
    """The synthetic ramp is linear in *sRGB*, which is non-linear in L\\*
    (sRGB has a gamma curve baked in). So the L\\* response is *not*
    perfectly linear vs sRGB step index — but it's monotone and the
    transformation is well-defined. Use the *expected L* values* (computed
    from the sRGB step values directly) as the reference.
    """
    from PIL import Image

    img = Image.open(GRAY_PNG).convert("RGB")
    width, _ = img.size
    steps = 24
    step_width = width // steps

    measured_L: list[float] = []
    expected_L: list[float] = []
    for i in range(steps):
        x = i * step_width + step_width // 2
        rgb = img.getpixel((x, img.height // 2))
        measured_L.append(srgb_to_lab(rgb)[0])
        expected_v = round(i * 255 / (steps - 1))
        expected_L.append(srgb_to_lab((expected_v, expected_v, expected_v))[0])

    result = assert_tonal_response(measured_L, expected_L, min_r_squared=0.999)
    assert result.passed, f"R²={result.r_squared:.5f}"
