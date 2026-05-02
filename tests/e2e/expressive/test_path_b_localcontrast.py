"""Path B: localcontrast entries (#46). Auto-skips ungated entries."""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_clarity_strong_increases_local_contrast(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """clarity_strong adds local-contrast / clarity. Laplacian variance
    increases vs baseline.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="clarity_strong",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_lc = pixel_stats.local_contrast_metric(base)
    after_lc = pixel_stats.local_contrast_metric(after)
    assert after_lc > base_lc, (
        f"clarity_strong should increase local contrast; "
        f"got base={base_lc:.2f}, after={after_lc:.2f}"
    )


def test_clarity_painterly_softens_local_contrast(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """clarity_painterly is the opposite move — softer edges, lower
    Laplacian variance vs the strong direction.
    """
    _ = darktable_binary
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="clarity_strong",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
    )
    painterly = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="clarity_painterly",
        pack=expressive_pack,
        out_dir=tmp_path / "painterly",
        configdir=configdir,
    )
    strong_lc = pixel_stats.local_contrast_metric(strong)
    painterly_lc = pixel_stats.local_contrast_metric(painterly)
    assert painterly_lc < strong_lc, (
        f"clarity_painterly should produce lower local-contrast variance "
        f"than clarity_strong; got painterly={painterly_lc:.2f}, "
        f"strong={strong_lc:.2f}"
    )
