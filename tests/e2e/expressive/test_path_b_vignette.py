"""Path B: vignette entries — directional darkens-corners check.

Originally written against discrete ``vignette_medium`` / ``vignette_heavy``
entries (#46). Those discrete magnitude variants were retired in v1.6.0
when the parameterized ``vignette`` entry shipped (RFC-021 / ADR-077):
strength is now a continuous axis exposed via ``--value V`` on the CLI
or ``value`` on MCP. Tests rewritten in this file use the parameterized
entry at progressive intensities — same intent, current API.

``vignette_subtle`` and ``vignette_strong`` (discrete L3 variants in
expressive-baseline) still ship as named recipes layered over the
parameterized primitive; they're directly testable without parameter
overrides.
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_vignette_subtle_darkens_corners(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """Discrete `vignette_subtle` recipe darkens corners relative to
    center. corner_vs_center_luma_ratio drops vs baseline."""
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="vignette_subtle",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
    )
    base_ratio = pixel_stats.corner_vs_center_luma_ratio(base)
    after_ratio = pixel_stats.corner_vs_center_luma_ratio(after)
    assert after_ratio < base_ratio, (
        f"vignette_subtle should darken corners (lower ratio); "
        f"got base={base_ratio:.3f}, after={after_ratio:.3f}"
    )


def test_vignette_strong_darker_than_subtle(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """``vignette_strong`` darkens corners more aggressively than
    ``vignette_subtle``. (Replaces the retired ``vignette_heavy`` check
    from v1.5.x — same intent, current entry names.)"""
    _ = darktable_binary
    subtle = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="vignette_subtle",
        pack=expressive_pack,
        out_dir=tmp_path / "subtle",
        configdir=configdir,
    )
    strong = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="vignette_strong",
        pack=expressive_pack,
        out_dir=tmp_path / "strong",
        configdir=configdir,
    )
    subtle_ratio = pixel_stats.corner_vs_center_luma_ratio(subtle)
    strong_ratio = pixel_stats.corner_vs_center_luma_ratio(strong)
    assert strong_ratio < subtle_ratio, (
        f"vignette_strong should darken corners more than vignette_subtle; "
        f"got subtle={subtle_ratio:.3f}, strong={strong_ratio:.3f}"
    )
