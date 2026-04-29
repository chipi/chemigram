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


def _write_minimal_xmp(tmp_path: Path, **overrides: str) -> Path:
    """Minimal valid XMP with overridable top-level attrs."""
    attrs = {
        "rating": "0",
        "auto_presets_applied": "0",
        "history_end": "0",
        "iop_order_version": "4",
        "label": "",
    }
    attrs.update(overrides)
    label_attr = f' xmp:Label="{attrs["label"]}"' if attrs["label"] else ""
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 4.4.0-Exiv2">'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '  <rdf:Description rdf:about=""'
        '    xmlns:xmp="http://ns.adobe.com/xap/1.0/"'
        '    xmlns:darktable="http://darktable.sf.net/"'
        f'   xmp:Rating="{attrs["rating"]}"{label_attr}'
        f'   darktable:auto_presets_applied="{attrs["auto_presets_applied"]}"'
        f'   darktable:history_end="{attrs["history_end"]}"'
        f'   darktable:iop_order_version="{attrs["iop_order_version"]}"/>'
        " </rdf:RDF>"
        "</x:xmpmeta>"
    )
    p = tmp_path / "test.xmp"
    p.write_text(xml)
    return p


def test_history_end_exceeds_length_raises(tmp_path: Path) -> None:
    """history_end > len(history) is malformed XMP."""
    p = _write_minimal_xmp(tmp_path, history_end="20")  # but no history entries
    with pytest.raises(XmpParseError, match="history_end=20 exceeds"):
        parse_xmp(p)


def test_history_end_less_than_length_ok(tmp_path: Path) -> None:
    """history_end can be less than len(history) — entries beyond are pending."""
    p = _write_minimal_xmp(tmp_path, history_end="0")
    xmp = parse_xmp(p)
    assert xmp.history_end == 0
    assert xmp.history == ()


def test_label_is_stripped(tmp_path: Path) -> None:
    """xmp:Label should be whitespace-stripped to match dtstyle.description."""
    p = _write_minimal_xmp(tmp_path, label="  finalist  ")
    xmp = parse_xmp(p)
    assert xmp.label == "finalist"


def test_missing_description_raises(tmp_path: Path) -> None:
    """An XMP without rdf:Description is malformed."""
    bad = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        ' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
        "</x:xmpmeta>"
    )
    p = tmp_path / "no_desc.xmp"
    p.write_text(bad)
    with pytest.raises(XmpParseError, match="missing rdf:Description"):
        parse_xmp(p)


def test_invalid_rating_raises(tmp_path: Path) -> None:
    p = _write_minimal_xmp(tmp_path, rating="not-an-int")
    with pytest.raises(XmpParseError, match="not an integer"):
        parse_xmp(p)


# --- parse_xmp_from_bytes -------------------------------------------------


def test_parse_xmp_from_bytes_round_trip(tmp_path: Path) -> None:
    """parse_xmp_from_bytes accepts what canonical_bytes produces."""
    from chemigram.core.versioning import canonical_bytes
    from chemigram.core.xmp import parse_xmp_from_bytes

    original = parse_xmp(FIXTURES / "synthesized_v3_reference.xmp")
    raw = canonical_bytes(original)
    reparsed = parse_xmp_from_bytes(raw)
    assert reparsed == original


def test_parse_xmp_from_bytes_uses_source_in_errors() -> None:
    from chemigram.core.xmp import parse_xmp_from_bytes

    bad = b"<?xml version='1.0'?><not_closed"
    with pytest.raises(XmpParseError, match=r"sha256:abc.*malformed XML"):
        parse_xmp_from_bytes(bad, source="sha256:abc")


def test_parse_xmp_from_bytes_invalid_utf8() -> None:
    from chemigram.core.xmp import parse_xmp_from_bytes

    # Random bytes that aren't valid UTF-8
    bad = b"\xff\xfe\x00\x80\x81\x82"
    with pytest.raises(XmpParseError, match="not valid UTF-8"):
        parse_xmp_from_bytes(bad)


def test_parse_xmp_from_bytes_missing_description() -> None:
    from chemigram.core.xmp import parse_xmp_from_bytes

    bad = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        b' <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
        b"</x:xmpmeta>"
    )
    with pytest.raises(XmpParseError, match="missing rdf:Description"):
        parse_xmp_from_bytes(bad)


def test_parse_xmp_from_bytes_default_source() -> None:
    """Default source label is '<bytes>' for callers who don't supply one."""
    from chemigram.core.xmp import parse_xmp_from_bytes

    bad = b"not xml at all"
    with pytest.raises(XmpParseError, match=r"<bytes>"):
        parse_xmp_from_bytes(bad)
