"""Integration: parameterized filmic v6 apply path. Closes #97."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.filmicrgb import _AXIS_FIELD_INDICES, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def filmic_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("filmic")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 8, "filmic: expected 8 magnitude axes"
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"contrast": 1.5},
        {"saturation": 20.0},
        {"output_power": 2.5},
        {"grey_point_source": 20.0, "white_point_source": 5.0},
        {"contrast": 1.2, "saturation": 10.0, "balance": -5.0},
        {
            "grey_point_source": 18.45,
            "black_point_source": -8.0,
            "white_point_source": 4.0,
            "output_power": 4.0,
            "latitude": 0.01,
            "contrast": 1.0,
            "saturation": 0.0,
            "balance": 0.0,
        },  # darktable defaults
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, filmic_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, filmic_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "filmicrgb"]
    assert plugins
    fields = decode(plugins[-1].params)
    for axis, expected in values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-3)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, filmic_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        filmic_entry,
        parameter_values={"contrast": 1.4, "output_power": 3.0},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="filmicrgb"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches
    fields = decode(matches[-1])
    assert fields[_AXIS_FIELD_INDICES["contrast"]] == pytest.approx(1.4, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["output_power"]] == pytest.approx(3.0, abs=1e-5)


def test_apply_entry_partial_update_preserves_other_axes(baseline_xmp, filmic_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, filmic_entry, parameter_values={"contrast": 2.0})
    plugins = [p for p in new_xmp.history if p.operation == "filmicrgb"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["contrast"]] == pytest.approx(2.0, abs=1e-5)
    # Other axes preserved at darktable defaults
    assert fields[_AXIS_FIELD_INDICES["grey_point_source"]] == pytest.approx(18.45, abs=1e-3)
    assert fields[_AXIS_FIELD_INDICES["output_power"]] == pytest.approx(4.0, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_defaults(baseline_xmp, filmic_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, filmic_entry)
    plugins = [p for p in new_xmp.history if p.operation == "filmicrgb"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["contrast"]] == pytest.approx(1.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["output_power"]] == pytest.approx(4.0, abs=1e-5)


def test_apply_entry_preserves_mode_enums(baseline_xmp, filmic_entry) -> None:
    """preserve_color (POWER_NORM=3), version (V5=4), spline_version (V3=2)
    must survive the apply path."""
    new_xmp = apply_entry(baseline_xmp, filmic_entry, parameter_values={"contrast": 1.5})
    plugins = [p for p in new_xmp.history if p.operation == "filmicrgb"]
    fields = decode(plugins[-1].params)
    assert fields[18] == 3  # preserve_color
    assert fields[19] == 4  # version
    assert fields[27] == 2  # spline_version
