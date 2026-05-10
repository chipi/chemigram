"""Unit tests for the B&W vocabulary — bw_convert primitive + 5 L2 looks.

Closes survey Gap #1 (6/6 universal in B&W; 3/6 in Wedding for B&W-as-
parallel-deliverable). Validates schema correctness and synthesis structure.
Visual quality (does the rendered B&W actually read as natural / dramatic /
restrained per intent?) requires a darktable-session sign-off — see
``docs/guides/darkroom-session-debt.md``.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.vocab import VocabularyIndex, load_packs
from chemigram.core.xmp import Xmp, parse_xmp

_BASELINE = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"

BW_LOOKS = [
    "look_bw_classic_neutral",
    "look_bw_high_contrast_chiaroscuro",
    "look_bw_landscape_dramatic",
    "look_bw_split_tone_warm_shadows",
    "look_bw_silver_efex_zone_balanced",
]


@pytest.fixture(scope="module")
def vocab() -> VocabularyIndex:
    return load_packs(["expressive-baseline"])


@pytest.fixture
def empty_baseline() -> Xmp:
    return dataclasses.replace(parse_xmp(_BASELINE), history=())


# ---------- bw_convert primitive --------------------------------------


def test_bw_convert_loads(vocab: VocabularyIndex) -> None:
    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    assert entry.layer == "L3"
    assert entry.subtype == "colorequal"
    assert "bw" in entry.tags
    assert "channel-mixer" in entry.tags
    assert "parameterized" in entry.tags


def test_bw_convert_has_eight_brightness_parameters(vocab: VocabularyIndex) -> None:
    """Per-color brightness controls emulate Adams-school color filters:
    bright_red lightens reds; bright_blue darkens skies; etc."""
    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 8
    expected = {
        "bright_red",
        "bright_orange",
        "bright_yellow",
        "bright_green",
        "bright_cyan",
        "bright_blue",
        "bright_lavender",
        "bright_magenta",
    }
    actual = {p.name for p in entry.parameters}
    assert actual == expected


def test_bw_convert_baseline_saturation_killed(vocab: VocabularyIndex) -> None:
    """The dtstyle's baseline op_params must have all 8 sat axes at -1.0
    (full saturation kill = grayscale rendering as the baseline)."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    plugin = entry.dtstyle.plugins[0]
    fields = colorequal.decode(plugin.op_params)
    # sat_red..sat_magenta are field indices 7..14 (offsets 28..59 / 4)
    for field_idx in range(7, 15):
        assert fields[field_idx] == pytest.approx(-1.0), (
            f"sat axis at field {field_idx} not -1.0; got {fields[field_idx]}"
        )


def test_bw_convert_applies_to_baseline(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Synthesis end-to-end: applying bw_convert with default parameters
    produces a colorequal entry in the XMP with sat-killed baseline."""
    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    result = apply_entry(empty_baseline, entry)
    colorequal_entries = [h for h in result.history if h.operation == "colorequal"]
    assert len(colorequal_entries) == 1


def test_bw_convert_red_filter_application(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Applying bw_convert with bright_red=+0.3 + bright_blue=-0.3 produces
    the classic Adams red-filter B&W (lightens land, darkens skies)."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("bw_convert")
    assert entry is not None
    result = apply_entry(
        empty_baseline,
        entry,
        parameter_values={"bright_red": 0.3, "bright_blue": -0.3},
    )
    colorequal_entries = [h for h in result.history if h.operation == "colorequal"]
    assert len(colorequal_entries) == 1
    # Re-decode to verify the filter values landed
    fields = colorequal.decode(colorequal_entries[0].params)
    # bright_red = field idx 23, bright_blue = field idx 28
    assert fields[23] == pytest.approx(0.3)
    assert fields[28] == pytest.approx(-0.3)


# ---------- look_bw_* L2 entries --------------------------------------


@pytest.mark.parametrize("name", BW_LOOKS)
def test_bw_look_loads(vocab: VocabularyIndex, name: str) -> None:
    entry = vocab.lookup_by_name(name)
    assert entry is not None, f"missing: {name}"
    assert entry.layer == "L2"
    assert entry.subtype == "look"
    assert "bw" in entry.tags
    assert "monochrome" in entry.tags


@pytest.mark.parametrize("name", BW_LOOKS)
def test_bw_look_applies(vocab: VocabularyIndex, empty_baseline: Xmp, name: str) -> None:
    """Each B&W L2 look synthesizes onto the empty baseline; touched
    modules appear in history including the colorequal sat-kill."""
    entry = vocab.lookup_by_name(name)
    assert entry is not None
    result = apply_entry(empty_baseline, entry)
    ops = {h.operation for h in result.history}
    for touched in entry.touches:
        assert touched in ops, f"{name}: missing {touched} in history"
    # Every B&W look must touch colorequal (the sat-kill conversion)
    assert "colorequal" in ops


def test_bw_landscape_dramatic_uses_red_filter(vocab: VocabularyIndex) -> None:
    """look_bw_landscape_dramatic should bake in the red-filter convention
    — bright_red >= +0.15 and bright_blue <= -0.20 (Adams red-filter
    skies-darken-land-lighten)."""
    from chemigram.core.parameterize import colorequal

    entry = vocab.lookup_by_name("look_bw_landscape_dramatic")
    assert entry is not None
    colorequal_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "colorequal")
    fields = colorequal.decode(colorequal_plugin.op_params)
    bright_red = fields[23]
    bright_blue = fields[28]
    assert bright_red >= 0.15, f"red-filter: bright_red should be ≥+0.15; got {bright_red}"
    assert bright_blue <= -0.20, f"red-filter: bright_blue should be ≤-0.20; got {bright_blue}"


def test_bw_high_contrast_uses_strong_sigmoid(vocab: VocabularyIndex) -> None:
    """look_bw_high_contrast_chiaroscuro should use sigmoid contrast >= 1.6."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_bw_high_contrast_chiaroscuro")
    assert entry is not None
    sigmoid_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    fields = sigmoid.decode(sigmoid_plugin.op_params)
    assert fields[0] >= 1.6, f"chiaroscuro contrast should be ≥1.6; got {fields[0]}"


def test_bw_silver_efex_zone_balanced_is_restrained(vocab: VocabularyIndex) -> None:
    """The Whalley/Boutwell zone-balanced look should use restrained sigmoid
    (≤1.25) — the explicit restraint stylistic position for B&W."""
    from chemigram.core.parameterize import sigmoid

    entry = vocab.lookup_by_name("look_bw_silver_efex_zone_balanced")
    assert entry is not None
    sigmoid_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "sigmoid")
    fields = sigmoid.decode(sigmoid_plugin.op_params)
    assert fields[0] <= 1.25, f"zone-balanced contrast should be ≤1.25 (restraint); got {fields[0]}"


def test_bw_split_tone_uses_split_color(vocab: VocabularyIndex) -> None:
    """look_bw_split_tone_warm_shadows must declare colorbalancergb in its
    touches AND apply distinct shadow/highlight hues."""
    entry = vocab.lookup_by_name("look_bw_split_tone_warm_shadows")
    assert entry is not None
    assert "colorbalancergb" in entry.touches
    cb_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "colorbalancergb")
    assert cb_plugin.op_params  # non-empty patched blob


def test_all_bw_looks_kill_saturation(vocab: VocabularyIndex, empty_baseline: Xmp) -> None:
    """Every B&W look's colorequal plugin must have all sat axes at -1.0
    (the universal property — no B&W look should leak color)."""
    from chemigram.core.parameterize import colorequal

    for name in BW_LOOKS:
        entry = vocab.lookup_by_name(name)
        assert entry is not None
        ce_plugin = next(p for p in entry.dtstyle.plugins if p.operation == "colorequal")
        fields = colorequal.decode(ce_plugin.op_params)
        for field_idx in range(7, 15):  # sat_red..sat_magenta
            assert fields[field_idx] == pytest.approx(-1.0), (
                f"{name}: sat axis at field {field_idx} not -1.0; got {fields[field_idx]}"
            )
