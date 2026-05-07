"""Integration: parameterized denoiseprofile apply path. Closes #96."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from chemigram.core.helpers import apply_entry
from chemigram.core.parameterize.denoiseprofile import _AXIS_FIELD_INDICES, decode
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp, write_xmp

_FIXTURE_BASELINE = (
    Path(__file__).resolve().parents[2] / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
)


@pytest.fixture
def baseline_xmp():
    return parse_xmp(_FIXTURE_BASELINE)


@pytest.fixture
def denoise_entry():
    index = load_packs(["starter", "expressive-baseline"])
    entry = index.lookup_by_name("denoise")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 4, "denoise: expected 4 magnitude axes"
    return entry


@pytest.mark.parametrize(
    "values",
    [
        {"denoise_strength": 2.0},
        {"denoise_shadows": 1.5},
        {"denoise_radius": 3.0},
        {"denoise_scattering": 5.0},
        {"denoise_strength": 10.0, "denoise_shadows": 1.4},
        {
            "denoise_strength": 1.0,
            "denoise_shadows": 1.0,
            "denoise_radius": 1.0,
            "denoise_scattering": 0.0,
        },  # darktable defaults
    ],
)
def test_apply_entry_with_multi_param_patches_op_params(
    baseline_xmp, denoise_entry, values: dict
) -> None:
    new_xmp = apply_entry(baseline_xmp, denoise_entry, parameter_values=values)
    plugins = [p for p in new_xmp.history if p.operation == "denoiseprofile"]
    assert plugins
    fields = decode(plugins[-1].params)
    for axis, expected in values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_apply_entry_round_trips_through_xmp_writer(
    baseline_xmp, denoise_entry, tmp_path: Path
) -> None:
    new_xmp = apply_entry(
        baseline_xmp,
        denoise_entry,
        parameter_values={"denoise_strength": 4.0, "denoise_shadows": 1.6},
    )
    out_path = tmp_path / "patched.xmp"
    write_xmp(new_xmp, out_path)
    text = out_path.read_text()
    matches = re.findall(
        r'darktable:operation="denoiseprofile"[^/]*?darktable:params="([0-9a-f]+)"', text
    )
    assert matches
    fields = decode(matches[-1])
    assert fields[_AXIS_FIELD_INDICES["denoise_strength"]] == pytest.approx(4.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["denoise_shadows"]] == pytest.approx(1.6, abs=1e-5)


def test_apply_entry_partial_update_preserves_other_axes(baseline_xmp, denoise_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, denoise_entry, parameter_values={"denoise_strength": 5.0})
    plugins = [p for p in new_xmp.history if p.operation == "denoiseprofile"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["denoise_strength"]] == pytest.approx(5.0, abs=1e-5)
    # Others preserved at darktable defaults
    assert fields[_AXIS_FIELD_INDICES["denoise_shadows"]] == pytest.approx(1.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["denoise_radius"]] == pytest.approx(1.0, abs=1e-5)
    assert fields[_AXIS_FIELD_INDICES["denoise_scattering"]] == pytest.approx(0.0, abs=1e-5)


def test_apply_entry_no_values_uses_dtstyle_defaults(baseline_xmp, denoise_entry) -> None:
    new_xmp = apply_entry(baseline_xmp, denoise_entry)
    plugins = [p for p in new_xmp.history if p.operation == "denoiseprofile"]
    fields = decode(plugins[-1].params)
    assert fields[_AXIS_FIELD_INDICES["denoise_strength"]] == pytest.approx(1.0, abs=1e-5)


def test_apply_entry_preserves_mode_and_calibration(baseline_xmp, denoise_entry) -> None:
    """mode (WAVELETS=1), wavelet_color_mode (Y0U0V0=1), and the 3 mode
    flags must survive the apply path. Calibration arrays a[3]/b[3] also
    preserved (would be auto-populated by darktable if camera/ISO known)."""
    new_xmp = apply_entry(baseline_xmp, denoise_entry, parameter_values={"denoise_strength": 3.0})
    plugins = [p for p in new_xmp.history if p.operation == "denoiseprofile"]
    fields = decode(plugins[-1].params)
    assert fields[14] == 1  # mode = WAVELETS
    assert fields[102] == 1  # wavelet_color_mode = Y0U0V0
    # Calibration arrays preserved
    for i in range(8, 14):
        assert fields[i] == pytest.approx(0.0, abs=1e-5)
