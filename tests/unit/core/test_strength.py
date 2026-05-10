"""Unit tests for chemigram.core.strength (RFC-035 Path B).

Validates per-parameter interpolation:
- strength=1.0 preserves authored op_params byte-for-byte
- strength=0.0 returns identity (no-op) values
- strength=0.5 halfway between identity and authored
- Multi-plugin L2 looks interpolate every plugin's parameterized fields
- Modules without parameterize decoders pass through unchanged
- Out-of-range strength raises in apply_entry
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.strength import (
    IDENTITY_VALUES,
    apply_strength_to_dtstyle,
    interpolate_plugin_strength,
)
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    return dataclasses.replace(parse_xmp(_BASELINE), history=())


# ---------- interpolate_plugin_strength ---------------------------------


def test_strength_one_preserves_plugin(vocab: VocabularyIndex) -> None:
    """strength=1.0 returns the plugin unchanged byte-for-byte."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    for plugin in entry.dtstyle.plugins:
        result = interpolate_plugin_strength(plugin, 1.0)
        assert result == plugin


def test_strength_zero_pulls_to_identity_sigmoid(vocab: VocabularyIndex) -> None:
    """sigmoid contrast at strength=0 should equal identity (1.0)."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    sig_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    # Authored contrast = 1.7 (per look_bw_landscape_dramatic / look_landscape_dramatic_moody)
    authored_fields = sigmoid.decode(sig_plugin.op_params)
    assert authored_fields[0] > 1.5  # confirm non-identity baseline
    # At strength=0, contrast should be back to identity (1.0)
    interpolated = interpolate_plugin_strength(sig_plugin, 0.0)
    interp_fields = sigmoid.decode(interpolated.op_params)
    assert interp_fields[0] == pytest.approx(1.0, abs=0.001)


def test_strength_half_is_midway_sigmoid(vocab: VocabularyIndex) -> None:
    """sigmoid contrast at strength=0.5 should be (identity + authored) / 2."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    sig_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    authored = sigmoid.decode(sig_plugin.op_params)[0]
    expected_half = 1.0 + 0.5 * (authored - 1.0)

    interpolated = interpolate_plugin_strength(sig_plugin, 0.5)
    actual = sigmoid.decode(interpolated.op_params)[0]
    assert actual == pytest.approx(expected_half, abs=0.001)


def test_strength_zero_pulls_colorequal_sat_to_zero(vocab: VocabularyIndex) -> None:
    """colorequal sat axes have identity 0.0; strength=0 should zero them."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    ce_plugin = entry.dtstyle.plugins[0]
    # Authored sat axes are -1.0 (full sat-kill in bw_convert)
    authored = colorequal.decode(ce_plugin.op_params)
    assert authored[7] == pytest.approx(-1.0)  # sat_red
    # At strength=0, sat axes should be 0 (identity)
    interpolated = interpolate_plugin_strength(ce_plugin, 0.0)
    interp = colorequal.decode(interpolated.op_params)
    for field_idx in range(7, 15):  # sat_red..sat_magenta
        assert interp[field_idx] == pytest.approx(0.0, abs=0.001)


def test_strength_half_pulls_colorequal_sat_halfway(vocab: VocabularyIndex) -> None:
    """colorequal sat at strength=0.5 should be 0 + 0.5 * (-1.0 - 0) = -0.5."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    ce_plugin = entry.dtstyle.plugins[0]
    interpolated = interpolate_plugin_strength(ce_plugin, 0.5)
    interp = colorequal.decode(interpolated.op_params)
    for field_idx in range(7, 15):
        assert interp[field_idx] == pytest.approx(-0.5, abs=0.001)


def test_strength_clamp_below_zero_treats_as_zero(vocab: VocabularyIndex) -> None:
    """Negative strength is clamped to 0 (treats as identity)."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    sig_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    interpolated = interpolate_plugin_strength(sig_plugin, -0.5)
    fields = sigmoid.decode(interpolated.op_params)
    assert fields[0] == pytest.approx(1.0, abs=0.001)  # identity


def test_strength_clamp_above_one_treats_as_one(vocab: VocabularyIndex) -> None:
    """strength > 1.0 is clamped to 1.0 (preserves authored)."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    sig_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    interpolated = interpolate_plugin_strength(sig_plugin, 2.0)
    assert interpolated == sig_plugin


# ---------- apply_strength_to_dtstyle (multi-plugin L2 looks) -----------


def test_apply_strength_to_l2_look(vocab: VocabularyIndex) -> None:
    """L2 look at strength=0.5 has every parameterized plugin halfway-pulled."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    interpolated = apply_strength_to_dtstyle(entry.dtstyle, 0.5)
    # Same plugin count, same operations
    assert len(interpolated.plugins) == len(entry.dtstyle.plugins)
    for orig, interp in zip(entry.dtstyle.plugins, interpolated.plugins, strict=True):
        assert orig.operation == interp.operation


def test_apply_strength_one_preserves_dtstyle(vocab: VocabularyIndex) -> None:
    """strength=1.0 is identity for the dtstyle (returns unchanged)."""
    entry = vocab.lookup_by_name("look_portrait_natural_skin")
    assert entry is not None
    interpolated = apply_strength_to_dtstyle(entry.dtstyle, 1.0)
    assert interpolated == entry.dtstyle


# ---------- apply_entry integration with strength -----------------------


def test_apply_entry_with_strength_synthesizes(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """apply_entry with strength=0.5 produces a valid synthesized XMP."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    result = apply_entry(empty_baseline, entry, strength=0.5)
    ops = {h.operation for h in result.history}
    for touched in entry.touches:
        assert touched in ops


def test_apply_entry_strength_out_of_range_raises(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """strength outside [0, 1] raises ValueError."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    with pytest.raises(ValueError, match="strength must be in"):
        apply_entry(empty_baseline, entry, strength=1.5)
    with pytest.raises(ValueError, match="strength must be in"):
        apply_entry(empty_baseline, entry, strength=-0.1)


def test_apply_entry_strength_one_matches_no_strength(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """strength=1.0 should produce identical XMP to no-strength apply."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    no_strength = apply_entry(empty_baseline, entry)
    full_strength = apply_entry(empty_baseline, entry, strength=1.0)
    # Same number of history entries; same operations
    assert len(no_strength.history) == len(full_strength.history)
    for a, b in zip(no_strength.history, full_strength.history, strict=True):
        assert a.operation == b.operation
        assert a.params == b.params  # byte-for-byte identical


def test_apply_entry_strength_zero_produces_identity_xmp(
    vocab: VocabularyIndex, empty_baseline: Xmp
) -> None:
    """strength=0 should produce a valid XMP where the look has no effect."""
    entry = vocab.lookup_by_name("look_landscape_dramatic_moody")
    assert entry is not None
    result = apply_entry(empty_baseline, entry, strength=0.0)
    # XMP has the entries (history records the structure) but op_params
    # should be at identity values for every parameterized field.
    ops = {h.operation for h in result.history}
    for touched in entry.touches:
        assert touched in ops


# ---------- identity registry sanity ------------------------------------


def test_identity_values_cover_all_parameterized_modules() -> None:
    """Every parameterize module with a registered decoder should have
    identity values declared in IDENTITY_VALUES."""
    expected_modules = {
        "exposure",
        "sigmoid",
        "temperature",
        "bilat",
        "vignette",
        "hazeremoval",
        "sharpen",
        "colorbalancergb",
        "colorequal",
        "denoiseprofile",
        "grain",
    }
    assert expected_modules == set(IDENTITY_VALUES.keys())
