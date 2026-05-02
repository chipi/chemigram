"""Unit tests for chemigram.core.xmp.synthesize_xmp + _plugin_to_history.

Covers the 10 unit cases listed in GH issue #3's implementation plan.
The integration case (real dtstyle onto real XMP) lives in
tests/integration/core/test_synthesis_integration.py.
"""

import dataclasses

import pytest

from chemigram.core.dtstyle import DtstyleEntry, PluginEntry
from chemigram.core.xmp import (
    HistoryEntry,
    Xmp,
    _plugin_to_history,
    synthesize_xmp,
)

# Default num values differ between PluginEntry and HistoryEntry on
# purpose: PluginEntry.num=13 mimics the real Phase 0 fixtures (where
# the user-authored exposure plugin has num=13 from darktable's GUI
# capture), while HistoryEntry.num=0 mimics a baseline-XMP slot. The
# synthesizer preserves the *baseline* num on collision (ADR-051), so
# tests that assert num preservation start from baseline values.


def _make_plugin(
    operation: str = "exposure",
    multi_priority: int = 0,
    *,
    num: int = 13,
    module: int = 7,
    op_params: str = "0000003f",
    blendop_params: str = "gz_test",
    blendop_version: int = 14,
    multi_name: str = "",
    enabled: bool = True,
) -> PluginEntry:
    return PluginEntry(
        operation=operation,
        num=num,
        module=module,
        op_params=op_params,
        blendop_params=blendop_params,
        blendop_version=blendop_version,
        multi_priority=multi_priority,
        multi_name=multi_name,
        enabled=enabled,
    )


def _make_history_entry(
    operation: str = "exposure",
    multi_priority: int = 0,
    *,
    num: int = 0,
    modversion: int = 7,
    params: str = "00000040",
    iop_order: float | None = None,
    multi_name: str = "",
    blendop_params: str = "gz_baseline",
    blendop_version: int = 14,
    enabled: bool = True,
    multi_name_hand_edited: bool = False,
) -> HistoryEntry:
    return HistoryEntry(
        num=num,
        operation=operation,
        enabled=enabled,
        modversion=modversion,
        params=params,
        multi_name=multi_name,
        multi_name_hand_edited=multi_name_hand_edited,
        multi_priority=multi_priority,
        blendop_version=blendop_version,
        blendop_params=blendop_params,
        iop_order=iop_order,
    )


def _make_xmp(
    history: tuple[HistoryEntry, ...] = (),
    *,
    rating: int = 0,
    label: str = "",
    auto_presets_applied: bool = False,
    history_end: int = 0,
    iop_order_version: int = 4,
    raw_extra_fields: tuple[tuple[str, str, str], ...] = (),
) -> Xmp:
    return Xmp(
        rating=rating,
        label=label,
        auto_presets_applied=auto_presets_applied,
        history_end=history_end,
        iop_order_version=iop_order_version,
        history=history,
        raw_extra_fields=raw_extra_fields,
    )


def _entry(*plugins: PluginEntry) -> DtstyleEntry:
    return DtstyleEntry(name="test", description="", iop_list=None, plugins=plugins)


def test_plugin_to_history_field_mapping() -> None:
    plugin = _make_plugin(
        operation="temperature",
        multi_priority=2,
        num=42,
        module=4,
        op_params="abcd",
        blendop_params="gz_xyz",
        blendop_version=14,
        multi_name="custom",
        enabled=False,
    )
    history = _plugin_to_history(plugin)
    assert history.num == 42
    assert history.operation == "temperature"
    assert history.enabled is False
    assert history.modversion == 4  # plugin.module → history.modversion
    assert history.params == "abcd"  # plugin.op_params → history.params
    assert history.multi_name == "custom"
    assert history.multi_name_hand_edited is False  # default
    assert history.multi_priority == 2
    assert history.blendop_version == 14
    assert history.blendop_params == "gz_xyz"
    assert history.iop_order is None  # default; baseline preserves on synthesis


def test_empty_entries_returns_baseline_copy() -> None:
    baseline = _make_xmp(
        history=(_make_history_entry(),),
        rating=3,
        history_end=1,
    )
    result = synthesize_xmp(baseline, [])
    assert result == baseline
    assert result is not baseline


def test_collision_replaces_in_place() -> None:
    baseline_entry = _make_history_entry(params="00000040", num=8, iop_order=None)
    baseline = _make_xmp(history=(baseline_entry,), history_end=1)
    plugin = _make_plugin(op_params="0000003f")
    result = synthesize_xmp(baseline, [_entry(plugin)])
    assert len(result.history) == 1
    assert result.history[0].operation == "exposure"
    assert result.history[0].params == "0000003f"


def test_collision_preserves_num_and_iop_order() -> None:
    baseline_entry = _make_history_entry(params="00000040", num=8, iop_order=42)
    baseline = _make_xmp(history=(baseline_entry,))
    plugin = _make_plugin(op_params="0000003f", num=999)
    result = synthesize_xmp(baseline, [_entry(plugin)])
    assert result.history[0].num == 8  # preserved from baseline
    assert result.history[0].iop_order == 42  # preserved from baseline
    assert result.history[0].params == "0000003f"  # taken from plugin


def test_last_writer_wins_among_entries() -> None:
    baseline = _make_xmp(history=(_make_history_entry(params="aaaa"),))
    first = _make_plugin(op_params="bbbb")
    second = _make_plugin(op_params="cccc")
    result = synthesize_xmp(baseline, [_entry(first), _entry(second)])
    assert result.history[0].params == "cccc"


def test_different_multi_priority_path_b_appends() -> None:
    """RFC-018 v0.2: Path B (new instance at unused multi_priority)
    appends a new HistoryEntry with iop_order=None. darktable 5.4.1
    resolves pipeline order from iop_order_version + internal iop_list.
    """
    baseline = _make_history_entry(num=8, multi_priority=0, params="aaaa")
    baseline_xmp = _make_xmp(history=(baseline,), history_end=1)
    plugin = _make_plugin(multi_priority=1, op_params="bbbb")
    result = synthesize_xmp(baseline_xmp, [_entry(plugin)])
    assert len(result.history) == 2
    # Original entry preserved
    assert result.history[0].num == 8
    assert result.history[0].multi_priority == 0
    assert result.history[0].params == "aaaa"
    # New entry appended at next num
    assert result.history[1].num == 9
    assert result.history[1].multi_priority == 1
    assert result.history[1].params == "bbbb"
    assert result.history[1].iop_order is None
    # history_end recomputed
    assert result.history_end == 2


def test_path_b_new_operation_appends() -> None:
    """Path B for a module not in baseline (e.g., grain absent from a
    minimal exposure-only baseline)."""
    baseline = _make_history_entry(num=0, operation="exposure", multi_priority=0)
    baseline_xmp = _make_xmp(history=(baseline,), history_end=1)
    plugin = _make_plugin(operation="grain", multi_priority=0, op_params="cafe")
    result = synthesize_xmp(baseline_xmp, [_entry(plugin)])
    assert len(result.history) == 2
    assert result.history[1].operation == "grain"
    assert result.history[1].iop_order is None
    assert result.history_end == 2


def test_path_a_and_path_b_mixed_in_one_synthesize() -> None:
    """Multiple entries — some replace, some append — work in one call."""
    baseline = _make_xmp(
        history=(
            _make_history_entry(num=0, operation="exposure", multi_priority=0, params="0000"),
            _make_history_entry(num=1, operation="temperature", multi_priority=0, params="1111"),
        ),
        history_end=2,
    )
    replace_plugin = _make_plugin(operation="exposure", multi_priority=0, op_params="2222")
    append_plugin = _make_plugin(operation="grain", multi_priority=0, op_params="3333")
    result = synthesize_xmp(
        baseline,
        [_entry(replace_plugin), _entry(append_plugin)],
    )
    assert len(result.history) == 3
    # Path A replacement preserved num
    expo = next(e for e in result.history if e.operation == "exposure")
    assert expo.num == 0
    assert expo.params == "2222"
    # temperature untouched
    temp = next(e for e in result.history if e.operation == "temperature")
    assert temp.params == "1111"
    # Path B append
    grain = next(e for e in result.history if e.operation == "grain")
    assert grain.num == 2  # max(existing) + 1
    assert grain.iop_order is None
    assert result.history_end == 3


def test_baseline_not_mutated() -> None:
    original_history = (_make_history_entry(params="aaaa"),)
    baseline = _make_xmp(history=original_history)
    plugin = _make_plugin(op_params="bbbb")
    synthesize_xmp(baseline, [_entry(plugin)])
    assert baseline.history == original_history


def test_output_is_frozen() -> None:
    baseline = _make_xmp(history=(_make_history_entry(),))
    result = synthesize_xmp(baseline, [_entry(_make_plugin())])
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.history = ()  # type: ignore[misc]


def test_top_level_metadata_preserved() -> None:
    extras = (
        ("attr", "darktable:xmp_version", "5"),
        ("elem", "dc:creator", "<dc:creator/>"),
    )
    baseline = _make_xmp(
        history=(_make_history_entry(),),
        rating=3,
        label="finalist",
        auto_presets_applied=True,
        history_end=1,
        iop_order_version=4,
        raw_extra_fields=extras,
    )
    result = synthesize_xmp(baseline, [_entry(_make_plugin(op_params="ffff"))])
    assert result.rating == 3
    assert result.label == "finalist"
    assert result.auto_presets_applied is True
    assert result.history_end == 1
    assert result.iop_order_version == 4
    assert result.raw_extra_fields == extras


def test_multi_plugin_dtstyle_entry() -> None:
    baseline = _make_xmp(
        history=(
            _make_history_entry(operation="exposure", num=0, params="aaaa"),
            _make_history_entry(operation="temperature", num=1, params="bbbb"),
        ),
    )
    entry = _entry(
        _make_plugin(operation="exposure", op_params="cccc"),
        _make_plugin(operation="temperature", op_params="dddd"),
    )
    result = synthesize_xmp(baseline, [entry])
    by_op = {h.operation: h for h in result.history}
    assert by_op["exposure"].params == "cccc"
    assert by_op["temperature"].params == "dddd"
    assert by_op["exposure"].num == 0  # preserved
    assert by_op["temperature"].num == 1  # preserved
