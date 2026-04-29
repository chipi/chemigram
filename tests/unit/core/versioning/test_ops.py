"""Unit tests for chemigram.core.versioning.ops."""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from chemigram.core.versioning import ImageRepo, xmp_hash
from chemigram.core.versioning.ops import (
    LogEntry,
    PrimitiveDiff,
    VersioningError,
    branch,
    checkout,
    diff,
    log,
    reset_to,
    snapshot,
    tag,
)
from chemigram.core.xmp import HistoryEntry, Xmp


def _repo(tmp_path: Path) -> ImageRepo:
    return ImageRepo.init(tmp_path / "repo")


def _xmp(history: tuple[HistoryEntry, ...] = (), **kw: object) -> Xmp:
    defaults: dict[str, object] = dict(
        rating=0,
        label="",
        auto_presets_applied=False,
        history_end=len(history),
        iop_order_version=4,
        history=history,
    )
    defaults.update(kw)
    return Xmp(**defaults)  # type: ignore[arg-type]


def _entry(
    operation: str = "exposure",
    multi_priority: int = 0,
    params: str = "00000040",
) -> HistoryEntry:
    return HistoryEntry(
        num=0,
        operation=operation,
        enabled=True,
        modversion=7,
        params=params,
        multi_name="",
        multi_name_hand_edited=False,
        multi_priority=multi_priority,
        blendop_version=14,
        blendop_params="gz_test",
    )


# ---- snapshot ---------------------------------------------------------------


def test_snapshot_writes_object_and_advances_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    assert repo.has_object(h)
    assert repo.resolve_ref("refs/heads/main") == h


def test_snapshot_idempotent_for_same_xmp(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h1 = snapshot(repo, _xmp())
    h2 = snapshot(repo, _xmp())
    assert h1 == h2
    assert repo.resolve_ref("refs/heads/main") == h1


def test_snapshot_from_detached_head_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    repo.write_ref("HEAD", h)  # detach
    with pytest.raises(VersioningError, match="detached HEAD"):
        snapshot(repo, _xmp(rating=1))


def test_snapshot_logs_entry_with_label_and_metadata(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp(), label="initial", metadata={"author": "marko"})
    entries = log(repo)
    assert entries[0].op == "snapshot"
    assert entries[0].hash == h
    assert entries[0].label == "initial"
    assert entries[0].metadata == {"author": "marko"}


# ---- checkout ---------------------------------------------------------------


def test_checkout_branch_sets_symbolic_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    branch(repo, "feature")
    checkout(repo, "feature")
    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/feature"


def test_checkout_hash_sets_detached_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    checkout(repo, h)
    assert repo.read_ref_raw("HEAD") == h


def test_checkout_tag_sets_detached_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    tag(repo, "v1")
    checkout(repo, "v1")
    assert repo.read_ref_raw("HEAD") == h


def test_checkout_unknown_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(VersioningError, match="unknown ref or hash"):
        checkout(repo, "nonexistent")


def test_checkout_returns_parsed_xmp(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    original = _xmp(rating=3)
    h = snapshot(repo, original)
    checked_out = checkout(repo, h)
    assert checked_out.rating == 3
    assert xmp_hash(checked_out) == xmp_hash(original)


# ---- branch -----------------------------------------------------------------


def test_branch_creates_ref(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    ref_name = branch(repo, "feature")
    assert ref_name == "refs/heads/feature"
    assert repo.has_object(repo.resolve_ref(ref_name))


def test_branch_name_exists_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    branch(repo, "feature")
    with pytest.raises(VersioningError, match="already exists"):
        branch(repo, "feature")


def test_branch_from_unknown_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(VersioningError, match=r"unknown ref or hash|cannot resolve"):
        branch(repo, "feature", from_="nonexistent")


def test_branch_from_full_branch_ref(tmp_path: Path) -> None:
    """branch() accepts ``refs/heads/X`` (full ref form), not just ``X``."""
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    branch(repo, "from-full-ref", from_="refs/heads/main")
    assert repo.resolve_ref("refs/heads/from-full-ref") == h


def test_branch_from_full_tag_ref(tmp_path: Path) -> None:
    """branch() accepts ``refs/tags/X`` (full ref form), not just ``X``."""
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    tag(repo, "v1")
    branch(repo, "from-full-tag", from_="refs/tags/v1")
    assert repo.resolve_ref("refs/heads/from-full-tag") == h


def test_branch_from_bare_tag_name(tmp_path: Path) -> None:
    """Symmetry with checkout: bare tag name resolves correctly."""
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    tag(repo, "baseline")
    branch(repo, "exp", from_="baseline")
    assert repo.resolve_ref("refs/heads/exp") == h


def test_branch_from_bare_branch_name(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    branch(repo, "exp", from_="main")
    assert repo.resolve_ref("refs/heads/exp") == h


def test_branch_from_hash_directly(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    branch(repo, "from-hash", from_=h)
    assert repo.resolve_ref("refs/heads/from-hash") == h


def test_checkout_to_full_branch_ref(tmp_path: Path) -> None:
    """Symmetry: checkout accepts ``refs/heads/X`` directly."""
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    checkout(repo, "refs/heads/main")
    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/main"


def test_checkout_to_full_tag_ref(tmp_path: Path) -> None:
    """Symmetry: checkout accepts ``refs/tags/X`` directly."""
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    tag(repo, "v1")
    checkout(repo, "refs/tags/v1")
    # Tag checkout detaches HEAD per ADR-019
    assert repo.read_ref_raw("HEAD") == h


def test_checkout_full_ref_unknown_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    with pytest.raises(VersioningError):
        checkout(repo, "refs/heads/no-such-branch")


def test_branch_does_not_switch_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    head_before = repo.read_ref_raw("HEAD")
    branch(repo, "feature")
    assert repo.read_ref_raw("HEAD") == head_before


# ---- log --------------------------------------------------------------------


def test_log_filters_by_ref(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    branch(repo, "feature")
    feature_only = log(repo, ref="refs/heads/feature")
    assert all(e.ref == "refs/heads/feature" for e in feature_only)


def test_log_limits(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    for i in range(5):
        snapshot(repo, _xmp(rating=i))
    entries = log(repo, limit=3)
    assert len(entries) == 3


def test_log_newest_first(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp(rating=0), label="first")
    snapshot(repo, _xmp(rating=1), label="second")
    entries = log(repo)
    assert entries[0].label == "second"
    assert entries[1].label == "first"


# ---- diff -------------------------------------------------------------------


def test_diff_added_removed_changed(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    a = _xmp(history=(_entry("exposure"), _entry("temperature", params="aa")))
    b = _xmp(
        history=(
            _entry("exposure", params="changed"),
            _entry("filmic"),
        )
    )
    h_a = snapshot(repo, a)
    snapshot(repo, b)
    h_b = repo.resolve_ref("refs/heads/main")
    deltas = diff(repo, h_a, h_b)
    by_op = {d.operation: d for d in deltas}
    assert by_op["exposure"].kind == "changed"
    assert by_op["temperature"].kind == "removed"
    assert by_op["filmic"].kind == "added"


def test_diff_empty_when_xmps_equal(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp(history=(_entry(),)))
    assert diff(repo, h, h) == []


def test_diff_ignores_top_level_metadata(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h_a = snapshot(repo, _xmp(rating=0, history=(_entry(),)))
    snapshot(repo, _xmp(rating=5, history=(_entry(),)))
    h_b = repo.resolve_ref("refs/heads/main")
    assert diff(repo, h_a, h_b) == []


def test_diff_sorted_stable(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    a = _xmp(
        history=(
            _entry("exposure", multi_priority=0),
            _entry("exposure", multi_priority=1),
            _entry("temperature", multi_priority=0),
        )
    )
    b = _xmp(
        history=(
            _entry("exposure", multi_priority=0, params="x"),
            _entry("temperature", multi_priority=0, params="y"),
        )
    )
    h_a = snapshot(repo, a)
    snapshot(repo, b)
    h_b = repo.resolve_ref("refs/heads/main")
    d1 = diff(repo, h_a, h_b)
    d2 = diff(repo, h_a, h_b)
    assert d1 == d2  # deterministic


# ---- tag --------------------------------------------------------------------


def test_tag_creates_immutable_ref(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    tag_ref = tag(repo, "v1")
    assert tag_ref == "refs/tags/v1"
    with pytest.raises(VersioningError, match="immutable"):
        tag(repo, "v1")


def test_tag_default_is_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h = snapshot(repo, _xmp())
    tag(repo, "v1")
    assert repo.resolve_ref("refs/tags/v1") == h


def test_tag_with_explicit_hash(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h1 = snapshot(repo, _xmp(rating=0))
    snapshot(repo, _xmp(rating=1))
    tag(repo, "first", hash_=h1)
    assert repo.resolve_ref("refs/tags/first") == h1


def test_tag_unknown_hash_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(VersioningError):
        tag(repo, "v1", hash_="0" * 64)


# ---- reset_to ---------------------------------------------------------------
#
# Per ADR-062: rewinds the current branch to the target hash and ensures
# HEAD is symbolic on a branch. ``apply_primitive`` (i.e. snapshot) must
# work immediately after.


def test_reset_to_tag_attaches_head_and_moves_branch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h_baseline = snapshot(repo, _xmp(), label="baseline")
    tag(repo, "baseline")
    h_after = snapshot(repo, _xmp(rating=1), label="agent move")
    assert repo.resolve_ref("refs/heads/main") == h_after  # tip advanced

    reset_to(repo, "baseline")

    # Branch tip rewound, HEAD still symbolic on main.
    assert repo.resolve_ref("refs/heads/main") == h_baseline
    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/main"


def test_reset_to_re_attaches_detached_head(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h_baseline = snapshot(repo, _xmp())
    tag(repo, "baseline")
    repo.write_ref("HEAD", h_baseline)  # detach

    reset_to(repo, "baseline")

    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/main"
    assert repo.resolve_ref("refs/heads/main") == h_baseline


def test_reset_to_enables_subsequent_snapshot(tmp_path: Path) -> None:
    """The whole point of ADR-062: reset → apply must work."""
    repo = _repo(tmp_path)
    snapshot(repo, _xmp(), label="baseline")
    tag(repo, "baseline")
    snapshot(repo, _xmp(rating=1))
    reset_to(repo, "baseline")
    h_new = snapshot(repo, _xmp(rating=2))  # would raise pre-fix
    assert repo.resolve_ref("refs/heads/main") == h_new


def test_reset_to_logs_entry_with_prior_hash(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    h_baseline = snapshot(repo, _xmp(), label="baseline")
    tag(repo, "baseline")
    h_prior = snapshot(repo, _xmp(rating=1))
    reset_to(repo, "baseline")
    entries = log(repo)
    reset_entries = [e for e in entries if e.op == "reset"]
    assert len(reset_entries) == 1
    e = reset_entries[0]
    assert e.hash == h_baseline
    assert e.ref == "refs/heads/main"
    assert e.parent == h_prior
    assert e.metadata.get("prior_hash") == h_prior
    assert e.metadata.get("target") == "baseline"


def test_reset_to_rejects_head_target(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    with pytest.raises(VersioningError, match="HEAD"):
        reset_to(repo, "HEAD")


def test_reset_to_unknown_target_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    snapshot(repo, _xmp())
    with pytest.raises(VersioningError, match="unknown"):
        reset_to(repo, "no-such-ref")


def test_reset_to_resets_current_branch_not_main(tmp_path: Path) -> None:
    """If HEAD is on `experiment-1`, reset rewinds experiment-1 — not main."""
    repo = _repo(tmp_path)
    h_baseline = snapshot(repo, _xmp(), label="baseline")
    tag(repo, "baseline")
    branch(repo, "experiment-1", from_="refs/tags/baseline")
    checkout(repo, "experiment-1")
    snapshot(repo, _xmp(rating=1))  # advance experiment-1

    reset_to(repo, "baseline")

    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/experiment-1"
    assert repo.resolve_ref("refs/heads/experiment-1") == h_baseline
    # main was untouched (still pointing to baseline from initial snapshot)
    assert repo.resolve_ref("refs/heads/main") == h_baseline


def test_log_entry_dataclass_shape() -> None:
    """LogEntry is a frozen dataclass with sensible defaults."""
    from datetime import UTC, datetime

    entry = LogEntry(timestamp=datetime.now(UTC), op="snapshot")
    assert entry.hash is None
    assert entry.ref is None
    assert entry.parent is None
    assert entry.label is None
    assert entry.metadata == {}
    # Frozen — should refuse mutation
    with pytest.raises(dataclasses.FrozenInstanceError):
        entry.op = "checkout"  # type: ignore[misc]


def test_primitive_diff_dataclass_shape() -> None:
    d = PrimitiveDiff("exposure", 0, "added", None, "ff")
    assert d.kind == "added"
