"""Path B: grain entries (#46). Auto-skips ungated entries."""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_grain_heavy_increases_noise_variance(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """grain_heavy produces measurably more high-frequency noise than
    the baseline render.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_heavy",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_var = pixel_stats.noise_variance(base)
    after_var = pixel_stats.noise_variance(after)
    assert after_var > base_var, (
        f"grain_heavy should increase noise_variance; "
        f"got base={base_var:.2f}, after={after_var:.2f}"
    )


def test_grain_relative_ordering(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """noise_variance(fine) ≤ noise_variance(medium) ≤ noise_variance(heavy)."""
    _ = darktable_binary
    fine = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_fine",
        pack=expressive_pack,
        out_dir=tmp_path / "fine",
        configdir=configdir,
    )
    medium = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_medium",
        pack=expressive_pack,
        out_dir=tmp_path / "medium",
        configdir=configdir,
    )
    heavy = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_heavy",
        pack=expressive_pack,
        out_dir=tmp_path / "heavy",
        configdir=configdir,
    )
    fine_var = pixel_stats.noise_variance(fine)
    medium_var = pixel_stats.noise_variance(medium)
    heavy_var = pixel_stats.noise_variance(heavy)
    assert fine_var <= medium_var <= heavy_var, (
        f"grain noise_variance should be monotonically increasing across "
        f"fine/medium/heavy; got fine={fine_var:.2f}, "
        f"medium={medium_var:.2f}, heavy={heavy_var:.2f}"
    )
