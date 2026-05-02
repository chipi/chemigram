"""Shared fixtures for the expressive-baseline pack e2e tests.

The pack is authored entry-by-entry across issues #45/#46/#47. Tests
auto-discover entries from the loaded pack and skip cleanly when an
expected entry isn't yet authored — this keeps the suite green during
the authoring slog while flagging missing entries clearly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.pipeline import render
from chemigram.core.vocab import VocabError, VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, synthesize_xmp, write_xmp


@pytest.fixture(scope="session")
def expressive_pack() -> VocabularyIndex:
    """Load the expressive-baseline pack (alongside starter).

    Skips the test if the pack isn't on disk or has no entries yet.
    """
    try:
        idx = load_packs(["starter", "expressive-baseline"])
    except VocabError as exc:
        pytest.skip(f"expressive-baseline pack not loadable: {exc}")
    if len(idx.list_all()) <= 5:
        pytest.skip("expressive-baseline pack has no entries yet (only starter loaded)")
    return idx


def render_with_entry(
    *,
    raw_path: Path,
    baseline: Xmp,
    entry_name: str,
    pack: VocabularyIndex,
    out_dir: Path,
    configdir: Path,
    size: int = 256,
) -> Path:
    """Synthesize ``entry_name`` onto ``baseline``, render, return JPEG path.

    Skips the test (rather than failing) if the entry isn't in the pack
    yet — entries are added incrementally during #45/#46/#47.
    """
    entry = pack.lookup_by_name(entry_name)
    if entry is None:
        pytest.skip(f"entry {entry_name!r} not yet authored in expressive-baseline")

    synthesized = synthesize_xmp(baseline, [entry.dtstyle])
    out_dir.mkdir(parents=True, exist_ok=True)
    xmp_path = out_dir / f"{entry_name}.xmp"
    out_path = out_dir / f"{entry_name}.jpg"
    write_xmp(synthesized, xmp_path)
    result = render(
        raw_path=raw_path,
        xmp_path=xmp_path,
        output_path=out_path,
        width=size,
        height=size,
        high_quality=False,
        configdir=configdir,
    )
    assert result.success, f"{entry_name} render failed: {result.error_message}"
    return out_path


def render_baseline(
    *, raw_path: Path, baseline: Xmp, out_dir: Path, configdir: Path, size: int = 256
) -> Path:
    """Render the bundled baseline (no vocabulary applied) to JPEG."""
    xmp_path = out_dir / "baseline.xmp"
    out_path = out_dir / "baseline.jpg"
    write_xmp(baseline, xmp_path)
    result = render(
        raw_path=raw_path,
        xmp_path=xmp_path,
        output_path=out_path,
        width=size,
        high_quality=False,
        height=size,
        configdir=configdir,
    )
    assert result.success, f"baseline render failed: {result.error_message}"
    return out_path
