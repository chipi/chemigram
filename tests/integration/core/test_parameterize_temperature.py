"""Integration: parameterized temperature (multi-axis WB) apply path.

The first multi-parameter parameterized module — exercises the apply
path's per-module value grouping and partial-update semantics.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.temperature import (
    _BLUE_FIELD_INDEX,
    _GREEN_FIELD_INDEX,
    _RED_FIELD_INDEX,
    decode,
)
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def temperature_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("temperature")
    assert entry is not None
    assert entry.parameters is not None
    # 3 axes after #90 Bucket A.3: red_coeff + green_coeff (Tint) + blue_coeff
    assert len(entry.parameters) == 3, "temperature multi-axis: expected 3 params (R/G/B)"
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"red_coeff": 2.148},
        {"blue_coeff": 2.137},
        {"green_coeff": 1.2},
        {"red_coeff": 2.0, "blue_coeff": 1.5},
        {"red_coeff": 1.0, "green_coeff": 1.0, "blue_coeff": 1.0},
        {"red_coeff": 1.5, "green_coeff": 1.1, "blue_coeff": 0.9},
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, temperature_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, temperature_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    assert plugins
    fields = decode(plugins[-1].params)
    if "red_coeff" in values:
        assert fields[_RED_FIELD_INDEX] == pytest.approx(values["red_coeff"], abs=1e-5)
    if "green_coeff" in values:
        assert fields[_GREEN_FIELD_INDEX] == pytest.approx(values["green_coeff"], abs=1e-5)
    if "blue_coeff" in values:
        assert fields[_BLUE_FIELD_INDEX] == pytest.approx(values["blue_coeff"], abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, temperature_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        temperature_entry,
        parameter_values={"red_coeff": 2.5, "blue_coeff": 0.8},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="temperature"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches
    fields = decode(matches[-1])
    assert fields[_RED_FIELD_INDEX] == pytest.approx(2.5, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(0.8, abs=1e-5)


def test_apply_entry_partial_update_preserves_unspecified_axes(
    baseline_xmp, temperature_entry
) -> None:
    """Supplying only red_coeff leaves green and blue at dtstyle defaults."""
    new_xmp = apply_entry(baseline_xmp, temperature_entry, parameter_values={"red_coeff": 2.5})
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(2.5, abs=1e-5)
    # green_coeff and blue_coeff were not supplied → preserved at dtstyle default 1.0
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


def test_apply_entry_tint_only_partial_update(baseline_xmp, temperature_entry) -> None:
    """#90 Bucket A.3: supplying only green_coeff leaves red and blue at default."""
    new_xmp = apply_entry(baseline_xmp, temperature_entry, parameter_values={"green_coeff": 1.15})
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.15, abs=1e-5)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, temperature_entry) -> None:
    """Default red=green=blue=1.0 (no shift)."""
    new_xmp = apply_entry(baseline_xmp, temperature_entry)
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


# ---------------------------------------------------------------------------
# #102 wb_kelvin_delta UX wrapper apply path
# ---------------------------------------------------------------------------


@pytest.fixture
def wb_kelvin_delta_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("wb_kelvin_delta")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 2
    return entry


def test_apply_wb_kelvin_delta_warmer(baseline_xmp, wb_kelvin_delta_entry) -> None:
    """kelvin_delta=2000 = warmer: red 1.0 → 1.2, blue 1.0 → 0.8."""
    new_xmp = apply_entry(
        baseline_xmp, wb_kelvin_delta_entry, parameter_values={"kelvin_delta": 2000.0}
    )
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.2, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(0.8, abs=1e-5)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


def test_apply_wb_kelvin_delta_cooler(baseline_xmp, wb_kelvin_delta_entry) -> None:
    """Negative kelvin_delta = cooler."""
    new_xmp = apply_entry(
        baseline_xmp, wb_kelvin_delta_entry, parameter_values={"kelvin_delta": -2500.0}
    )
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    fields = decode(plugins[-1].params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(0.75, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.25, abs=1e-5)


def test_apply_wb_kelvin_delta_tint_only(baseline_xmp, wb_kelvin_delta_entry) -> None:
    """tint_delta only affects green coefficient."""
    new_xmp = apply_entry(
        baseline_xmp, wb_kelvin_delta_entry, parameter_values={"tint_delta": 100.0}
    )
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    fields = decode(plugins[-1].params)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.01, abs=1e-5)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


def test_apply_wb_kelvin_delta_combined(baseline_xmp, wb_kelvin_delta_entry) -> None:
    """kelvin_delta + tint_delta apply together."""
    new_xmp = apply_entry(
        baseline_xmp,
        wb_kelvin_delta_entry,
        parameter_values={"kelvin_delta": 1000.0, "tint_delta": 50.0},
    )
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    fields = decode(plugins[-1].params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.1, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(0.9, abs=1e-5)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.005, abs=1e-5)


def test_apply_wb_kelvin_delta_no_values_is_identity(baseline_xmp, wb_kelvin_delta_entry) -> None:
    """No values supplied = passthrough; default kelvin_delta=tint_delta=0."""
    new_xmp = apply_entry(baseline_xmp, wb_kelvin_delta_entry)
    plugins = [p for p in new_xmp.history if p.operation == "temperature"]
    fields = decode(plugins[-1].params)
    assert fields[_RED_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_GREEN_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_BLUE_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
