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


@pytest.fixture
def pixel_stats() -> object:
    """Expose the helpers as a small namespace fixture for tests."""

    class _Stats:
        mean_luminance = staticmethod(mean_luminance)
        warmth_ratio = staticmethod(warmth_ratio)

    return _Stats()
