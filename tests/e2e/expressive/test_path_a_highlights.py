"""Path A: highlights module entries.

Phase 4 / RFC-021: ``highlights_recovery_subtle`` / ``_strong`` collapsed
into a single parameterized ``highlights_clip_threshold`` entry. Tests
exercise the parameterized form at the equivalent clip values
(0.95 = subtle, 0.85 = strong).
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_highlights_clip_threshold_subtle_reduces_clipping(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """highlights_clip_threshold at 0.95 (subtle-equivalent) pulls clipped
    highlights back below the 250 threshold; clip-pct should not increase
    vs baseline.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="highlights_clip_threshold",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
        parameter_values={"clip_threshold": 0.95},
    )
    base_clip = pixel_stats.highlight_clip_pct(base)
    after_clip = pixel_stats.highlight_clip_pct(after)
    assert after_clip <= base_clip, (
        f"highlights_clip_threshold at 0.95 should not increase clip pct; "
        f"got base={base_clip:.4f}, after={after_clip:.4f}"
    )


def test_highlights_clip_threshold_strong_reduces_clipping_more_than_subtle(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """At clip=0.85 (strong-equivalent) recovery is more aggressive than
    at clip=0.95 (subtle-equivalent). If the baseline has zero clip pct
    both round to 0 — tolerated."""
    _ = darktable_binary
    subtle = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="highlights_clip_threshold",
        pack=expressive_pack,
        out_dir=tmp_path / "subtle",
        configdir=configdir,
        parameter_values={"clip_threshold": 0.95},
    )
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="highlights_clip_threshold",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
        parameter_values={"clip_threshold": 0.85},
    )
    subtle_clip = pixel_stats.highlight_clip_pct(subtle)
    strong_clip = pixel_stats.highlight_clip_pct(strong)
    assert strong_clip <= subtle_clip + 0.001, (
        f"highlights_clip_threshold at 0.85 should pull at least as much as at 0.95; "
        f"got subtle={subtle_clip:.4f}, strong={strong_clip:.4f}"
    )
