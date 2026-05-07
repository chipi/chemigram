"""Integration: parameterized HSL Color Mixer (colorequal) apply path.

Closes RFC-023 (Tier 2 part). Three multi-axis vocabulary entries
(hsl_saturation / hsl_hue / hsl_luminance), each with 8 per-color axes,
share a single colorequal mv4 decoder.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.colorequal import _AXIS_FIELD_INDICES, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def hsl_saturation_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("hsl_saturation")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 8, "hsl_saturation: expected 8 per-color axes"
    return entry


@pytest.fixture
def hsl_hue_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("hsl_hue")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 8
    return entry


@pytest.fixture
def hsl_luminance_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("hsl_luminance")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 8
    return entry


@pytest.mark.parametrize(
    "axis,test_value",
    [
        ("sat_red", 0.4),
        ("sat_orange", -0.3),
        ("sat_blue", 0.5),
        ("sat_magenta", -0.2),
    ],
)
def test_apply_hsl_saturation_axis_patches_op_params(
    baseline_xmp, hsl_saturation_entry, axis: str, test_value: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, hsl_saturation_entry, parameter_values={axis: test_value})
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(test_value, abs=1e-5)


@pytest.mark.parametrize(
    "axis,test_value",
    [
        ("hue_red", 10.0),
        ("hue_green", 15.0),
        ("hue_blue", -20.0),
        ("hue_lavender", 30.0),
    ],
)
def test_apply_hsl_hue_axis_patches_op_params(
    baseline_xmp, hsl_hue_entry, axis: str, test_value: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, hsl_hue_entry, parameter_values={axis: test_value})
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(test_value, abs=1e-5)


@pytest.mark.parametrize(
    "axis,test_value",
    [
        ("bright_red", 0.2),
        ("bright_blue", -0.4),  # deeper sky
        ("bright_yellow", 0.3),
        ("bright_cyan", -0.2),
    ],
)
def test_apply_hsl_luminance_axis_patches_op_params(
    baseline_xmp, hsl_luminance_entry, axis: str, test_value: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, hsl_luminance_entry, parameter_values={axis: test_value})
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(test_value, abs=1e-5)


def test_apply_hsl_saturation_full_row(baseline_xmp, hsl_saturation_entry) -> None:
    """All 8 sat axes set in one apply call."""
    values = {
        "sat_red": 0.3,
        "sat_orange": -0.2,
        "sat_yellow": 0.1,
        "sat_green": 0.4,
        "sat_cyan": -0.3,
        "sat_blue": 0.5,
        "sat_lavender": 0.0,
        "sat_magenta": -0.4,
    }
    new_xmp = apply_entry(baseline_xmp, hsl_saturation_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    fields = decode(plugins[-1].params)
    for axis, expected in values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_apply_round_trips_through_xmp_writer(baseline_xmp, hsl_hue_entry, tmp_path: Path) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        hsl_hue_entry,
        parameter_values={"hue_blue": 25.0, "hue_orange": -15.0},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="colorequal"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches
    fields = decode(matches[-1])
    assert fields[_AXIS_FIELD_INDICES["hue_blue"]] == pytest.approx(25.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["hue_orange"]] == pytest.approx(-15.0, abs=1e-5)


def test_apply_partial_update_preserves_other_axes(baseline_xmp, hsl_saturation_entry) -> None:
    """Supplying only sat_blue leaves the other 7 sat axes at the dtstyle default."""
    new_xmp = apply_entry(baseline_xmp, hsl_saturation_entry, parameter_values={"sat_blue": 0.5})
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["sat_blue"]] == pytest.approx(0.5, abs=1e-5)
    for other_axis in [
        "sat_red",
        "sat_orange",
        "sat_yellow",
        "sat_green",
        "sat_cyan",
        "sat_lavender",
        "sat_magenta",
    ]:
        assert fields[_AXIS_FIELD_INDICES[other_axis]] == pytest.approx(0.0, abs=1e-5)


def test_apply_no_values_uses_dtstyle_default(baseline_xmp, hsl_saturation_entry) -> None:
    """Default: all 24 HSL axes 0.0 (no change)."""
    new_xmp = apply_entry(baseline_xmp, hsl_saturation_entry)
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    fields = decode(plugins[-1].params)
    for axis, idx in _AXIS_FIELD_INDICES.items():
        assert fields[idx] == pytest.approx(0.0, abs=1e-5), f"{axis} should default to 0.0"


def test_apply_preserves_globals(baseline_xmp, hsl_hue_entry) -> None:
    """threshold, smoothing_hue, contrast, white_level, chroma_size, param_size,
    use_filter, hue_shift all preserved across the apply path."""
    new_xmp = apply_entry(baseline_xmp, hsl_hue_entry, parameter_values={"hue_red": 10.0})
    plugins = [p for p in new_xmp.history if p.operation == "colorequal"]
    fields = decode(plugins[-1].params)
    assert fields[0] == pytest.approx(0.1, abs=1e-5)  # threshold
    assert fields[1] == pytest.approx(1.0, abs=1e-5)  # smoothing_hue
    assert fields[2] == pytest.approx(0.0, abs=1e-5)  # contrast
    assert fields[3] == pytest.approx(1.0, abs=1e-5)  # white_level
    assert fields[4] == pytest.approx(1.5, abs=1e-5)  # chroma_size
    assert fields[5] == pytest.approx(1.0, abs=1e-5)  # param_size
    assert fields[6] == 1  # use_filter TRUE
    assert fields[31] == pytest.approx(0.0, abs=1e-5)  # hue_shift
