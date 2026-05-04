"""Lab-grade validation that highlights_recovery actually reduces clipped
pixel count on the clipped-gradient fixture (issue #79).

The colorchecker24 and grayscale-ramp fixtures don't have blown
highlights, so the existing lab-grade isolation suite can only assert
"highlights_recovery dampens bright patches" via grayscale-ramp luma —
which works as a direction-of-change proxy but doesn't actually test
the recovery operation. The clipped-gradient fixture has a 60% pure-
white band on the bottom half by design; this test counts the clipped
pixels there before and after applying ``highlights_recovery_strong``
and asserts the count drops.

Per RFC-019 / ADR-067 fixture-integrity rules: the test stays in
direction-of-change territory (just asserts clip-count direction +
minimum delta), not a Delta-E reference test, since the clipped
fixture isn't anchored in the published reference data.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from pathlib import Path

import pytest
from PIL import Image

from chemigram.core.pipeline import render
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp, synthesize_xmp, write_xmp

_TESTS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_TESTS_ROOT.parent))

_REPO = Path(__file__).resolve().parents[2]
_BASELINE_TEMPLATE = _REPO / "src/chemigram/core/_baseline_v1.xmp"
_CLIPPED = _REPO / "tests/fixtures/reference-targets/clipped_gradient_synthetic.png"

# The clipped fixture is 600x400. Its bottom-left 60% (rows 200..399,
# cols 0..359) is pinned at 255,255,255 in the source. After render,
# the same proportional region in the output contains the clipped band.
# We count pixels at or above the threshold within that region.
_CLIP_THRESHOLD = 250  # 8-bit; matches conftest.highlight_clip_pct convention


def _resolve_configdir() -> Path:
    raw = os.environ.get("CHEMIGRAM_DT_CONFIGDIR")
    if raw:
        path = Path(raw).expanduser()
        if path.exists():
            return path
    fallback = Path.home() / "chemigram-phase0" / "dt-config"
    if fallback.exists():
        return fallback
    pytest.skip("CHEMIGRAM_DT_CONFIGDIR not set and ~/chemigram-phase0/dt-config absent")


def _empty_baseline() -> Xmp:
    template = parse_xmp(_BASELINE_TEMPLATE)
    return dataclasses.replace(template, history=())


def _clipped_pixel_count(image_path: Path, threshold: int = _CLIP_THRESHOLD) -> int:
    """Count pixels in the bottom-left 60% region with all RGB channels
    at or above ``threshold``.

    Region: rows H/2..H, cols 0..0.6*W (the clipped band in the source).
    """
    img = Image.open(image_path).convert("RGB")
    w, h = img.size
    band = img.crop((0, h // 2, int(w * 0.6), h))
    n = 0
    for r, g, b in band.getdata():
        if r >= threshold and g >= threshold and b >= threshold:
            n += 1
    return n


@pytest.fixture(scope="module")
def configdir() -> Path:
    return _resolve_configdir()


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


def test_highlights_recovery_strong_reduces_clipped_pixels_on_clipped_fixture(
    vocab: VocabularyIndex,
    configdir: Path,
    tmp_path_factory: pytest.TempPathFactory,
    darktable_binary: str,
) -> None:
    """Render the clipped fixture twice — empty baseline vs through
    ``highlights_recovery_strong`` — and assert the clipped-pixel count
    in the white band drops.

    Threshold for pass: at least 5% reduction in clipped pixels. Real
    highlights recovery on actual blown raw data drops clipping much
    more aggressively (often 30-80%); the modest 5% threshold here is
    deliberately conservative because the synthetic fixture is sRGB
    PNG (display-referred), not raw — recovery only has the limited
    headroom darktable's display-referred path provides.
    """
    _ = darktable_binary
    out_dir = tmp_path_factory.mktemp("clipped_recovery")
    baseline_xmp = _empty_baseline()

    # Baseline render
    base_xmp_path = out_dir / "baseline.xmp"
    base_out = out_dir / "baseline.jpg"
    write_xmp(baseline_xmp, base_xmp_path)
    base_result = render(
        raw_path=_CLIPPED,
        xmp_path=base_xmp_path,
        output_path=base_out,
        width=400,
        height=400,
        high_quality=False,
        configdir=configdir,
    )
    if not base_result.success:
        pytest.fail(f"baseline render failed: {base_result.error_message}")

    # Recovery render
    entry = vocab.lookup_by_name("highlights_recovery_strong")
    if entry is None:
        pytest.fail("highlights_recovery_strong not found in expressive-baseline pack")
    recovery_xmp = synthesize_xmp(baseline_xmp, [entry.dtstyle])
    recovery_xmp_path = out_dir / "recovery.xmp"
    recovery_out = out_dir / "recovery.jpg"
    write_xmp(recovery_xmp, recovery_xmp_path)
    recovery_result = render(
        raw_path=_CLIPPED,
        xmp_path=recovery_xmp_path,
        output_path=recovery_out,
        width=400,
        height=400,
        high_quality=False,
        configdir=configdir,
    )
    if not recovery_result.success:
        pytest.fail(f"recovery render failed: {recovery_result.error_message}")

    base_clipped = _clipped_pixel_count(base_out)
    recovery_clipped = _clipped_pixel_count(recovery_out)

    if base_clipped == 0:
        pytest.fail(
            f"baseline render has 0 clipped pixels in the band — fixture "
            f"may not have rendered with the expected clipped region "
            f"({base_out})"
        )

    reduction_pct = (base_clipped - recovery_clipped) / base_clipped * 100
    if reduction_pct < 5.0:
        pytest.fail(
            f"highlights_recovery_strong reduced clipped pixels by only "
            f"{reduction_pct:.2f}% (baseline {base_clipped} -> recovery "
            f"{recovery_clipped}); expected >= 5% reduction. The clipped "
            f"fixture is sRGB display-referred so recovery is limited, but "
            f"any reduction below 5% suggests the module isn't engaging."
        )
