"""Path B: vignette entries (#46). Auto-skips ungated entries."""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_vignette_medium_darkens_corners(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """A vignette darkens corners relative to center. The
    corner_vs_center_luma_ratio should drop vs baseline.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="vignette_medium",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_ratio = pixel_stats.corner_vs_center_luma_ratio(base)
    after_ratio = pixel_stats.corner_vs_center_luma_ratio(after)
    assert after_ratio < base_ratio, (
        f"vignette_medium should darken corners (lower ratio); "
        f"got base={base_ratio:.3f}, after={after_ratio:.3f}"
    )


def test_vignette_heavy_darker_than_subtle(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """heavy vignette darkens corners more aggressively than subtle."""
    _ = darktable_binary
    subtle = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="vignette_subtle",
        pack=expressive_pack,
        out_dir=tmp_path / "subtle",
        configdir=configdir,
    )
    heavy = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="vignette_heavy",
        pack=expressive_pack,
        out_dir=tmp_path / "heavy",
        configdir=configdir,
    )
    subtle_ratio = pixel_stats.corner_vs_center_luma_ratio(subtle)
    heavy_ratio = pixel_stats.corner_vs_center_luma_ratio(heavy)
    assert heavy_ratio < subtle_ratio, (
        f"vignette_heavy should darken corners more than vignette_subtle; "
        f"got subtle={subtle_ratio:.3f}, heavy={heavy_ratio:.3f}"
    )
