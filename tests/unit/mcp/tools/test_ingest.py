"""Unit tests for chemigram.mcp.tools.ingest (and bind_layers, gap-log)."""

from __future__ import annotations

import json
from pathlib import Path

import anyio
import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import ToolContext, clear_registry, get_tool
from chemigram.mcp.tools import register_all

REPO_ROOT = Path(__file__).resolve().parents[4]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"


@pytest.fixture
def empty_ctx() -> ToolContext:
    """Fresh context with no workspaces — for ingest-from-scratch tests."""
    clear_registry()
    register_all()
    ctx = ToolContext(
        vocabulary=VocabularyIndex(VOCAB_TEST_PACK),
        prompts=PromptStore(SHIPPED_PROMPTS),
    )
    yield ctx
    clear_registry()


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


def _make_stub_raw(tmp_path: Path) -> Path:
    raw = tmp_path / "DSC_0001.NEF"
    raw.write_bytes(b"placeholder raw bytes")
    return raw


def test_ingest_creates_workspace(tmp_path: Path, empty_ctx: ToolContext) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    result = _call(
        "ingest",
        {"raw_path": str(raw), "workspace_root": str(ws_root)},
        empty_ctx,
    )
    assert result.success is True
    assert result.data["image_id"] == "DSC_0001"
    assert (Path(result.data["root"]) / "objects").is_dir()
    assert "DSC_0001" in empty_ctx.workspaces


def test_ingest_with_explicit_image_id(tmp_path: Path, empty_ctx: ToolContext) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    result = _call(
        "ingest",
        {
            "raw_path": str(raw),
            "image_id": "manta-001",
            "workspace_root": str(ws_root),
        },
        empty_ctx,
    )
    assert result.success is True
    assert result.data["image_id"] == "manta-001"


def test_ingest_unknown_raw_returns_not_found(tmp_path: Path, empty_ctx: ToolContext) -> None:
    result = _call(
        "ingest",
        {
            "raw_path": str(tmp_path / "ghost.NEF"),
            "workspace_root": str(tmp_path / "ws"),
        },
        empty_ctx,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_ingest_duplicate_image_id_returns_state_error(
    tmp_path: Path, empty_ctx: ToolContext
) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    result = _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    assert result.success is False
    assert result.error.code == ErrorCode.STATE_ERROR


def test_bind_layers_no_templates_returns_baseline(tmp_path: Path, empty_ctx: ToolContext) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    ingest_r = _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    image_id = ingest_r.data["image_id"]
    result = _call("bind_layers", {"image_id": image_id}, empty_ctx)
    assert result.success is True
    assert result.data["applied"] == []


def test_bind_layers_with_l2(tmp_path: Path, empty_ctx: ToolContext) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    ingest_r = _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    image_id = ingest_r.data["image_id"]
    result = _call(
        "bind_layers",
        {"image_id": image_id, "l2_template": "look_neutral"},
        empty_ctx,
    )
    assert result.success is True
    assert "snapshot_hash" in result.data
    assert result.data["applied"] == ["look_neutral"]


def test_bind_layers_wrong_layer_rejected(tmp_path: Path, empty_ctx: ToolContext) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    ingest_r = _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    image_id = ingest_r.data["image_id"]
    # 'expo_+0.5' is L3, not L2
    result = _call(
        "bind_layers",
        {"image_id": image_id, "l2_template": "expo_+0.5"},
        empty_ctx,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_log_vocabulary_gap_appends(tmp_path: Path, empty_ctx: ToolContext) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    ingest_r = _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    image_id = ingest_r.data["image_id"]
    result = _call(
        "log_vocabulary_gap",
        {
            "image_id": image_id,
            "description": "needs a 'subtle gradient warm tone' move",
            "workaround": "approximated with wb_warm_subtle",
        },
        empty_ctx,
    )
    assert result.success is True
    gap_path = Path(result.data["path"])
    assert gap_path.exists()
    record = json.loads(gap_path.read_text().strip())
    assert "subtle gradient" in record["description"]


def test_log_vocabulary_gap_empty_description_rejected(
    tmp_path: Path, empty_ctx: ToolContext
) -> None:
    raw = _make_stub_raw(tmp_path)
    ws_root = tmp_path / "workspaces"
    ingest_r = _call("ingest", {"raw_path": str(raw), "workspace_root": str(ws_root)}, empty_ctx)
    image_id = ingest_r.data["image_id"]
    result = _call(
        "log_vocabulary_gap",
        {"image_id": image_id, "description": "   "},
        empty_ctx,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT
