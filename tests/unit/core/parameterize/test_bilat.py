"""Round-trip and patching tests for the bilat (clarity) Path C decoder.

Mirrors test_exposure.py for the fifth parameterized module (Phase 4 /
RFC-021). Only the strength axis (``detail`` field) is parameterized;
``clarity_painterly`` stays as a discrete entry per the survey § 10
("different kind, not strength").
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.bilat import (
    _DETAIL_FIELD_INDEX,
    _DETAIL_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params from the v1.5.x clarity_strong (removed in v1.6.0)
# and clarity_painterly (still shipped as a discrete entry — different
# kind, not strength). Each is a 20-byte (40-hex-char) bilat mv3 blob.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    "clarity_strong": ("010000003333333f3333333f0000c03f0000003f", 1.5),
    "clarity_painterly": ("01000000cdcccc3ecdcccc3ecdcccc3e3333333f", 0.4),
}

_SHIPPED_DTSTYLE = (
    _REPO_ROOT
    / "vocabulary/packs/expressive-baseline/layers/L3/localcontrast/bilat_clarity_strength.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_three() -> None:
    assert SUPPORTED_MODVERSION == 3


@pytest.mark.parametrize(
    "label,op_params",
    [(label, hex_) for label, (hex_, _v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_round_trip_on_reference_op_params(label: str, op_params: str) -> None:
    assert encode(decode(op_params)) == op_params


def test_round_trip_on_shipped_v1_6_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


@pytest.mark.parametrize(
    "label,expected",
    [(label, v) for label, (_hex, v) in _REFERENCE_OP_PARAMS_BY_LABEL.items()],
)
def test_decode_extracts_known_strength(label: str, expected: float) -> None:
    op_params = _REFERENCE_OP_PARAMS_BY_LABEL[label][0]
    fields = decode(op_params)
    assert fields[_DETAIL_FIELD_INDEX] == pytest.approx(expected, abs=1e-5)


def test_decode_extracts_default_strength_from_shipped_dtstyle() -> None:
    """Default strength=0.0 (no clarity applied without --value)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_DETAIL_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


@pytest.mark.parametrize("strength", [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.5, 4.0])
def test_patch_sets_strength_value(strength: float) -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["clarity_strong"][0]
    out = patch(src, clarity_strength=strength)
    fields = decode(out)
    assert fields[_DETAIL_FIELD_INDEX] == pytest.approx(strength, abs=1e-5)


def test_patch_preserves_bytes_outside_detail_field() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["clarity_strong"][0]
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, clarity_strength=2.0))
    assert src_bytes[:_DETAIL_OFFSET] == patched_bytes[:_DETAIL_OFFSET]
    assert src_bytes[_DETAIL_OFFSET + 4 :] == patched_bytes[_DETAIL_OFFSET + 4 :]


def test_patch_preserves_other_fields() -> None:
    """All decoded fields except ``detail`` equal the source's."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["clarity_strong"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, clarity_strength=2.0))
    for i in range(len(src_fields)):
        if i == _DETAIL_FIELD_INDEX:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_patch_preserves_mode_enum() -> None:
    """The ``mode`` enum (uint32 at offset 0) must survive a patch —
    bilat's apply behavior depends on it (laplacian vs bilateral)."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["clarity_strong"][0]
    src_mode = decode(src)[0]
    patched_mode = decode(patch(src, clarity_strength=0.0))[0]
    assert src_mode == patched_mode == 1


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 20 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
