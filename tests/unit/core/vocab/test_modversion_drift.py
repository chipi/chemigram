"""Tests for the modversion-drift detection at vocab-load time.

Closes RFC-007 / ADR-082. The policy:
- Default: emit a UserWarning for every mismatch; vocab still loads.
- Strict mode (env var CHEMIGRAM_VOCAB_STRICT_MODVERSION=1): raise
  ManifestError on first detected mismatch batch; vocab refuses to load.
- Modules without a registered Path C decoder are skipped (we don't
  know the 'correct' modversion).
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

from chemigram.core.vocab import ManifestError, VocabularyIndex, load_packs
from chemigram.core.vocab._modversion_drift import (
    _build_known_pinned_modversions,
    check_entry_modversion_drift,
)


def test_clean_starter_pack_loads_silently_no_drift_warnings() -> None:
    """The currently shipped starter manifest declares the correct
    modversions for its entries (per #85 fix). Loading it must produce
    no UserWarnings about drift."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        load_packs(["starter"])
    drift_warnings = [w for w in captured if "modversion drift" in str(w.message)]
    assert drift_warnings == [], (
        f"starter pack should load drift-free, got {len(drift_warnings)} warning(s): "
        f"{[str(w.message) for w in drift_warnings]}"
    )


def test_clean_expressive_baseline_pack_loads_silently() -> None:
    """expressive-baseline post-Phase-4/Tier-2 must also load drift-free."""
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        load_packs(["expressive-baseline"])
    drift_warnings = [w for w in captured if "modversion drift" in str(w.message)]
    assert drift_warnings == [], (
        f"expressive-baseline should load drift-free, got {len(drift_warnings)} "
        f"warning(s): {[str(w.message) for w in drift_warnings]}"
    )


def test_pinned_modversions_includes_all_registered_decoders() -> None:
    """The drift-detection registry must list every Path C decoder."""
    pinned = _build_known_pinned_modversions()
    expected = {
        "bilat",
        "colorbalancergb",
        "crop",
        "exposure",
        "grain",
        "highlights",
        "sharpen",
        "sigmoid",
        "temperature",
        "toneequal",
        "vignette",
    }
    assert set(pinned.keys()) == expected, (
        f"pinned-modversions registry mismatch: got {set(pinned.keys())}, expected {expected}"
    )


def _make_synthetic_pack_with_drift(tmp_path: Path) -> Path:
    """Create a temp pack whose manifest declares a deliberately-wrong
    modversion for ``exposure`` (mv999 instead of the pinned mv7).
    Returns the pack root path."""
    pack_root = tmp_path / "drift_synthetic"
    layer_dir = pack_root / "layers" / "L3" / "exposure"
    layer_dir.mkdir(parents=True)
    # Minimal valid exposure dtstyle (mv7 28-byte blob with ev=0)
    (layer_dir / "exposure_drift.dtstyle").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<darktable_style version="1.0"><info><name>exposure_drift</name>'
        "<description>Test fixture — wrong modversion declared.</description></info>"
        "<style><plugin><num>0</num><module>7</module>"
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
        "_comment": "synthetic drift fixture",
        "entries": [
            {
                "name": "exposure_drift",
                "layer": "L3",
                "subtype": "exposure",
                "path": "layers/L3/exposure/exposure_drift.dtstyle",
                "touches": ["exposure"],
                "tags": ["exposure", "test"],
                "description": "Test fixture",
                "modversions": {"exposure": 999},  # WRONG: real pin is 7
                "darktable_version": "5.4",
                "source": "drift_synthetic",
                "license": "MIT",
            }
        ],
    }
    (pack_root / "manifest.json").write_text(json.dumps(manifest))
    return pack_root


def test_drift_emits_userwarning_in_default_mode(tmp_path, monkeypatch) -> None:
    """A pack whose manifest declares a wrong modversion produces a
    UserWarning at load time. The vocab still loads."""
    monkeypatch.delenv("CHEMIGRAM_VOCAB_STRICT_MODVERSION", raising=False)
    pack_root = _make_synthetic_pack_with_drift(tmp_path)
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        index = VocabularyIndex(pack_root)
    drift_warnings = [w for w in captured if "modversion drift" in str(w.message)]
    assert len(drift_warnings) == 1
    msg = str(drift_warnings[0].message)
    assert "exposure_drift" in msg
    assert "modversions['exposure']=999" in msg
    assert "mv7" in msg
    # Vocab loaded despite the warning
    assert index.lookup_by_name("exposure_drift") is not None


def test_drift_raises_in_strict_mode(tmp_path, monkeypatch) -> None:
    """When CHEMIGRAM_VOCAB_STRICT_MODVERSION is set, drift becomes
    a ManifestError that prevents the vocab from loading."""
    monkeypatch.setenv("CHEMIGRAM_VOCAB_STRICT_MODVERSION", "1")
    pack_root = _make_synthetic_pack_with_drift(tmp_path)
    with pytest.raises(ManifestError, match="modversion mismatch"):
        VocabularyIndex(pack_root)


def test_check_entry_skips_modules_without_registered_decoder() -> None:
    """A manifest declaring modversions for a module that has no
    Path C decoder (e.g. channelmixerrgb) is silently skipped by the
    drift check — we don't know the 'correct' modversion."""

    class _MockEntry:
        name = "test_entry"

        def __init__(self) -> None:
            self.modversions = {"channelmixerrgb": 99}  # not in registry

    mismatches = check_entry_modversion_drift(_MockEntry())
    assert mismatches == []


def test_strict_mode_env_var_truthy_values(tmp_path, monkeypatch) -> None:
    """The strict-mode env var accepts 1/true/yes/on (case-insensitive)."""
    pack_root = _make_synthetic_pack_with_drift(tmp_path)
    for truthy in ("1", "true", "TRUE", "yes", "On"):
        monkeypatch.setenv("CHEMIGRAM_VOCAB_STRICT_MODVERSION", truthy)
        with pytest.raises(ManifestError):
            VocabularyIndex(pack_root)


def test_strict_mode_env_var_falsy_values(tmp_path, monkeypatch) -> None:
    """Falsy / unset env var preserves default warn-loud behavior."""
    pack_root = _make_synthetic_pack_with_drift(tmp_path)
    for falsy in ("", "0", "false", "no", "off"):
        monkeypatch.setenv("CHEMIGRAM_VOCAB_STRICT_MODVERSION", falsy)
        with warnings.catch_warnings(record=True) as captured:
            warnings.simplefilter("always")
            VocabularyIndex(pack_root)
        # Should have warned, not raised
        assert any("modversion drift" in str(w.message) for w in captured)
