"""Path A: B&W (channelmixerrgb) entries — bw_sky_drama / bw_foliage.

Closes #63. These channelmixerrgb mv3 B&W variants collapse to monochrome
in "destination = grey" mode (normalize_grey=true; per-channel grey
weights sum-normalize). They produce true monochrome output (R==G==B per
pixel) but differ in luminance distribution because the grey weights
differ:

- bw_sky_drama:  red-emphasis (0.5 / 0.4 / 0.1) — lightens reds, darkens
                 blues; classic "red filter" landscape look
- bw_foliage:    green-emphasis (0.1 / 0.7 / 0.2) — lightens greens;
                 useful for forest / botanical work

bw_convert was retired from this trio in v1.10.0 — survey Gap #1
(photographer-workflows Round 2) replaced the channelmixerrgb-based
bw_convert with a colorequal-based parameterized B&W primitive (8
sat axes at -1.0 + 8 bright_X parameters emulating Adams-school color
filters). Visual review per the darkroom-session checkpoint validates
the new bw_convert; flat-patch chroma assertions don't apply.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


@pytest.mark.parametrize("bw_entry", ["bw_sky_drama", "bw_foliage"])
def test_bw_entry_collapses_channel_spread(
    bw_entry: str,
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Each B&W entry desaturates: post-render saturation_avg drops sharply
    vs baseline."""
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name=bw_entry,
        pack=expressive_pack,
        out_dir=tmp_path / bw_entry,
        configdir=configdir,
    )
    base_sat = pixel_stats.saturation_avg(base)
    after_sat = pixel_stats.saturation_avg(after)
    assert after_sat < base_sat - 0.05, (
        f"{bw_entry} should sharply reduce saturation_avg; "
        f"got base={base_sat:.3f}, after={after_sat:.3f}"
    )


def test_bw_variants_produce_distinct_luminance_distributions(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """The 2 channelmixerrgb B&W variants must produce *different* luminance
    distributions — if they rendered identically, the per-variant grey
    weights aren't actually being applied. The 2 variants' grey weights
    differ by ~0.3 across R/G/B channels; on a synthetic ColorChecker
    the rendered mean luminance should shift measurably between them."""
    _ = darktable_binary
    luminances: dict[str, float] = {}
    for name in ("bw_sky_drama", "bw_foliage"):
        rendered = render_with_entry(
            raw_path=test_raw,
            baseline=baseline_xmp,
            entry_name=name,
            pack=expressive_pack,
            out_dir=tmp_path / name,
            configdir=configdir,
        )
        luminances[name] = pixel_stats.mean_luminance(rendered)

    delta = abs(luminances["bw_sky_drama"] - luminances["bw_foliage"])
    assert delta > 0.3, (
        f"bw_sky_drama and bw_foliage should differ in luminance "
        f"(per-variant grey weights differ by ~0.3); got "
        f"sky_drama={luminances['bw_sky_drama']:.2f}, "
        f"foliage={luminances['bw_foliage']:.2f}, delta={delta:.2f}"
    )
