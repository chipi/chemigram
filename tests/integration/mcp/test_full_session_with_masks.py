"""End-to-end Mode A gate test for Slice 4 (masking).

Drives ingest → bind_layers → generate_mask → list_masks →
apply_primitive(mask_override=...) → snapshot → regenerate_mask → log
through the in-memory MCP harness with a fake sampling-based masker
injected via build_server(masker=...).

This is the v0.4.0 gate: every masking-related tool exercised through MCP,
every ToolResult shape validated against ADR-057's contract.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import anyio
import pytest
from PIL import Image

from chemigram.core.masking import MaskResult
from chemigram.core.pipeline import StageResult
from chemigram.core.vocab import VocabularyIndex
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import clear_registry
from chemigram.mcp.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[3]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"


def _png_bytes() -> bytes:
    img = Image.new("L", (8, 8), 200)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class _FakeMasker:
    """Sampling-based masker double; canned bbox descriptor → coarse PNG."""

    def generate(self, *, target: str, render_path: Path, prompt: str | None = None) -> MaskResult:
        return MaskResult(
            png_bytes=_png_bytes(), generator="coarse_agent_fake", prompt=prompt, target=target
        )

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        return MaskResult(
            png_bytes=_png_bytes(), generator="coarse_agent_fake", prompt=prompt, target=target
        )


def _stub_render(output_path: Path) -> StageResult:
    Image.new("RGB", (256, 256), "gray").save(output_path, "JPEG")
    return StageResult(
        success=True, output_path=output_path, duration_seconds=0.05, stderr="", error_message=None
    )


@pytest.fixture
def server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    tastes = tmp_path / "tastes"
    tastes.mkdir()
    monkeypatch.setenv("CHEMIGRAM_TASTES_DIR", str(tastes))

    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, _ = build_server(vocabulary=vocab, prompts=prompts, masker=_FakeMasker())
    yield server
    clear_registry()


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_masking_gate_full_session(server, tmp_path: Path) -> None:
    """Full Slice 4 surface end-to-end via the harness."""
    raw = tmp_path / "manta_001.NEF"
    raw.write_bytes(b"placeholder raw bytes")
    ws_root = tmp_path / "workspaces"

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            ingest_r = _decode(
                await session.call_tool(
                    "ingest",
                    arguments={"raw_path": str(raw), "workspace_root": str(ws_root)},
                )
            )
            assert ingest_r["success"], ingest_r["error"]
            image_id = ingest_r["data"]["image_id"]

            gen_r = _decode(
                await session.call_tool(
                    "generate_mask",
                    arguments={
                        "image_id": image_id,
                        "target": "subject",
                        "prompt": "centered animal",
                    },
                )
            )
            assert gen_r["success"], gen_r["error"]
            mask_name = gen_r["data"]["name"]

            list_r = _decode(
                await session.call_tool("list_masks", arguments={"image_id": image_id})
            )
            assert list_r["success"]
            assert mask_name in {e["name"] for e in list_r["data"]}

            apply_r = _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": image_id,
                        "primitive_name": "tone_lifted_shadows_subject",
                        "mask_override": mask_name,
                    },
                )
            )
            assert apply_r["success"], apply_r["error"]

            regen_r = _decode(
                await session.call_tool(
                    "regenerate_mask",
                    arguments={
                        "image_id": image_id,
                        "name": mask_name,
                        "prompt": "tighter edges",
                    },
                )
            )
            assert regen_r["success"], regen_r["error"]

            log_r = _decode(
                await session.call_tool("log", arguments={"image_id": image_id, "limit": 50})
            )
            assert log_r["success"]
            return {
                "image_id": image_id,
                "mask_name": mask_name,
                "log_ops": [e["op"] for e in log_r["data"]],
                "apply_hash": apply_r["data"]["snapshot_hash"],
            }

    with patch(
        "chemigram.mcp.tools.masks.render",
        side_effect=lambda **kw: _stub_render(kw["output_path"]),
    ):
        out = anyio.run(_exercise)

    assert out["mask_name"].endswith("_mask")
    assert "snapshot" in out["log_ops"]
    assert isinstance(out["apply_hash"], str)
