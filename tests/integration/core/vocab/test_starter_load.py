"""Integration: load the bundled starter pack via load_starter() if populated.

Slice 6 fills ``vocabulary/starter/`` with real entries. Until then this test
skips with a clear message rather than failing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.vocab import VocabularyIndex, load_starter

REPO_STARTER = Path(__file__).resolve().parents[4] / "vocabulary" / "starter"


def test_load_starter_or_skip() -> None:
    if not (REPO_STARTER / "manifest.json").exists():
        pytest.skip("Starter pack not populated yet (Phase 1 Slice 6 work)")

    index = load_starter()
    assert isinstance(index, VocabularyIndex)
    assert len(index.list_all()) > 0
