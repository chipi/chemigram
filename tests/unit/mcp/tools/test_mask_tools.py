"""Unit tests for chemigram.mcp.tools.masks."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any
from unittest.mock import patch

import anyio
import pytest
from PIL import Image

from chemigram.core.masking import MaskingError, MaskResult
from chemigram.core.pipeline import StageResult
from chemigram.core.versioning.masks import register_mask
from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


class _FakeMasker:
    """Test double for MaskingProvider — returns a canned MaskResult."""

    def __init__(self, png_bytes: bytes) -> None:
        self.png_bytes = png_bytes
        self.calls: list[dict[str, Any]] = []

    def generate(self, *, target: str, render_path: Path, prompt: str | None = None) -> MaskResult:
        self.calls.append(
            {"op": "generate", "target": target, "render_path": render_path, "prompt": prompt}
        )
        return MaskResult(
            png_bytes=self.png_bytes,
            generator="fake",
            prompt=prompt,
            target=target,
        )

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        self.calls.append(
            {
                "op": "regenerate",
                "target": target,
                "render_path": render_path,
                "prior_mask": prior_mask,
                "prompt": prompt,
            }
        )
        return MaskResult(
            png_bytes=self.png_bytes,
            generator="fake",
            prompt=prompt,
            target=target,
        )


def _stub_render(output_path: Path) -> StageResult:
    Image.new("RGB", (256, 256), "gray").save(output_path, "JPEG")
    return StageResult(
        success=True,
        output_path=output_path,
        duration_seconds=0.1,
        stderr="",
        error_message=None,
    )


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


def _png_bytes() -> bytes:
    img = Image.new("L", (8, 8), 128)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.mark.parametrize("tool_name", ["generate_mask", "regenerate_mask"])
def test_mask_tools_no_masker_configured_returns_masking_error(
    context: ToolContext, tool_name: str
) -> None:
    """Without ctx.masker set (default in the fixture), tools surface a
    clean MASKING_ERROR instead of crashing."""
    args: dict[str, Any] = {"image_id": "test-image", "target": "subject"}
    if tool_name == "regenerate_mask":
        args["name"] = "current_subject_mask"
        # Pre-register a mask so we get past the existence check
        from chemigram.core.versioning.masks import register_mask

        register_mask(
            context.workspaces["test-image"].repo,
            "current_subject_mask",
            _png_bytes(),
            generator="manual",
        )
    result = _call(tool_name, args, context)
    assert result.success is False
    assert result.error.code == ErrorCode.MASKING_ERROR
    assert "no masker configured" in result.error.message


def test_list_masks_empty(context: ToolContext) -> None:
    result = _call("list_masks", {"image_id": "test-image"}, context)
    assert result.success is True
    assert result.data == []


def test_list_masks_after_register(context: ToolContext) -> None:
    ws = context.workspaces["test-image"]
    register_mask(ws.repo, "sky", _png_bytes(), generator="manual")
    result = _call("list_masks", {"image_id": "test-image"}, context)
    assert result.success is True
    assert {e["name"] for e in result.data} == {"sky"}


def test_tag_mask(context: ToolContext) -> None:
    ws = context.workspaces["test-image"]
    register_mask(ws.repo, "subject", _png_bytes(), generator="manual")
    result = _call(
        "tag_mask",
        {"image_id": "test-image", "source": "subject", "new_name": "subject_v1"},
        context,
    )
    assert result.success is True
    assert result.data["name"] == "subject_v1"


def test_tag_mask_unknown_returns_not_found(context: ToolContext) -> None:
    result = _call(
        "tag_mask",
        {"image_id": "test-image", "source": "ghost", "new_name": "x"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_invalidate_mask(context: ToolContext) -> None:
    ws = context.workspaces["test-image"]
    register_mask(ws.repo, "tmp", _png_bytes(), generator="manual")
    result = _call("invalidate_mask", {"image_id": "test-image", "name": "tmp"}, context)
    assert result.success is True
    list_after = _call("list_masks", {"image_id": "test-image"}, context).data
    assert all(e["name"] != "tmp" for e in list_after)


def test_invalidate_mask_unknown_returns_not_found(context: ToolContext) -> None:
    result = _call("invalidate_mask", {"image_id": "test-image", "name": "ghost"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


# --- generate_mask / regenerate_mask with a fake provider ----------------


def _ctx_with_masker(context: ToolContext, masker: _FakeMasker) -> ToolContext:
    """Mutate the fixture context to attach a masker (the field is ``Any``)."""
    context.masker = masker
    return context


def test_generate_mask_unknown_image_returns_not_found(context: ToolContext) -> None:
    _ctx_with_masker(context, _FakeMasker(_png_bytes()))
    result = _call("generate_mask", {"image_id": "ghost", "target": "manta"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_generate_mask_round_trip_with_fake_provider(context: ToolContext) -> None:
    masker = _FakeMasker(_png_bytes())
    _ctx_with_masker(context, masker)
    with patch(
        "chemigram.core.pipeline.render", side_effect=lambda **kw: _stub_render(kw["output_path"])
    ):
        result = _call(
            "generate_mask",
            {"image_id": "test-image", "target": "manta", "prompt": "centered"},
            context,
        )
    assert result.success is True
    assert result.data["name"] == "current_manta_mask"
    assert masker.calls[0]["op"] == "generate"
    assert masker.calls[0]["target"] == "manta"
    assert masker.calls[0]["prompt"] == "centered"


def test_generate_mask_default_name_derives_from_target(context: ToolContext) -> None:
    masker = _FakeMasker(_png_bytes())
    _ctx_with_masker(context, masker)
    with patch(
        "chemigram.core.pipeline.render", side_effect=lambda **kw: _stub_render(kw["output_path"])
    ):
        result = _call(
            "generate_mask",
            {"image_id": "test-image", "target": "subject"},
            context,
        )
    assert result.success is True
    assert result.data["name"] == "current_subject_mask"


def test_generate_mask_explicit_name_used(context: ToolContext) -> None:
    masker = _FakeMasker(_png_bytes())
    _ctx_with_masker(context, masker)
    with patch(
        "chemigram.core.pipeline.render", side_effect=lambda **kw: _stub_render(kw["output_path"])
    ):
        result = _call(
            "generate_mask",
            {"image_id": "test-image", "target": "manta", "name": "manta_v1"},
            context,
        )
    assert result.success is True
    assert result.data["name"] == "manta_v1"


def test_generate_mask_provider_failure_returns_masking_error(
    context: ToolContext,
) -> None:
    class FailingMasker(_FakeMasker):
        def generate(self, **_kw: Any) -> MaskResult:
            raise MaskingError("agent declined")

    _ctx_with_masker(context, FailingMasker(_png_bytes()))
    with patch(
        "chemigram.core.pipeline.render", side_effect=lambda **kw: _stub_render(kw["output_path"])
    ):
        result = _call(
            "generate_mask",
            {"image_id": "test-image", "target": "manta"},
            context,
        )
    assert result.success is False
    assert result.error.code == ErrorCode.MASKING_ERROR


def test_regenerate_mask_unknown_returns_not_found(context: ToolContext) -> None:
    _ctx_with_masker(context, _FakeMasker(_png_bytes()))
    result = _call(
        "regenerate_mask",
        {"image_id": "test-image", "name": "current_subject_mask"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_regenerate_mask_passes_prior_bytes(context: ToolContext) -> None:
    masker = _FakeMasker(_png_bytes())
    _ctx_with_masker(context, masker)
    register_mask(
        context.workspaces["test-image"].repo,
        "current_manta_mask",
        b"\x89PNG\r\n\x1a\nPRIOR",
        generator="manual",
    )
    with patch(
        "chemigram.core.pipeline.render", side_effect=lambda **kw: _stub_render(kw["output_path"])
    ):
        result = _call(
            "regenerate_mask",
            {"image_id": "test-image", "name": "current_manta_mask", "prompt": "tighter"},
            context,
        )
    assert result.success is True
    assert masker.calls[0]["op"] == "regenerate"
    # target inferred from "current_manta_mask"
    assert masker.calls[0]["target"] == "manta"
    assert masker.calls[0]["prior_mask"] == b"\x89PNG\r\n\x1a\nPRIOR"


def test_regenerate_mask_target_uninferrable_returns_invalid_input(
    context: ToolContext,
) -> None:
    _ctx_with_masker(context, _FakeMasker(_png_bytes()))
    register_mask(
        context.workspaces["test-image"].repo,
        "weird_name",
        b"\x89PNG\r\n\x1a\n",
        generator="manual",
    )
    result = _call(
        "regenerate_mask",
        {"image_id": "test-image", "name": "weird_name"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT
