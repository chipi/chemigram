"""Round-trip and patching tests for the highlights Path C decoder."""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.highlights import (
    _CLIP_FIELD_INDEX,
    _CLIP_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

# Reference op_params from the v1.5.x discrete entries (removed in v1.6.0+).
# Each is a 48-byte (96-hex-char) highlights mv4 blob.
_REFERENCE_OP_PARAMS_BY_LABEL = {
    "highlights_recovery_subtle": (
        "050000000000803f000000009a99993e3333733f000000001e00000006000000cdcccc3e000000400500000000000000",
        0.95,
    ),
    "highlights_recovery_strong": (
        "050000000000803f000000003333333f9a99593f000000001e00000006000000cdcccc3e000080400500000000000000",
        0.85,
    ),
}

_SHIPPED_DTSTYLE = (
    _REPO_ROOT
    / "vocabulary/packs/expressive-baseline/layers/L3/highlights/highlights_clip_threshold.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_four() -> None:
    assert SUPPORTED_MODVERSION == 4


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
def test_decode_extracts_known_clip(label: str, expected: float) -> None:
    op_params = _REFERENCE_OP_PARAMS_BY_LABEL[label][0]
    fields = decode(op_params)
    assert fields[_CLIP_FIELD_INDEX] == pytest.approx(expected, abs=1e-3)


def test_decode_extracts_default_clip_from_shipped_dtstyle() -> None:
    """Default clip_threshold=1.0 (darktable default = no recovery below 1.0)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[_CLIP_FIELD_INDEX] == pytest.approx(1.0, abs=1e-5)


@pytest.mark.parametrize("clip", [0.0, 0.5, 0.85, 0.95, 1.0, 1.5, 2.0])
def test_patch_sets_clip_value(clip: float) -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["highlights_recovery_subtle"][0]
    out = patch(src, clip_threshold=clip)
    fields = decode(out)
    assert fields[_CLIP_FIELD_INDEX] == pytest.approx(clip, abs=1e-5)


def test_patch_preserves_bytes_outside_clip_field() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["highlights_recovery_subtle"][0]
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, clip_threshold=0.7))
    assert src_bytes[:_CLIP_OFFSET] == patched_bytes[:_CLIP_OFFSET]
    assert src_bytes[_CLIP_OFFSET + 4 :] == patched_bytes[_CLIP_OFFSET + 4 :]


def test_patch_preserves_other_fields() -> None:
    src = _REFERENCE_OP_PARAMS_BY_LABEL["highlights_recovery_strong"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, clip_threshold=0.6))
    for i in range(len(src_fields)):
        if i == _CLIP_FIELD_INDEX:
            continue
        assert patched_fields[i] == src_fields[i], (
            f"field {i} changed: {src_fields[i]} -> {patched_fields[i]}"
        )


def test_patch_preserves_mode_and_recovery_enums() -> None:
    """The mode + recovery enums (uint32 at offsets 0 and 40) must survive."""
    src = _REFERENCE_OP_PARAMS_BY_LABEL["highlights_recovery_strong"][0]
    src_fields = decode(src)
    patched_fields = decode(patch(src, clip_threshold=0.7))
    assert src_fields[0] == patched_fields[0]  # mode
    assert src_fields[10] == patched_fields[10]  # recovery


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 48 bytes"):
        decode("00" * 16)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
