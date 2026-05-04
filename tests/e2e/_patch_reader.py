"""Read 24-patch values from rendered ColorChecker / grayscale targets.

Used by the lab-grade primitive tests in
:mod:`tests.e2e.test_lab_grade_primitives`. Both rendered fixtures have
fixed grid layouts derived from
``tests/fixtures/reference-targets/colorchecker_synthetic_srgb.png``
(600x400, 6 cols x 4 rows) and ``grayscale_synthetic_linear.png``
(600x100, 24 patches in a single row).

The renders preserve aspect ratio (darktable's ``--width N --height N``
fits, doesn't stretch), so any rendered output of these fixtures has
the patches in the same proportional positions. We sample the center
50% of each patch to avoid bilinear-interpolation artifacts at patch
edges.

Per-patch values are returned as :class:`PatchSample` with sRGB,
linear-RGB, and CIE Lab D50 representations — the test author picks
which one to assert against based on what the primitive's effect is
most cleanly expressed in.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from chemigram.core.assertions import (
    _M_SRGB_TO_XYZ_D50,
    _matmul3,
    _srgb_to_linear,
    _xyz_to_lab,
)

# 24 patches in a 6-col x 4-row grid for the ColorChecker.
_CC_COLS = 6
_CC_ROWS = 4

# 24 patches in a single row for the grayscale ramp.
_GRAYSCALE_PATCHES = 24


@dataclass(frozen=True)
class PatchSample:
    """One patch's mean values in three useful color spaces.

    Attributes:
        index: 0..23, matching the patch order in
            ``tests/fixtures/reference-targets/colorchecker24_lab_d50.json``.
        srgb: Mean sRGB triple (0.0..1.0 floats).
        linear: Mean linear-RGB triple (0.0..1.0 floats).
        lab: Mean CIE Lab D50 triple (L 0..100, a/b roughly -128..127).
    """

    index: int
    srgb: tuple[float, float, float]
    linear: tuple[float, float, float]
    lab: tuple[float, float, float]


def _patch_to_sample(idx: int, mean_srgb_8bit: tuple[float, float, float]) -> PatchSample:
    """Convert mean 0..255 sRGB to PatchSample with linear + Lab attached."""
    srgb = (mean_srgb_8bit[0] / 255.0, mean_srgb_8bit[1] / 255.0, mean_srgb_8bit[2] / 255.0)
    linear = (
        _srgb_to_linear(srgb[0]),
        _srgb_to_linear(srgb[1]),
        _srgb_to_linear(srgb[2]),
    )
    xyz = _matmul3(_M_SRGB_TO_XYZ_D50, linear)
    lab = _xyz_to_lab(*xyz)
    return PatchSample(index=idx, srgb=srgb, linear=linear, lab=lab)


def _sample_region_mean(
    img: Image.Image, x0: int, y0: int, x1: int, y1: int
) -> tuple[float, float, float]:
    """Return mean R/G/B (0..255 floats) over an axis-aligned crop."""
    crop = img.crop((x0, y0, x1, y1)).convert("RGB")
    pixels = list(crop.getdata())
    n = len(pixels)
    if n == 0:
        raise ValueError(f"empty crop: ({x0},{y0})-({x1},{y1})")
    rs = sum(p[0] for p in pixels)
    gs = sum(p[1] for p in pixels)
    bs = sum(p[2] for p in pixels)
    return rs / n, gs / n, bs / n


def read_colorchecker(image_path: Path) -> list[PatchSample]:
    """Read 24 patches from a rendered ColorChecker chart.

    Returns patches in row-major order matching
    ``colorchecker24_lab_d50.json``'s ``patches[*].index``.
    """
    img = Image.open(image_path).convert("RGB")
    try:
        W, H = img.size  # noqa: N806 — image-dimension convention
        pw = W / _CC_COLS  # patch width (may be fractional after aspect-fit render)
        ph = H / _CC_ROWS  # patch height
        # Sample the center 50% of each patch to avoid edge interpolation
        margin_x = pw * 0.25
        margin_y = ph * 0.25

        out: list[PatchSample] = []
        for idx in range(_CC_COLS * _CC_ROWS):
            row = idx // _CC_COLS
            col = idx % _CC_COLS
            x0 = int(col * pw + margin_x)
            y0 = int(row * ph + margin_y)
            x1 = int((col + 1) * pw - margin_x)
            y1 = int((row + 1) * ph - margin_y)
            mean = _sample_region_mean(img, x0, y0, x1, y1)
            out.append(_patch_to_sample(idx, mean))
        return out
    finally:
        img.close()


def read_grayscale_ramp(image_path: Path) -> list[PatchSample]:
    """Read 24 patches from a rendered grayscale ramp (single row).

    Patches are ordered left-to-right matching the source layout in
    ``grayscale_synthetic_linear.png`` (24 patches at 25 px wide each
    in the 600x100 source).
    """
    img = Image.open(image_path).convert("RGB")
    try:
        W, H = img.size  # noqa: N806 — image-dimension convention
        pw = W / _GRAYSCALE_PATCHES
        # Sample the center 50% horizontally and vertically
        margin_x = pw * 0.25
        margin_y = H * 0.25

        out: list[PatchSample] = []
        for idx in range(_GRAYSCALE_PATCHES):
            x0 = int(idx * pw + margin_x)
            y0 = int(margin_y)
            x1 = int((idx + 1) * pw - margin_x)
            y1 = int(H - margin_y)
            mean = _sample_region_mean(img, x0, y0, x1, y1)
            out.append(_patch_to_sample(idx, mean))
        return out
    finally:
        img.close()


def luma_linear(sample: PatchSample) -> float:
    """Rec.709 / sRGB luma weights on the linear-RGB triple."""
    r, g, b = sample.linear
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def chroma_lab(sample: PatchSample) -> float:
    """Lab chroma magnitude: sqrt(a^2 + b^2). 0 = neutral gray."""
    _, a, b = sample.lab
    return (a * a + b * b) ** 0.5
