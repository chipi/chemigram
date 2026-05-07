"""Round-trip and patching tests for the ashift Path C decoder.

Closes #101 — Lightroom Transform panel parity. ashift mv5 is an 892-byte
struct (the largest in the parameterize registry), with 800 bytes of that
being user-drawn-lines storage that's preserved verbatim. 5 magnitude
axes parameterized; the other 218 fields preserved.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.ashift import (
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
_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/ashift/transform.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_five() -> None:
    assert SUPPORTED_MODVERSION == 5


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
    assert _STRUCT_SIZE == 892


def test_axis_count_is_5() -> None:
    assert len(_AXIS_FIELD_INDICES) == 5


def test_axes_use_transform_prefix() -> None:
    for name in _AXIS_FIELD_INDICES:
        assert name.startswith("transform_"), f"{name!r} should start with 'transform_'"


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_darktable_defaults() -> None:
    """Shipped transform.dtstyle uses darktable's documented v5 defaults."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[0] == pytest.approx(0.0)  # rotation
    assert fields[1] == pytest.approx(0.0)  # lensshift_v
    assert fields[2] == pytest.approx(0.0)  # lensshift_h
    assert fields[3] == pytest.approx(0.0)  # shear
    assert fields[4] == pytest.approx(35.0)  # f_length
    assert fields[5] == pytest.approx(1.0)  # crop_factor
    assert fields[6] == pytest.approx(100.0)  # orthocorr
    assert fields[7] == pytest.approx(1.0)  # aspect
    assert fields[8] == 0  # mode = GENERIC
    assert fields[9] == 1  # cropmode = LARGEST


@pytest.mark.parametrize("axis", list(_AXIS_FIELD_INDICES.keys()))
def test_patch_sets_one_axis_only(axis: str) -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    test_value = 1.2 if axis == "transform_aspect" else 0.3
    out = patch(src, **{axis: test_value})
    fields = decode(out)
    target_idx = _AXIS_FIELD_INDICES[axis]
    assert fields[target_idx] == pytest.approx(test_value, abs=1e-5)
    for i in range(len(src_fields)):
        if i == target_idx:
            continue
        assert fields[i] == src_fields[i], f"field {i} changed unexpectedly"


def test_patch_all_5_axes_simultaneously() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    values = {
        "transform_rotation": 5.0,
        "transform_lensshift_v": 0.2,
        "transform_lensshift_h": -0.1,
        "transform_shear": 0.05,
        "transform_aspect": 1.1,
    }
    out = patch(src, **values)
    fields = decode(out)
    for axis, expected in values.items():
        assert fields[_AXIS_FIELD_INDICES[axis]] == pytest.approx(expected, abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_lens_tuning_and_modes() -> None:
    """f_length, crop_factor, orthocorr, mode, cropmode preserved across patches."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    out = patch(src, transform_rotation=10.0, transform_aspect=1.5)
    fields = decode(out)
    assert fields[4] == src_fields[4]  # f_length
    assert fields[5] == src_fields[5]  # crop_factor
    assert fields[6] == src_fields[6]  # orthocorr
    assert fields[8] == src_fields[8]  # mode
    assert fields[9] == src_fields[9]  # cropmode


def test_patch_preserves_user_drawn_lines_storage() -> None:
    """The 200-float last_drawn_lines array (indices 14..213), the count
    (214), and the 8-float last_quad_lines (215..222) preserved verbatim."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    out = patch(src, transform_rotation=15.0, transform_lensshift_v=0.3)
    fields = decode(out)
    for i in range(14, 223):
        assert fields[i] == src_fields[i], f"line-storage field {i} changed"


def test_patch_unknown_kwarg_raises() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        patch(src, rotation=10.0)  # missing transform_ prefix
    with pytest.raises(TypeError, match="unexpected keyword argument"):
        patch(src, transform_rotation=10.0, f_length=50.0)  # f_length not parameterized


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 892 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 100)


def test_axis_offsets_match_field_indices() -> None:
    for name, idx in _AXIS_FIELD_INDICES.items():
        assert _AXIS_OFFSETS[name] == idx * 4
