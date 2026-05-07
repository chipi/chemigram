"""Path B: localcontrast entries.

Phase 4 / RFC-021: ``clarity_strong`` was retired and replaced by the
parameterized ``bilat_clarity_strength`` entry; ``clarity_painterly``
remains discrete (different *kind* of clarity, not strength).
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_bilat_clarity_strength_increases_local_contrast(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """bilat_clarity_strength at 1.5 (clarity_strong-equivalent) adds
    local-contrast / clarity. Laplacian variance increases vs baseline.
    Replaces the v1.5.x clarity_strong test (RFC-021 / Phase 4).
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="bilat_clarity_strength",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
        parameter_values={"clarity_strength": 1.5},
    )
    base_lc = pixel_stats.local_contrast_metric(base)
    after_lc = pixel_stats.local_contrast_metric(after)
    assert after_lc > base_lc, (
        f"bilat_clarity_strength at 1.5 should increase local contrast; "
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
    """clarity_painterly is a different *kind* of clarity move (softer
    edges, lower Laplacian variance) — kept as a discrete entry. Compared
    against bilat_clarity_strength at 1.5 (the clarity_strong-equivalent).
    """
    _ = darktable_binary
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="bilat_clarity_strength",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
        parameter_values={"clarity_strength": 1.5},
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
        f"than bilat_clarity_strength at 1.5; "
        f"got painterly={painterly_lc:.2f}, strong={strong_lc:.2f}"
    )
