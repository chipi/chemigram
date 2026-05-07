"""Integration: parameterized ashift (transform/perspective) apply path. Closes #101."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.ashift import _AXIS_FIELD_INDICES, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def transform_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("transform")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 5
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"transform_rotation": 5.0},
        {"transform_lensshift_v": 0.3},
        {"transform_lensshift_h": -0.2},
        {"transform_shear": 0.1},
        {"transform_aspect": 1.2},
        {"transform_rotation": 5.0, "transform_lensshift_v": 0.2, "transform_aspect": 1.1},
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, transform_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, transform_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "ashift"]
    assert plugins
    fields = decode(plugins[-1].params)
    for axis, expected in values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_apply_round_trips_through_xmp_writer(
    baseline_xmp, transform_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        transform_entry,
        parameter_values={"transform_rotation": 7.5, "transform_lensshift_v": 0.4},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="ashift"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_AXIS_FIELD_INDICES["transform_rotation"]] == pytest.approx(7.5, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["transform_lensshift_v"]] == pytest.approx(0.4, abs=1e-5)


def test_apply_partial_update_preserves_other_axes(baseline_xmp, transform_entry) -> None:
    new_xmp = apply_entry(
        baseline_xmp, transform_entry, parameter_values={"transform_rotation": 5.0}
    )
    plugins = [p for p in new_xmp.history if p.operation == "ashift"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["transform_rotation"]] == pytest.approx(5.0, abs=1e-5)
    # Others preserved at defaults
    for axis in ["transform_lensshift_v", "transform_lensshift_h", "transform_shear"]:
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(0.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["transform_aspect"]] == pytest.approx(1.0, abs=1e-5)


def test_apply_no_values_uses_dtstyle_defaults(baseline_xmp, transform_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, transform_entry)
    plugins = [p for p in new_xmp.history if p.operation == "ashift"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["transform_rotation"]] == pytest.approx(0.0)
    assert fields[_AXIS_FIELD_INDICES["transform_aspect"]] == pytest.approx(1.0)
