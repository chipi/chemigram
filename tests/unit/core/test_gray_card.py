"""Unit tests for chemigram.core.gray_card (survey Gap #20)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from chemigram.core.gray_card import GrayCardError, wb_from_gray_card


def _make_solid_image(tmp_path: Path, color: tuple[int, int, int], size: int = 100) -> Path:
    """Create a solid-color test image."""
    img = Image.new("RGB", (size, size), color)
    path = tmp_path / f"test_{color[0]}_{color[1]}_{color[2]}.jpg"
    img.save(path, "JPEG", quality=95)
    return path


def test_neutral_gray_returns_unity_coefficients(tmp_path: Path) -> None:
    """Sampling a true neutral gray (R=G=B) returns red_coeff ≈ 1.0,
    blue_coeff ≈ 1.0 (no correction needed)."""
    path = _make_solid_image(tmp_path, (128, 128, 128))
    coeffs = wb_from_gray_card(path, x=50, y=50, sample_radius=5)
    assert coeffs.red_coeff == pytest.approx(1.0, abs=0.05)
    assert coeffs.green_coeff == pytest.approx(1.0)
    assert coeffs.blue_coeff == pytest.approx(1.0, abs=0.05)


def test_warm_cast_returns_correction_for_red_only(tmp_path: Path) -> None:
    """Sampling a region with too-warm color (high R, neutral G+B) returns
    red_coeff < 1.0 (red needs to be pulled down)."""
    path = _make_solid_image(tmp_path, (160, 128, 128))
    coeffs = wb_from_gray_card(path, x=50, y=50, sample_radius=5)
    assert coeffs.red_coeff < 1.0
    assert coeffs.green_coeff == pytest.approx(1.0)
    assert coeffs.blue_coeff == pytest.approx(1.0, abs=0.05)


def test_cool_cast_returns_correction_for_blue_only(tmp_path: Path) -> None:
    """Sampling a region with too-cool color (high B, neutral R+G) returns
    blue_coeff < 1.0."""
    path = _make_solid_image(tmp_path, (128, 128, 160))
    coeffs = wb_from_gray_card(path, x=50, y=50, sample_radius=5)
    assert coeffs.red_coeff == pytest.approx(1.0, abs=0.05)
    assert coeffs.blue_coeff < 1.0


def test_out_of_bounds_x_raises(tmp_path: Path) -> None:
    path = _make_solid_image(tmp_path, (128, 128, 128))
    with pytest.raises(GrayCardError, match="out of bounds"):
        wb_from_gray_card(path, x=150, y=50)


def test_out_of_bounds_y_raises(tmp_path: Path) -> None:
    path = _make_solid_image(tmp_path, (128, 128, 128))
    with pytest.raises(GrayCardError, match="out of bounds"):
        wb_from_gray_card(path, x=50, y=150)


def test_negative_radius_raises(tmp_path: Path) -> None:
    path = _make_solid_image(tmp_path, (128, 128, 128))
    with pytest.raises(GrayCardError, match="sample_radius"):
        wb_from_gray_card(path, x=50, y=50, sample_radius=-1)


def test_pure_black_region_raises(tmp_path: Path) -> None:
    """All-black region has no useful WB info; raises rather than divide-by-zero."""
    path = _make_solid_image(tmp_path, (0, 0, 0))
    with pytest.raises(GrayCardError, match="too dark"):
        wb_from_gray_card(path, x=50, y=50)


def test_pure_red_pixel_raises(tmp_path: Path) -> None:
    """A pure-red region (no green) would produce a divide-by-zero. Raises
    a clear error rather than crashing."""
    path = _make_solid_image(tmp_path, (200, 0, 100))
    with pytest.raises(GrayCardError, match=r"too dark|outside reasonable"):
        wb_from_gray_card(path, x=50, y=50)


def test_unreadable_image_raises(tmp_path: Path) -> None:
    bad = tmp_path / "not_an_image.jpg"
    bad.write_text("this is not a JPEG")
    with pytest.raises(GrayCardError, match="failed to read"):
        wb_from_gray_card(bad, x=10, y=10)


def test_as_parameter_values_round_trips(tmp_path: Path) -> None:
    """The returned dict matches what apply_primitive's parameter_values arg expects
    for the temperature primitive."""
    path = _make_solid_image(tmp_path, (140, 128, 110))
    coeffs = wb_from_gray_card(path, x=50, y=50, sample_radius=5)
    pv = coeffs.as_parameter_values()
    assert set(pv.keys()) == {"red_coeff", "green_coeff", "blue_coeff"}
    assert all(isinstance(v, float) for v in pv.values())


def test_clamped_sample_box_stays_in_image(tmp_path: Path) -> None:
    """Sample radius extending past the image edge is silently clamped, not
    an error — the photographer doesn't have to know exact image dimensions."""
    path = _make_solid_image(tmp_path, (128, 128, 128), size=20)
    # Radius 10 + center (5, 5) extends past image edge — should clamp, not error
    coeffs = wb_from_gray_card(path, x=5, y=5, sample_radius=10)
    assert coeffs.red_coeff == pytest.approx(1.0, abs=0.05)
