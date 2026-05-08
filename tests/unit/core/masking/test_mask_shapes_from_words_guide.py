"""Lint test: round-trip every example mask_spec from the
``docs/guides/mask-shapes-from-words.md`` guide through
``build_form_from_spec``. Catches doc rot when encoder parameter
names or schema shape change. Per ADR-084's implementation note.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from chemigram.core.masking.dt_serialize import build_form_from_spec

GUIDE_PATH = Path(__file__).resolve().parents[4] / "docs" / "guides" / "mask-shapes-from-words.md"


def _extract_inline_specs() -> list[tuple[str, dict]]:
    """Pull every `{dt_form: ..., dt_params: {...}}` table cell out of
    the guide. Returns list of (phrase_label, spec_dict)."""
    text = GUIDE_PATH.read_text()
    # Match table rows like: | "Phrase" | `{dt_form: "...", dt_params: {...}}` |
    row = re.compile(
        r"\|\s*\"(?P<phrase>[^\"]+)\"[^|]*\|\s*`(?P<spec>\{dt_form:[^`]+\})`",
    )
    out: list[tuple[str, dict]] = []
    for m in row.finditer(text):
        phrase = m.group("phrase")
        raw = m.group("spec")
        # The guide uses unquoted JS-style keys ("dt_form: ...") for
        # readability. Normalize to JSON: quote bare keys.
        norm = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', raw)
        try:
            spec = json.loads(norm)
        except json.JSONDecodeError as e:
            pytest.fail(f"could not parse spec for {phrase!r}: {raw!r} -> {norm!r} ({e})")
        out.append((phrase, spec))
    return out


def _extract_fenced_specs() -> list[tuple[str, dict]]:
    """Pull every ```jsonc block whose body is a single mask_spec dict."""
    text = GUIDE_PATH.read_text()
    out: list[tuple[str, dict]] = []
    for m in re.finditer(r"```jsonc\n(.*?)```", text, re.DOTALL):
        body = m.group(1)
        # Strip jsonc-style line comments (// ...) so we can json.loads it
        stripped = re.sub(r"//[^\n]*", "", body)
        try:
            spec = json.loads(stripped)
        except json.JSONDecodeError:
            # Some fenced blocks may be illustrative non-spec snippets;
            # only round-trip the ones that look like a spec dict.
            continue
        if isinstance(spec, dict) and "dt_form" in spec:
            out.append((f"fenced[{m.start()}]", spec))
    return out


def test_guide_file_exists() -> None:
    assert GUIDE_PATH.exists(), f"guide doc missing: {GUIDE_PATH}"


def test_guide_has_at_least_twenty_table_examples() -> None:
    """The guide ships ~30 phrase->spec examples; sanity-check we
    parsed something, not an empty regex haul."""
    specs = _extract_inline_specs()
    assert len(specs) >= 20, (
        f"only extracted {len(specs)} table examples — regex may be broken or "
        f"the guide may have lost coverage"
    )


@pytest.mark.parametrize(
    "phrase,spec",
    _extract_inline_specs() + _extract_fenced_specs(),
    ids=lambda v: v if isinstance(v, str) else "",
)
def test_guide_example_specs_round_trip_through_encoder(phrase: str, spec: dict) -> None:
    """Every example mask_spec in the guide must parse cleanly through
    build_form_from_spec — that's the contract the guide promises to
    the agent. If this fails, the guide is lying about parameter
    semantics and needs to be updated."""
    form = build_form_from_spec(mask_id=42, spec=spec)
    assert form.mask_id == 42
    # Every form must produce non-empty point bytes
    assert len(form.mask_points) > 0
    # Every form must produce a non-empty src (8 zero bytes for non-clone)
    assert form.mask_src == b"\x00" * 8


def test_guide_covers_all_four_dt_form_kinds() -> None:
    """The guide must showcase every shape the schema accepts. If
    'path' is added but no example ships, agents won't know it exists."""
    specs = _extract_inline_specs() + _extract_fenced_specs()
    forms_seen = {s["dt_form"] for _, s in specs}
    expected = {"gradient", "ellipse", "rectangle", "path"}
    missing = expected - forms_seen
    assert not missing, f"guide missing examples for dt_form(s): {missing}"
