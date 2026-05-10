"""Smoke tests for the 10 R3-cheap L2 looks (wildlife + food/product).

Closes survey-derived L2 catalog for genres 5 + 6. Validates schema
correctness and synthesis structure. Visual quality requires
darktable-session sign-off — see ``docs/guides/darkroom-session-debt.md``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry, apply_with_mask
from chemigram.core.vocab import VocabularyIndex, load_packs, resolve_named_mask_spec
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"

R3_GLOBAL_LOOKS = [
    "look_wildlife_high_iso_recovery",
    "look_wildlife_natural_warm",
    "look_food_appetizing_warm",
    "look_food_orange_pop",
    "look_food_green_natural",
    "look_product_packshot_clean",
]

R3_MASKED_LOOKS = [
    "look_wildlife_subject_sharpen",  # mask_subject
    "look_wildlife_background_blur",  # mask_subject + invert
    "look_wildlife_eye_lift",  # mask_eye_region
    "look_food_texture_subtle",  # mask_subject (food)
]


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    return dataclasses.replace(parse_xmp(_BASELINE), history=())


def test_all_r3_looks_load(vocab: VocabularyIndex) -> None:
    for name in R3_GLOBAL_LOOKS + R3_MASKED_LOOKS:
        entry = vocab.lookup_by_name(name)
        assert entry is not None, f"missing: {name}"
        assert entry.layer == "L2"
        assert entry.subtype == "look"


@pytest.mark.parametrize("name", R3_GLOBAL_LOOKS)
def test_global_r3_look_applies(vocab: VocabularyIndex, empty_baseline: Xmp, name: str) -> None:
    entry = vocab.lookup_by_name(name)
    assert entry is not None
    result = apply_entry(empty_baseline, entry)
    ops = {h.operation for h in result.history}
    for touched in entry.touches:
        assert touched in ops, f"{name}: missing {touched} in history"


@pytest.mark.parametrize("name", R3_MASKED_LOOKS)
def test_masked_r3_look_applies(vocab: VocabularyIndex, empty_baseline: Xmp, name: str) -> None:
    entry = vocab.lookup_by_name(name)
    assert entry is not None
    assert entry.mask_spec is not None
    assert entry.mask_spec.get("kind") == "named"
    resolved = resolve_named_mask_spec(entry.mask_spec, vocab)
    assert resolved is not None
    result = apply_with_mask(empty_baseline, entry.dtstyle, resolved)
    ops = {h.operation for h in result.history}
    for touched in entry.touches:
        assert touched in ops


def test_wildlife_subject_sharpen_uses_mask_subject(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("look_wildlife_subject_sharpen")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_subject"}


def test_wildlife_background_blur_uses_inverted_subject(vocab: VocabularyIndex) -> None:
    """RFC-034 invert flag — background blur is "everything except subject"."""
    entry = vocab.lookup_by_name("look_wildlife_background_blur")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_subject", "invert": True}
    # The resolved spec should have parametric invert: True
    resolved = resolve_named_mask_spec(entry.mask_spec, vocab)
    assert resolved is not None
    assert resolved["range_filter"]["invert"] is True


def test_wildlife_background_blur_uses_negative_clarity(vocab: VocabularyIndex) -> None:
    """Background blur means SOFTENING — negative clarity_strength."""
    from chemigram.core.parameterize import bilat

    entry = vocab.lookup_by_name("look_wildlife_background_blur")
    assert entry is not None
    bilat_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "bilat")
    fields = bilat.decode(bilat_plugin.op_params)
    clarity = fields[3]
    assert clarity < 0.0, f"background_blur should soften (negative clarity); got {clarity}"


def test_wildlife_eye_lift_uses_mask_eye_region(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("look_wildlife_eye_lift")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_eye_region"}


def test_food_orange_pop_lifts_orange_red(vocab: VocabularyIndex) -> None:
    """orange_pop must lift sat_orange + sat_red but NOT sat_green or sat_blue."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("look_food_orange_pop")
    assert entry is not None
    ce_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "colorequal")
    fields = colorequal.decode(ce_plugin.op_params)
    # sat_red=7, sat_orange=8, sat_green=10, sat_blue=12
    assert fields[7] > 0.10, f"sat_red should be lifted; got {fields[7]}"
    assert fields[8] > 0.10, f"sat_orange should be lifted; got {fields[8]}"
    assert fields[10] == pytest.approx(0.0), f"sat_green should be untouched; got {fields[10]}"
    assert fields[12] == pytest.approx(0.0), f"sat_blue should be untouched; got {fields[12]}"


def test_food_green_natural_lifts_green_only(vocab: VocabularyIndex) -> None:
    """green_natural lifts sat_green + sat_yellow without affecting other bands."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("look_food_green_natural")
    assert entry is not None
    ce_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "colorequal")
    fields = colorequal.decode(ce_plugin.op_params)
    assert fields[10] > 0.10, f"sat_green should be lifted; got {fields[10]}"
    assert fields[7] == pytest.approx(0.0), f"sat_red should be untouched; got {fields[7]}"


def test_food_texture_subtle_uses_clarity_ceiling(vocab: VocabularyIndex) -> None:
    """Food clarity ceiling — must NOT exceed +0.30 (Kopcok's 'don't dry it' rule)."""
    from chemigram.core.parameterize import bilat

    entry = vocab.lookup_by_name("look_food_texture_subtle")
    assert entry is not None
    bilat_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "bilat")
    fields = bilat.decode(bilat_plugin.op_params)
    clarity = fields[3]
    assert 0 < clarity <= 0.30, f"food texture clarity should be in (0, 0.30]; got {clarity}"


def test_product_packshot_clean_uses_gentle_contrast(vocab: VocabularyIndex) -> None:
    """Product packshot — restraint discipline; sigmoid contrast ≤ 1.20."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_product_packshot_clean")
    assert entry is not None
    s_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    fields = sigmoid.decode(s_plugin.op_params)
    assert fields[0] <= 1.20, f"packshot contrast should be ≤1.20 (restraint); got {fields[0]}"
