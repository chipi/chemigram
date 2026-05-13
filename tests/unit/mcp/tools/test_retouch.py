"""Unit tests for chemigram.mcp.tools.retouch — `apply_spot` MCP wrapper.

Catches wire-shape bugs in the MCP wrapper (kind validation, coord
range, source-coord requirement for clone, snapshot label format) that
the integration test only covers as a single happy-path round-trip.
RFC-025 / ADR-087 closes the wire spec; this file locks the input
schema's behavioral contract.
"""

from __future__ import annotations

import anyio

from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


def test_apply_spot_heal_succeeds(context: ToolContext) -> None:
    """The minimal heal call: image_id + kind + coords + radius."""
    result = _call(
        "apply_spot",
        {
            "image_id": "test-image",
            "kind": "heal",
            "x": 0.5,
            "y": 0.5,
            "radius": 0.05,
        },
        context,
    )
    assert result.success is True, result.error
    assert result.data["kind"] == "heal"
    assert result.data["coordinates"] == {"x": 0.5, "y": 0.5, "radius": 0.05}
    assert "snapshot_hash" in result.data
    assert "state_after" in result.data


def test_apply_spot_clone_with_source(context: ToolContext) -> None:
    """Clone needs source_x/source_y in addition to target coords."""
    result = _call(
        "apply_spot",
        {
            "image_id": "test-image",
            "kind": "clone",
            "x": 0.5,
            "y": 0.5,
            "radius": 0.05,
            "source_x": 0.7,
            "source_y": 0.7,
        },
        context,
    )
    assert result.success is True, result.error


def test_apply_spot_unknown_image_returns_not_found(context: ToolContext) -> None:
    """Missing workspace surfaces NOT_FOUND, not INTERNAL_ERROR."""
    result = _call(
        "apply_spot",
        {
            "image_id": "no-such-image",
            "kind": "heal",
            "x": 0.5,
            "y": 0.5,
            "radius": 0.05,
        },
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_apply_spot_invalid_kind_returns_invalid_input(context: ToolContext) -> None:
    """`kind` must be 'heal' or 'clone'; other values fail INVALID_INPUT."""
    result = _call(
        "apply_spot",
        {
            "image_id": "test-image",
            "kind": "bogus",
            "x": 0.5,
            "y": 0.5,
            "radius": 0.05,
        },
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


def test_apply_spot_with_explicit_opacity_and_border(context: ToolContext) -> None:
    """opacity + border are optional kwargs with defaults."""
    result = _call(
        "apply_spot",
        {
            "image_id": "test-image",
            "kind": "heal",
            "x": 0.3,
            "y": 0.3,
            "radius": 0.04,
            "opacity": 75.0,
            "border": 0.05,
        },
        context,
    )
    assert result.success is True
