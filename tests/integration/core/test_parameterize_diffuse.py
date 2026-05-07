"""Integration: parameterized texture (diffuse-or-sharpen) apply path.

Closes #92 Bucket A.6 — Lightroom Texture parity. Three axes (first,
second, sharpness) routed through the parameterize registry.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.diffuse import (
    _FIRST_FIELD_INDEX,
    _SECOND_FIELD_INDEX,
    _SHARPNESS_FIELD_INDEX,
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
def texture_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("texture")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 3, "texture multi-axis: expected 3 params"
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"first": 0.5},
        {"second": 0.4},
        {"sharpness": 0.6},
        {"first": -0.3},  # negative → smoothing
        {"first": 0.5, "second": 0.3, "sharpness": 0.7},
        {"first": 0.0, "second": 0.0, "sharpness": 0.0},
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, texture_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, texture_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "diffuse"]
    assert plugins
    fields = decode(plugins[-1].params)
    if "first" in values:
        assert fields[_FIRST_FIELD_INDEX] == pytest.approx(values["first"], abs=1e-5)
    if "second" in values:
        assert fields[_SECOND_FIELD_INDEX] == pytest.approx(values["second"], abs=1e-5)
    if "sharpness" in values:
        assert fields[_SHARPNESS_FIELD_INDEX] == pytest.approx(values["sharpness"], abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, texture_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp, texture_entry, parameter_values={"first": 0.45, "second": 0.2}
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="diffuse"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_FIRST_FIELD_INDEX] == pytest.approx(0.45, abs=1e-5)
    assert fields[_SECOND_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)


def test_apply_entry_partial_update_preserves_unspecified_axes(baseline_xmp, texture_entry) -> None:
    """Supplying only first leaves second and sharpness at the dtstyle defaults."""
    new_xmp = apply_entry(baseline_xmp, texture_entry, parameter_values={"first": 0.6})
    plugins = [p for p in new_xmp.history if p.operation == "diffuse"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_FIRST_FIELD_INDEX] == pytest.approx(0.6, abs=1e-5)
    assert fields[_SECOND_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_SHARPNESS_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, texture_entry) -> None:
    """Default first=second=sharpness=0.0 (no change)."""
    new_xmp = apply_entry(baseline_xmp, texture_entry)
    plugins = [p for p in new_xmp.history if p.operation == "diffuse"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_FIRST_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_SECOND_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_SHARPNESS_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_preserves_iterations_and_radius(baseline_xmp, texture_entry) -> None:
    """iterations (1), radius (8), and radius_center (0) persist through the apply path."""
    new_xmp = apply_entry(
        baseline_xmp, texture_entry, parameter_values={"first": 0.5, "sharpness": 0.4}
    )
    plugins = [p for p in new_xmp.history if p.operation == "diffuse"]
    fields = decode(plugins[-1].params)
    assert fields[0] == 1  # iterations
    assert fields[2] == 8  # radius
    assert fields[14] == 0  # radius_center
