"""Path B: colorbalancergb entries (#47). Auto-skips ungated entries.

Final structure depends on Pre-flight 1 (#40). The tests below assume
the v0.1 entry table (per-axis entries compose). If Pre-flight 1
confirms axes clobber, the entries restructure as multi-axis profiles
and these tests need adjustment.
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_sat_boost_strong_increases_saturation(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="sat_boost_strong",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_sat = pixel_stats.saturation_avg(base)
    after_sat = pixel_stats.saturation_avg(after)
    assert after_sat > base_sat, (
        f"sat_boost_strong should increase saturation; "
        f"got base={base_sat:.3f}, after={after_sat:.3f}"
    )


def test_sat_kill_decreases_saturation(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="sat_kill",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_sat = pixel_stats.saturation_avg(base)
    after_sat = pixel_stats.saturation_avg(after)
    assert after_sat < base_sat, (
        f"sat_kill should decrease saturation; got base={base_sat:.3f}, after={after_sat:.3f}"
    )


def test_sat_boost_strong_vs_moderate_relative_ordering(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    _ = darktable_binary
    moderate = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="sat_boost_moderate",
        pack=expressive_pack,
        out_dir=tmp_path / "moderate",
        configdir=configdir,
    )
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="sat_boost_strong",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
    )
    mod_sat = pixel_stats.saturation_avg(moderate)
    strong_sat = pixel_stats.saturation_avg(strong)
    assert strong_sat > mod_sat, (
        f"sat_boost_strong should saturate more than sat_boost_moderate; "
        f"got moderate={mod_sat:.3f}, strong={strong_sat:.3f}"
    )
