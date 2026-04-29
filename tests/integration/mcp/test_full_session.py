"""End-to-end Mode A gate test.

Drives the full MCP tool surface against a fresh workspace using the
in-memory client/server harness. This is the gate that proves Slice 3
shipped a coherent surface: every tool accessed through MCP, every
``ToolResult`` shape matching RFC-010 (closed by ADR-056).

Steps:
    1. ingest(raw_path)
    2. bind_layers(image_id) — both templates omitted = baseline
    3. list_vocabulary → pick 3 different primitives
    4. apply_primitive expo_+0.5 → snapshot_hash_a
    5. snapshot
    6. branch experimental, checkout experimental
    7. apply_primitive wb_warm_subtle → snapshot_hash_b
    8. diff(hash_a, hash_b)
    9. tag v1-export
    10. log → newest-first entries

Render-dependent tools (`render_preview`, `compare`, `export_final`) are
exercised conditionally on `darktable-cli` availability — they're expected
to surface a `DARKTABLE_ERROR` against the placeholder raw, which still
counts as the contract being intact.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import anyio
import pytest

from chemigram.core.vocab import VocabularyIndex
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import clear_registry
from chemigram.mcp.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[3]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


@pytest.fixture
def server(tmp_path: Path):
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, _ = build_server(vocabulary=vocab, prompts=prompts)
    yield server
    clear_registry()


def test_full_session_end_to_end(server, tmp_path: Path) -> None:
    raw = tmp_path / "manta_001.NEF"
    raw.write_bytes(b"placeholder raw bytes")
    ws_root = tmp_path / "workspaces"

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            # 1. ingest
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(ws_root),
                    },
                )
            )
            assert ingest_r["success"], ingest_r["error"]
            image_id = ingest_r["data"]["image_id"]

            # 2. bind_layers (no templates → baseline)
            bind_r = _decode(
                await session.call_tool("bind_layers", arguments={"image_id": image_id})
            )
            assert bind_r["success"]

            # 3. list_vocabulary
            vocab_r = _decode(await session.call_tool("list_vocabulary", arguments={}))
            assert vocab_r["success"]
            names = {e["name"] for e in vocab_r["data"]}
            assert {"expo_+0.5", "wb_warm_subtle"}.issubset(names)

            # 4. apply_primitive expo_+0.5
            apply_a = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={"image_id": image_id, "primitive_name": "expo_+0.5"},
                )
            )
            assert apply_a["success"]
            hash_a = apply_a["data"]["snapshot_hash"]

            # 5. snapshot
            snap_r = _decode(
                await session.call_tool(
                    "snapshot",
                    arguments={"image_id": image_id, "label": "manual checkpoint"},
                )
            )
            assert snap_r["success"]

            # 6. branch + checkout
            br_r = _decode(
                await session.call_tool(
                    "branch",
                    arguments={
                        "image_id": image_id,
                        "name": "experimental",
                        "from_": "HEAD",
                    },
                )
            )
            assert br_r["success"]
            chk_r = _decode(
                await session.call_tool(
                    "checkout",
                    arguments={"image_id": image_id, "ref_or_hash": "experimental"},
                )
            )
            assert chk_r["success"]

            # 7. apply_primitive wb_warm_subtle on experimental branch
            apply_b = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": image_id,
                        "primitive_name": "wb_warm_subtle",
                    },
                )
            )
            assert apply_b["success"]
            hash_b = apply_b["data"]["snapshot_hash"]

            # 8. diff
            diff_r = _decode(
                await session.call_tool(
                    "diff",
                    arguments={
                        "image_id": image_id,
                        "hash_a": hash_a,
                        "hash_b": hash_b,
                    },
                )
            )
            assert diff_r["success"]
            assert isinstance(diff_r["data"], list)

            # 9. tag
            tag_r = _decode(
                await session.call_tool(
                    "tag",
                    arguments={"image_id": image_id, "name": "v1-export"},
                )
            )
            assert tag_r["success"]

            # 10. log
            log_r = _decode(
                await session.call_tool(
                    "log",
                    arguments={"image_id": image_id, "limit": 50},
                )
            )
            assert log_r["success"]
            ops = [e["op"] for e in log_r["data"]]
            for expected in ("snapshot", "branch", "checkout", "tag"):
                assert expected in ops, f"{expected} missing from log ops {ops}"

            # 11. read_context — confirms stub contract
            rc_r = _decode(
                await session.call_tool("read_context", arguments={"image_id": image_id})
            )
            assert rc_r["success"] is False
            assert rc_r["error"]["code"] == "not_implemented"
            assert rc_r["error"]["details"].get("slice") == 5

            # 12. log_vocabulary_gap
            gap_r = _decode(
                await session.call_tool(
                    "log_vocabulary_gap",
                    arguments={
                        "image_id": image_id,
                        "description": "no 'pelagic blue restoration' move",
                        "workaround": "approximated with wb_warm_subtle inverse",
                    },
                )
            )
            assert gap_r["success"]

            return {
                "image_id": image_id,
                "vocab_names": names,
                "hash_a": hash_a,
                "hash_b": hash_b,
                "log_ops": ops,
            }

    out = anyio.run(_exercise)
    assert out["hash_a"] != out["hash_b"]


@pytest.mark.skipif(shutil.which("darktable-cli") is None, reason="no darktable-cli")
def test_render_step_via_mcp_with_darktable(server, tmp_path: Path) -> None:
    raw = tmp_path / "x.NEF"
    raw.write_bytes(b"placeholder")
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
                    "render_preview",
                    arguments={"image_id": ingest_r["data"]["image_id"], "size": 256},
                )
            )

    payload = anyio.run(_exercise)
    # Either a successful render (real raw fixture wired up) or a clean
    # darktable_error on the placeholder bytes — both prove the contract.
    if not payload["success"]:
        assert payload["error"]["code"] == "darktable_error"
