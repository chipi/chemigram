"""Shared fixtures for the MCP tool unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.vocab import VocabularyIndex
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import ToolContext, clear_registry
from chemigram.mcp.tools import register_all

REPO_ROOT = Path(__file__).resolve().parents[4]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"
BASELINE_XMP = REPO_ROOT / "tests" / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"


@pytest.fixture
def vocab() -> VocabularyIndex:
    return VocabularyIndex(VOCAB_TEST_PACK)


@pytest.fixture
def prompts() -> PromptStore:
    return PromptStore(SHIPPED_PROMPTS)


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    """A workspace with a real ImageRepo and an initial baseline snapshot."""
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    baseline_xmp = parse_xmp(BASELINE_XMP)
    baseline_hash = snapshot(repo, baseline_xmp, label="baseline")
    tag(repo, "baseline", baseline_hash)
    return Workspace(
        image_id="test-image",
        root=root,
        repo=repo,
        raw_path=raw_path,
    )


@pytest.fixture
def context(vocab: VocabularyIndex, prompts: PromptStore, workspace: Workspace) -> ToolContext:
    clear_registry()
    register_all()
    ctx = ToolContext(vocabulary=vocab, prompts=prompts)
    ctx.workspaces[workspace.image_id] = workspace
    yield ctx
    clear_registry()
