"""Unit tests for the built-in geometric mask providers (ADR-074)."""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from chemigram.core.masking import MaskGenerationError, MaskResult
from chemigram.core.masking.geometric import (
    GradientMaskProvider,
    RadialMaskProvider,
    RectangleMaskProvider,
)


@pytest.fixture
def render_path(tmp_path: Path) -> Path:
    """Write a small JPEG so providers can read its dimensions."""
    img = Image.new("RGB", (200, 100), (128, 128, 128))
    p = tmp_path / "preview.jpg"
    img.save(p, "JPEG")
    return p


def _decode(result: MaskResult) -> np.ndarray:
    img = Image.open(io.BytesIO(result.png_bytes))
    assert img.mode == "L"
    return np.asarray(img)


# ---------------------------------------------------------------------------
# GradientMaskProvider
# ---------------------------------------------------------------------------


def test_gradient_default_top_brighter(render_path: Path) -> None:
    provider = GradientMaskProvider()
    result = provider.generate(target="sky", render_path=render_path)
    arr = _decode(result)
    assert arr.shape == (100, 200)  # (height, width)
    # angle=90 ⇒ top is bright. First row mean > last row mean.
    assert arr[0].mean() > arr[-1].mean()


def test_gradient_horizontal_left_brighter(render_path: Path) -> None:
    provider = GradientMaskProvider(angle_degrees=180.0)  # bright side faces left
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    # First column brighter than last
    assert arr[:, 0].mean() > arr[:, -1].mean()


def test_gradient_peak_caps_intensity(render_path: Path) -> None:
    provider = GradientMaskProvider(peak=0.5)
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    # 0.5 * 255 = 127.5 → max possible 128
    assert arr.max() <= 128


def test_gradient_offsets_clamp(render_path: Path) -> None:
    # angle=270 (bottom-bright), end_offset=0.5: ramps 0→peak across the
    # top half, holds at peak across the bottom half.
    provider = GradientMaskProvider(angle_degrees=270.0, start_offset=0.0, end_offset=0.5)
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    h = arr.shape[0]
    # Top row at 0; bottom half saturated at peak (255).
    assert arr[0].mean() < 5
    assert arr[h // 2 + 5 :].mean() > 250


def test_gradient_invalid_offsets_raise() -> None:
    with pytest.raises(MaskGenerationError):
        GradientMaskProvider(start_offset=0.6, end_offset=0.4)


def test_gradient_out_of_unit_range_raises() -> None:
    with pytest.raises(MaskGenerationError):
        GradientMaskProvider(peak=1.5)


def test_gradient_metadata_round_trip(render_path: Path) -> None:
    provider = GradientMaskProvider()
    result = provider.generate(target="sky", render_path=render_path, prompt="top half")
    assert result.generator == "gradient"
    assert result.target == "sky"
    assert result.prompt == "top half"


def test_gradient_regenerate_delegates(render_path: Path) -> None:
    provider = GradientMaskProvider()
    first = provider.generate(target="x", render_path=render_path)
    second = provider.regenerate(target="x", render_path=render_path, prior_mask=first.png_bytes)
    # Geometric → deterministic; bytes match exactly
    assert first.png_bytes == second.png_bytes


# ---------------------------------------------------------------------------
# RadialMaskProvider
# ---------------------------------------------------------------------------


def test_radial_center_brightest(render_path: Path) -> None:
    provider = RadialMaskProvider()
    result = provider.generate(target="subject", render_path=render_path)
    arr = _decode(result)
    h, w = arr.shape
    cy, cx = h // 2, w // 2
    # Center pixel should be at peak (255)
    assert arr[cy, cx] == 255
    # Corners should be 0
    assert arr[0, 0] == 0
    assert arr[-1, -1] == 0


def test_radial_off_center(render_path: Path) -> None:
    provider = RadialMaskProvider(cx=0.25, cy=0.25, inner_radius=0.05, outer_radius=0.2)
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    h, w = arr.shape
    # Top-left quadrant intensity should exceed bottom-right
    assert arr[: h // 2, : w // 2].mean() > arr[h // 2 :, w // 2 :].mean()


def test_radial_inner_outer_ordering_required() -> None:
    with pytest.raises(MaskGenerationError):
        RadialMaskProvider(inner_radius=0.5, outer_radius=0.4)


def test_radial_negative_ellipse_ratio_rejected() -> None:
    with pytest.raises(MaskGenerationError):
        RadialMaskProvider(ellipse_ratio=0.0)


def test_radial_peak_caps_intensity(render_path: Path) -> None:
    provider = RadialMaskProvider(peak=0.4)
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    assert arr.max() <= int(0.4 * 255) + 1  # +1 for rounding


def test_radial_metadata(render_path: Path) -> None:
    provider = RadialMaskProvider()
    result = provider.generate(target="subject", render_path=render_path)
    assert result.generator == "radial"


# ---------------------------------------------------------------------------
# RectangleMaskProvider
# ---------------------------------------------------------------------------


def test_rectangle_full_image_default(render_path: Path) -> None:
    provider = RectangleMaskProvider()
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    # Full coverage → all pixels at peak (255)
    assert (arr == 255).all()


def test_rectangle_half_image(render_path: Path) -> None:
    provider = RectangleMaskProvider(x0=0.0, y0=0.0, x1=0.5, y1=1.0)
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    _h, w = arr.shape
    # Left half peak, right half zero
    assert arr[:, : w // 2 - 1].mean() > 200
    assert arr[:, w // 2 + 5 :].mean() < 5


def test_rectangle_with_feather_smooths_edge(render_path: Path) -> None:
    hard = RectangleMaskProvider(x0=0.25, y0=0.25, x1=0.75, y1=0.75, feather=0.0)
    soft = RectangleMaskProvider(x0=0.25, y0=0.25, x1=0.75, y1=0.75, feather=0.3)
    h_arr = _decode(hard.generate(target="x", render_path=render_path))
    s_arr = _decode(soft.generate(target="x", render_path=render_path))
    # Feathered has a gradient along the edges → its histogram has more
    # intermediate values than the hard mask (which is just 0 / 255).
    h_unique = np.unique(h_arr).size
    s_unique = np.unique(s_arr).size
    assert s_unique > h_unique


def test_rectangle_invalid_box_rejected() -> None:
    with pytest.raises(MaskGenerationError):
        RectangleMaskProvider(x0=0.6, y0=0.0, x1=0.4, y1=1.0)


def test_rectangle_peak_caps_intensity(render_path: Path) -> None:
    provider = RectangleMaskProvider(peak=0.7)
    result = provider.generate(target="x", render_path=render_path)
    arr = _decode(result)
    assert arr.max() <= int(0.7 * 255) + 1


def test_rectangle_regenerate_deterministic(render_path: Path) -> None:
    provider = RectangleMaskProvider(x0=0.1, y0=0.1, x1=0.9, y1=0.9, feather=0.1)
    first = provider.generate(target="x", render_path=render_path)
    again = provider.regenerate(target="x", render_path=render_path, prior_mask=first.png_bytes)
    assert first.png_bytes == again.png_bytes


# ---------------------------------------------------------------------------
# Integration: registering a generated mask in the per-image registry
# ---------------------------------------------------------------------------


def test_geometric_provider_output_registers_in_repo(tmp_path: Path) -> None:
    """Smoke: a generated PNG round-trips through register_mask + get_mask
    just like the agent provider's output."""
    from chemigram.core.versioning import ImageRepo
    from chemigram.core.versioning.masks import get_mask, register_mask
    from chemigram.core.workspace import init_workspace_root

    ws_root = tmp_path / "ws"
    init_workspace_root(ws_root)
    repo = ImageRepo.init(ws_root)
    img = Image.new("RGB", (256, 128), (200, 200, 200))
    render_path = ws_root / "preview.jpg"
    img.save(render_path, "JPEG")

    provider = GradientMaskProvider()
    result = provider.generate(target="sky", render_path=render_path)
    register_mask(repo, "sky_gradient", result.png_bytes, generator=result.generator)
    _entry, png = get_mask(repo, "sky_gradient")
    assert png == result.png_bytes
