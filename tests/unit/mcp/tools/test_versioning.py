"""Unit tests for chemigram.mcp.tools.versioning."""

from __future__ import annotations

import anyio

from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool


def _call(tool_name: str, args: dict, ctx: ToolContext):
    spec = get_tool(tool_name)
    assert spec is not None
    return anyio.run(spec.handler, args, ctx)


def test_snapshot_round_trip(context: ToolContext) -> None:
    result = _call("snapshot", {"image_id": "test-image", "label": "manual"}, context)
    assert result.success is True
    assert "hash" in result.data


def test_snapshot_unknown_image_returns_not_found(context: ToolContext) -> None:
    result = _call("snapshot", {"image_id": "ghost"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.NOT_FOUND


def test_checkout_baseline_tag(context: ToolContext) -> None:
    result = _call("checkout", {"image_id": "test-image", "ref_or_hash": "baseline"}, context)
    assert result.success is True
    assert isinstance(result.data["head_hash"], str)


def test_checkout_unknown_ref_returns_versioning_error(context: ToolContext) -> None:
    result = _call(
        "checkout",
        {"image_id": "test-image", "ref_or_hash": "no-such-ref"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.VERSIONING_ERROR


def test_branch_creates_ref(context: ToolContext) -> None:
    """`branch` from HEAD — `from_` must be fully-qualified per ImageRepo.resolve_ref."""
    result = _call(
        "branch",
        {"image_id": "test-image", "name": "experiment", "from_": "HEAD"},
        context,
    )
    assert result.success is True
    assert result.data["ref"] == "refs/heads/experiment"


def test_log_returns_entries(context: ToolContext) -> None:
    result = _call("log", {"image_id": "test-image"}, context)
    assert result.success is True
    assert isinstance(result.data, list)
    assert len(result.data) >= 1
    assert any(e["op"] == "snapshot" for e in result.data)


def test_log_limit_respected(context: ToolContext) -> None:
    _call("snapshot", {"image_id": "test-image", "label": "extra"}, context)
    result = _call("log", {"image_id": "test-image", "limit": 1}, context)
    assert result.success is True
    assert len(result.data) == 1


def test_diff_returns_primitive_diffs(context: ToolContext) -> None:
    a = _call("snapshot", {"image_id": "test-image", "label": "a"}, context).data["hash"]
    apply_r = _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "expo_+0.5"},
        context,
    )
    b = apply_r.data["snapshot_hash"]
    result = _call("diff", {"image_id": "test-image", "hash_a": a, "hash_b": b}, context)
    assert result.success is True
    assert isinstance(result.data, list)


def test_tag_creates_ref(context: ToolContext) -> None:
    result = _call("tag", {"image_id": "test-image", "name": "v1-export"}, context)
    assert result.success is True
    assert result.data["ref"] == "refs/tags/v1-export"


def test_tag_re_tag_refused(context: ToolContext) -> None:
    _call("tag", {"image_id": "test-image", "name": "frozen"}, context)
    # Re-tag with same name → versioning error per ADR-019 immutability
    result = _call("tag", {"image_id": "test-image", "name": "frozen"}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.VERSIONING_ERROR


def test_tag_empty_name_invalid_input(context: ToolContext) -> None:
    result = _call("tag", {"image_id": "test-image", "name": ""}, context)
    assert result.success is False
    assert result.error.code == ErrorCode.INVALID_INPUT
