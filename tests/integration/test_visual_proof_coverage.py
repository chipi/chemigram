"""Visual-proof coverage audit.

Asserts that every vocabulary entry has at least one rendered visual
proof on disk OR is in the documented skip list. Catches the bug class
that surfaced in the v1.10.0 round-3 audit: 10 entries with named-mask
references (`{"kind": "named", "name": "mask_X"}`) silently failed
during synthesis in the visual-proof generator (the script's broad
except logged + dropped them), and the gallery quietly lost them.

This test reads the on-disk proofs without rendering — it's cheap to
run in CI and catches the next silent generator-side drop the moment
it happens.

For visual *correctness* (does the rendered output actually match the
entry's documented intent?), see `docs/guides/darkroom-session-debt.md`
items 7-11 — that's photographer review against real raws, not a CI
property.
"""

from __future__ import annotations

import re
from pathlib import Path

from chemigram.core.vocab import load_packs

REPO_ROOT = Path(__file__).resolve().parents[2]
PROOFS_ROOT = REPO_ROOT / "docs" / "visual-proofs"


def _load_skip_set() -> set[str]:
    """Parse the visual-proof generator's :data:`_SKIP_VISUAL_PROOF_ENTRIES`
    set so this test stays automatically in sync with deliberate skips
    (HSL via colorequal on synthetic chart, real-raw-only entries, etc.).

    Parses the source text rather than importing the module — the
    generator imports dataclass-decorated types that don't survive
    importlib.util.module_from_spec without a sys.modules registration
    dance. Plain-text parse is robust + read-only.
    """
    gen_path = REPO_ROOT / "scripts" / "generate-visual-proofs.py"
    source = gen_path.read_text()
    match = re.search(
        r"_SKIP_VISUAL_PROOF_ENTRIES:\s*set\[str\]\s*=\s*\{([^}]*)\}",
        source,
        re.S,
    )
    assert match, "could not locate _SKIP_VISUAL_PROOF_ENTRIES in generator"
    body = match.group(1)
    names: set[str] = set()
    for entry in re.finditer(r'"([a-zA-Z0-9_+\-./]+)"', body):
        names.add(entry.group(1))
    return names


def _entry_has_proof(entry_name: str) -> bool:
    """True if ``docs/visual-proofs/<pack>/<entry>-<target>.jpg`` exists
    for at least one (pack, target) combination."""
    for pack in ("starter", "expressive-baseline"):
        pack_dir = PROOFS_ROOT / pack
        if not pack_dir.is_dir():
            continue
        # Match the base render only; sweep / masked variants are extra
        # coverage but not the canonical "did this entry render at all?"
        for target in ("colorchecker", "grayscale", "realraw"):
            if (pack_dir / f"{entry_name}-{target}.jpg").exists():
                return True
    return False


def test_every_vocabulary_entry_has_a_visual_proof_or_is_skipped() -> None:
    """Catches the v1.10.0 bug class: silent generator-side drops where
    entries fail during synthesis and disappear from the gallery without
    raising."""
    vocab = load_packs(["starter", "expressive-baseline"])
    skip_set = _load_skip_set()

    missing: list[str] = []
    for entry in vocab.list_all():
        if entry.name in skip_set:
            continue
        # L1 entries (camera baselines) aren't rendered as standalone
        # proofs — they're applied via bind-layers as part of a stack.
        # Skip them.
        if entry.layer == "L1":
            continue
        if not _entry_has_proof(entry.name):
            missing.append(entry.name)

    assert not missing, (
        f"Vocabulary entries with no visual proof on disk and not in "
        f"_SKIP_VISUAL_PROOF_ENTRIES: {sorted(missing)}. Either run "
        "`make docs-cli`-equivalent (`uv run scripts/generate-visual-proofs.py`) "
        "to render them, or add the names to _SKIP_VISUAL_PROOF_ENTRIES "
        "with a documented reason for skipping. This test prevents the "
        "v1.10.0 silent-drop bug class from recurring."
    )


def test_skip_set_has_no_stale_entries() -> None:
    """Every name in ``_SKIP_VISUAL_PROOF_ENTRIES`` must reference a
    vocabulary entry that actually exists. Catches refactor cruft."""
    vocab = load_packs(["starter", "expressive-baseline"])
    all_names = {e.name for e in vocab.list_all()}
    skip_set = _load_skip_set()

    stale = sorted(skip_set - all_names)
    assert not stale, (
        f"_SKIP_VISUAL_PROOF_ENTRIES references entries that no longer "
        f"exist in any loaded pack: {stale}. Remove them."
    )
