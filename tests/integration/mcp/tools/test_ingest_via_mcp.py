"""Integration: batch-3 ingest + workspace + masks via the harness."""

from __future__ import annotations

import json
from pathlib import Path

import anyio
import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import clear_registry
from chemigram.mcp.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[4]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"


@pytest.fixture
def empty_server(tmp_path: Path):
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, _ = build_server(vocabulary=vocab, prompts=prompts)
    yield server
    clear_registry()


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_ingest_then_apply_via_mcp(empty_server, tmp_path: Path) -> None:
    server = empty_server
    raw = tmp_path / "manta_001.NEF"
    raw.write_bytes(b"placeholder raw")
    ws_root = tmp_path / "workspaces"

    async def _exercise() -> tuple[dict, dict, dict]:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(ws_root),
                    },
                )
            )
            apply_r = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "primitive_name": "expo_+0.5",
                    },
                )
            )
            log_r = _decode(
                await session.call_tool(
                    "log",
                    arguments={"image_id": ingest_r["data"]["image_id"]},
                )
            )
            return ingest_r, apply_r, log_r

    ingest_r, apply_r, log_r = anyio.run(_exercise)
    assert ingest_r["success"]
    assert apply_r["success"]
    assert log_r["success"]
    assert any(e["op"] == "snapshot" for e in log_r["data"])


def test_log_vocabulary_gap_via_mcp(empty_server, tmp_path: Path) -> None:
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")
    ws_root = tmp_path / "ws"

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(ws_root),
                    },
                )
            )
            return _decode(
                await session.call_tool(
                    "log_vocabulary_gap",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "description": "no smoothing primitive for water surface texture",
                        "workaround": "skipped",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"]
    gap_path = Path(payload["data"]["path"])
    assert gap_path.exists()


def test_mask_stubs_via_mcp(empty_server, tmp_path: Path) -> None:
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")
    ws_root = tmp_path / "ws"

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(ws_root),
                    },
                )
            )
            return _decode(
                await session.call_tool(
                    "generate_mask",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "target": "subject",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_implemented"
    assert payload["error"]["details"].get("slice") == 4
