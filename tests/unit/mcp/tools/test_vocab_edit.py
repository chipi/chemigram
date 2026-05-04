"""Unit tests for chemigram.mcp.tools.vocab_edit."""

from __future__ import annotations

from pathlib import Path

import anyio
import pytest

from chemigram.mcp.errors import ErrorCode
from chemigram.mcp.registry import ToolContext, get_tool

_REPO_ROOT = Path(__file__).resolve().parents[4]
_EXPRESSIVE_BASELINE = _REPO_ROOT / "vocabulary" / "packs" / "expressive-baseline"

# The four mask-bound entries shipped in expressive-baseline as of v1.4.0
# (ADR-076). Each exercises a distinct dt_form serialization in dt_serialize.
_SHIPPED_MASK_BOUND_ENTRIES = (
    "gradient_top_dampen_highlights",
    "gradient_bottom_lift_shadows",
    "radial_subject_lift",
    "rectangle_subject_band_dim",
)


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


@pytest.fixture
def context_with_shipped_masks(context: ToolContext) -> ToolContext:
    """Augment the test-pack context with the four shipped mask-bound
    entries from expressive-baseline. Lets dispatch tests exercise the
    real specs we ship, not synthetic stand-ins.
    """
    from chemigram.core.vocab import VocabularyIndex

    eb = VocabularyIndex(_EXPRESSIVE_BASELINE)
    for name in _SHIPPED_MASK_BOUND_ENTRIES:
        entry = eb.lookup_by_name(name)
        assert entry is not None, (
            f"shipped mask-bound entry {name!r} missing from expressive-baseline; "
            f"_SHIPPED_MASK_BOUND_ENTRIES is out of date"
        )
        context.vocabulary._by_name[name] = entry
    return context


@pytest.mark.parametrize("entry_name", _SHIPPED_MASK_BOUND_ENTRIES)
def test_apply_primitive_routes_through_drawn_mask_for_shipped_entry(
    context_with_shipped_masks: ToolContext,
    entry_name: str,
) -> None:
    """Each shipped mask-bound entry routes through ``apply_with_drawn_mask``
    and ends up with ``masks_history`` injected into the snapshotted XMP.
    Parity coverage across all four dt_form variants we ship (two gradient,
    one ellipse, one rectangle).

    The e2e suite (``tests/e2e/expressive/test_mask_bound_entries.py``)
    validates that the binding actually shapes pixels under real darktable
    via the noise-floor digital-reference protocol. This dispatch test
    proves the apply-path routing + serialization layer is sound for each
    specific spec we ship — without requiring darktable in the loop.
    """
    context = context_with_shipped_masks
    result = _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": entry_name},
        context,
    )
    assert result.success is True, f"{entry_name}: {result.error}"
    snapshot_hash = result.data["snapshot_hash"]
    raw = context.workspaces["test-image"].repo.read_object(snapshot_hash)
    assert b"masks_history" in raw, (
        f"{entry_name}: drawn-mask path should inject darktable:masks_history "
        f"into the XMP (ADR-076)"
    )


def test_apply_primitive_with_invalid_mask_spec_returns_masking_error(
    context: ToolContext,
) -> None:
    """Malformed mask_spec → MASKING_ERROR (not a stack trace through MCP)."""
    from dataclasses import replace as dc_replace

    base = context.vocabulary.lookup_by_name("expo_+0.5")
    assert base is not None
    bad = dc_replace(
        base,
        name="expo_bad_mask_test",
        mask_spec={"dt_form": "not_a_real_form", "dt_params": {}},
    )
    context.vocabulary._by_name["expo_bad_mask_test"] = bad

    result = _call(
        "apply_primitive",
        {"image_id": "test-image", "primitive_name": "expo_bad_mask_test"},
        context,
    )
    assert result.success is False
    assert result.error.code == ErrorCode.MASKING_ERROR


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
