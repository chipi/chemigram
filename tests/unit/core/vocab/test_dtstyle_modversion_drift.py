"""Tests for the dtstyle-modversion-drift check at vocab-load time.

Sister to :mod:`test_modversion_drift`. The check catches the bug class
where a dtstyle file's ``<module>N</module>`` byte disagrees with the
engine's pinned modversion for that operation, which causes darktable
to silently hang at render. The bug surfaced in the v1.10.0 photographer-
survey vocabulary expansion (25 entries with wrong colorequal/bilat/etc
module bytes); this check would have caught it at load time.

Policy:
- Default: emit UserWarning per affected plugin; vocab still loads.
- Strict mode (CHEMIGRAM_VOCAB_STRICT_MODVERSION=1): raise ManifestError.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from chemigram.core.vocab import ManifestError, VocabularyIndex, load_packs
from chemigram.core.vocab._dtstyle_modversion_drift import (
    check_entry_dtstyle_modversion_drift,
)


def test_clean_starter_pack_no_dtstyle_drift_warnings() -> None:
    """starter pack must load without dtstyle-drift warnings — every
    plugin's ``<module>`` byte agrees with the engine pin."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        load_packs(["starter"])
    drift_warnings = [w for w in captured if "dtstyle modversion drift" in str(w.message)]
    assert drift_warnings == [], (
        f"starter pack should be dtstyle-drift-free, got {len(drift_warnings)} "
        f"warning(s): {[str(w.message) for w in drift_warnings]}"
    )


def test_clean_expressive_baseline_pack_no_dtstyle_drift_warnings() -> None:
    """expressive-baseline must also load without dtstyle-drift warnings.

    This is the regression guard for the v1.10.0 bug class — the 25
    entries with wrong ``<module>`` bytes were fixed in commit 969d647;
    if this test starts failing, that class of bug has reappeared.
    """
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        load_packs(["expressive-baseline"])
    drift_warnings = [w for w in captured if "dtstyle modversion drift" in str(w.message)]
    assert drift_warnings == [], (
        f"expressive-baseline must be dtstyle-drift-free, got {len(drift_warnings)} "
        f"warning(s): {[str(w.message) for w in drift_warnings]}"
    )


def _make_synthetic_pack_with_dtstyle_drift(tmp_path: Path) -> Path:
    """Create a temp pack whose dtstyle has a deliberately-wrong
    ``<module>`` byte (mv999 for ``exposure`` whose engine pin is mv7).
    Manifest declares the correct modversion — the lie is in the
    dtstyle, not the manifest. Returns the pack root."""
    pack_root = tmp_path / "dtstyle_drift_synthetic"
    layer_dir = pack_root / "layers" / "L3" / "exposure"
    layer_dir.mkdir(parents=True)
    (layer_dir / "exposure_dtstyle_drift.dtstyle").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<darktable_style version="1.0"><info><name>exposure_dtstyle_drift</name>'
        "<description>Test fixture — wrong dtstyle module byte.</description></info>"
        "<style><plugin><num>0</num><module>999</module>"  # WRONG: pin is 7
        "<operation>exposure</operation>"
        "<op_params>00000000000080b9000000000000484200008c40010000000000000a</op_params>"
        "<enabled>1</enabled>"
        "<blendop_params>gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh</blendop_params>"
        "<blendop_version>14</blendop_version>"
        "<multi_priority>0</multi_priority><multi_name></multi_name>"
        "<multi_name_hand_edited>0</multi_name_hand_edited></plugin></style>"
        "</darktable_style>\n"
    )
    manifest = {
        "_comment": "synthetic dtstyle-drift fixture",
        "entries": [
            {
                "name": "exposure_dtstyle_drift",
                "layer": "L3",
                "subtype": "exposure",
                "path": "layers/L3/exposure/exposure_dtstyle_drift.dtstyle",
                "touches": ["exposure"],
                "tags": ["exposure", "test"],
                "description": "Test fixture",
                "modversions": {"exposure": 7},  # honest manifest; bug is in the dtstyle
                "darktable_version": "5.4",
                "source": "dtstyle_drift_synthetic",
                "license": "MIT",
            }
        ],
    }
    (pack_root / "manifest.json").write_text(json.dumps(manifest))
    return pack_root


def test_dtstyle_drift_emits_userwarning_in_default_mode(tmp_path, monkeypatch) -> None:
    """A pack whose dtstyle has a wrong ``<module>`` byte produces a
    UserWarning at load time; vocab still loads."""
    monkeypatch.delenv("CHEMIGRAM_VOCAB_STRICT_MODVERSION", raising=False)
    pack_root = _make_synthetic_pack_with_dtstyle_drift(tmp_path)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        index = VocabularyIndex(pack_root)
    drift_warnings = [w for w in captured if "dtstyle modversion drift" in str(w.message)]
    assert len(drift_warnings) == 1
    msg = str(drift_warnings[0].message)
    assert "exposure_dtstyle_drift" in msg
    assert "<module>999</module>" in msg
    assert "mv7" in msg
    # Vocab still loaded
    assert index.lookup_by_name("exposure_dtstyle_drift") is not None


def test_dtstyle_drift_raises_in_strict_mode(tmp_path, monkeypatch) -> None:
    """In strict mode the wrong ``<module>`` byte raises ManifestError."""
    monkeypatch.setenv("CHEMIGRAM_VOCAB_STRICT_MODVERSION", "1")
    pack_root = _make_synthetic_pack_with_dtstyle_drift(tmp_path)
    with pytest.raises(ManifestError, match="dtstyle-modversion"):
        VocabularyIndex(pack_root)


def test_check_skips_plugins_for_unregistered_ops() -> None:
    """A plugin for an op without a registered Path C decoder is
    skipped — for those we have no pinned reference."""
    from chemigram.core.dtstyle import DtstyleEntry, PluginEntry

    plug = PluginEntry(
        operation="channelmixerrgb",
        num=0,
        module=99,
        op_params="00",
        blendop_params="gz08X",
        blendop_version=14,
        multi_priority=0,
        multi_name="",
        enabled=True,
    )
    dt = DtstyleEntry(name="t", description="", iop_list=None, plugins=(plug,))

    class _MockEntry:
        name = "t"
        dtstyle = dt

    mismatches = check_entry_dtstyle_modversion_drift(_MockEntry())
    assert mismatches == []


def test_check_catches_v1_10_0_bug_class_pattern() -> None:
    """Reproduce the exact v1.10.0 bug pattern: a colorequal plugin with
    ``<module>8</module>`` (wrong) when the engine is pinned to mv4.
    This is the regression guard for the bug that caused the 25-entry
    render-hang."""
    from chemigram.core.dtstyle import DtstyleEntry, PluginEntry

    plug = PluginEntry(
        operation="colorequal",
        num=0,
        module=8,  # WRONG: pin is 4
        op_params="00",
        blendop_params="gz08X",
        blendop_version=14,
        multi_priority=0,
        multi_name="",
        enabled=True,
    )
    dt = DtstyleEntry(name="t", description="", iop_list=None, plugins=(plug,))

    class _MockEntry:
        name = "look_v1_10_0_bug_repro"
        dtstyle = dt

    mismatches = check_entry_dtstyle_modversion_drift(_MockEntry())
    assert len(mismatches) == 1
    assert "<module>8</module>" in mismatches[0]
    assert "mv4" in mismatches[0]
    assert "darktable will silently hang" in mismatches[0]
