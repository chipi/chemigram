"""Smoke tests for the 14 L2 looks authored from the photographer-workflows
survey (RFC-031/032/033 follow-up).

Each look:
- Loads from the expressive-baseline manifest
- Has the expected touches
- Synthesizes onto an empty baseline without raising
- Pre-baked masks (3 of the 14) resolve cleanly through RFC-032
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry, apply_with_mask
from chemigram.core.vocab import VocabularyIndex, load_packs, resolve_named_mask_spec
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"

SURVEY_LOOKS_GLOBAL = [
    "look_portrait_natural_skin",
    "look_portrait_editorial",
    "look_portrait_split_tone_moody",
    "look_landscape_grand_vista",
    "look_landscape_intimate_quiet",
    "look_landscape_golden_hour",
    "look_landscape_blue_hour_cool",
    "look_landscape_atmospheric_haze",
    "look_landscape_dramatic_moody",
    "look_landscape_autumn_pop",
]

SURVEY_LOOKS_MASKED = [
    "look_portrait_skin_warm_lift",  # mask_skin_region
    "look_portrait_background_dim",  # mask_subject + invert (RFC-034)
    "look_landscape_sky_enhance",  # mask_sky
    "look_landscape_water_silk",  # mask_water_blue_cyan
]


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    template = parse_xmp(_BASELINE)
    return dataclasses.replace(template, history=())


def test_all_survey_looks_load(vocab: VocabularyIndex) -> None:
    for name in SURVEY_LOOKS_GLOBAL + SURVEY_LOOKS_MASKED:
        entry = vocab.lookup_by_name(name)
        assert entry is not None, f"missing: {name}"
        assert entry.layer == "L2"
        assert entry.subtype == "look"


@pytest.mark.parametrize("name", SURVEY_LOOKS_GLOBAL)
def test_global_survey_look_applies(vocab: VocabularyIndex, empty_baseline: Xmp, name: str) -> None:
    """Each global (no pre-baked mask) survey look synthesizes onto the
    empty baseline without raising and produces history entries for every
    touched module."""
    entry = vocab.lookup_by_name(name)
    assert entry is not None
    result = apply_entry(empty_baseline, entry)
    ops = {h.operation for h in result.history}
    for touched in entry.touches:
        assert touched in ops, f"{name}: missing {touched} in history"


@pytest.mark.parametrize("name", SURVEY_LOOKS_MASKED)
def test_masked_survey_look_applies(vocab: VocabularyIndex, empty_baseline: Xmp, name: str) -> None:
    """Each masked survey look's pre-baked named mask resolves and applies."""
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


def test_skin_warm_lift_pre_baked_with_skin_region(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("look_portrait_skin_warm_lift")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_skin_region"}


def test_sky_enhance_pre_baked_with_sky(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("look_landscape_sky_enhance")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_sky"}


def test_water_silk_pre_baked_with_water_band(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("look_landscape_water_silk")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_water_blue_cyan"}


def test_background_dim_pre_baked_with_inverted_subject(vocab: VocabularyIndex) -> None:
    """RFC-034: look_portrait_background_dim ships with mask_subject +
    invert: true (no caller-supplied mask required)."""
    entry = vocab.lookup_by_name("look_portrait_background_dim")
    assert entry is not None
    assert entry.mask_spec == {
        "kind": "named",
        "name": "mask_subject",
        "invert": True,
    }
    # Resolution applies the invert XOR
    resolved = resolve_named_mask_spec(entry.mask_spec, vocab)
    assert resolved is not None
    assert resolved["range_filter"]["invert"] is True


def test_intimate_quiet_uses_negative_clarity(vocab: VocabularyIndex) -> None:
    """Marino restraint discipline: the look should use negative
    clarity_strength (softening) rather than the typical positive value.
    Verified by re-decoding the bilat plugin's op_params."""
    from chemigram.core.parameterize import bilat

    entry = vocab.lookup_by_name("look_landscape_intimate_quiet")
    assert entry is not None
    bilat_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "bilat")
    fields = bilat.decode(bilat_plugin.op_params)
    # bilat fields: (mode, sigma_r, sigma_s, detail/clarity_strength, midtone)
    clarity_strength = fields[3]
    assert clarity_strength < 0.0, (
        f"intimate_quiet should soften (negative clarity), got {clarity_strength}"
    )


def test_water_silk_uses_negative_clarity(vocab: VocabularyIndex) -> None:
    """Water silk: bilat clarity_strength should be negative (smoothing)."""
    from chemigram.core.parameterize import bilat

    entry = vocab.lookup_by_name("look_landscape_water_silk")
    assert entry is not None
    bilat_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "bilat")
    fields = bilat.decode(bilat_plugin.op_params)
    clarity_strength = fields[3]
    assert clarity_strength < 0.0


def test_dramatic_moody_uses_strong_contrast(vocab: VocabularyIndex) -> None:
    """Dramatic moody should use strong sigmoid contrast (>1.5)."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    sigmoid_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    fields = sigmoid.decode(sigmoid_plugin.op_params)
    contrast = fields[0]
    assert contrast > 1.5, f"dramatic_moody contrast={contrast} should be >1.5"
