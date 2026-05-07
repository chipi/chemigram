"""Integration: parameterized crop apply path. First workflow-primitive
parameterized entry; multi-axis with partial-update support."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.crop import (
    _CH_FIELD_INDEX,
    _CW_FIELD_INDEX,
    _CX_FIELD_INDEX,
    _CY_FIELD_INDEX,
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
def crop_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("crop")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 4
    return entry


def test_apply_entry_with_full_crop_rectangle(baseline_xmp, crop_entry) -> None:
    """All 4 margins applied — typical agent invocation pattern."""
    new_xmp = apply_entry(
        baseline_xmp,
        crop_entry,
        parameter_values={"cx": 0.1, "cy": 0.15, "cw": 0.9, "ch": 0.85},
    )
    plugins = [p for p in new_xmp.history if p.operation == "crop"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_CX_FIELD_INDEX] == pytest.approx(0.1, abs=1e-5)
    assert fields[_CY_FIELD_INDEX] == pytest.approx(0.15, abs=1e-5)
    assert fields[_CW_FIELD_INDEX] == pytest.approx(0.9, abs=1e-5)
    assert fields[_CH_FIELD_INDEX] == pytest.approx(0.85, abs=1e-5)


def test_apply_entry_partial_update_one_axis(baseline_xmp, crop_entry) -> None:
    """Supplying only cx leaves the other 3 at the dtstyle defaults."""
    new_xmp = apply_entry(baseline_xmp, crop_entry, parameter_values={"cx": 0.2})
    plugins = [p for p in new_xmp.history if p.operation == "crop"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_CX_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)
    assert fields[_CY_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)  # default
    assert fields[_CW_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)  # default
    assert fields[_CH_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)  # default


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, crop_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        crop_entry,
        parameter_values={"cx": 0.05, "cy": 0.1, "cw": 0.95, "ch": 0.9},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="crop"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_CX_FIELD_INDEX] == pytest.approx(0.05, abs=1e-5)
    assert fields[_CH_FIELD_INDEX] == pytest.approx(0.9, abs=1e-5)


def test_apply_entry_no_values_produces_no_op_crop(baseline_xmp, crop_entry) -> None:
    """Defaults cx=cy=0.0, cw=ch=1.0 → no-op crop (full image)."""
    new_xmp = apply_entry(baseline_xmp, crop_entry)
    plugins = [p for p in new_xmp.history if p.operation == "crop"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_CX_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_CY_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
    assert fields[_CW_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
    assert fields[_CH_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)
