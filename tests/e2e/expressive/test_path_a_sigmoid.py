"""Path A: sigmoid module entries (#45). Auto-skips ungated entries."""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_blacks_crushed_increases_shadow_clip_pct(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Crushing blacks moves shadow values below the 5/255 threshold;
    shadow_clip_pct should increase vs baseline.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="blacks_crushed",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_clip = pixel_stats.shadow_clip_pct(base)
    after_clip = pixel_stats.shadow_clip_pct(after)
    assert after_clip > base_clip, (
        f"blacks_crushed should increase shadow_clip_pct; "
        f"got base={base_clip:.4f}, after={after_clip:.4f}"
    )


def test_blacks_lifted_decreases_shadow_clip_pct(
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
        entry_name="blacks_lifted",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_clip = pixel_stats.shadow_clip_pct(base)
    after_clip = pixel_stats.shadow_clip_pct(after)
    assert after_clip <= base_clip, (
        f"blacks_lifted should not increase shadow_clip_pct; "
        f"got base={base_clip:.4f}, after={after_clip:.4f}"
    )


def test_contrast_high_vs_low_relative_ordering(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """contrast_high produces measurably higher local contrast than
    contrast_low. Direction-of-change between two entries that both touch
    sigmoid; tolerant of scene-specific magnitude.
    """
    _ = darktable_binary
    low = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="contrast_low",
        pack=expressive_pack,
        out_dir=tmp_path / "low",
        configdir=configdir,
    )
    high = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="contrast_high",
        pack=expressive_pack,
        out_dir=tmp_path / "high",
        configdir=configdir,
    )
    low_lc = pixel_stats.local_contrast_metric(low)
    high_lc = pixel_stats.local_contrast_metric(high)
    assert high_lc > low_lc, (
        f"contrast_high should produce higher local-contrast variance "
        f"than contrast_low; got low={low_lc:.2f}, high={high_lc:.2f}"
    )


def test_whites_open_changes_baseline(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """whites_open opens the white point — measurable change vs baseline.
    Direction depends on the scene; assert |delta| is non-trivial.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="whites_open",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_lum = pixel_stats.mean_luminance(base)
    after_lum = pixel_stats.mean_luminance(after)
    assert abs(after_lum - base_lum) > 0.5, (
        f"whites_open should change baseline; got base={base_lum:.2f}, after={after_lum:.2f}"
    )
