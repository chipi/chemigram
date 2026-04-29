"""End-to-end Mode A gate test for Slice 5 (context layer).

Drives a full session that exercises every Slice 5 surface:
read_context → apply_primitive x2 → propose_taste_update + confirm →
log_vocabulary_gap (RFC-013 shape) → propose_notes_update + confirm →
read_context (again, sees gap + log entries).

Asserts: tastes file gained the proposed line; notes file gained the
proposed paragraph; transcript JSONL contains all events in order.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
import pytest

from chemigram.core.session import start_session
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
def setup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    tastes = tmp_path / "tastes"
    tastes.mkdir()
    monkeypatch.setenv("CHEMIGRAM_TASTES_DIR", str(tastes))
    # Pre-populate _default.md so the agent's first read_context call
    # sees existing taste content.
    (tastes / "_default.md").write_text("base preferences: calm tones, low contrast\n")

    clear_registry()
    yield tastes, tmp_path
    clear_registry()


def test_context_gate_full_session(setup: Any) -> None:
    tastes, tmp = setup
    raw = tmp / "manta_001.NEF"
    raw.write_bytes(b"placeholder")
    ws_root = tmp / "workspaces"

    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)

    # Ingest happens via the MCP tool; we'll start the transcript afterwards
    # against the resolved workspace.
    async def _ingest_only() -> tuple[Any, str]:
        srv, ctx = build_server(vocabulary=vocab, prompts=prompts)
        async with in_memory_session(srv) as session:
            r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={
                        "raw_path": str(raw),
                        "workspace_root": str(ws_root),
                    },
                )
            )
        return ctx, r["data"]["image_id"]

    ctx_ingest, image_id = anyio.run(_ingest_only)
    workspace = ctx_ingest.workspaces[image_id]

    # Pre-populate brief.md with a Tastes line for the read_context surface.
    (workspace.root / "brief.md").write_text(
        "# Manta photo\n\nTastes: [underwater]\n\nIntent: clean blue water\n"
    )
    # Pre-populate the underwater genre file
    (tastes / "underwater.md").write_text("slate-blue over cyan-pop\n")

    clear_registry()
    transcript = start_session(workspace, session_id="ctx-gate")
    server, ctx = build_server(vocabulary=vocab, prompts=prompts, transcript=transcript)
    ctx.workspaces[image_id] = workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            # 1. read_context — sees pre-populated tastes + brief
            rc1 = _decode(await session.call_tool("read_context", arguments={"image_id": image_id}))
            assert rc1["success"]
            assert "calm tones" in rc1["data"]["tastes"]["default"]
            assert "underwater" in rc1["data"]["tastes"]["genres"]

            # 2-3. apply_primitive x2
            apply_a = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": image_id,
                        "primitive_name": "expo_+0.5",
                    },
                )
            )
            assert apply_a["success"]
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

            # 4. propose_taste_update + confirm
            propose_t = _decode(
                await session.call_tool(
                    "propose_taste_update",
                    arguments={
                        "content": "for pelagic shots, slate-blue beats cyan-pop",
                        "category": "appearance",
                        "file": "underwater",
                    },
                )
            )
            assert propose_t["success"]
            confirm_t = _decode(
                await session.call_tool(
                    "confirm_taste_update",
                    arguments={"proposal_id": propose_t["data"]["proposal_id"]},
                )
            )
            assert confirm_t["success"]

            # 5. log_vocabulary_gap (full RFC-013 shape)
            gap = _decode(
                await session.call_tool(
                    "log_vocabulary_gap",
                    arguments={
                        "image_id": image_id,
                        "description": "no parametric warm gradient on highlights",
                        "intent": "warm gradient highlights",
                        "intent_category": "tone",
                        "missing_capability": "parametric_warm_gradient",
                        "operations_involved": ["temperature"],
                        "vocabulary_used": ["wb_warm_subtle"],
                        "satisfaction": 0,
                    },
                )
            )
            assert gap["success"]
            assert gap["data"]["session_id"] == "ctx-gate"

            # 6. propose_notes_update + confirm
            propose_n = _decode(
                await session.call_tool(
                    "propose_notes_update",
                    arguments={
                        "image_id": image_id,
                        "content": (
                            "session ctx-gate: applied expo_+0.5 + wb_warm_subtle; "
                            "logged gap for parametric warm gradient"
                        ),
                    },
                )
            )
            assert propose_n["success"]
            confirm_n = _decode(
                await session.call_tool(
                    "confirm_notes_update",
                    arguments={"proposal_id": propose_n["data"]["proposal_id"]},
                )
            )
            assert confirm_n["success"]

            # 7. read_context again — should now include the gap and log entries
            rc2 = _decode(await session.call_tool("read_context", arguments={"image_id": image_id}))
            assert rc2["success"]
            return {
                "rc1": rc1,
                "rc2": rc2,
                "apply_a": apply_a,
                "apply_b": apply_b,
                "gap": gap,
            }

    try:
        out = anyio.run(_exercise)
    finally:
        transcript.close()

    # tastes file gained the proposed line
    underwater = (tastes / "underwater.md").read_text()
    assert "slate-blue beats cyan-pop" in underwater

    # notes file gained the proposed paragraph
    notes = (workspace.root / "notes.md").read_text()
    assert "session ctx-gate" in notes

    # final read_context surfaced the gap + log entries
    rc2 = out["rc2"]
    assert any("parametric warm gradient" in g["description"] for g in rc2["data"]["recent_gaps"])
    assert any(e["op"] == "snapshot" for e in rc2["data"]["recent_log"])

    # transcript contains header + tool_calls + proposals + confirmations + footer
    lines = [json.loads(line) for line in transcript.path.read_text(encoding="utf-8").splitlines()]
    kinds = [line["kind"] for line in lines]
    assert kinds[0] == "header"
    assert kinds[-1] == "footer"
    assert "tool_call" in kinds
    assert "tool_result" in kinds
    assert "proposal" in kinds
    assert "confirmation" in kinds
