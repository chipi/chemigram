"""Integration: parameterized lens correction apply path. Closes #95
(decoder shipped; EXIF auto-binding is a follow-up)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.lens import _AXIS_FIELD_INDICES, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def lens_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("lens_correction")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 10, "lens_correction: expected 10 magnitude axes"
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"lens_scale": 1.2},
        {"lens_tca_r": 1.005},
        {"lens_v_strength": 0.5},
        {"lens_cor_distortion": 0.8, "lens_cor_vignette": 0.5},
        {
            "lens_scale": 1.0,
            "lens_tca_r": 1.0,
            "lens_tca_b": 1.0,
            "lens_cor_distortion": 0.0,
        },  # passthrough defaults
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, lens_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, lens_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "lens"]
    assert plugins
    fields = decode(plugins[-1].params)
    for axis, expected in values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, lens_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        lens_entry,
        parameter_values={"lens_v_strength": 0.4, "lens_cor_distortion": 0.7},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(r'darktable:operation="lens"[^/]*?darktable:params="([0-9a-f]+)"', text)
    assert matches
    fields = decode(matches[-1])
    assert fields[_AXIS_FIELD_INDICES["lens_v_strength"]] == pytest.approx(0.4, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["lens_cor_distortion"]] == pytest.approx(0.7, abs=1e-5)


def test_apply_entry_partial_update_preserves_other_axes(baseline_xmp, lens_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, lens_entry, parameter_values={"lens_scale": 1.3})
    plugins = [p for p in new_xmp.history if p.operation == "lens"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["lens_scale"]] == pytest.approx(1.3, abs=1e-5)
    # tca_r, tca_b preserved at 1.0 (no-shift baseline)
    assert fields[_AXIS_FIELD_INDICES["lens_tca_r"]] == pytest.approx(1.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["lens_tca_b"]] == pytest.approx(1.0, abs=1e-5)
    # v_strength preserved at 0.0 (off)
    assert fields[_AXIS_FIELD_INDICES["lens_v_strength"]] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_defaults(baseline_xmp, lens_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, lens_entry)
    plugins = [p for p in new_xmp.history if p.operation == "lens"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["lens_scale"]] == pytest.approx(0.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["lens_tca_r"]] == pytest.approx(1.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["lens_v_radius"]] == pytest.approx(1.0, abs=1e-5)


def test_apply_entry_preserves_method_and_lens_identifiers(baseline_xmp, lens_entry) -> None:
    """method (LENSFUN=1), modify_flags (ALL=7), and the camera/lens
    char[128] strings must survive the apply path. With identifier
    strings empty, darktable's lensfun-method correction won't fire —
    EXIF auto-binding is a follow-up; the apply path correctness is
    independent of whether the lensfun lookup succeeds."""
    new_xmp = apply_entry(baseline_xmp, lens_entry, parameter_values={"lens_v_strength": 0.4})
    plugins = [p for p in new_xmp.history if p.operation == "lens"]
    fields = decode(plugins[-1].params)
    assert fields[0] == 1  # method = LENSFUN
    assert fields[1] == 7  # modify_flags = ALL
    assert fields[9] == b"\x00" * 128  # camera (empty)
    assert fields[10] == b"\x00" * 128  # lens (empty)
