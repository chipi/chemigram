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


def test_log_gap_full_rfc_013_schema_via_mcp(empty_server, tmp_path: Path) -> None:
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")
    ws_root = tmp_path / "ws"

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={"raw_path": str(raw), "workspace_root": str(ws_root)},
                )
            )
            return _decode(
                await session.call_tool(
                    "log_vocabulary_gap",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "description": "needs gradient warmth",
                        "intent": "warm gradient highlights",
                        "intent_category": "tone",
                        "missing_capability": "parametric_warm_gradient",
                        "operations_involved": ["temperature"],
                        "vocabulary_used": ["wb_warm_subtle"],
                        "satisfaction": 0,
                        "notes": "approximation only",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"]
    import json as _json

    record = _json.loads(Path(payload["data"]["path"]).read_text().strip())
    assert record["intent_category"] == "tone"
    assert record["satisfaction"] == 0
    assert isinstance(record["snapshot_hash"], str)


def test_log_gap_read_back_via_read_context(empty_server, tmp_path: Path) -> None:
    """Logging a gap then read_context should surface it in recent_gaps."""
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")
    ws_root = tmp_path / "ws"

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={"raw_path": str(raw), "workspace_root": str(ws_root)},
                )
            )
            image_id = ingest_r["data"]["image_id"]
            await session.call_tool(
                "log_vocabulary_gap",
                arguments={
                    "image_id": image_id,
                    "description": "bring back the gradient warm tone",
                    "missing_capability": "parametric_warm_gradient",
                },
            )
            return _decode(
                await session.call_tool("read_context", arguments={"image_id": image_id})
            )

    payload = anyio.run(_exercise)
    assert payload["success"]
    gaps = payload["data"]["recent_gaps"]
    assert any("gradient warm tone" in g["description"] for g in gaps)


# ---------- ingest error paths ----------------------------------------


def test_ingest_nonexistent_raw_returns_not_found(empty_server, tmp_path: Path) -> None:
    server = empty_server

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(tmp_path / "no-such.NEF"),
                        "workspace_root": str(tmp_path / "ws"),
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_ingest_duplicate_image_id_returns_state_error(empty_server, tmp_path: Path) -> None:
    """Re-ingesting the same image_id without removing the workspace
    first must fail cleanly — silently overwriting would lose history.
    """
    server = empty_server
    raw = tmp_path / "dupe.NEF"
    raw.write_bytes(b"raw")

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "ingest",
                arguments={
                    "raw_path": str(raw),
                    "workspace_root": str(tmp_path / "ws"),
                    "image_id": "fixed",
                },
            )
            return _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(tmp_path / "ws"),
                        "image_id": "fixed",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "state_error"


# ---------- bind_layers error paths -----------------------------------


def test_bind_layers_unknown_image_returns_not_found(empty_server, tmp_path: Path) -> None:
    server = empty_server

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "bind_layers",
                    arguments={"image_id": "no-such-image"},
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_bind_layers_unknown_vocab_returns_not_found(empty_server, tmp_path: Path) -> None:
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(tmp_path / "ws"),
                    },
                )
            )
            return _decode(
                await session.call_tool(
                    "bind_layers",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "l1_template": "no_such_l1",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_bind_layers_wrong_layer_returns_invalid_input(empty_server, tmp_path: Path) -> None:
    """Passing an L3 entry as l1_template should fail invalid_input —
    the contract is that l1_template must be an L1 entry.
    """
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(tmp_path / "ws"),
                    },
                )
            )
            # expo_+0.5 is L3 in the test pack; pass it as l1_template.
            return _decode(
                await session.call_tool(
                    "bind_layers",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "l1_template": "expo_+0.5",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "invalid_input"


def test_bind_layers_no_templates_returns_current_state(empty_server, tmp_path: Path) -> None:
    """bind_layers with neither L1 nor L2 is a state-summary read."""
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(tmp_path / "ws"),
                    },
                )
            )
            return _decode(
                await session.call_tool(
                    "bind_layers",
                    arguments={"image_id": ingest_r["data"]["image_id"]},
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"], payload.get("error")
    assert payload["data"]["applied"] == []
    assert "state_after" in payload["data"]


# ---------- log_vocabulary_gap error paths ----------------------------


def test_log_gap_empty_description_invalid_input(empty_server, tmp_path: Path) -> None:
    server = empty_server
    raw = tmp_path / "p.NEF"
    raw.write_bytes(b"raw")

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={"raw_path": str(raw), "workspace_root": str(tmp_path / "ws")},
                )
            )
            return _decode(
                await session.call_tool(
                    "log_vocabulary_gap",
                    arguments={
                        "image_id": ingest_r["data"]["image_id"],
                        "description": "   ",  # whitespace-only
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "invalid_input"


def test_mask_no_masker_via_mcp(empty_server, tmp_path: Path) -> None:
    """build_server without masker → MASKING_ERROR (was slice=4 NOT_IMPLEMENTED in v0.3.0)."""
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
    assert payload["error"]["code"] == "masking_error"
    assert "no masker configured" in payload["error"]["message"]
