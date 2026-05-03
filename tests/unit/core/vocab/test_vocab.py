"""Unit tests for chemigram.core.vocab."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from chemigram.core.vocab import ManifestError, VocabEntry, VocabularyIndex

TEST_PACK_ROOT = Path(__file__).resolve().parents[3] / "fixtures" / "vocabulary" / "test_pack"


@pytest.fixture
def loaded_pack() -> VocabularyIndex:
    return VocabularyIndex(TEST_PACK_ROOT)


def _write_pack(tmp_path: Path, entries: list[dict]) -> Path:
    pack = tmp_path / "pack"
    pack.mkdir()
    (pack / "manifest.json").write_text(json.dumps({"entries": entries}))
    return pack


def test_load_test_pack_succeeds(loaded_pack: VocabularyIndex) -> None:
    assert len(loaded_pack.list_all()) == 6


def test_lookup_by_name_returns_vocab_entry(loaded_pack: VocabularyIndex) -> None:
    entry = loaded_pack.lookup_by_name("expo_+0.5")
    assert isinstance(entry, VocabEntry)
    assert entry.layer == "L3"
    assert "exposure" in entry.touches
    assert entry.dtstyle.name == "expo_+0.5"


def test_lookup_by_name_unknown_returns_none(loaded_pack: VocabularyIndex) -> None:
    assert loaded_pack.lookup_by_name("does_not_exist") is None


def test_list_all_unfiltered(loaded_pack: VocabularyIndex) -> None:
    names = {e.name for e in loaded_pack.list_all()}
    assert names == {
        "canon_eos_r5_baseline_l1",
        "look_neutral",
        "expo_+0.5",
        "expo_-0.5",
        "wb_warm_subtle",
        "tone_lifted_shadows_subject",
    }


def test_list_all_by_layer(loaded_pack: VocabularyIndex) -> None:
    l3 = loaded_pack.list_all(layer="L3")
    assert {e.name for e in l3} == {
        "expo_+0.5",
        "expo_-0.5",
        "wb_warm_subtle",
        "tone_lifted_shadows_subject",
    }
    assert all(e.layer == "L3" for e in l3)


def test_list_all_by_tags_or_match(loaded_pack: VocabularyIndex) -> None:
    matches = loaded_pack.list_all(tags=["lift", "warm"])
    names = {e.name for e in matches}
    assert names == {"expo_+0.5", "wb_warm_subtle"}


def test_list_all_combined_layer_and_tags(loaded_pack: VocabularyIndex) -> None:
    matches = loaded_pack.list_all(layer="L3", tags=["global"])
    assert {e.name for e in matches} == {"expo_+0.5", "expo_-0.5", "wb_warm_subtle"}


def test_lookup_l1_exact_match(loaded_pack: VocabularyIndex) -> None:
    matches = loaded_pack.lookup_l1(
        make="Canon",
        model="EOS R5",
        lens_model="RF24-105mm F4 L IS USM",
    )
    assert len(matches) == 1
    assert matches[0].plugins[0].operation == "exposure"


def test_lookup_l1_no_match_returns_empty(loaded_pack: VocabularyIndex) -> None:
    assert loaded_pack.lookup_l1("Nikon", "Z9", "Z 24-70mm f/2.8 S") == []


def test_lookup_l1_partial_mismatch_returns_empty(loaded_pack: VocabularyIndex) -> None:
    # Wrong lens, right body — must NOT match (exact-tuple per ADR-053)
    assert loaded_pack.lookup_l1("Canon", "EOS R5", "Other Lens") == []


def test_manifest_missing_field_raises(tmp_path: Path) -> None:
    pack = _write_pack(
        tmp_path,
        [
            {
                "name": "broken",
                "layer": "L3",
                # path missing
                "touches": ["exposure"],
                "tags": [],
                "description": "",
                "modversions": {},
                "darktable_version": "5.4",
                "source": "test",
                "license": "MIT",
            }
        ],
    )
    with pytest.raises(ManifestError, match="missing required field 'path'"):
        VocabularyIndex(pack)


def test_manifest_path_missing_raises(tmp_path: Path) -> None:
    pack = _write_pack(
        tmp_path,
        [
            {
                "name": "ghost",
                "layer": "L3",
                "path": "does_not_exist.dtstyle",
                "touches": ["exposure"],
                "tags": [],
                "description": "",
                "modversions": {},
                "darktable_version": "5.4",
                "source": "test",
                "license": "MIT",
            }
        ],
    )
    with pytest.raises(ManifestError, match="references missing file"):
        VocabularyIndex(pack)


def test_manifest_dtstyle_parse_fails_raises(tmp_path: Path) -> None:
    src = TEST_PACK_ROOT.parents[1] / "dtstyles" / "malformed_xml.dtstyle"
    pack = tmp_path / "pack"
    pack.mkdir()
    target_dir = pack / "layers" / "L3"
    target_dir.mkdir(parents=True)
    shutil.copy(src, target_dir / "broken.dtstyle")
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "broken_dtstyle",
                        "layer": "L3",
                        "path": "layers/L3/broken.dtstyle",
                        "touches": ["exposure"],
                        "tags": [],
                        "description": "",
                        "modversions": {},
                        "darktable_version": "5.4",
                        "source": "test",
                        "license": "MIT",
                    }
                ]
            }
        )
    )
    with pytest.raises(ManifestError, match="dtstyle failed to parse"):
        VocabularyIndex(pack)


def test_touches_mismatch_raises(tmp_path: Path) -> None:
    src = TEST_PACK_ROOT.parents[1] / "dtstyles" / "expo_plus_0p5.dtstyle"
    pack = tmp_path / "pack"
    (pack / "layers" / "L3").mkdir(parents=True)
    shutil.copy(src, pack / "layers" / "L3" / "expo.dtstyle")
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "wrong_touches",
                        "layer": "L3",
                        "path": "layers/L3/expo.dtstyle",
                        "touches": ["temperature"],  # actual is exposure
                        "tags": [],
                        "description": "",
                        "modversions": {},
                        "darktable_version": "5.4",
                        "source": "test",
                        "license": "MIT",
                    }
                ]
            }
        )
    )
    with pytest.raises(ManifestError, match="not declared in 'touches'"):
        VocabularyIndex(pack)


def test_l1_without_applies_to_raises(tmp_path: Path) -> None:
    src = TEST_PACK_ROOT.parents[1] / "dtstyles" / "expo_plus_0p5.dtstyle"
    pack = tmp_path / "pack"
    (pack / "layers" / "L1").mkdir(parents=True)
    shutil.copy(src, pack / "layers" / "L1" / "x.dtstyle")
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "l1_no_applies",
                        "layer": "L1",
                        "path": "layers/L1/x.dtstyle",
                        "touches": ["exposure"],
                        "tags": [],
                        "description": "",
                        "modversions": {},
                        "darktable_version": "5.4",
                        "source": "test",
                        "license": "MIT",
                    }
                ]
            }
        )
    )
    with pytest.raises(ManifestError, match="requires 'applies_to'"):
        VocabularyIndex(pack)


def test_invalid_layer_raises(tmp_path: Path) -> None:
    pack = _write_pack(
        tmp_path,
        [
            {
                "name": "bad_layer",
                "layer": "L4",
                "path": "x.dtstyle",
                "touches": ["exposure"],
                "tags": [],
                "description": "",
                "modversions": {},
                "darktable_version": "5.4",
                "source": "test",
                "license": "MIT",
            }
        ],
    )
    with pytest.raises(ManifestError, match="invalid layer"):
        VocabularyIndex(pack)


def test_duplicate_entry_name_raises(tmp_path: Path) -> None:
    src = TEST_PACK_ROOT.parents[1] / "dtstyles" / "expo_plus_0p5.dtstyle"
    pack = tmp_path / "pack"
    (pack / "layers").mkdir(parents=True)
    shutil.copy(src, pack / "layers" / "x.dtstyle")
    common = {
        "layer": "L3",
        "path": "layers/x.dtstyle",
        "touches": ["exposure"],
        "tags": [],
        "description": "",
        "modversions": {},
        "darktable_version": "5.4",
        "source": "test",
        "license": "MIT",
    }
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"name": "dup", **common},
                    {"name": "dup", **common},
                ]
            }
        )
    )
    with pytest.raises(ManifestError, match="duplicate entry name"):
        VocabularyIndex(pack)


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match=r"manifest\.json not found"):
        VocabularyIndex(tmp_path)


def test_malformed_json_raises(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{ not json")
    with pytest.raises(ManifestError, match="malformed JSON"):
        VocabularyIndex(tmp_path)


# ---------- multi-pack loading (RFC-018, v1.2.0) -----------------------


def _make_simple_pack(tmp_path: Path, name: str, entries: list[dict]) -> Path:
    """Create a minimal pack on disk with given entry names + a stub dtstyle each."""
    pack = tmp_path / name
    pack.mkdir()
    layers_dir = pack / "layers" / "L3" / "exposure"
    layers_dir.mkdir(parents=True)

    # Reuse the test_pack's expo_+0.5.dtstyle as a reference dtstyle for stubs
    src = TEST_PACK_ROOT / "layers" / "L3" / "exposure" / "expo_+0.5.dtstyle"

    full_entries = []
    for e in entries:
        dtstyle_filename = f"{e['name']}.dtstyle"
        shutil.copy(src, layers_dir / dtstyle_filename)
        full_entries.append(
            {
                "name": e["name"],
                "layer": "L3",
                "subtype": "exposure",
                "path": f"layers/L3/exposure/{dtstyle_filename}",
                "touches": ["exposure"],
                "tags": [],
                "description": e["name"],
                "modversions": {"exposure": 7},
                "darktable_version": "5.4",
                "source": "test",
                "license": "MIT",
                **{k: v for k, v in e.items() if k not in ("name",)},
            }
        )
    (pack / "manifest.json").write_text(json.dumps({"entries": full_entries}))
    return pack


def test_multi_pack_loads_merged_namespace(tmp_path: Path) -> None:
    pack_a = _make_simple_pack(tmp_path, "pack_a", [{"name": "expo_+0.5"}])
    pack_b = _make_simple_pack(tmp_path, "pack_b", [{"name": "expo_-0.5"}])
    idx = VocabularyIndex([pack_a, pack_b])
    names = {e.name for e in idx.list_all()}
    assert names == {"expo_+0.5", "expo_-0.5"}
    assert idx.pack_for("expo_+0.5") == pack_a
    assert idx.pack_for("expo_-0.5") == pack_b


def test_multi_pack_collision_raises_with_both_paths(tmp_path: Path) -> None:
    pack_a = _make_simple_pack(tmp_path, "pack_a", [{"name": "boom"}])
    pack_b = _make_simple_pack(tmp_path, "pack_b", [{"name": "boom"}])
    with pytest.raises(ManifestError, match=r"name collision across packs.*boom"):
        VocabularyIndex([pack_a, pack_b])


def test_multi_pack_pack_roots_property(tmp_path: Path) -> None:
    pack_a = _make_simple_pack(tmp_path, "pack_a", [{"name": "a1"}])
    pack_b = _make_simple_pack(tmp_path, "pack_b", [{"name": "b1"}])
    idx = VocabularyIndex([pack_a, pack_b])
    assert idx.pack_roots == (pack_a, pack_b)


def test_single_path_constructor_still_works(tmp_path: Path) -> None:
    """Backward-compat: VocabularyIndex(pack_root: Path) — legacy form."""
    pack = _make_simple_pack(tmp_path, "single", [{"name": "alpha"}])
    idx = VocabularyIndex(pack)
    assert {e.name for e in idx.list_all()} == {"alpha"}
    assert idx.pack_roots == (pack,)


def test_empty_pack_list_raises(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="at least one pack_root"):
        VocabularyIndex([])


# ---------- mask_spec field (v1.4.0, ADR-074) --------------------------


def test_entry_without_mask_spec_defaults_to_none(loaded_pack: VocabularyIndex) -> None:
    """Entries that don't declare mask_spec keep it as None."""
    entry = loaded_pack.lookup_by_name("expo_+0.5")
    assert entry is not None
    assert entry.mask_spec is None


def test_entry_with_mask_spec_round_trips(tmp_path: Path) -> None:
    """A manifest entry's mask_spec is loaded into VocabEntry.mask_spec verbatim."""
    src = TEST_PACK_ROOT.parents[1] / "dtstyles" / "expo_plus_0p5.dtstyle"
    pack = tmp_path / "pack"
    (pack / "layers" / "L3" / "exposure").mkdir(parents=True)
    shutil.copy(src, pack / "layers" / "L3" / "exposure" / "x.dtstyle")
    spec = {"provider": "gradient", "config": {"angle_degrees": 90, "end_offset": 0.5}}
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "name": "gradient_top_dampen",
                        "layer": "L3",
                        "subtype": "exposure",
                        "path": "layers/L3/exposure/x.dtstyle",
                        "touches": ["exposure"],
                        "tags": ["mask", "gradient"],
                        "description": "Gradient top dampen.",
                        "modversions": {"exposure": 6},
                        "darktable_version": "5.4",
                        "source": "test",
                        "license": "MIT",
                        "mask_kind": "raster",
                        "mask_ref": "current_sky_mask",
                        "mask_spec": spec,
                    }
                ]
            }
        )
    )
    index = VocabularyIndex(pack)
    entry = index.lookup_by_name("gradient_top_dampen")
    assert entry is not None
    assert entry.mask_spec == spec


# ---------- iop_order manifest fields ----------------------------------
#
# Removed in v1.2.0 prep. The empirical Path-B finding (see
# tests/fixtures/preflight-evidence/) showed darktable 5.4.1 doesn't
# require per-entry iop_order; the manifest schema dropped those fields.
# If a future dt version regresses, restore the field-validation tests
# alongside the synthesizer changes.
