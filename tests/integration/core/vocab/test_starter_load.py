"""Integration: load the bundled starter pack via ``load_starter()``.

The starter pack is populated in v1.0.0 (Slice 6). This test asserts the
real shipped pack loads cleanly and has the expected entries.
"""

from __future__ import annotations

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
