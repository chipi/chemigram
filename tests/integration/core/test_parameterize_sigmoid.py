"""Integration: parameterized sigmoid (contrast) apply path end-to-end.

Mirrors test_parameterize_exposure.py for the fourth parameterized
module (Phase 4 / RFC-021).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.sigmoid import _CONTRAST_FIELD_INDEX, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def sigmoid_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("sigmoid_contrast")
    assert entry is not None
    assert entry.parameters is not None
    return entry


@pytest.mark.parametrize("contrast", [0.5, 1.0, 1.5, 2.0, 2.5, 5.0])
def test_apply_entry_with_contrast_patches_op_params(
    baseline_xmp, sigmoid_entry, contrast: float
) -> None:
    new_xmp = apply_entry(baseline_xmp, sigmoid_entry, parameter_values={"contrast": contrast})
    plugins = [p for p in new_xmp.history if p.operation == "sigmoid"]
    assert plugins, "no sigmoid plugin in synthesized XMP history"
    fields = decode(plugins[-1].params)
    assert fields[_CONTRAST_FIELD_INDEX] == pytest.approx(contrast, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, sigmoid_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(baseline_xmp, sigmoid_entry, parameter_values={"contrast": 2.2})
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="sigmoid"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_CONTRAST_FIELD_INDEX] == pytest.approx(2.2, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_default(baseline_xmp, sigmoid_entry) -> None:
    """Without parameter_values, the dtstyle's default contrast=1.5 carries through."""
    new_xmp = apply_entry(baseline_xmp, sigmoid_entry)
    plugins = [p for p in new_xmp.history if p.operation == "sigmoid"]
    assert plugins
    fields = decode(plugins[-1].params)
    assert fields[_CONTRAST_FIELD_INDEX] == pytest.approx(1.5, abs=1e-5)
