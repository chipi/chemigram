"""Shared fixtures for e2e tests.

Discovers the Phase 0 raw + darktable configdir via env vars (or default
paths under ``~/chemigram-phase0/``). Skips cleanly when prerequisites
are absent so ``make test`` and ``make test-integration`` don't stall.

Per ADR-040 e2e tests are not run in CI; they're gated to
``make test-e2e`` and ``scripts/pre-release-check.sh``.
"""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path

import pytest
from PIL import Image

from chemigram.core.vocab import VocabularyIndex, load_starter
from chemigram.core.xmp import Xmp, parse_xmp

_DEFAULT_CONFIGDIR = Path.home() / "chemigram-phase0" / "dt-config"
_DEFAULT_RAW = Path.home() / "chemigram-phase0" / "raws" / "raw-test.NEF"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_XMP = _REPO_ROOT / "src" / "chemigram" / "core" / "_baseline_v1.xmp"


# --- prerequisite fixtures ---------------------------------------------


def _darktable_available() -> bool:
    if "DARKTABLE_CLI" in os.environ:
        return True
    return shutil.which("darktable-cli") is not None


@pytest.fixture(scope="session")
def darktable_binary() -> str:
    if not _darktable_available():
        pytest.skip("darktable-cli not on PATH and DARKTABLE_CLI env var not set")
    return os.environ.get("DARKTABLE_CLI", "darktable-cli")


@pytest.fixture(scope="session")
def configdir() -> Path:
    raw = os.environ.get("CHEMIGRAM_DT_CONFIGDIR")
    candidate = Path(raw).expanduser() if raw else _DEFAULT_CONFIGDIR
    if not candidate.exists():
        pytest.skip(
            f"no usable darktable configdir (CHEMIGRAM_DT_CONFIGDIR unset "
            f"and {_DEFAULT_CONFIGDIR} absent)"
        )
    return candidate


@pytest.fixture(scope="session")
def test_raw() -> Path:
    raw = os.environ.get("CHEMIGRAM_TEST_RAW")
    candidate = Path(raw).expanduser() if raw else _DEFAULT_RAW
    if not candidate.exists():
        pytest.skip(f"no usable test raw (CHEMIGRAM_TEST_RAW unset and {_DEFAULT_RAW} absent)")
    return candidate


@pytest.fixture(scope="session")
def baseline_xmp() -> Xmp:
    """The bundled baseline XMP — same one ``ingest_workspace`` uses."""
    return parse_xmp(_BASELINE_XMP)


@pytest.fixture(scope="session")
def starter_vocab() -> VocabularyIndex:
    """The shipped starter pack — five real entries calibrated to dt 5.4.1."""
    return load_starter()


# --- pixel statistics --------------------------------------------------


def _mean_channels(jpeg_bytes: bytes) -> tuple[float, float, float]:
    """Return (mean_R, mean_G, mean_B) for a JPEG byte string.

    Uses per-band histograms so we avoid materializing the full pixel
    list and don't rely on the deprecated ``Image.getdata`` API.
    """
    img = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
    r_band, g_band, b_band = img.split()
    return _band_mean(r_band), _band_mean(g_band), _band_mean(b_band)


def _band_mean(band: Image.Image) -> float:
    """Mean intensity of a single 8-bit band via its histogram."""
    hist = band.histogram()  # 256 bins for 8-bit
    total = sum(i * count for i, count in enumerate(hist))
    n = sum(hist)
    return total / max(n, 1)


def mean_luminance(jpeg_path: Path) -> float:
    """Rec. 709 luma over all pixels of a JPEG file."""
    r, g, b = _mean_channels(jpeg_path.read_bytes())
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def warmth_ratio(jpeg_path: Path) -> float:
    """(mean_R + mean_G) / (2 * mean_B). Higher = warmer (toward yellow/red).

    Designed so a WB shift toward warmth produces a measurable delta on a
    typical scene without being so noise-sensitive that small renders trip
    the test.
    """
    r, g, b = _mean_channels(jpeg_path.read_bytes())
    return (r + g) / (2 * max(b, 1.0))


def highlight_clip_pct(jpeg_path: Path, *, threshold: int = 250) -> float:
    """Fraction of pixels at intensity ``threshold`` or higher (per-channel
    max). 0.0 = no clipping; 1.0 = fully blown.

    Used by `highlights_recovery_*` entries: a recovery move pulls
    highlights back, so this fraction should *decrease* relative to the
    untreated baseline.
    """
    img = Image.open(jpeg_path).convert("RGB")
    total = img.width * img.height
    clipped = 0
    for r, g, b in img.getdata():
        if r >= threshold or g >= threshold or b >= threshold:
            clipped += 1
    return clipped / max(total, 1)


def shadow_clip_pct(jpeg_path: Path, *, threshold: int = 5) -> float:
    """Fraction of pixels at intensity ``threshold`` or lower (per-channel
    max). Used by `blacks_*` and `whites_*` sigmoid entries: a black-crush
    move increases this fraction; a black-lift move decreases it.
    """
    img = Image.open(jpeg_path).convert("RGB")
    total = img.width * img.height
    crushed = 0
    for r, g, b in img.getdata():
        if max(r, g, b) <= threshold:
            crushed += 1
    return crushed / max(total, 1)


def saturation_avg(jpeg_path: Path) -> float:
    """Mean HSV saturation [0..1]. Used by `colorbalancergb` saturation/
    vibrance entries: a sat-boost move increases this; sat-kill decreases it.
    """
    img = Image.open(jpeg_path).convert("HSV")
    _h, s, _v = img.split()
    return _band_mean(s) / 255.0


def corner_vs_center_luma_ratio(jpeg_path: Path, *, corner_frac: float = 0.15) -> float:
    """Ratio of corner-region mean luma to center-region mean luma.

    Higher = corners are darker relative to center (vignette stronger).
    Used by `vignette_*` entries: a vignette darkens corners; this ratio
    decreases (corner luma / center luma falls below 1.0). Sample 4
    corner squares of side ``corner_frac * min_dim`` and one center
    square the same size.
    """
    img = Image.open(jpeg_path).convert("RGB")
    w, h = img.size
    side = max(8, int(min(w, h) * corner_frac))
    cx, cy = w // 2, h // 2

    def _region_luma(box: tuple[int, int, int, int]) -> float:
        region = img.crop(box)
        r, g, b = region.split()
        return 0.2126 * _band_mean(r) + 0.7152 * _band_mean(g) + 0.0722 * _band_mean(b)

    corners = [
        (0, 0, side, side),
        (w - side, 0, w, side),
        (0, h - side, side, h),
        (w - side, h - side, w, h),
    ]
    corner_luma = sum(_region_luma(c) for c in corners) / 4
    center_luma = _region_luma((cx - side // 2, cy - side // 2, cx + side // 2, cy + side // 2))
    return corner_luma / max(center_luma, 1.0)


def local_contrast_metric(jpeg_path: Path) -> float:
    """Laplacian-variance proxy for local contrast / clarity.

    Higher = more local edges / texture (clarity boost). Lower = softer
    (clarity reduction / painterly). Computed via PIL's `find_edges` filter
    (a 3x3 Laplacian), then variance of the result. Avoids a NumPy/SciPy
    dependency for a per-pixel-stat helper.
    """
    from PIL import ImageFilter

    img = Image.open(jpeg_path).convert("L")
    edges = img.filter(ImageFilter.FIND_EDGES)
    hist = edges.histogram()
    n = sum(hist)
    if n == 0:
        return 0.0
    mean = sum(i * c for i, c in enumerate(hist)) / n
    var = sum(c * (i - mean) ** 2 for i, c in enumerate(hist)) / n
    return var


def noise_variance(jpeg_path: Path) -> float:
    """High-frequency content as a proxy for grain/noise.

    Computed as the variance of a high-pass-filtered luminance channel
    (Pillow's EDGE_ENHANCE filter approximates a high-pass kernel). A
    grain-application primitive raises this; a grain-suppression primitive
    lowers it.
    """
    from PIL import ImageFilter

    img = Image.open(jpeg_path).convert("L")
    hp = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    # Subtract original to isolate high-frequency residuals
    hist = hp.histogram()
    n = sum(hist)
    if n == 0:
        return 0.0
    mean = sum(i * c for i, c in enumerate(hist)) / n
    return sum(c * (i - mean) ** 2 for i, c in enumerate(hist)) / n


@pytest.fixture
def pixel_stats() -> object:
    """Expose the helpers as a small namespace fixture for tests."""

    class _Stats:
        mean_luminance = staticmethod(mean_luminance)
        warmth_ratio = staticmethod(warmth_ratio)
        highlight_clip_pct = staticmethod(highlight_clip_pct)
        shadow_clip_pct = staticmethod(shadow_clip_pct)
        saturation_avg = staticmethod(saturation_avg)
        corner_vs_center_luma_ratio = staticmethod(corner_vs_center_luma_ratio)
        local_contrast_metric = staticmethod(local_contrast_metric)
        noise_variance = staticmethod(noise_variance)

    return _Stats()
