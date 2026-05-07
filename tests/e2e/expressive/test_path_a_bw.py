"""Path A: B&W (channelmixerrgb) entries — bw_convert / bw_sky_drama / bw_foliage.

Closes #63. The 3 B&W entries collapse to monochrome via channelmixerrgb mv3
in "destination = grey" mode (normalize_grey=true; per-channel grey
weights sum-normalize). They produce true monochrome output (R==G==B per
pixel) but differ in luminance distribution because the grey weights
differ:

- bw_convert:    Rec. 709 (0.2126 / 0.7152 / 0.0722) — neutral
- bw_sky_drama:  red-emphasis (0.5 / 0.4 / 0.1) — lightens reds, darkens
                 blues; classic "red filter" landscape look
- bw_foliage:    green-emphasis (0.1 / 0.7 / 0.2) — lightens greens;
                 useful for forest / botanical work
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


@pytest.mark.parametrize("bw_entry", ["bw_convert", "bw_sky_drama", "bw_foliage"])
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
    """The 3 B&W entries must produce *different* luminance distributions —
    if they all rendered identically, the per-variant grey weights aren't
    actually being applied. Each variant's avg luminance should differ
    from the others by at least a small but measurable amount on the
    chart fixture (the variants vary their grey weights by ~0.3 across
    R/G/B channels; on a synthetic ColorChecker the rendered mean
    luminance shifts a few units between them)."""
    _ = darktable_binary
    luminances: dict[str, float] = {}
    for name in ("bw_convert", "bw_sky_drama", "bw_foliage"):
        rendered = render_with_entry(
            raw_path=test_raw,
            baseline=baseline_xmp,
            entry_name=name,
            pack=expressive_pack,
            out_dir=tmp_path / name,
            configdir=configdir,
        )
        luminances[name] = pixel_stats.mean_luminance(rendered)

    # Each pair should differ by at least 0.3 luminance units (out of 255).
    # Render-to-render variance on luminance sits well below 0.1.
    pairs = [
        ("bw_convert", "bw_sky_drama"),
        ("bw_convert", "bw_foliage"),
        ("bw_sky_drama", "bw_foliage"),
    ]
    for a, b in pairs:
        delta = abs(luminances[a] - luminances[b])
        assert delta > 0.3, (
            f"{a} and {b} should differ in luminance "
            f"(per-variant grey weights differ by ~0.3); got "
            f"{a}={luminances[a]:.2f}, {b}={luminances[b]:.2f}, delta={delta:.2f}"
        )
