"""Unit tests for chemigram.core.propagate (RFC-037).

Validates the propagate_state core function:
- Atomic semantics: empty / oversized / unknown-source all hard-reject
- Filter discipline: framing-bound ops (drawn masks, retouch, crop, lens)
  excluded by default; opt-in via include_per_image
- exclude_ops opt-out for "everything except <X>"
- Multi-target apply: per-target snapshot; same source state propagates
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from chemigram.core.propagate import (
    FRAMING_BOUND_OPS,
    MAX_TARGETS_PER_CALL,
    PropagateError,
    filter_history_for_propagation,
)
from chemigram.core.xmp import HistoryEntry, Xmp, parse_xmp

_BASELINE_PATH = Path(__file__).resolve().parents[3] / "src/chemigram/core/_baseline_v1.xmp"


def _h(operation: str, num: int = 0, multi_priority: int = 0) -> HistoryEntry:
    """Build a minimal HistoryEntry for filter testing."""
    return HistoryEntry(
        num=num,
        operation=operation,
        enabled=True,
        modversion=1,
        params="00",
        multi_name="",
        multi_name_hand_edited=False,
        multi_priority=multi_priority,
        blendop_version=14,
        blendop_params="",
        iop_order=None,
    )


# ---------- filter_history_for_propagation -------------------------------


def test_filter_includes_all_non_framing_ops_by_default() -> None:
    history = (
        _h("temperature"),
        _h("exposure", num=1),
        _h("sigmoid", num=2),
        _h("colorequal", num=3),
    )
    result = filter_history_for_propagation(history)
    assert len(result) == 4


def test_filter_excludes_framing_bound_ops_by_default() -> None:
    history = (
        _h("temperature"),
        _h("crop", num=1),
        _h("retouch", num=2),
        _h("ashift", num=3),
        _h("lens", num=4),
        _h("exposure", num=5),
    )
    result = filter_history_for_propagation(history)
    surviving = {h.operation for h in result}
    assert surviving == {"temperature", "exposure"}
    for excluded in FRAMING_BOUND_OPS:
        assert excluded not in surviving


def test_filter_includes_per_image_when_opted_in() -> None:
    history = (
        _h("temperature"),
        _h("crop", num=1),
        _h("retouch", num=2),
    )
    result = filter_history_for_propagation(history, include_per_image=True)
    assert len(result) == 3


def test_filter_respects_exclude_ops() -> None:
    history = (
        _h("temperature"),
        _h("exposure", num=1),
        _h("sigmoid", num=2),
    )
    result = filter_history_for_propagation(history, exclude_ops=["exposure"])
    surviving = {h.operation for h in result}
    assert surviving == {"temperature", "sigmoid"}


def test_filter_combines_exclude_ops_and_framing_exclusion() -> None:
    history = (
        _h("temperature"),
        _h("exposure", num=1),
        _h("crop", num=2),
        _h("sigmoid", num=3),
    )
    result = filter_history_for_propagation(
        history, exclude_ops=["exposure"], include_per_image=False
    )
    assert {h.operation for h in result} == {"temperature", "sigmoid"}


def test_filter_empty_history_returns_empty() -> None:
    assert filter_history_for_propagation(()) == ()


def test_filter_preserves_order() -> None:
    history = (
        _h("sigmoid", num=0),
        _h("temperature", num=1),
        _h("exposure", num=2),
    )
    result = filter_history_for_propagation(history)
    assert [h.operation for h in result] == ["sigmoid", "temperature", "exposure"]


# ---------- propagate_state validation -----------------------------------


def _make_workspace_mock(image_id: str, xmp: Xmp | None = None) -> MagicMock:
    """Build a minimal Workspace mock for validation tests."""
    ws = MagicMock()
    ws.image_id = image_id
    ws.root = Path(f"/tmp/_test_workspace_{image_id}")  # noqa: S108 — mock; never written
    ws.repo = MagicMock()
    return ws


def test_empty_targets_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from chemigram.core.propagate import propagate_state

    src = _make_workspace_mock("source")
    with pytest.raises(PropagateError, match="target_workspaces is empty"):
        propagate_state(src, [])


def test_too_many_targets_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from chemigram.core.propagate import propagate_state

    src = _make_workspace_mock("source")
    targets = [_make_workspace_mock(f"t{i}") for i in range(MAX_TARGETS_PER_CALL + 1)]
    with pytest.raises(PropagateError, match="exceeds soft cap"):
        propagate_state(src, targets)


def test_target_same_as_source_raises() -> None:
    from chemigram.core.propagate import propagate_state

    src = _make_workspace_mock("same_id")
    target = _make_workspace_mock("same_id")
    with pytest.raises(PropagateError, match="propagating to oneself"):
        propagate_state(src, [target])


def test_duplicate_target_ids_raises() -> None:
    from chemigram.core.propagate import propagate_state

    src = _make_workspace_mock("source")
    targets = [_make_workspace_mock("dup"), _make_workspace_mock("dup")]
    with pytest.raises(PropagateError, match="duplicate target image_id"):
        propagate_state(src, targets)


def test_source_no_current_xmp_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """If source has no XMP, propagation can't proceed (no anchor edit)."""
    from chemigram.core import propagate as propagate_mod

    monkeypatch.setattr(propagate_mod, "current_xmp", lambda ws: None, raising=False)
    # The above patches at module level; current_xmp is imported inside
    # propagate_state, so we patch the underlying helpers module instead.
    from chemigram.core import helpers

    monkeypatch.setattr(helpers, "current_xmp", lambda ws: None)

    src = _make_workspace_mock("source")
    target = _make_workspace_mock("t1")
    from chemigram.core.propagate import propagate_state

    with pytest.raises(PropagateError, match="has no current XMP"):
        propagate_state(src, [target])


def test_filter_produces_empty_set_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """If exclude_ops + framing-bound exclusion drops all entries, raise."""
    from chemigram.core import helpers

    template = parse_xmp(_BASELINE_PATH)
    # Source XMP with only crop (framing-bound; auto-excluded)
    src_xmp = dataclasses.replace(template, history=(_h("crop"),))
    target_xmp = dataclasses.replace(template, history=(_h("temperature"),))

    monkeypatch.setattr(
        helpers,
        "current_xmp",
        lambda ws: src_xmp if ws.image_id == "source" else target_xmp,
    )
    src = _make_workspace_mock("source")
    target = _make_workspace_mock("t1")
    from chemigram.core.propagate import propagate_state

    with pytest.raises(PropagateError, match="empty op set"):
        propagate_state(src, [target])
