"""Integration: generate_mask + regenerate_mask through the in-memory harness.

Uses a fake MaskingProvider injected via build_server(masker=...) and patches
the rendering call so the integration doesn't depend on darktable.
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
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.ops import snapshot, tag
from chemigram.core.vocab import VocabularyIndex
from chemigram.core.workspace import Workspace, init_workspace_root
from chemigram.core.xmp import parse_xmp
from chemigram.mcp._test_harness import in_memory_session
from chemigram.mcp.prompts import PromptStore
from chemigram.mcp.registry import clear_registry
from chemigram.mcp.server import build_server

REPO_ROOT = Path(__file__).resolve().parents[4]
VOCAB_TEST_PACK = REPO_ROOT / "tests" / "fixtures" / "vocabulary" / "test_pack"
SHIPPED_PROMPTS = REPO_ROOT / "src" / "chemigram" / "mcp" / "prompts"
BASELINE_XMP = REPO_ROOT / "tests" / "fixtures" / "xmps" / "synthesized_v3_reference.xmp"


def _png_bytes() -> bytes:
    img = Image.new("L", (8, 8), 200)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class _FakeMasker:
    def generate(self, *, target: str, render_path: Path, prompt: str | None = None) -> MaskResult:
        return MaskResult(png_bytes=_png_bytes(), generator="fake", prompt=prompt, target=target)

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        return MaskResult(png_bytes=_png_bytes(), generator="fake", prompt=prompt, target=target)


def _stub_render(output_path: Path) -> StageResult:
    Image.new("RGB", (256, 256), "gray").save(output_path, "JPEG")
    return StageResult(
        success=True,
        output_path=output_path,
        duration_seconds=0.05,
        stderr="",
        error_message=None,
    )


@pytest.fixture
def server_and_workspace(tmp_path: Path) -> Any:
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts, masker=_FakeMasker())

    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    ws = Workspace(image_id="img-1", root=root, repo=repo, raw_path=raw_path)
    ctx.workspaces[ws.image_id] = ws

    yield server, ctx
    clear_registry()


def _decode(call_result) -> dict:
    return json.loads(call_result.content[0].text)


def test_generate_then_regenerate_via_mcp(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> tuple[dict, dict, dict]:
        async with in_memory_session(server) as session:
            gen = await session.call_tool(
                "generate_mask",
                arguments={"image_id": "img-1", "target": "manta"},
            )
            list_r = await session.call_tool("list_masks", arguments={"image_id": "img-1"})
            regen = await session.call_tool(
                "regenerate_mask",
                arguments={
                    "image_id": "img-1",
                    "name": "current_manta_mask",
                    "prompt": "tighten edges",
                },
            )
            return _decode(gen), _decode(list_r), _decode(regen)

    with patch(
        "chemigram.core.pipeline.render",
        side_effect=lambda **kw: _stub_render(kw["output_path"]),
    ):
        gen, list_r, regen = anyio.run(_exercise)

    assert gen["success"], gen.get("error")
    assert gen["data"]["name"] == "current_manta_mask"
    assert gen["data"]["generator"] == "fake"

    assert list_r["success"]
    names = {e["name"] for e in list_r["data"]}
    assert "current_manta_mask" in names

    assert regen["success"], regen.get("error")
    assert regen["data"]["name"] == "current_manta_mask"


def test_generate_mask_no_masker_via_mcp(tmp_path: Path) -> None:
    """build_server without masker → MASKING_ERROR end-to-end."""
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts)  # no masker

    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    ctx.workspaces["img-2"] = Workspace(image_id="img-2", root=root, repo=repo, raw_path=raw_path)

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool(
                "generate_mask",
                arguments={"image_id": "img-2", "target": "manta"},
            )
            return _decode(r)

    payload = anyio.run(_exercise)
    clear_registry()
    assert payload["success"] is False
    assert payload["error"]["code"] == "masking_error"
    assert "no masker configured" in payload["error"]["message"]


# ---------- regenerate_mask error path ---------------------------------


def test_regenerate_mask_unknown_name_returns_not_found(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool(
                "regenerate_mask",
                arguments={
                    "image_id": "img-1",
                    "name": "no_such_mask",
                },
            )
            return _decode(r)

    with patch(
        "chemigram.core.pipeline.render",
        side_effect=lambda **kw: _stub_render(kw["output_path"]),
    ):
        payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


# ---------- generate_mask provider failure -----------------------------


class _RaisingMasker:
    def generate(self, **kwargs: Any) -> Any:
        raise RuntimeError("simulated provider failure")

    def regenerate(self, **kwargs: Any) -> Any:  # pragma: no cover (not exercised here)
        raise RuntimeError("not used")


def test_generate_mask_provider_raise_returns_masking_error(tmp_path: Path) -> None:
    clear_registry()
    vocab = VocabularyIndex(VOCAB_TEST_PACK)
    prompts = PromptStore(SHIPPED_PROMPTS)
    server, ctx = build_server(vocabulary=vocab, prompts=prompts, masker=_RaisingMasker())

    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw_path = root / "raw" / "input.NEF"
    raw_path.touch()
    h = snapshot(repo, parse_xmp(BASELINE_XMP), label="baseline")
    tag(repo, "baseline", h)
    ctx.workspaces["img-3"] = Workspace(image_id="img-3", root=root, repo=repo, raw_path=raw_path)

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            r = await session.call_tool(
                "generate_mask",
                arguments={"image_id": "img-3", "target": "manta"},
            )
            return _decode(r)

    with patch(
        "chemigram.core.pipeline.render",
        side_effect=lambda **kw: _stub_render(kw["output_path"]),
    ):
        payload = anyio.run(_exercise)
    clear_registry()
    assert payload["success"] is False
    assert payload["error"]["code"] == "masking_error"


# ---------- list_masks coverage ---------------------------------------


def test_list_masks_empty_registry(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("list_masks", arguments={"image_id": "img-1"}))

    payload = anyio.run(_exercise)
    assert payload["success"], payload.get("error")
    assert payload["data"] == []


def test_list_masks_unknown_image_not_found(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(await session.call_tool("list_masks", arguments={"image_id": "no-such"}))

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


# ---------- tag_mask coverage -----------------------------------------


def test_tag_mask_happy_path(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> tuple[dict, dict, dict]:
        async with in_memory_session(server) as session:
            gen = _decode(
                await session.call_tool(
                    "generate_mask",
                    arguments={"image_id": "img-1", "target": "manta"},
                )
            )
            tagged = _decode(
                await session.call_tool(
                    "tag_mask",
                    arguments={
                        "image_id": "img-1",
                        "source": "current_manta_mask",
                        "new_name": "manta_v1_export",
                    },
                )
            )
            listed = _decode(await session.call_tool("list_masks", arguments={"image_id": "img-1"}))
            return gen, tagged, listed

    with patch(
        "chemigram.core.pipeline.render",
        side_effect=lambda **kw: _stub_render(kw["output_path"]),
    ):
        gen, tagged, listed = anyio.run(_exercise)
    assert tagged["success"], tagged.get("error")
    assert tagged["data"]["name"] == "manta_v1_export"
    # Both names point to the same content hash.
    assert tagged["data"]["hash"] == gen["data"]["hash"]
    names = {e["name"] for e in listed["data"]}
    assert names == {"current_manta_mask", "manta_v1_export"}


def test_tag_mask_already_exists_rejects(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            await session.call_tool(
                "generate_mask",
                arguments={"image_id": "img-1", "target": "manta"},
            )
            await session.call_tool(
                "tag_mask",
                arguments={
                    "image_id": "img-1",
                    "source": "current_manta_mask",
                    "new_name": "snapshot",
                },
            )
            return _decode(
                await session.call_tool(
                    "tag_mask",
                    arguments={
                        "image_id": "img-1",
                        "source": "current_manta_mask",
                        "new_name": "snapshot",
                    },
                )
            )

    with patch(
        "chemigram.core.pipeline.render",
        side_effect=lambda **kw: _stub_render(kw["output_path"]),
    ):
        payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "masking_error"
    assert "already exists" in payload["error"]["message"]


def test_tag_mask_unknown_source_returns_not_found(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "tag_mask",
                    arguments={
                        "image_id": "img-1",
                        "source": "no_such_mask",
                        "new_name": "wherever",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"


def test_tag_mask_empty_new_name_invalid_input(server_and_workspace: Any) -> None:
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "tag_mask",
                    arguments={
                        "image_id": "img-1",
                        "source": "anything",
                        "new_name": "",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "invalid_input"


# ---------- apply_primitive(mask_override) error path ------------------


def test_apply_primitive_mask_override_unregistered_returns_not_found(
    server_and_workspace: Any,
) -> None:
    """If the named mask isn't in the registry, apply rejects cleanly."""
    server, _ = server_and_workspace

    async def _exercise() -> dict:
        async with in_memory_session(server) as session:
            return _decode(
                await session.call_tool(
                    "apply_primitive",
                    arguments={
                        "image_id": "img-1",
                        "primitive_name": "tone_lifted_shadows_subject",
                        "mask_override": "no_such_mask",
                    },
                )
            )

    payload = anyio.run(_exercise)
    assert payload["success"] is False
    assert payload["error"]["code"] == "not_found"
