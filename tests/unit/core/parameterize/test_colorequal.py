"""Round-trip and patching tests for the colorequal Path C decoder.

Closes RFC-023 (Tier 2 part) — Lightroom HSL Color Mixer parity. The
colorequal mv4 struct is 128 bytes flat (31 floats + 1 uint32 use_filter
gboolean). We expose 24 per-color HSL axes (8 sat + 8 hue + 8 brightness)
across 3 multi-axis vocabulary entries; the 7 globals + use_filter +
hue_shift are preserved verbatim.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.colorequal import (
    _AXIS_FIELD_INDICES,
    _AXIS_OFFSETS,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HSL_SAT_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/colorequal/hsl_saturation.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_four() -> None:
    assert SUPPORTED_MODVERSION == 4


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
    assert _STRUCT_SIZE == 128


def test_axis_count_is_24() -> None:
    """3 channels (H/S/L) x 8 colors = 24 per-color axes."""
    assert len(_AXIS_FIELD_INDICES) == 24


def test_axis_offsets_match_field_indices() -> None:
    """Sanity: each axis byte offset is 4 * field_index."""
    for name, idx in _AXIS_FIELD_INDICES.items():
        assert _AXIS_OFFSETS[name] == idx * 4, (
            f"{name}: offset {_AXIS_OFFSETS[name]} != 4 * field_index {idx}"
        )


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_HSL_SAT_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_globals_from_shipped_dtstyle() -> None:
    """Shipped HSL dtstyle uses darktable defaults for the 7 globals.

    threshold=0.1, smoothing_hue=1.0, contrast=0.0, white_level=1.0,
    chroma_size=1.5, param_size=1.0, use_filter=TRUE."""
    fields = decode(_read_op_params(_HSL_SAT_DTSTYLE))
    assert fields[0] == pytest.approx(0.1, abs=1e-5)  # threshold
    assert fields[1] == pytest.approx(1.0, abs=1e-5)  # smoothing_hue
    assert fields[2] == pytest.approx(0.0, abs=1e-5)  # contrast
    assert fields[3] == pytest.approx(1.0, abs=1e-5)  # white_level
    assert fields[4] == pytest.approx(1.5, abs=1e-5)  # chroma_size
    assert fields[5] == pytest.approx(1.0, abs=1e-5)  # param_size
    assert fields[6] == 1  # use_filter TRUE
    assert fields[31] == pytest.approx(0.0, abs=1e-5)  # hue_shift


def test_decode_extracts_zero_hsl_axes_from_shipped_dtstyle() -> None:
    """All 24 per-color HSL axes default to 0.0 in the shipped baseline."""
    fields = decode(_read_op_params(_HSL_SAT_DTSTYLE))
    for axis_name, idx in _AXIS_FIELD_INDICES.items():
        assert fields[idx] == pytest.approx(0.0, abs=1e-5), (
            f"{axis_name} (field {idx}) should default to 0.0 in baseline"
        )


@pytest.mark.parametrize("axis", list(_AXIS_FIELD_INDICES.keys()))
def test_patch_sets_one_axis_only(axis: str) -> None:
    """Patching one HSL axis preserves the other 23 + all 8 non-parameterized fields."""
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    src_fields = decode(src)
    test_value = 30.0 if axis.startswith("hue_") else 0.4
    out = patch(src, **{axis: test_value})
    fields = decode(out)
    target_idx = _AXIS_FIELD_INDICES[axis]
    assert fields[target_idx] == pytest.approx(test_value, abs=1e-5)
    for i in range(len(src_fields)):
        if i == target_idx:
            continue
        assert fields[i] == src_fields[i], f"field {i} changed unexpectedly when patching {axis}"


def test_patch_full_saturation_row() -> None:
    """All 8 sat axes patched at once."""
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    sat_values = {
        "sat_red": 0.3,
        "sat_orange": -0.2,
        "sat_yellow": 0.1,
        "sat_green": 0.4,
        "sat_cyan": -0.3,
        "sat_blue": 0.5,
        "sat_lavender": 0.0,
        "sat_magenta": -0.4,
    }
    out = patch(src, **sat_values)
    fields = decode(out)
    for axis, expected in sat_values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_patch_full_hue_row() -> None:
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    hue_values = {
        "hue_red": 5.0,
        "hue_orange": -10.0,
        "hue_yellow": 15.0,
        "hue_green": 20.0,
        "hue_cyan": -5.0,
        "hue_blue": 30.0,
        "hue_lavender": 0.0,
        "hue_magenta": -15.0,
    }
    out = patch(src, **hue_values)
    fields = decode(out)
    for axis, expected in hue_values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_patch_full_luminance_row() -> None:
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    bright_values = {
        "bright_red": 0.1,
        "bright_orange": 0.2,
        "bright_yellow": 0.0,
        "bright_green": -0.3,
        "bright_cyan": 0.4,
        "bright_blue": -0.5,
        "bright_lavender": 0.0,
        "bright_magenta": 0.1,
    }
    out = patch(src, **bright_values)
    fields = decode(out)
    for axis, expected in bright_values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_patch_all_24_axes_simultaneously() -> None:
    """Stress test: patch every axis at once."""
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    all_values = {axis: 0.1 + (idx * 0.01) for axis, idx in _AXIS_FIELD_INDICES.items()}
    out = patch(src, **all_values)
    fields = decode(out)
    for axis, expected in all_values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_globals() -> None:
    """The 7 global fields + hue_shift must survive every patch."""
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    src_fields = decode(src)
    out = patch(src, sat_red=0.5, hue_blue=20.0, bright_green=-0.3)
    fields = decode(out)
    # Field indices 0..6 are globals; 31 is hue_shift
    for global_idx in [0, 1, 2, 3, 4, 5, 6, 31]:
        assert fields[global_idx] == src_fields[global_idx], (
            f"global field {global_idx} should be preserved"
        )


def test_patch_unknown_kwarg_raises() -> None:
    """Typo'd or non-axis kwargs raise TypeError early."""
    src = _read_op_params(_HSL_SAT_DTSTYLE)
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        patch(src, sat_carmine=0.5)  # not a valid color zone
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        patch(src, sat_red=0.5, contrast=0.3)  # contrast is a global, not a parameterized axis


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 128 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 100)
