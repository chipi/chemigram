"""Round-trip and patching tests for the colorbalancergb Path C decoder.

Mirrors test_exposure.py and test_vignette.py for the third parameterized
module. Validates the same byte-level guarantees: round-trip preserves
bytes, patch sets the named field, bytes outside the field are preserved.

The pre-v1.6 discrete entries (``sat_kill``, ``sat_boost_moderate``,
``sat_boost_strong``) are kept here as reference fixtures with known
saturation_global values (-1.0, +0.25, +0.5). Their ``.dtstyle`` files
were removed when this module shipped, but the byte patterns serve as
canonical pre-parameterization fixtures.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.colorbalancergb import (
    _CHROMA_GLOBAL_FIELD_INDEX,
    _CHROMA_GLOBAL_OFFSET,
    _HUE_ANGLE_FIELD_INDEX,
    _HUE_ANGLE_OFFSET,
    _SATURATION_GLOBAL_FIELD_INDEX,
    _SATURATION_GLOBAL_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    _VIBRANCE_FIELD_INDEX,
    _VIBRANCE_OFFSET,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params hex from the v1.5.x discrete sat_* entries (those
# entries were removed in v1.6.0 when the parameterized form shipped —
# RFC-021). Each is a 132-byte (264-hex-char) colorbalancergb mv5
# op_params blob; the only differing field across the three is
# saturation_global at offset 76.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    "sat_kill": (
        "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000803f000000000000803f00000000000000000000000000000000000080bf000000000000000000000000000000000000000000000000000000000000000091ed3c3e0000000091ed3c3e0000000001000000",
        -1.0,
    ),
    "sat_boost_moderate": (
        "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000803f000000000000803f000000000000000000000000000000000000803e000000000000000000000000000000000000000000000000000000000000000091ed3c3e0000000091ed3c3e0000000001000000",
        0.25,
    ),
    "sat_boost_strong": (
        "0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000803f000000000000803f000000000000000000000000000000000000003f000000000000000000000000000000000000000000000000000000000000000091ed3c3e0000000091ed3c3e0000000001000000",
        0.5,
    ),
}

# Shipped parameterized colorbalancergb dtstyle (default saturation_global=0.0).
_SHIPPED_DTSTYLE = (
    _REPO_ROOT
    / "vocabulary/packs/expressive-baseline/layers/L3/colorbalancergb/saturation_global.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    """Extract the <op_params> hex from a .dtstyle file."""
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_five() -> None:
    assert SUPPORTED_MODVERSION == 5


@pytest.mark.parametrize(
    "label,op_params",
    [(label, hex_) for label, (hex_, _v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_round_trip_on_reference_op_params(label: str, op_params: str) -> None:
    """Every pre-v1.6 reference op_params blob round-trips byte-for-byte
    through decode → encode."""
    assert encode(decode(op_params)) == op_params


def test_round_trip_on_shipped_v1_6_dtstyle() -> None:
    """The live v1.6.0+ parameterized ``saturation_global.dtstyle``
    round-trips byte-for-byte."""
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


@pytest.mark.parametrize(
    "label,expected_sat",
    [(label, v) for label, (_hex, v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_decode_extracts_known_saturation(label: str, expected_sat: float) -> None:
    """Each reference blob's saturation_global field decodes to the value
    its label claims."""
    op_params = _REFERENCE_OP_PARAMS_BY_LABEL[label][0]
    fields = decode(op_params)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(expected_sat, abs=1e-5)


def test_decode_extracts_default_saturation_from_shipped_dtstyle() -> None:
    """The shipped ``saturation_global.dtstyle`` ships with
    saturation_global=0.0 (the parameter default)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


@pytest.mark.parametrize("sat", [-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0])
def test_patch_sets_saturation_value(sat: float) -> None:
    """``patch(blob, saturation_global=v)`` produces a blob whose
    saturation_global field equals v."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_boost_strong"][0]
    out = patch(src, saturation_global=sat)
    fields = decode(out)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(sat, abs=1e-5)


def test_patch_preserves_bytes_outside_saturation_field() -> None:
    """Bytes 0..75 and 80..131 are byte-identical before and after patching."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, saturation_global=0.7))
    assert src_bytes[:_SATURATION_GLOBAL_OFFSET] == patched_bytes[:_SATURATION_GLOBAL_OFFSET]
    assert (
        src_bytes[_SATURATION_GLOBAL_OFFSET + 4 :] == patched_bytes[_SATURATION_GLOBAL_OFFSET + 4 :]
    )


def test_patch_preserves_other_fields() -> None:
    """All decoded fields except saturation_global equal the source's."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_boost_moderate"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, saturation_global=0.3))
    for i in range(len(src_fields)):
        if i == _SATURATION_GLOBAL_FIELD_INDEX:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_patch_preserves_saturation_formula_enum() -> None:
    """The trailing ``saturation_formula`` enum (uint32 at offset 128) must
    survive a patch — colorbalancergb's apply behavior depends on it."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    src_enum = decode(src)[-1]
    patched_enum = decode(patch(src, saturation_global=0.0))[-1]
    assert src_enum == patched_enum == 1


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 132 bytes"):
        decode("00" * 16)


def test_decode_rejects_wrong_size_blob() -> None:
    """A blob of the wrong size raises with a modversion-hint message."""
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)  # exposure-sized; not colorbalancergb


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE


# ---------------------------------------------------------------------------
# Additional axes (RFC-022 Tier 2): vibrance, chroma_global, hue_angle.
# Each axis is independently patchable; partial-update semantics.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("vibrance_value", [-1.0, -0.3, 0.0, 0.3, 1.0])
def test_patch_sets_vibrance_only(vibrance_value: float) -> None:
    """Patching vibrance leaves the other 3 axes at the source values."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    src_fields = decode(src)
    out = patch(src, vibrance=vibrance_value)
    fields = decode(out)
    assert fields[_VIBRANCE_FIELD_INDEX] == pytest.approx(vibrance_value, abs=1e-5)
    # Other parameterized axes preserved
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == src_fields[_SATURATION_GLOBAL_FIELD_INDEX]
    assert fields[_CHROMA_GLOBAL_FIELD_INDEX] == src_fields[_CHROMA_GLOBAL_FIELD_INDEX]
    assert fields[_HUE_ANGLE_FIELD_INDEX] == src_fields[_HUE_ANGLE_FIELD_INDEX]


@pytest.mark.parametrize("chroma_value", [-1.0, -0.3, 0.0, 0.5, 1.0])
def test_patch_sets_chroma_global_only(chroma_value: float) -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    src_fields = decode(src)
    out = patch(src, chroma_global=chroma_value)
    fields = decode(out)
    assert fields[_CHROMA_GLOBAL_FIELD_INDEX] == pytest.approx(chroma_value, abs=1e-5)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == src_fields[_SATURATION_GLOBAL_FIELD_INDEX]
    assert fields[_VIBRANCE_FIELD_INDEX] == src_fields[_VIBRANCE_FIELD_INDEX]
    assert fields[_HUE_ANGLE_FIELD_INDEX] == src_fields[_HUE_ANGLE_FIELD_INDEX]


@pytest.mark.parametrize("hue_value", [-180.0, -30.0, 0.0, 30.0, 180.0])
def test_patch_sets_hue_angle_only(hue_value: float) -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    src_fields = decode(src)
    out = patch(src, hue_angle=hue_value)
    fields = decode(out)
    assert fields[_HUE_ANGLE_FIELD_INDEX] == pytest.approx(hue_value, abs=1e-5)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == src_fields[_SATURATION_GLOBAL_FIELD_INDEX]
    assert fields[_CHROMA_GLOBAL_FIELD_INDEX] == src_fields[_CHROMA_GLOBAL_FIELD_INDEX]
    assert fields[_VIBRANCE_FIELD_INDEX] == src_fields[_VIBRANCE_FIELD_INDEX]


def test_patch_sets_all_four_axes_simultaneously() -> None:
    """Multi-axis patch: all 4 parameterized axes update in a single call."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    out = patch(
        src,
        saturation_global=0.4,
        chroma_global=0.2,
        hue_angle=15.0,
        vibrance=0.3,
    )
    fields = decode(out)
    assert fields[_SATURATION_GLOBAL_FIELD_INDEX] == pytest.approx(0.4, abs=1e-5)
    assert fields[_CHROMA_GLOBAL_FIELD_INDEX] == pytest.approx(0.2, abs=1e-5)
    assert fields[_HUE_ANGLE_FIELD_INDEX] == pytest.approx(15.0, abs=1e-5)
    assert fields[_VIBRANCE_FIELD_INDEX] == pytest.approx(0.3, abs=1e-5)


def test_patch_with_no_args_is_identity() -> None:
    """All-None kwargs produces byte-identical output."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    assert patch(src) == src


def test_field_offsets_match_struct_layout() -> None:
    """Sanity: declared offsets are 4*field_index for the four axes."""
    assert _SATURATION_GLOBAL_OFFSET == _SATURATION_GLOBAL_FIELD_INDEX * 4
    assert _CHROMA_GLOBAL_OFFSET == _CHROMA_GLOBAL_FIELD_INDEX * 4
    assert _HUE_ANGLE_OFFSET == _HUE_ANGLE_FIELD_INDEX * 4
    assert _VIBRANCE_OFFSET == _VIBRANCE_FIELD_INDEX * 4


def test_patch_preserves_saturation_formula_enum_across_all_axes() -> None:
    """saturation_formula enum (offset 128) survives any combination of patches."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["sat_kill"][0]
    src_enum = decode(src)[-1]
    patched_enum = decode(
        patch(src, saturation_global=0.5, vibrance=-0.2, hue_angle=45.0, chroma_global=0.1)
    )[-1]
    assert src_enum == patched_enum == 1
