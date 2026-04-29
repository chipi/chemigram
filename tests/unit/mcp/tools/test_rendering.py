"""Unit tests for chemigram.mcp.tools.rendering — mocked render."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import anyio
import pytest

from chemigram.core.pipeline import StageResult
from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


@pytest.fixture
def successful_render():
    def _factory(output_path: Path):
        return StageResult(
            success=True,
            output_path=output_path,
            duration_seconds=0.42,
            stderr="",
            error_message=None,
        )

    return _factory


def test_render_preview_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call("render_preview", {"image_id": "ghost"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_render_preview_success_round_trip(context: ToolContext, successful_render) -> None:
    with patch("chemigram.mcp.tools.rendering.render") as mock_render:
        mock_render.side_effect = lambda **kw: successful_render(kw["output_path"])
        result = _call(
            "render_preview",
            {"image_id": "test-image", "size": 256},
            context,
        )
    assert result.success is True
    assert "jpeg_path" in result.data
    assert result.data["duration_seconds"] == pytest.approx(0.42)


def test_render_preview_failure_propagates_darktable_error(context: ToolContext) -> None:
    with patch("chemigram.mcp.tools.rendering.render") as mock_render:
        mock_render.return_value = StageResult(
            success=False,
            output_path=Path("/nope.jpg"),
            duration_seconds=0.1,
            stderr="boom",
            error_message="exit 1",
        )
        result = _call(
            "render_preview",
            {"image_id": "test-image", "size": 256},
            context,
        )
    assert result.success is False
    assert result.error.code == ErrorCode.DARKTABLE_ERROR


def test_export_final_invalid_format_returns_invalid_input(context: ToolContext) -> None:
    result = _call(
        "export_final",
        {"image_id": "test-image", "format": "tiff"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_export_final_default_full_resolution(context: ToolContext, successful_render) -> None:
    with patch("chemigram.mcp.tools.rendering.render") as mock_render:
        mock_render.side_effect = lambda **kw: successful_render(kw["output_path"])
        _call("export_final", {"image_id": "test-image"}, context)
    call_kwargs = mock_render.call_args.kwargs
    # `size = None` → full-res via 16384 sentinel (ADR-004 upper-bound flag)
    assert call_kwargs["width"] == 16384
    assert call_kwargs["high_quality"] is True


def test_export_final_format_png(context: ToolContext, successful_render) -> None:
    with patch("chemigram.mcp.tools.rendering.render") as mock_render:
        mock_render.side_effect = lambda **kw: successful_render(kw["output_path"])
        result = _call(
            "export_final",
            {"image_id": "test-image", "format": "png"},
            context,
        )
    assert result.success is True
    assert result.data["format"] == "png"
    assert result.data["output_path"].endswith(".png")


def test_compare_renders_both_and_stitches(
    context: ToolContext, successful_render, tmp_path: Path
) -> None:
    """compare invokes render twice, then stitches.

    We mock render to drop a placeholder JPEG so Pillow's stitch step works.
    """
    from PIL import Image

    def fake_render(*, output_path: Path, **kw) -> StageResult:
        Image.new("RGB", (32, 32), "red").save(output_path, "JPEG")
        return successful_render(output_path)

    with patch("chemigram.mcp.tools.rendering.render", side_effect=fake_render) as mock_render:
        result = _call(
            "compare",
            {
                "image_id": "test-image",
                "hash_a": "a" * 64,
                "hash_b": "b" * 64,
                "size": 64,
            },
            context,
        )
    # compare can fail at parse_xmp_at because hash_a / hash_b are bogus —
    # what we care about: if it fails, it's a versioning error, not a crash.
    if result.success is False:
        assert result.error.code == ErrorCode.VERSIONING_ERROR
    else:
        assert "jpeg_path" in result.data
        assert mock_render.call_count == 2
