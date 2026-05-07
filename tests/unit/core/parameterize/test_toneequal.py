"""Round-trip and patching tests for the toneequalizer Path C decoder.

The most complex parameterized entry (RFC-022 Tier 2): 9 photographic
axes (one per luminance band), all independently patchable with
partial-update semantics. Stress-tests the multi-parameter apply path
beyond temperature's 2-axis case.
"""

from __future__ import annotations

import math
import re
import struct
from pathlib import Path

import pytest

from chemigram.core.parameterize.toneequalizer import (
    _NODE_FIELDS,
    _STRUCT_FORMAT,
    _STRUCT_SIZE,
    SUPPORTED_MODVERSION,
    decode,
    encode,
    patch,
)

_REPO_ROOT = Path(__file__).resolve().parents[4]

_SHIPPED_DTSTYLE = (
    _REPO_ROOT
    / "vocabulary/packs/expressive-baseline/layers/L3/toneequalizer/toneequalizer.dtstyle"
)

_NODE_NAMES = list(_NODE_FIELDS.keys())  # in struct order


def _read_op_params(dtstyle_path: Path) -> str:
    text = dtstyle_path.read_text()
    m = re.search(r"<op_params>(.+?)</op_params>", text, re.DOTALL)
    assert m, f"no op_params in {dtstyle_path}"
    return m.group(1).strip()


def test_supported_modversion_is_two() -> None:
    assert SUPPORTED_MODVERSION == 2


def test_round_trip_on_shipped_dtstyle() -> None:
    op_params = _read_op_params(_SHIPPED_DTSTYLE)
    assert encode(decode(op_params)) == op_params


def test_decode_extracts_default_zero_nodes() -> None:
    """All 9 nodes default to 0.0 (no shift)."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    for name in _NODE_NAMES:
        idx, _offset = _NODE_FIELDS[name]
        assert fields[idx] == pytest.approx(0.0, abs=1e-5), f"node {name}"


def test_decode_algorithm_field_defaults() -> None:
    """Algorithm fields: blending=5.0, smoothing=√2, feathering=1.0, others=0.0."""
    fields = decode(_read_op_params(_SHIPPED_DTSTYLE))
    assert fields[9] == pytest.approx(5.0, abs=1e-5)  # blending
    assert fields[10] == pytest.approx(math.sqrt(2.0), abs=1e-5)  # smoothing
    assert fields[11] == pytest.approx(1.0, abs=1e-5)  # feathering
    assert fields[12] == pytest.approx(0.0, abs=1e-5)  # quantization
    assert fields[13] == pytest.approx(0.0, abs=1e-5)  # contrast_boost
    assert fields[14] == pytest.approx(0.0, abs=1e-5)  # exposure_boost


@pytest.mark.parametrize("node_name", _NODE_NAMES)
def test_patch_sets_single_node(node_name: str) -> None:
    """Patching one node leaves the other 8 at their source values."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    out = patch(src, **{node_name: 1.5})
    fields = decode(out)
    target_idx, _ = _NODE_FIELDS[node_name]
    assert fields[target_idx] == pytest.approx(1.5, abs=1e-5)
    # Other 8 nodes preserved
    for name in _NODE_NAMES:
        if name == node_name:
            continue
        idx, _ = _NODE_FIELDS[name]
        assert fields[idx] == src_fields[idx], f"node {name} should be preserved"


def test_patch_sets_all_nine_nodes_simultaneously() -> None:
    """All 9 nodes patched at once — full s-curve via the parameterized path."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    expected = {name: float((i - 4) * 0.25) for i, name in enumerate(_NODE_NAMES)}
    out = patch(src, **expected)
    fields = decode(out)
    for name, target in expected.items():
        idx, _ = _NODE_FIELDS[name]
        assert fields[idx] == pytest.approx(target, abs=1e-5), f"node {name}"


def test_patch_with_no_args_is_identity() -> None:
    src = _read_op_params(_SHIPPED_DTSTYLE)
    assert patch(src) == src


def test_patch_preserves_algorithm_and_enum_fields() -> None:
    """Algorithm floats (blending, smoothing, feathering, quantization,
    contrast_boost, exposure_boost), enums (details, method), and
    iterations must survive any node patch."""
    src = _read_op_params(_SHIPPED_DTSTYLE)
    src_fields = decode(src)
    patched_fields = decode(patch(src, shadows=1.0, highlights=-0.5, midtones=0.3))
    # Algorithm fields (indices 9..14)
    for i in range(9, 15):
        assert patched_fields[i] == src_fields[i], f"algorithm field {i} changed"
    # Enums + iterations (indices 15..17)
    for i in range(15, 18):
        assert patched_fields[i] == src_fields[i], f"enum/int field {i} changed"


def test_node_offsets_match_field_indices() -> None:
    """Sanity: each node's byte offset is 4 * field_index."""
    for name, (idx, offset) in _NODE_FIELDS.items():
        assert offset == idx * 4, f"node {name}: offset {offset} != {idx * 4}"


def test_decode_rejects_short_blob() -> None:
    with pytest.raises(ValueError, match="expected 72 bytes"):
        decode("00" * 16)


def test_decode_rejects_wrong_size_blob() -> None:
    with pytest.raises(ValueError, match="modversion"):
        decode("00" * 28)


def test_struct_format_matches_size() -> None:
    assert struct.calcsize(_STRUCT_FORMAT) == _STRUCT_SIZE
