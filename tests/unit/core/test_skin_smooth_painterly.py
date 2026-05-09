"""Unit tests for the skin_smooth_painterly primitive.

Approximate frequency separation for skin smoothing — RFC-033 Portrait
Gap #4 cheap variant. Reduces local-contrast bilat strength on the skin
hue range. Composes orthogonally with skin_uniformity (color-band) for
the full skin-uniformity-plus-smoothing move.

Tests verify schema correctness and synthesis structure. Visual quality
(natural-skin vs over-smoothed boundary) requires human review per
ADR-080's lab-grade tier.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.vocab import VocabularyIndex, load_packs, resolve_named_mask_spec
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE_XMP_PATH = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    template = parse_xmp(_BASELINE_XMP_PATH)
    return dataclasses.replace(template, history=())


def test_skin_smooth_painterly_loads(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("skin_smooth_painterly")
    assert entry is not None
    assert entry.layer == "L3"
    assert entry.subtype == "localcontrast"
    assert "skin" in entry.tags
    assert "smoothing" in entry.tags
    assert "frequency-separation-approximation" in entry.tags


def test_skin_smooth_painterly_has_clarity_strength_parameter(
    vocab: VocabularyIndex,
) -> None:
    entry = vocab.lookup_by_name("skin_smooth_painterly")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 1
    p = entry.parameters[0]
    assert p.name == "clarity_strength"
    assert p.range == (-1.0, 0.0)
    assert p.default == -0.5
    assert p.field.module == "bilat"
    # detail / clarity_strength field offset on bilat mv3
    assert p.field.offset == 12


def test_skin_smooth_painterly_pre_baked_named_mask(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("skin_smooth_painterly")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_skin_region"}


def test_skin_smooth_painterly_named_mask_resolves(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("skin_smooth_painterly")
    assert entry is not None
    resolved = resolve_named_mask_spec(entry.mask_spec, vocab)
    assert resolved is not None
    assert "range_filter" in resolved


def test_skin_smooth_painterly_applies_to_baseline(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """Synthesis end-to-end: applying at -0.5 clarity_strength produces a
    bilat history entry with the parametric mask binding encoded."""
    entry = vocab.lookup_by_name("skin_smooth_painterly")
    assert entry is not None
    resolved_mask = resolve_named_mask_spec(entry.mask_spec, vocab)
    result = apply_entry(
        empty_baseline,
        entry,
        parameter_values={"clarity_strength": -0.5},
        mask_spec=resolved_mask,
    )
    bilat_entries = [h for h in result.history if h.operation == "bilat"]
    assert len(bilat_entries) == 1
    assert bilat_entries[0].blendop_params  # patched with mask binding


def test_skin_smooth_painterly_composes_with_skin_uniformity(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """The two skin primitives compose orthogonally: skin_uniformity
    operates on colorequal (color band), skin_smooth_painterly operates
    on bilat (texture band). Both bound to mask_skin_region. Together
    they're the chemigram approximation of Photoshop's frequency-
    separation skin retouch."""
    uniform = vocab.lookup_by_name("skin_uniformity")
    smooth = vocab.lookup_by_name("skin_smooth_painterly")
    assert uniform is not None and smooth is not None
    resolved = resolve_named_mask_spec(uniform.mask_spec, vocab)

    after_uniform = apply_entry(
        empty_baseline,
        uniform,
        parameter_values={"sat_orange": -0.3},
        mask_spec=resolved,
    )
    after_smooth = apply_entry(
        after_uniform,
        smooth,
        parameter_values={"clarity_strength": -0.5},
        mask_spec=resolved,
    )
    ops = {h.operation for h in after_smooth.history}
    assert "colorequal" in ops
    assert "bilat" in ops


def test_skin_smooth_painterly_default_is_subtle(vocab: VocabularyIndex) -> None:
    """Default -0.5 sits in the middle of the recommended -0.3 to -0.7
    range. Stronger values produce the over-smoothed 'plastic skin' look
    photographers warn against."""
    entry = vocab.lookup_by_name("skin_smooth_painterly")
    assert entry is not None
    assert entry.parameters is not None
    assert entry.parameters[0].default == -0.5
