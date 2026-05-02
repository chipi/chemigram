"""Shared fixtures for the CLI integration tests.

Mirrors the MCP unit-test workspace fixture (tests/unit/mcp/tools/conftest.py)
but produces a layout the CLI can discover via ``--workspace <root>`` plus
the image_id positional argument: ``<root>/<image_id>/{objects,refs,...}``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.workspace import init_workspace_root
from chemigram.core.xmp import parse_xmp

REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_XMP = REPO_ROOT / "tests" / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"
TEST_RAW_NAME = "input.NEF"


@pytest.fixture
def cli_workspace_root(tmp_path: Path) -> Path:
    """A workspace root containing one image_id 'test-image' with a baseline snapshot.

    Pass ``--workspace <root>`` plus ``test-image`` as the image_id to any
    CLI verb that needs a loaded workspace.
    """
    root = tmp_path / "ws_root"
    image_id = "test-image"
    image_root = root / image_id
    init_workspace_root(image_root)
    repo = ImageRepo.init(image_root)
    raw_dir = image_root / "raw"
    raw_dir.mkdir(exist_ok=True)
    (raw_dir / TEST_RAW_NAME).touch()
    baseline_xmp = parse_xmp(BASELINE_XMP)
    baseline_hash = snapshot(repo, baseline_xmp, label="baseline")
    tag(repo, "baseline", baseline_hash)
    return root


@pytest.fixture
def fresh_raw(tmp_path: Path) -> Path:
    """A real on-disk raw file (the synthesized fixture or a touched stub)."""
    target = tmp_path / "fresh.NEF"
    # Prefer the real NEF fixture if present; else touch a stub for ingest.
    candidate = REPO_ROOT / "tests" / "fixtures" / "raws" / "minimal.NEF"
    if candidate.exists():
        shutil.copy(candidate, target)
    else:
        target.write_bytes(b"")
    return target


@pytest.fixture
def isolated_tastes_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Override ``CHEMIGRAM_TASTES_DIR`` so apply-taste-update doesn't touch ~/.chemigram."""
    target = tmp_path / "tastes"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("CHEMIGRAM_TASTES_DIR", str(target))
    return target
