"""Integration: load the bundled starter pack via ``load_starter()``.

The starter pack is populated in v1.0.0 (Slice 6). This test asserts the
real shipped pack loads cleanly and has the expected entries.
"""

from __future__ import annotations

import pytest

from chemigram.core.vocab import VocabularyIndex, load_starter


def test_load_starter_via_factory() -> None:
    index = load_starter()
    assert isinstance(index, VocabularyIndex)
    assert len(index.list_all()) > 0


def test_starter_pack_has_expected_entries() -> None:
    index = load_starter()
    names = {e.name for e in index.list_all()}
    expected = {
        "expo_+0.5",
        "expo_-0.5",
        "wb_warm_subtle",
        "look_neutral",
        "tone_lifted_shadows_subject",
    }
    assert expected.issubset(names), f"missing: {expected - names}"


def test_starter_pack_layers_present() -> None:
    """The shipped pack has L2 + L3 entries, no L1 (per ADR-016)."""
    index = load_starter()
    layers = {e.layer for e in index.list_all()}
    assert "L2" in layers
    assert "L3" in layers
    assert "L1" not in layers


def test_starter_pack_mask_bound_entry_lookups() -> None:
    """tone_lifted_shadows_subject ships as a mask-bound L3 entry."""
    index = load_starter()
    entry = index.lookup_by_name("tone_lifted_shadows_subject")
    assert entry is not None
    assert entry.mask_kind == "raster"
    assert entry.mask_ref == "current_subject_mask"


def test_load_packs_starter_only_equivalent_to_load_starter() -> None:
    """``load_packs(["starter"])`` is a multi-pack-shaped alias for the
    common single-pack default. Same names, same count.
    """
    from chemigram.core.vocab import load_packs

    starter = load_starter()
    via_packs = load_packs(["starter"])
    assert {e.name for e in starter.list_all()} == {e.name for e in via_packs.list_all()}


def test_load_packs_starter_plus_expressive_baseline_loads() -> None:
    """Both packs load together; expressive-baseline currently empty
    (entries: []) but the index still merges cleanly.
    """
    from chemigram.core.vocab import load_packs

    via_packs = load_packs(["starter", "expressive-baseline"])
    assert len(via_packs.pack_roots) == 2
    # Empty expressive-baseline contributes 0 entries; total = starter count.
    starter_count = len(load_starter().list_all())
    assert len(via_packs.list_all()) == starter_count


def test_load_packs_unknown_pack_raises() -> None:
    """An unresolvable pack name fails fast with a clear message."""
    from chemigram.core.vocab import VocabError, load_packs

    with pytest.raises(VocabError, match="not found"):
        load_packs(["no-such-pack"])


def test_load_packs_empty_list_raises() -> None:
    from chemigram.core.vocab import VocabError, load_packs

    with pytest.raises(VocabError, match="at least one pack name"):
        load_packs([])
