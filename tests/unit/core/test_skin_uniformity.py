"""Unit tests for the skin_uniformity primitive (RFC-033).

Validates the Path-B implementation: a parameterized colorequal-touching
entry pre-baked with mask_skin_region. The entry exposes a single
``strength`` parameter [-1.0, 0.0] mapped to colorequal's sat_orange
field; the named-mask binding scopes the move to the skin hue band.

These tests verify schema correctness and synthesis structure. Visual
quality (whether the rendered result reads as natural skin) requires
human review against representative portraits — not automated here.
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


def test_skin_uniformity_loads(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    assert entry.layer == "L3"
    assert entry.subtype == "colorequal"
    assert "skin" in entry.tags
    assert "portrait" in entry.tags
    assert "uniformity" in entry.tags


def test_skin_uniformity_has_strength_parameter(vocab: VocabularyIndex) -> None:
    """Parameter shape: single float ``strength`` in [-1.0, 0.0], default
    -0.3 (moderate). Maps to colorequal's sat_orange byte offset."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 1
    p = entry.parameters[0]
    assert p.name == "sat_orange"
    assert p.type == "float"
    assert p.range == (-1.0, 0.0)
    assert p.default == -0.3
    assert p.field.module == "colorequal"
    assert p.field.offset == 32  # sat_orange byte offset


def test_skin_uniformity_pre_baked_named_mask(vocab: VocabularyIndex) -> None:
    """The manifest mask_spec is a named-mask reference to mask_skin_region —
    photographers don't have to remember to bind the mask explicitly."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    assert entry.mask_spec == {"kind": "named", "name": "mask_skin_region"}


def test_skin_uniformity_named_mask_resolves(vocab: VocabularyIndex) -> None:
    """The pre-baked named mask resolves to the parametric skin-region spec
    at apply time."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    resolved = resolve_named_mask_spec(entry.mask_spec, vocab)
    assert resolved is not None
    assert "range_filter" in resolved
    assert resolved["range_filter"]["kind"] == "color_h"


def test_skin_uniformity_applies_to_baseline(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Synthesis end-to-end: applying skin_uniformity at moderate strength
    produces a colorequal entry in the XMP with the parametric mask binding
    encoded in blendop_params."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    resolved_mask = resolve_named_mask_spec(entry.mask_spec, vocab)
    result = apply_entry(
        empty_baseline,
        entry,
        parameter_values={"sat_orange": -0.5},
        mask_spec=resolved_mask,
    )
    colorequal_entries = [h for h in result.history if h.operation == "colorequal"]
    assert len(colorequal_entries) == 1
    # blendop_params should be patched with the parametric mask binding
    # (mask_skin_region's color_h range).
    assert colorequal_entries[0].blendop_params  # non-empty


def test_skin_uniformity_range_excludes_positive_values(vocab: VocabularyIndex) -> None:
    """Range is [-1.0, 0.0] — positive values would *boost* skin saturation,
    the opposite of uniformity. Range validation happens at CLI / MCP entry
    points (typer.BadParameter / ToolError) before reaching the core; this
    test asserts the contract is declared at the manifest level."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    assert entry.parameters is not None
    p = entry.parameters[0]
    lo, hi = p.range
    assert lo == -1.0
    assert hi == 0.0
    assert hi - lo == 1.0  # full unit range
    # Positive values would be rejected by the CLI/MCP validators because
    # they exceed hi=0.0; we don't re-test that here (covered by the
    # parameterize test suite).


def test_skin_uniformity_strength_zero_is_no_op_value(
    vocab: VocabularyIndex,
) -> None:
    """strength=0.0 is the boundary — no skin desaturation. Useful as a
    check that the parameter shape allows the no-op endpoint."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    assert entry.parameters is not None
    p = entry.parameters[0]
    assert p.range[1] == 0.0  # max is exactly 0 (the no-op boundary)


def test_skin_uniformity_default_is_subtle(vocab: VocabularyIndex) -> None:
    """Default -0.3 matches surveyed photographer practice: subtle enough
    to pass a quick visual check, strong enough to noticeably even out
    patches. Not an aesthetic claim — just records the chosen default."""
    entry = vocab.lookup_by_name("skin_uniformity")
    assert entry is not None
    assert entry.parameters is not None
    p = entry.parameters[0]
    assert p.default == -0.3
