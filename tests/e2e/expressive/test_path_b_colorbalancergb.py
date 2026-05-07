"""Path B: colorbalancergb saturation entries (Phase 4 / RFC-021).

These tests originally exercised the v1.5.x discrete entries
(``sat_kill``, ``sat_boost_moderate``, ``sat_boost_strong``). When
v1.6.0 / Phase 4 collapsed those into the parameterized
``saturation_global`` entry, the tests were rewritten to apply the
single parameterized entry at the equivalent saturation values.
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_saturation_boost_increases_saturation(
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
        entry_name="saturation_global",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
        parameter_values={"saturation_global": 0.5},
    )
    base_sat = pixel_stats.saturation_avg(base)
    after_sat = pixel_stats.saturation_avg(after)
    assert after_sat > base_sat, (
        f"saturation_global at +0.5 should increase saturation; "
        f"got base={base_sat:.3f}, after={after_sat:.3f}"
    )


def test_saturation_kill_decreases_saturation(
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
        entry_name="saturation_global",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
        parameter_values={"saturation_global": -1.0},
    )
    base_sat = pixel_stats.saturation_avg(base)
    after_sat = pixel_stats.saturation_avg(after)
    assert after_sat < base_sat, (
        f"saturation_global at -1.0 should decrease saturation; "
        f"got base={base_sat:.3f}, after={after_sat:.3f}"
    )


def test_saturation_strong_vs_moderate_relative_ordering(
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
        entry_name="saturation_global",
        pack=expressive_pack,
        out_dir=tmp_path / "moderate",
        configdir=configdir,
        parameter_values={"saturation_global": 0.25},
    )
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="saturation_global",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
        parameter_values={"saturation_global": 0.5},
    )
    mod_sat = pixel_stats.saturation_avg(moderate)
    strong_sat = pixel_stats.saturation_avg(strong)
    assert strong_sat > mod_sat, (
        f"saturation_global at +0.5 should saturate more than +0.25; "
        f"got moderate={mod_sat:.3f}, strong={strong_sat:.3f}"
    )
