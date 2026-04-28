"""Unit tests for chemigram.core.xmp parse + write.

Covers the 13 cases listed in GH issue #2's implementation plan.
Real fixtures live at tests/fixtures/xmps/.
"""

from pathlib import Path

import pytest

from chemigram.core.xmp import (
    HistoryEntry,
    Xmp,
    XmpParseError,
    parse_xmp,
    write_xmp,
)

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "xmps"


def test_parse_minimal_xmp() -> None:
    xmp = parse_xmp(FIXTURES / "minimal.xmp")
    assert isinstance(xmp, Xmp)
    assert xmp.history == ()
    assert xmp.history_end == 0
    assert xmp.iop_order_version == 4
    assert xmp.rating == 0
    assert xmp.auto_presets_applied is False


def test_parse_single_history_entry() -> None:
    xmp = parse_xmp(FIXTURES / "single_history.xmp")
    assert len(xmp.history) == 1
    entry = xmp.history[0]
    assert isinstance(entry, HistoryEntry)
    assert entry.num == 0
    assert entry.operation == "exposure"
    assert entry.enabled is True
    assert entry.modversion == 7
    assert entry.multi_name == ""
    assert entry.multi_name_hand_edited is False
    assert entry.multi_priority == 0
    assert entry.blendop_version == 14
    assert entry.iop_order is None


def test_parse_v3_reference() -> None:
    xmp = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    assert xmp.history_end == 11
    assert len(xmp.history) == 11
    operations = [e.operation for e in xmp.history]
    assert operations[0] == "rawprepare"
    assert "exposure" in operations
    assert "channelmixerrgb" in operations
    assert "sigmoid" in operations
    user_exposure = next(e for e in xmp.history if e.operation == "exposure" and e.multi_name == "")
    assert user_exposure.num == 8
    assert user_exposure.multi_priority == 0
    assert "00000040" in user_exposure.params  # +2.0 EV (Phase 0 v3)
    builtin_sigmoid = next(
        e for e in xmp.history if e.operation == "sigmoid" and e.multi_name.startswith("_builtin_")
    )
    assert builtin_sigmoid.multi_name == "_builtin_scene-referred default"


def test_top_level_metadata() -> None:
    xmp = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    assert xmp.rating == 0
    assert xmp.auto_presets_applied is True
    assert xmp.history_end == 11
    assert xmp.iop_order_version == 4


def test_params_byte_identity() -> None:
    """ADR-008: opaque blobs preserved string-equal to source XML."""
    xmp = parse_xmp(FIXTURES / "single_history.xmp")
    entry = xmp.history[0]
    assert entry.params == ("00000000000080b90000003f00004842000080c00100000001000000")
    assert entry.blendop_params == (
        "gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh"
    )


def test_iop_order_optional_none() -> None:
    """darktable 5.4.1 doesn't write iop_order on history entries."""
    xmp = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    for entry in xmp.history:
        assert entry.iop_order is None


def test_round_trip_minimal(tmp_path: Path) -> None:
    original = parse_xmp(FIXTURES / "minimal.xmp")
    out = tmp_path / "out.xmp"
    write_xmp(original, out)
    reparsed = parse_xmp(out)
    assert reparsed == original


def test_round_trip_with_history(tmp_path: Path) -> None:
    original = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    out = tmp_path / "out.xmp"
    write_xmp(original, out)
    reparsed = parse_xmp(out)
    assert reparsed == original


def test_round_trip_unknown_fields(tmp_path: Path) -> None:
    original = parse_xmp(FIXTURES / "with_unknown_field.xmp")
    assert any(
        kind == "attr" and qname == "darktable:fake_test_attr" and value == "42"
        for kind, qname, value in original.raw_extra_fields
    )
    assert any(
        kind == "elem" and qname == "dc:creator"
        for kind, qname, _value in original.raw_extra_fields
    )
    out = tmp_path / "out.xmp"
    write_xmp(original, out)
    reparsed = parse_xmp(out)
    assert reparsed == original


def test_malformed_xml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xmp"
    bad.write_text("<?xml version='1.0'?><not_closed")
    with pytest.raises(XmpParseError, match="malformed"):
        parse_xmp(bad)


def test_file_not_found(tmp_path: Path) -> None:
    nonexistent = tmp_path / "missing.xmp"
    with pytest.raises(FileNotFoundError):
        parse_xmp(nonexistent)


def test_write_creates_file(tmp_path: Path) -> None:
    xmp = parse_xmp(FIXTURES / "minimal.xmp")
    out = tmp_path / "subdir_does_not_exist_yet.xmp"
    # parent (tmp_path) exists; out doesn't yet
    write_xmp(xmp, out)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_write_overwrites(tmp_path: Path) -> None:
    xmp = parse_xmp(FIXTURES / "minimal.xmp")
    out = tmp_path / "out.xmp"
    out.write_text("placeholder content that should disappear")
    write_xmp(xmp, out)
    assert out.read_text().startswith("<?xml")
    assert "placeholder" not in out.read_text()
