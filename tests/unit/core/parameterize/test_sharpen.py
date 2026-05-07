"""Round-trip and patching tests for the sharpen Path C decoder.

Single-axis brand-new module (RFC-022 Tier 2). No v1.5.x predecessor —
sharpening was a thin gap in the survey's § 1 (no entries shipped).
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.sharpen import (
    _AMOUNT_FIELD_INDEX,
    _AMOUNT_OFFSET,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

_SHIPPED_DTSTYLE = (
    _REPO_ROOT / "vocabulary/packs/expressive-baseline/layers/L3/sharpen/sharpen.dtstyle"
)


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_one() -> None:
    assert SUPPORTED_MODVERSION == 1


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_dtstyle_default_values() -> None:
    """radius=2.0 (darktable default), amount=0.0 (no-op), threshold=0.5."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[0] == pytest.approx(2.0, abs=1e-5)  # radius
    assert fields[_AMOUNT_FIELD_INDEX] == pytest.approx(0.0, abs=1e-5)  # amount
    assert fields[2] == pytest.approx(0.5, abs=1e-5)  # threshold


@pytest.mark.parametrize("amount", [0.0, 0.25, 0.5, 1.0, 1.5, 2.0])
def test_patch_sets_amount_value(amount: float) -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    out = patch(src, amount=amount)
    fields = decode(out)
    assert fields[_AMOUNT_FIELD_INDEX] == pytest.approx(amount, abs=1e-5)


def test_patch_preserves_bytes_outside_amount_field() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_bytes = bytes.fromhex(src)
    patched_bytes = bytes.fromhex(patch(src, amount=1.2))
    assert src_bytes[:_AMOUNT_OFFSET] == patched_bytes[:_AMOUNT_OFFSET]
    assert src_bytes[_AMOUNT_OFFSET + 4 :] == patched_bytes[_AMOUNT_OFFSET + 4 :]


def test_patch_preserves_radius_and_threshold() -> None:
    """radius (offset 0) and threshold (offset 8) must survive any patch."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    patched_fields = decode(patch(src, amount=1.5))
    assert patched_fields[0] == src_fields[0]  # radius
    assert patched_fields[2] == src_fields[2]  # threshold


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 12 bytes"):
        decode("00" * 4)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
