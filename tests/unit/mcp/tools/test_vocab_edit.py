"""Unit tests for chemigram.mcp.tools.vocab_edit."""

from __future__ import annotations

import anyio

from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


# --- list_vocabulary ----------------------------------------------------


def test_list_vocabulary_unfiltered(context: ToolContext) -> None:
    result = _call("list_vocabulary", {}, context)
    assert result.success is True
    names = {e["name"] for e in result.data}
    assert names == {
        "canon_eos_r5_baseline_l1",
        "look_neutral",
        "expo_+0.5",
        "expo_-0.5",
        "wb_warm_subtle",
    }


def test_list_vocabulary_by_layer(context: ToolContext) -> None:
    result = _call("list_vocabulary", {"layer": "L3"}, context)
    assert result.success is True
    assert {e["name"] for e in result.data} == {
        "expo_+0.5",
        "expo_-0.5",
        "wb_warm_subtle",
    }


def test_list_vocabulary_by_tags_or(context: ToolContext) -> None:
    result = _call("list_vocabulary", {"tags": ["lift", "warm"]}, context)
    assert result.success is True
    assert {e["name"] for e in result.data} == {"expo_+0.5", "wb_warm_subtle"}


def test_list_vocabulary_invalid_layer(context: ToolContext) -> None:
    # Bypass schema check by hitting the handler directly with bad value.
    result = _call("list_vocabulary", {"layer": "L4"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT


# --- get_state ----------------------------------------------------------


def test_get_state_returns_summary_shape(context: ToolContext) -> None:
    result = _call("get_state", {"image_id": "test-image"}, context)
    assert result.success is True
    assert set(result.data.keys()) >= {
        "head_hash",
        "entry_count",
        "enabled_count",
        "layers_present",
    }
    assert isinstance(result.data["head_hash"], str)
    assert result.data["entry_count"] > 0


def test_get_state_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call("get_state", {"image_id": "ghost"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


# --- apply_primitive ---------------------------------------------------


def test_apply_primitive_round_trip(context: ToolContext) -> None:
    result = _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "expo_+0.5"},
        context,
    )
    assert result.success is True
    assert "snapshot_hash" in result.data
    assert result.data["state_after"]["entry_count"] > 0


def test_apply_primitive_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call(
        "apply_primitive",
        {"image_id": "nope", "primitive_name": "expo_+0.5"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_apply_primitive_unknown_primitive_returns_not_found(
    context: ToolContext,
) -> None:
    result = _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "unknown_primitive"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_apply_primitive_with_mask_override_says_slice_4(context: ToolContext) -> None:
    result = _call(
        "apply_primitive",
        {
            "image_id": "test-image",
            "primitive_name": "expo_+0.5",
            "mask_override": "subject_mask",
        },
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_IMPLEMENTED
    assert result.error.details.get("slice") == 4


# --- remove_module ------------------------------------------------------


def test_remove_module_strips_entries(context: ToolContext) -> None:
    # Apply something first so we have an entry to remove.
    _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "expo_+0.5"},
        context,
    )
    before = _call("get_state", {"image_id": "test-image"}, context).data
    result = _call(
        "remove_module",
        {"image_id": "test-image", "module_name": "exposure"},
        context,
    )
    assert result.success is True
    assert result.data["state_after"]["entry_count"] < before["entry_count"]


def test_remove_module_unknown_returns_not_found(context: ToolContext) -> None:
    result = _call(
        "remove_module",
        {"image_id": "test-image", "module_name": "no_such_module"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


# --- reset --------------------------------------------------------------


def test_reset_returns_baseline_state(context: ToolContext) -> None:
    # Apply, then reset — the result should match the original baseline.
    baseline = _call("get_state", {"image_id": "test-image"}, context).data
    _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "expo_+0.5"},
        context,
    )
    result = _call("reset", {"image_id": "test-image"}, context)
    assert result.success is True
    assert result.data["head_hash"] == baseline["head_hash"]


def test_reset_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call("reset", {"image_id": "ghost"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND
