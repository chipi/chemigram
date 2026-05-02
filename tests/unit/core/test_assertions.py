"""Unit tests for ``chemigram.core.assertions`` (RFC-019 v0.2)."""

from __future__ import annotations

import math

import pytest
from PIL import Image

from chemigram.core.assertions import (
    ColorAccuracyResult,
    PatchCoord,
    TonalResponseResult,
    assert_color_accuracy,
    assert_exposure_shift,
    assert_tonal_response,
    assert_wb_shift,
    delta_e_2000,
    extract_patch_values,
    lab_to_srgb,
    srgb_to_lab,
)

# ----- sRGB ↔ Lab round-trip -----------------------------------------------


def test_srgb_to_lab_white_is_perceptual_white() -> None:
    """sRGB white should map to (L=100, a≈0, b≈0) within rounding."""
    lab = srgb_to_lab((255, 255, 255))
    assert math.isclose(lab[0], 100.0, abs_tol=0.5)
    assert abs(lab[1]) < 0.5
    assert abs(lab[2]) < 0.5


def test_srgb_to_lab_black_is_perceptual_black() -> None:
    lab = srgb_to_lab((0, 0, 0))
    assert math.isclose(lab[0], 0.0, abs_tol=0.5)
    assert abs(lab[1]) < 0.5
    assert abs(lab[2]) < 0.5


def test_srgb_to_lab_accepts_floats() -> None:
    lab_int = srgb_to_lab((128, 128, 128))
    lab_float = srgb_to_lab((128 / 255, 128 / 255, 128 / 255))
    for a, b in zip(lab_int, lab_float, strict=True):
        assert math.isclose(a, b, abs_tol=0.001)


def test_srgb_lab_round_trip_in_gamut() -> None:
    """Convert sRGB → Lab → sRGB and assert the round trip is near-identity."""
    for rgb in [(64, 128, 192), (200, 100, 50), (128, 128, 128), (240, 240, 100)]:
        lab = srgb_to_lab(rgb)
        rgb_back = lab_to_srgb(lab)
        for a, b in zip(rgb, rgb_back, strict=True):
            assert abs(a - b) <= 1, f"round-trip drift for {rgb}: got {rgb_back}"


# ----- Delta E 2000 --------------------------------------------------------


def test_delta_e_zero_for_identical_colors() -> None:
    lab = (50.0, 10.0, -20.0)
    assert delta_e_2000(lab, lab) == pytest.approx(0.0, abs=1e-9)


def test_delta_e_known_pair_from_sharma_table() -> None:
    """Sharma/Wu/Dalal 2005 reference test pair (Table 1, row 1).

    Lab1 = (50.0000, 2.6772, -79.7751)
    Lab2 = (50.0000, 0.0000, -82.7485)
    Expected DE2000 = 2.0425 (published)
    """
    de = delta_e_2000((50.0000, 2.6772, -79.7751), (50.0000, 0.0000, -82.7485))
    assert math.isclose(de, 2.0425, abs_tol=0.01), f"expected 2.0425, got {de}"


def test_delta_e_known_pair_neutral_lightness_shift() -> None:
    """A pure-luminance shift produces DE2000 close to the L* difference
    for low-chroma colors. (50, 0, 0) -> (60, 0, 0) should be ~10.
    """
    de = delta_e_2000((50.0, 0.0, 0.0), (60.0, 0.0, 0.0))
    # The DE2000 lightness term equals delta_L / SL; for L≈55 the SL
    # factor is small, so the result is near 10.
    assert 9.0 < de < 11.0, f"expected ~10, got {de}"


def test_delta_e_near_zero_chroma_is_finite() -> None:
    """Two near-neutral patches: avg_C ≈ 0 makes the G-factor and Hue terms
    numerically delicate, but DE2000 must remain finite and small.
    """
    de = delta_e_2000((50.0, 0.001, -0.001), (50.0, -0.001, 0.001))
    assert math.isfinite(de)
    assert de < 0.05


def test_delta_e_hue_wrap_at_0_360_boundary() -> None:
    """A pair with hues straddling the 0°/360° wrap (near-red on either side)
    must use the wrap-around average, not a 180° flip. The two colors are
    perceptually almost identical, so DE2000 should be small (well under 1).
    """
    # Pick two near-red colors: a slight +b (hue ≈ 1°) and a slight -b
    # (hue ≈ 359°). Naive averaging would give 180°; correct behavior wraps.
    de = delta_e_2000((50.0, 30.0, 0.5), (50.0, 30.0, -0.5))
    assert math.isfinite(de)
    assert de < 1.0, f"hue wrap mishandled: DE2000={de}"


def test_delta_e_symmetric_in_arguments() -> None:
    """DE2000 is symmetric: DE(A, B) == DE(B, A)."""
    a = (40.0, 25.0, -15.0)
    b = (55.0, -10.0, 30.0)
    assert delta_e_2000(a, b) == pytest.approx(delta_e_2000(b, a), abs=1e-9)


def test_delta_e_out_of_gamut_inputs_are_finite() -> None:
    """Lab values outside the sRGB gamut (high chroma, e.g. spectral cyan)
    are still valid CIE coordinates. DE2000 must remain finite.
    """
    de = delta_e_2000((50.0, -100.0, -50.0), (50.0, 0.0, 0.0))
    assert math.isfinite(de)
    assert de > 0.0


# ----- assert_color_accuracy ---------------------------------------------


def test_color_accuracy_pass_for_identical_patches() -> None:
    measured = [(50.0, 0.0, 0.0), (60.0, 10.0, -10.0)]
    reference = [(50.0, 0.0, 0.0), (60.0, 10.0, -10.0)]
    result = assert_color_accuracy(measured, reference)
    assert result.passed
    assert result.mean_de < 0.01
    assert result.max_de < 0.01


def test_color_accuracy_fail_when_above_threshold() -> None:
    measured = [(50.0, 0.0, 0.0)]
    reference = [(70.0, 0.0, 0.0)]  # 20 L* delta → DE2000 ~14
    result = assert_color_accuracy(measured, reference, max_mean_de=3.0, max_max_de=6.0)
    assert not result.passed


def test_color_accuracy_skip_indices() -> None:
    """Skipped patches don't contribute to mean/max, but still appear in per_patch."""
    measured = [(50.0, 0.0, 0.0), (50.0, 0.0, 0.0)]
    reference = [(50.0, 0.0, 0.0), (90.0, 50.0, 50.0)]  # patch 1 huge DE
    result = assert_color_accuracy(measured, reference, skip_indices=[1])
    assert result.passed
    assert len(result.per_patch) == 2
    # The skipped patch's DE is reported but not enforced
    assert result.per_patch[1] > 5.0


def test_color_accuracy_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="must have the same length"):
        assert_color_accuracy([(50.0, 0.0, 0.0)], [])


def test_color_accuracy_all_skipped_raises() -> None:
    with pytest.raises(ValueError, match="all patches skipped"):
        assert_color_accuracy([(50.0, 0.0, 0.0)], [(50.0, 0.0, 0.0)], skip_indices=[0])


# ----- assert_tonal_response ---------------------------------------------


def test_tonal_response_perfect_linear_pass() -> None:
    ref = [10.0, 20.0, 30.0, 40.0, 50.0]
    measured = [11.0, 21.0, 31.0, 41.0, 51.0]  # offset, perfectly linear
    result = assert_tonal_response(measured, ref, min_r_squared=0.99)
    assert result.passed
    assert result.r_squared > 0.999


def test_tonal_response_curved_fail() -> None:
    """A bent measured response (cubic-ish) should not pass linearity."""
    ref = list(range(10))
    measured = [(x**1.5) for x in ref]
    result = assert_tonal_response(measured, ref, min_r_squared=0.99)
    assert not result.passed


def test_tonal_response_constant_measured_fails() -> None:
    ref = [10.0, 20.0, 30.0]
    measured = [50.0, 50.0, 50.0]
    result = assert_tonal_response(measured, ref)
    assert not result.passed
    assert result.r_squared == 0.0


def test_tonal_response_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        assert_tonal_response([1.0], [1.0, 2.0])


def test_tonal_response_too_few_points_raises() -> None:
    with pytest.raises(ValueError):
        assert_tonal_response([1.0], [1.0])


def test_tonal_response_negative_slope_passes_when_linear() -> None:
    """R² is slope-agnostic: a perfectly inverted ramp is still linear and
    must pass. (Catches a regression where the regression formula required
    slope > 0.)
    """
    ref = [10.0, 20.0, 30.0, 40.0, 50.0]
    measured = [50.0, 40.0, 30.0, 20.0, 10.0]
    result = assert_tonal_response(measured, ref, min_r_squared=0.99)
    assert result.passed
    assert result.r_squared > 0.999


# ----- assert_exposure_shift ---------------------------------------------


def test_exposure_shift_brighter_passes() -> None:
    base = [(40.0, 0.0, 0.0)]
    shifted = [(50.0, 0.0, 0.0)]
    assert assert_exposure_shift(base, shifted, direction=+1)


def test_exposure_shift_wrong_direction_fails() -> None:
    base = [(50.0, 0.0, 0.0)]
    shifted = [(40.0, 0.0, 0.0)]
    assert not assert_exposure_shift(base, shifted, direction=+1)


def test_exposure_shift_below_magnitude_fails() -> None:
    base = [(50.0, 0.0, 0.0)]
    shifted = [(50.5, 0.0, 0.0)]
    assert not assert_exposure_shift(base, shifted, direction=+1, min_magnitude=1.0)


def test_exposure_shift_invalid_direction_raises() -> None:
    with pytest.raises(ValueError):
        assert_exposure_shift([(50.0, 0.0, 0.0)], [(50.0, 0.0, 0.0)], direction=0)


# ----- assert_wb_shift ----------------------------------------------------


def test_wb_shift_warm_passes() -> None:
    base = [(50.0, 0.0, 0.0)]
    shifted = [(50.0, 0.0, 5.0)]  # b* up = warmer
    assert assert_wb_shift(base, shifted, axis="b", direction=+1)


def test_wb_shift_wrong_axis_raises() -> None:
    with pytest.raises(ValueError):
        assert_wb_shift([(50.0, 0.0, 0.0)], [(50.0, 0.0, 5.0)], axis="L", direction=+1)


def test_wb_shift_wrong_direction_fails() -> None:
    base = [(50.0, 0.0, 0.0)]
    shifted = [(50.0, 0.0, -5.0)]  # cooler
    assert not assert_wb_shift(base, shifted, axis="b", direction=+1)


# ----- result types -------------------------------------------------------


def test_color_accuracy_result_frozen() -> None:
    import dataclasses

    r = ColorAccuracyResult(
        passed=True,
        mean_de=0.5,
        max_de=1.0,
        per_patch=(0.5, 1.0),
        threshold_mean=3.0,
        threshold_max=6.0,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def test_tonal_response_result_frozen() -> None:
    import dataclasses

    r = TonalResponseResult(passed=True, r_squared=0.99, threshold_r_squared=0.98)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.passed = False  # type: ignore[misc]


def test_patch_coord_frozen() -> None:
    import dataclasses

    c = PatchCoord(x=10, y=20, w=30, h=40)
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.x = 0  # type: ignore[misc]


# ----- extract_patch_values -----------------------------------------------


def test_extract_patch_values_accepts_pil_image_directly() -> None:
    """Callers that already hold a PIL ``Image.Image`` shouldn't have to
    write it to disk. The function accepts both ``Path`` and ``Image``.
    """
    img = Image.new("RGB", (50, 50), color=(255, 255, 255))
    coords = [PatchCoord(x=10, y=10, w=20, h=20)]
    result = extract_patch_values(img, coords)
    assert len(result) == 1
    L, a, b = result[0]
    assert math.isclose(L, 100.0, abs_tol=0.5)
    assert abs(a) < 0.5
    assert abs(b) < 0.5


def test_extract_patch_values_multiple_solid_patches() -> None:
    """Two patches over a hand-built two-region image return the two
    expected Lab triples in input order.
    """
    img = Image.new("RGB", (200, 100), color=(0, 0, 0))
    # Right half: pure mid-gray
    for x in range(100, 200):
        for y in range(100):
            img.putpixel((x, y), (128, 128, 128))
    coords = [
        PatchCoord(x=10, y=10, w=80, h=80),
        PatchCoord(x=110, y=10, w=80, h=80),
    ]
    [(L1, _, _), (L2, _, _)] = extract_patch_values(img, coords)
    assert math.isclose(L1, 0.0, abs_tol=1.0)
    assert 50.0 < L2 < 60.0  # sRGB 128 → L* ≈ 53.6 (D50)
