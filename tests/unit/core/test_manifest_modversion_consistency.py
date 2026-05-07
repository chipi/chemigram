"""Manifest declarations must agree with the actual `.dtstyle` blob sizes.

Closes #85 — surfaced when starter pack's ``wb_warm_subtle`` was annotated
``modversions: {"temperature": 3}`` but the dtstyle's op_params blob was
20 bytes (mv4 layout). The synthesizer treats op_params as opaque per
ADR-008, so render didn't break, but downstream tooling that trusts the
manifest annotation (e.g., the Path C parameterize registry, drift
detection per RFC-007) would misreport.

This test walks every manifest entry that declares ``modversions``, finds
each plugin in the corresponding ``.dtstyle`` file, and asserts the
op_params byte size matches what the parameterize registry declares for
that ``(module, modversion)`` tuple. Modules without a registered
decoder are skipped — we only know the expected struct size for the
modules we've reverse-engineered.

This is a static-data consistency check. It runs in the unit-test tier
(no darktable required) and is fast.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from chemigram.core.parameterize import (
    bilat,
    colorbalancergb,
    crop,
    exposure,
    grain,
    highlights,
    sharpen,
    sigmoid,
    temperature,
    toneequalizer,
    vignette,
)

_REPO_ROOT = Path(__file__).resolve().parents[3]

# (module, modversion) → expected op_params struct size in bytes.
# Sourced from each decoder's _STRUCT_SIZE constant. When a new decoder
# ships, add it here so manifests claiming that (module, mv) are
# byte-checked.
_KNOWN_STRUCT_SIZES: dict[tuple[str, int], int] = {
    ("exposure", exposure.SUPPORTED_MODVERSION): exposure._STRUCT_SIZE,
    ("vignette", vignette.SUPPORTED_MODVERSION): vignette._STRUCT_SIZE,
    ("colorbalancergb", colorbalancergb.SUPPORTED_MODVERSION): colorbalancergb._STRUCT_SIZE,
    ("sigmoid", sigmoid.SUPPORTED_MODVERSION): sigmoid._STRUCT_SIZE,
    ("bilat", bilat.SUPPORTED_MODVERSION): bilat._STRUCT_SIZE,
    ("grain", grain.SUPPORTED_MODVERSION): grain._STRUCT_SIZE,
    ("highlights", highlights.SUPPORTED_MODVERSION): highlights._STRUCT_SIZE,
    ("temperature", temperature.SUPPORTED_MODVERSION): temperature._STRUCT_SIZE,
    ("crop", crop.SUPPORTED_MODVERSION): crop._STRUCT_SIZE,
    ("sharpen", sharpen.SUPPORTED_MODVERSION): sharpen._STRUCT_SIZE,
    ("toneequal", toneequalizer.SUPPORTED_MODVERSION): toneequalizer._STRUCT_SIZE,
}

_MANIFESTS = [
    _REPO_ROOT / "vocabulary" / "starter" / "manifest.json",
    _REPO_ROOT / "vocabulary" / "packs" / "expressive-baseline" / "manifest.json",
]


def _collect_assertions() -> list[tuple[str, str, str, int, int]]:
    """Walk all manifests; for each (entry, module, modversion) where we
    have a decoder, return (manifest_name, entry_name, module, declared_mv,
    actual_blob_bytes) for the test to assert on.
    """
    out: list[tuple[str, str, str, int, int]] = []
    for manifest_path in _MANIFESTS:
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text())
        manifest_name = manifest_path.parent.name
        for entry in manifest.get("entries", []):
            modversions = entry.get("modversions", {})
            if not modversions:
                continue
            dtstyle_path = manifest_path.parent / entry["path"]
            if not dtstyle_path.exists():
                continue
            text = dtstyle_path.read_text()
            for module, modversion in modversions.items():
                if (module, modversion) not in _KNOWN_STRUCT_SIZES:
                    continue
                # Find the plugin matching this module
                plugin_pattern = (
                    rf"<plugin>(?:(?!</plugin>).)*?"
                    rf"<operation>{re.escape(module)}</operation>"
                    rf"(?:(?!</plugin>).)*?"
                    rf"<op_params>([0-9a-f]+)</op_params>"
                    rf"(?:(?!</plugin>).)*?</plugin>"
                )
                m = re.search(plugin_pattern, text, re.DOTALL)
                if not m:
                    continue
                actual_bytes = len(m.group(1)) // 2
                out.append((manifest_name, entry["name"], module, modversion, actual_bytes))
    return out


_ASSERTIONS = _collect_assertions()


@pytest.mark.parametrize(
    "manifest,entry_name,module,declared_mv,actual_bytes",
    _ASSERTIONS,
    ids=[f"{m}/{e}/{mod}@{mv}" for m, e, mod, mv, _ in _ASSERTIONS],
)
def test_manifest_modversion_matches_blob_size(
    manifest: str,
    entry_name: str,
    module: str,
    declared_mv: int,
    actual_bytes: int,
) -> None:
    """For every manifest entry that declares ``modversions: {<module>: N}``
    and where we have a Path C decoder for ``(module, N)``: the blob in
    the entry's dtstyle for that module must be exactly the size the
    decoder's struct expects.

    Mismatch → either the manifest annotation is wrong (most common; just
    update the modversion number) or the dtstyle was authored against a
    different darktable version than the manifest claims.
    """
    expected_bytes = _KNOWN_STRUCT_SIZES[(module, declared_mv)]
    assert actual_bytes == expected_bytes, (
        f"manifest '{manifest}' entry {entry_name!r}: declared "
        f"modversions[{module!r}]={declared_mv} expects {expected_bytes}-byte "
        f"op_params (per chemigram.core.parameterize.{module}._STRUCT_SIZE), "
        f"but the dtstyle's {module} plugin has {actual_bytes} bytes. "
        f"Either (a) the manifest's modversion number is wrong — fix it to "
        f"match the actual blob, or (b) the dtstyle was authored against a "
        f"different darktable version than the manifest claims and needs "
        f"re-authoring."
    )


def test_assertions_collected_at_least_one() -> None:
    """Sanity: the parametrize discovered at least one (entry, module, mv)
    triple to check. Catches accidental manifest-walking breakage."""
    assert len(_ASSERTIONS) > 0, (
        "no manifest entries with known-decoder modversions found — either "
        "manifests are missing 'modversions' fields or the parametrize "
        "broke."
    )
