"""Path B: grain entries.

Phase 4 / RFC-021: ``grain_fine``, ``grain_medium``, ``grain_heavy`` were
collapsed into a single parameterized ``grain_strength`` entry. Tests
exercise the parameterized form at the equivalent strength values
(8 = fine, 25 = medium, 50 = heavy).
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.vocab import VocabularyIndex
from chemigram.core.xmp import Xmp

from .conftest import render_baseline, render_with_entry


def test_grain_strength_heavy_increases_noise_variance(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """grain_strength at 50 (grain_heavy-equivalent) produces measurably
    more high-frequency noise than the baseline render.
    """
    _ = darktable_binary
    base = render_baseline(
        raw_path=test_raw, baseline=baseline_xmp, out_dir=tmp_path, configdir=configdir
    )
    after = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_strength",
        pack=expressive_pack,
        out_dir=tmp_path,
        configdir=configdir,
        parameter_values={"grain_strength": 50.0},
    )
    base_var = pixel_stats.noise_variance(base)
    after_var = pixel_stats.noise_variance(after)
    assert after_var > base_var, (
        f"grain_strength at 50 should increase noise_variance; "
        f"got base={base_var:.2f}, after={after_var:.2f}"
    )


def test_grain_strength_relative_ordering(
    test_raw: Path,
    configdir: Path,
    baseline_xmp: Xmp,
    expressive_pack: VocabularyIndex,
    darktable_binary: str,
    tmp_path: Path,
    pixel_stats,
) -> None:
    """noise_variance(strength=8) ≤ noise_variance(25) ≤ noise_variance(50).
    Replaces the v1.5.x grain_fine / grain_medium / grain_heavy ordering
    test (RFC-021 / Phase 4).
    """
    _ = darktable_binary
    fine = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_strength",
        pack=expressive_pack,
        out_dir=tmp_path / "fine",
        configdir=configdir,
        parameter_values={"grain_strength": 8.0},
    )
    medium = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_strength",
        pack=expressive_pack,
        out_dir=tmp_path / "medium",
        configdir=configdir,
        parameter_values={"grain_strength": 25.0},
    )
    heavy = render_with_entry(
        raw_path=test_raw,
        baseline=baseline_xmp,
        entry_name="grain_strength",
        pack=expressive_pack,
        out_dir=tmp_path / "heavy",
        configdir=configdir,
        parameter_values={"grain_strength": 50.0},
    )
    fine_var = pixel_stats.noise_variance(fine)
    medium_var = pixel_stats.noise_variance(medium)
    heavy_var = pixel_stats.noise_variance(heavy)
    assert fine_var <= medium_var <= heavy_var, (
        f"grain noise_variance should be monotonically increasing across "
        f"strength=8/25/50; got fine={fine_var:.2f}, "
        f"medium={medium_var:.2f}, heavy={heavy_var:.2f}"
    )
