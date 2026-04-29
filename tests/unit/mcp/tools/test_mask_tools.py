"""Unit tests for chemigram.mcp.tools.masks."""

from __future__ import annotations

import io
from typing import Any

import anyio
import pytest
from PIL import Image

from chemigram.core.versioning.masks import register_mask
from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


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
def test_mask_stubs_return_slice_4(context: ToolContext, tool_name: str) -> None:
    args: dict[str, Any] = {"image_id": "test-image", "target": "subject"}
    if tool_name == "regenerate_mask":
        args["name"] = "current_subject_mask"
    result = _call(tool_name, args, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_IMPLEMENTED
    assert result.error.details.get("slice") == 4


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
