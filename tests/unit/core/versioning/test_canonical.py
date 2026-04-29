"""Unit tests for chemigram.core.versioning.canonical.

Covers the 10 cases listed in GH issue #6's implementation plan.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.versioning import canonical_bytes, xmp_hash
from chemigram.core.xmp import HistoryEntry, Xmp, parse_xmp, write_xmp

FIXTURES = Path(__file__).resolve().parents[4] / "tests" / "fixtures" / "xmps"


def _minimal_xmp() -> Xmp:
    return Xmp(
        rating=0,
        label="",
        auto_presets_applied=False,
        history_end=0,
        iop_order_version=4,
        history=(),
    )


def _exposure_history_entry(params: str = "00000040") -> HistoryEntry:
    return HistoryEntry(
        num=8,
        operation="exposure",
        enabled=True,
        modversion=7,
        params=params,
        multi_name="",
        multi_name_hand_edited=False,
        multi_priority=0,
        blendop_version=14,
        blendop_params="gz_test",
    )


def test_xmp_hash_returns_64_hex_chars() -> None:
    h = xmp_hash(_minimal_xmp())
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


def test_canonical_bytes_starts_with_xml_decl_lf_only() -> None:
    raw = canonical_bytes(_minimal_xmp())
    assert raw.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    assert b"\r" not in raw
    assert raw.endswith(b"\n")


def test_canonical_bytes_utf8_no_bom() -> None:
    raw = canonical_bytes(_minimal_xmp())
    raw.decode("utf-8")  # no UnicodeDecodeError
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_canonical_bytes_stable_within_process() -> None:
    xmp = _minimal_xmp()
    expected = canonical_bytes(xmp)
    for _ in range(100):
        assert canonical_bytes(xmp) == expected


def test_canonical_bytes_equal_for_equal_xmps() -> None:
    """Two Xmps with equal field values produce equal bytes."""
    a = _minimal_xmp()
    b = _minimal_xmp()
    assert a == b
    assert a is not b
    assert canonical_bytes(a) == canonical_bytes(b)


@pytest.mark.parametrize(
    "field,value",
    [
        ("rating", 5),
        ("label", "finalist"),
        ("auto_presets_applied", True),
        ("history_end", 1),
        ("iop_order_version", 5),
    ],
)
def test_xmp_hash_changes_when_top_level_field_changes(field: str, value: object) -> None:
    base = _minimal_xmp()
    mutated = dataclasses.replace(base, **{field: value})
    assert xmp_hash(base) != xmp_hash(mutated)


def test_xmp_hash_changes_when_history_entry_changes() -> None:
    base = dataclasses.replace(_minimal_xmp(), history=(_exposure_history_entry(),), history_end=1)
    mutated_history = (_exposure_history_entry(params="0000003f"),)
    mutated = dataclasses.replace(base, history=mutated_history)
    assert xmp_hash(base) != xmp_hash(mutated)


def test_xmp_hash_changes_when_raw_extra_field_changes() -> None:
    base = _minimal_xmp()
    with_extra = dataclasses.replace(base, raw_extra_fields=(("attr", "darktable:fake_test", "1"),))
    assert xmp_hash(base) != xmp_hash(with_extra)


def test_canonical_bytes_round_trip(tmp_path: Path) -> None:
    """canonical_bytes survives parse → write → re-parse."""
    original = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")

    out = tmp_path / "round.xmp"
    out.write_bytes(canonical_bytes(original))

    reparsed = parse_xmp(out)
    assert canonical_bytes(reparsed) == canonical_bytes(original)
    assert xmp_hash(reparsed) == xmp_hash(original)


def test_canonical_bytes_v3_reference_snapshot() -> None:
    """v3 reference XMP has a stable, known hash. Drift fails here loudly."""
    xmp = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    h = xmp_hash(xmp)
    # Snapshot value captured on first stable run; future regressions in
    # canonical_bytes' determinism rules will change this and fail the test.
    assert h == "7f8f514f0de121d51a3e04e3c9b39dec67f38c3db41c92d746eac971f58d74fe", (
        f"v3 reference hash drift: got {h}"
    )


def test_canonical_bytes_minimal_fixture_snapshot() -> None:
    xmp = parse_xmp(FIXTURES / "minimal.xmp")
    h = xmp_hash(xmp)
    assert h == "ee535a24a0e21d7d967d4c206f2d5050c7cebb7c480670917c97e114f3c503c4", (
        f"minimal fixture hash drift: got {h}"
    )


def test_canonical_bytes_with_unknown_field_round_trip(tmp_path: Path) -> None:
    """raw_extra_fields (attrs + nested elements) round-trip via canonical."""
    original = parse_xmp(FIXTURES / "with_unknown_field.xmp")
    assert original.raw_extra_fields, "fixture should have extras"

    out = tmp_path / "round.xmp"
    out.write_bytes(canonical_bytes(original))

    reparsed = parse_xmp(out)
    assert canonical_bytes(reparsed) == canonical_bytes(original)


def test_write_xmp_then_canonical_matches(tmp_path: Path) -> None:
    """write_xmp + parse_xmp + canonical_bytes equals canonical_bytes directly.

    Sanity check that the v0.1.0 write_xmp pathway interoperates cleanly
    with the new canonical hashing.
    """
    original = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    written = tmp_path / "written.xmp"
    write_xmp(original, written)
    reparsed = parse_xmp(written)
    assert canonical_bytes(reparsed) == canonical_bytes(original)
