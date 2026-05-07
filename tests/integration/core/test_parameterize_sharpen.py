"""Integration: parameterized sharpen apply path."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.sharpen import _AMOUNT_FIELD_INDEX, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def sharpen_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("sharpen")
    assert entry is not None
    assert entry.parameters is not None
    return entry


@pytest.mark.parametrize("amount", [0.0, 0.25, 0.5, 1.0, 1.5, 2.0])
def test_apply_entry_with_amount_patches_op_params(
    baseline_xmp, sharpen_entry, amount: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, sharpen_entry, parameter_values={"amount": amount})
    plugins = [p for p in new_xmp.history if p.operation == "sharpen"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_AMOUNT_FIELD_INDEX] == pytest.approx(amount, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, sharpen_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(baseline_xmp, sharpen_entry, parameter_values={"amount": 0.8})
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="sharpen"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_AMOUNT_FIELD_INDEX] == pytest.approx(0.8, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, sharpen_entry) -> None:
    """Default amount=0.0 (no sharpening)."""
    new_xmp = apply_entry(baseline_xmp, sharpen_entry)
    plugins = [p for p in new_xmp.history if p.operation == "sharpen"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_AMOUNT_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)
