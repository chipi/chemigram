"""Path A: highlights module entries (#45). Auto-skips ungated entries."""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_highlights_recovery_subtle_reduces_clipping(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """A highlights-recovery move pulls clipped highlights back below the
    250 threshold; clip-pct should decrease vs baseline.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="highlights_recovery_subtle",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_clip = pixel_stats.highlight_clip_pct(base)
    after_clip = pixel_stats.highlight_clip_pct(after)
    assert after_clip <= base_clip, (
        f"highlights_recovery_subtle should not increase clip pct; "
        f"got base={base_clip:.4f}, after={after_clip:.4f}"
    )


def test_highlights_recovery_strong_reduces_clipping_more_than_subtle(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    _ = darktable_binary
    subtle = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="highlights_recovery_subtle",
        pack=expressive_pack,
        out_dir=tmp_path / "subtle",
        configdir=configdir,
    )
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="highlights_recovery_strong",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
    )
    subtle_clip = pixel_stats.highlight_clip_pct(subtle)
    strong_clip = pixel_stats.highlight_clip_pct(strong)
    # "Strong" means more aggressive recovery. If the scene has any
    # highlights to recover, strong should pull them more than subtle.
    # If the baseline has zero clip pct, both round to 0 — ok.
    assert strong_clip <= subtle_clip + 0.001, (
        f"highlights_recovery_strong should pull at least as much as subtle; "
        f"got subtle={subtle_clip:.4f}, strong={strong_clip:.4f}"
    )
