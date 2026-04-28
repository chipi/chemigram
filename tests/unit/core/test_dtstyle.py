"""Unit tests for chemigram.core.dtstyle.

Covers the 10 cases listed in GH issue #1's implementation plan, in
the same execution order. Real fixtures live at tests/fixtures/dtstyles/.
"""

from pathlib import Path

import pytest

from chemigram.core.dtstyle import (
    DtstyleEntry,
    DtstyleParseError,
    PluginEntry,
    parse_dtstyle,
)

FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "dtstyles"

_ENABLED_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<darktable_style version="1.0">'
    "<info><name>t</name><description></description></info>"
    "<style><plugin>"
    "<num>0</num><module>1</module><operation>x</operation>"
    "<op_params>00</op_params><enabled>{enabled}</enabled>"
    "<blendop_params>gz</blendop_params><blendop_version>14</blendop_version>"
    "<multi_priority>0</multi_priority><multi_name></multi_name>"
    "</plugin></style></darktable_style>"
)


def test_parse_single_plugin_style() -> None:
    entry = parse_dtstyle(FIXTURES / "expo_plus_0p5.dtstyle")
    assert isinstance(entry, DtstyleEntry)
    assert entry.name == "expo_+0.5"
    assert entry.description == ""
    assert entry.iop_list is None
    assert len(entry.plugins) == 1
    plugin = entry.plugins[0]
    assert isinstance(plugin, PluginEntry)
    assert plugin.operation == "exposure"
    assert plugin.num == 13
    assert plugin.module == 7
    assert plugin.multi_priority == 0
    assert plugin.multi_name == ""
    assert plugin.enabled is True
    assert plugin.blendop_version == 14


def test_op_params_byte_identity() -> None:
    """ADR-008: opaque blobs preserved string-equal to source XML."""
    entry = parse_dtstyle(FIXTURES / "expo_plus_0p5.dtstyle")
    plugin = entry.plugins[0]
    assert plugin.op_params == ("00000000000080b90000003f00004842000080c00100000001000000")
    assert plugin.blendop_params == (
        "gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh"
    )


def test_enabled_field_parsing(tmp_path: Path) -> None:
    p1 = tmp_path / "enabled1.dtstyle"
    p1.write_text(_ENABLED_TEMPLATE.format(enabled="1"))
    assert parse_dtstyle(p1).plugins[0].enabled is True

    p0 = tmp_path / "enabled0.dtstyle"
    p0.write_text(_ENABLED_TEMPLATE.format(enabled="0"))
    assert parse_dtstyle(p0).plugins[0].enabled is False

    px = tmp_path / "enabled_invalid.dtstyle"
    px.write_text(_ENABLED_TEMPLATE.format(enabled="x"))
    with pytest.raises(DtstyleParseError, match="enabled"):
        parse_dtstyle(px)


def test_iop_list_optional() -> None:
    """Single-module GUI exports omit <iop_list>."""
    entry = parse_dtstyle(FIXTURES / "expo_plus_0p5.dtstyle")
    assert entry.iop_list is None


def test_user_entry_multi_name_empty() -> None:
    """ADR-010: user-authored entries have empty <multi_name>."""
    entry = parse_dtstyle(FIXTURES / "expo_plus_0p5.dtstyle")
    assert entry.plugins[0].multi_name == ""


def test_parse_multi_plugin_style() -> None:
    entry = parse_dtstyle(FIXTURES / "multi_module_synthetic.dtstyle")
    assert entry.name == "multi_module_synthetic"
    assert len(entry.plugins) == 2
    operations = {p.operation for p in entry.plugins}
    assert operations == {"exposure", "temperature"}
    # document order preserved
    assert entry.plugins[0].operation == "exposure"
    assert entry.plugins[1].operation == "temperature"


def test_iop_list_present_on_multi_module() -> None:
    entry = parse_dtstyle(FIXTURES / "multi_module_synthetic.dtstyle")
    assert entry.iop_list is not None
    assert "exposure" in entry.iop_list
    assert "temperature" in entry.iop_list


def test_malformed_xml_raises() -> None:
    with pytest.raises(DtstyleParseError, match="malformed"):
        parse_dtstyle(FIXTURES / "malformed_xml.dtstyle")


def test_missing_plugin_raises() -> None:
    with pytest.raises(DtstyleParseError, match="plugin"):
        parse_dtstyle(FIXTURES / "malformed_no_plugin.dtstyle")


def test_file_not_found(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist.dtstyle"
    with pytest.raises(FileNotFoundError):
        parse_dtstyle(nonexistent)


def test_parser_filters_builtin_plugins() -> None:
    """ADR-010 + Phase 0 safety-net: _builtin_* plugins are filtered."""
    entry = parse_dtstyle(FIXTURES / "with_builtin_filtered.dtstyle")
    assert len(entry.plugins) == 1
    assert entry.plugins[0].operation == "exposure"
    assert entry.plugins[0].multi_name == ""


def test_parser_raises_when_all_plugins_filtered() -> None:
    """A dtstyle with only _builtin_* plugins has no user-authored content."""
    with pytest.raises(DtstyleParseError, match="no user-authored"):
        parse_dtstyle(FIXTURES / "all_builtin_no_user.dtstyle")
