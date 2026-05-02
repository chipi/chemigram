"""Path A: B&W (channelmixerrgb) entries (#45). Auto-skips ungated entries."""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_bw_convert_collapses_channel_spread(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """bw_convert desaturates: post-render saturation_avg drops sharply
    vs baseline.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="bw_convert",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_sat = pixel_stats.saturation_avg(base)
    after_sat = pixel_stats.saturation_avg(after)
    assert after_sat < base_sat - 0.05, (
        f"bw_convert should sharply reduce saturation_avg; "
        f"got base={base_sat:.3f}, after={after_sat:.3f}"
    )
