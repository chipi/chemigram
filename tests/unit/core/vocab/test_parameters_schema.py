"""Unit tests for VocabEntry.parameters schema parsing + validation.

Closes part of RFC-021 / ADR-078: every parameterized vocabulary entry
declares a ``parameters`` array on its manifest entry. The parser
validates structure (required keys, type, range, default-in-range,
field offset/encoding), turns it into a tuple of :class:`ParameterSpec`,
and attaches it to :class:`VocabEntry`. Entries without ``parameters``
load unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chemigram.core.vocab import (
    ManifestError,
    ParameterField,
    ParameterSpec,
    VocabularyIndex,
)

# Reuse the test_pack's expo_+0.5 dtstyle as a fixture body — the tests
# exercise the manifest parser only, not the dtstyle parser, so any
# valid 28-byte exposure dtstyle works as the body.
_TESTS_ROOT = Path(__file__).resolve().parents[3]
_TEST_PACK_DTSTYLE = (
    _TESTS_ROOT
    / "fixtures"
    / "vocabulary"
    / "test_pack"
    / "layers"
    / "L3"
    / "exposure"
    / "expo_+0.5.dtstyle"
)


def _make_pack(tmp_path: Path, entry_extras: dict) -> Path:
    """Build a minimal one-entry pack at ``tmp_path``; return pack root."""
    pack_root = tmp_path / "pack"
    pack_root.mkdir()
    layers = pack_root / "layers" / "L3" / "exposure"
    layers.mkdir(parents=True)
    dtstyle_dst = layers / "test_entry.dtstyle"
    dtstyle_dst.write_bytes(_TEST_PACK_DTSTYLE.read_bytes())

    base_entry = {
        "name": "test_entry",
        "layer": "L3",
        "path": "layers/L3/exposure/test_entry.dtstyle",
        "touches": ["exposure"],
        "tags": ["test"],
        "description": "schema test entry",
        "modversions": {"exposure": 7},
        "darktable_version": "5.4",
        "source": "test",
        "license": "MIT",
    }
    base_entry.update(entry_extras)
    (pack_root / "manifest.json").write_text(json.dumps({"entries": [base_entry]}))
    return pack_root


def test_entry_without_parameters_has_none(tmp_path: Path) -> None:
    """Backwards compat: a manifest entry without ``parameters`` loads
    with ``VocabEntry.parameters is None``."""
    pack_root = _make_pack(tmp_path, {})
    idx = VocabularyIndex(pack_root)
    entry = idx.lookup_by_name("test_entry")
    assert entry is not None
    assert entry.parameters is None


def test_single_parameter_entry_parses(tmp_path: Path) -> None:
    """Single-parameter entry parses into a tuple of one ParameterSpec."""
    pack_root = _make_pack(
        tmp_path,
        {
            "parameters": [
                {
                    "name": "ev",
                    "type": "float",
                    "range": [-3.0, 3.0],
                    "default": 0.0,
                    "field": {
                        "module": "exposure",
                        "modversion": 7,
                        "offset": 8,
                        "encoding": "le_f32",
                    },
                }
            ]
        },
    )
    idx = VocabularyIndex(pack_root)
    entry = idx.lookup_by_name("test_entry")
    assert entry is not None
    assert entry.parameters == (
        ParameterSpec(
            name="ev",
            type="float",
            range=(-3.0, 3.0),
            default=0.0,
            field=ParameterField(module="exposure", modversion=7, offset=8, encoding="le_f32"),
        ),
    )


def test_multi_parameter_entry_parses(tmp_path: Path) -> None:
    """Multi-parameter entry returns a tuple in declaration order."""
    pack_root = _make_pack(
        tmp_path,
        {
            "parameters": [
                {
                    "name": "temp",
                    "type": "float",
                    "range": [-2.0, 2.0],
                    "default": 0.0,
                    "field": {
                        "module": "exposure",
                        "modversion": 7,
                        "offset": 0,
                        "encoding": "le_f32",
                    },
                },
                {
                    "name": "tint",
                    "type": "float",
                    "range": [-1.0, 1.0],
                    "default": 0.0,
                    "field": {
                        "module": "exposure",
                        "modversion": 7,
                        "offset": 4,
                        "encoding": "le_f32",
                    },
                },
            ]
        },
    )
    idx = VocabularyIndex(pack_root)
    entry = idx.lookup_by_name("test_entry")
    assert entry is not None
    assert entry.parameters is not None
    assert len(entry.parameters) == 2
    assert [p.name for p in entry.parameters] == ["temp", "tint"]


@pytest.mark.parametrize(
    "bad_extras,expected_msg",
    [
        ({"parameters": []}, "must be a non-empty list"),
        ({"parameters": "not_a_list"}, "must be a non-empty list"),
        (
            {
                "parameters": [
                    {
                        "name": "ev",
                        "type": "int",
                        "range": [0, 1],
                        "default": 0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": 8,
                            "encoding": "le_f32",
                        },
                    }
                ]
            },
            "unsupported type",
        ),
        (
            {
                "parameters": [
                    {
                        "name": "ev",
                        "type": "float",
                        "range": [3.0, -3.0],
                        "default": 0.0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": 8,
                            "encoding": "le_f32",
                        },
                    }
                ]
            },
            "must be < max",
        ),
        (
            {
                "parameters": [
                    {
                        "name": "ev",
                        "type": "float",
                        "range": [-3.0, 3.0],
                        "default": 5.0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": 8,
                            "encoding": "le_f32",
                        },
                    }
                ]
            },
            "outside range",
        ),
        (
            {
                "parameters": [
                    {
                        "name": "ev",
                        "type": "float",
                        "range": [-3.0, 3.0],
                        "default": 0.0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": -1,
                            "encoding": "le_f32",
                        },
                    }
                ]
            },
            "non-negative integer",
        ),
        (
            {
                "parameters": [
                    {
                        "name": "ev",
                        "type": "float",
                        "range": [-3.0, 3.0],
                        "default": 0.0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": 8,
                            "encoding": "le_f64",
                        },
                    }
                ]
            },
            "unsupported encoding",
        ),
        (
            {
                "parameters": [
                    {
                        "name": "ev",
                        "type": "float",
                        "range": [-3.0, 3.0],
                        "default": 0.0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": 8,
                            "encoding": "le_f32",
                        },
                    },
                    {
                        "name": "ev",
                        "type": "float",
                        "range": [-1.0, 1.0],
                        "default": 0.0,
                        "field": {
                            "module": "exposure",
                            "modversion": 7,
                            "offset": 12,
                            "encoding": "le_f32",
                        },
                    },
                ]
            },
            "duplicate name",
        ),
    ],
    ids=[
        "empty-list",
        "non-list",
        "wrong-type",
        "inverted-range",
        "default-out-of-range",
        "negative-offset",
        "unsupported-encoding",
        "duplicate-param-name",
    ],
)
def test_parameter_validation_failures(tmp_path: Path, bad_extras: dict, expected_msg: str) -> None:
    """Each malformed-parameters case raises ManifestError early at load time."""
    pack_root = _make_pack(tmp_path, bad_extras)
    with pytest.raises(ManifestError, match=expected_msg):
        VocabularyIndex(pack_root)
