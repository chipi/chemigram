"""Round-trip and patching tests for the grain Path C decoder.

Mirrors test_exposure.py for the sixth parameterized module (Phase 4 /
RFC-021). Replaces the v1.5.x discrete grain_fine / grain_medium /
grain_heavy entries.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.grain import (
    _STRENGTH_FIELD_INDEX,
    _STRENGTH_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params from the v1.5.x grain_fine / grain_medium / grain_heavy
# entries (removed in v1.6.0+). Each is a 16-byte (32-hex-char) grain mv2 blob.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    "grain_fine": ("02000000c520f040000000410000c842", 8.0),
    "grain_medium": ("02000000c520f0400000c8410000c842", 25.0),
    "grain_heavy": ("02000000f6283441000048420000c842", 50.0),
}

_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/grain/grain_strength.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_two() -> None:
    assert SUPPORTED_MODVERSION == 2


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
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(expected, abs=1e-3)


def test_decode_extracts_default_strength_from_shipped_dtstyle() -> None:
    """Default grain_strength=0.0 (no grain without --value)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)


@pytest.mark.parametrize("strength", [0.0, 8.0, 25.0, 50.0, 100.0])
def test_patch_sets_strength_value(strength: float) -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["grain_medium"][0]
    out = patch(src, grain_strength=strength)
    fields = decode(out)
    assert fields[_STRENGTH_FIELD_INDEX] == pytest.approx(strength, abs=1e-5)


def test_patch_preserves_bytes_outside_strength_field() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["grain_medium"][0]
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, grain_strength=42.0))
    assert src_bytes[:_STRENGTH_OFFSET] == patched_bytes[:_STRENGTH_OFFSET]
    assert src_bytes[_STRENGTH_OFFSET + 4 :] == patched_bytes[_STRENGTH_OFFSET + 4 :]


def test_patch_preserves_other_fields() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["grain_fine"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, grain_strength=42.0))
    for i in range(len(src_fields)):
        if i == _STRENGTH_FIELD_INDEX:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_patch_preserves_channel_enum() -> None:
    """The ``channel`` enum (uint32 at offset 0) must survive a patch."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["grain_fine"][0]
    src_channel = decode(src)[0]
    patched_channel = decode(patch(src, grain_strength=10.0))[0]
    assert src_channel == patched_channel == 2  # DT_GRAIN_CHANNEL_LIGHTNESS


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 16 bytes"):
        decode("00" * 8)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
