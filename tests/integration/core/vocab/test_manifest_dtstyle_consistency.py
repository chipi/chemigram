"""B6 — manifest.touches[] vs dtstyle plugin operations audit.

Would have caught the starter ``tone_lifted_shadows_subject`` bug
(#62) where the dtstyle file held the wrong content for its manifest
entry. Runs against every loaded pack at import time so adding an
entry whose dtstyle plugin operations don't match its manifest
``touches[]`` fails CI loudly.

Skips raster-mask-bound entries — those carry blend-op-driven mask
references that don't appear as plugin ``<operation>`` elements but
DO add operations to the effective ``touches[]`` set.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.vocab import VocabularyIndex, load_packs

REPO_ROOT = Path(__file__).resolve().parents[4]


def _packs_to_audit() -> list[VocabularyIndex]:
    """Every pack that ships in-tree."""
    indices = []
    starter_root = REPO_ROOT / "vocabulary" / "starter"
    if starter_root.exists():
        indices.append(VocabularyIndex(starter_root))
    expressive_root = REPO_ROOT / "vocabulary" / "packs" / "expressive-baseline"
    if expressive_root.exists():
        indices.append(VocabularyIndex(expressive_root))
    return indices


@pytest.mark.parametrize("index", _packs_to_audit(), ids=lambda i: str(i.pack_roots[0].name))
def test_every_entry_dtstyle_operations_match_manifest_touches(index: VocabularyIndex) -> None:
    failures = []
    for entry in index.list_all():
        if entry.mask_kind == "raster":
            # Mask-bound entries have additional touches via blendop_params
            # that don't surface as plugin <operation> elements; this audit
            # would false-positive on them.
            continue
        plugin_ops = {p.operation for p in entry.dtstyle.plugins}
        manifest_touches = set(entry.touches)
        if plugin_ops != manifest_touches:
            failures.append(
                f"{entry.name} ({entry.path.name}): "
                f"plugins={sorted(plugin_ops)} != touches={sorted(manifest_touches)}"
            )
    assert not failures, "\n".join(failures)


def test_starter_pack_via_load_packs_helper_consistent() -> None:
    """Sanity: same audit through the load_packs() entry point."""
    index = load_packs(["starter"])
    failures = []
    for entry in index.list_all():
        if entry.mask_kind == "raster":
            continue
        plugin_ops = {p.operation for p in entry.dtstyle.plugins}
        if plugin_ops != set(entry.touches):
            failures.append(entry.name)
    assert not failures, f"inconsistent entries in starter via load_packs: {failures}"
