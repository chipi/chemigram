"""Unit tests for chemigram.core.versioning.repo.

Covers the 24 cases listed in GH issue #7's implementation plan.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from chemigram.core.versioning.repo import (
    ImageRepo,
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
)


def _init(tmp_path: Path) -> ImageRepo:
    return ImageRepo.init(tmp_path / "repo")


# ---- init / layout ----------------------------------------------------------


def test_init_creates_layout(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    assert (repo.root / "objects").is_dir()
    assert (repo.root / "refs" / "heads").is_dir()
    assert (repo.root / "refs" / "tags").is_dir()
    assert (repo.root / "HEAD").is_file()
    assert (repo.root / "log.jsonl").is_file()


def test_init_is_idempotent(tmp_path: Path) -> None:
    a = _init(tmp_path)
    b = ImageRepo.init(a.root)
    assert a.root == b.root


def test_init_default_head_points_at_main(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/main"


def test_constructor_rejects_invalid_root(tmp_path: Path) -> None:
    bare = tmp_path / "not_a_repo"
    bare.mkdir()
    with pytest.raises(RepoError, match="not an image repo"):
        ImageRepo(bare)


def test_constructor_rejects_nonexistent_root(tmp_path: Path) -> None:
    with pytest.raises(RepoError, match="not a directory"):
        ImageRepo(tmp_path / "does_not_exist")


# ---- objects ----------------------------------------------------------------


def test_write_object_returns_lowercase_hex_hash(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = repo.write_object(b"hello")
    assert len(h) == 64
    assert h == h.lower()
    assert all(c in "0123456789abcdef" for c in h)


def test_write_object_sharded_path(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = repo.write_object(b"hello")
    expected = repo.objects_dir / h[:2] / h[2:]
    assert expected.is_file()


def test_write_object_idempotent(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h1 = repo.write_object(b"hello")
    h2 = repo.write_object(b"hello")
    assert h1 == h2


def test_read_object_round_trip(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = repo.write_object(b"some bytes")
    assert repo.read_object(h) == b"some bytes"


def test_read_object_missing_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    nope = "0" * 64
    with pytest.raises(ObjectNotFoundError):
        repo.read_object(nope)


def test_has_object_true_false(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = repo.write_object(b"x")
    assert repo.has_object(h) is True
    assert repo.has_object("0" * 64) is False


def test_invalid_hash_format_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    with pytest.raises(RepoError, match="invalid object hash"):
        repo.read_object("not-a-hash")


# ---- refs -------------------------------------------------------------------


def test_write_ref_simple_hash(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = "a" * 64
    repo.write_ref("refs/heads/main", h)
    assert repo.read_ref_raw("refs/heads/main") == h


def test_write_ref_symbolic(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    repo.write_ref("HEAD", "ref: refs/heads/feature")
    assert repo.read_ref_raw("HEAD") == "ref: refs/heads/feature"


def test_write_ref_invalid_name_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    with pytest.raises(RepoError, match="must start with"):
        repo.write_ref("notarefname", "deadbeef")


def test_resolve_ref_simple_hash(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = "b" * 64
    repo.write_ref("refs/heads/main", h)
    assert repo.resolve_ref("refs/heads/main") == h


def test_resolve_ref_one_indirection(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = "c" * 64
    repo.write_ref("refs/heads/main", h)
    # HEAD is symbolic by default (init writes "ref: refs/heads/main")
    assert repo.resolve_ref("HEAD") == h


def test_resolve_ref_unknown_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    with pytest.raises(RefNotFoundError):
        repo.resolve_ref("refs/heads/nonexistent")


def test_resolve_ref_circular_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    repo.write_ref("refs/heads/a", "ref: refs/heads/b")
    repo.write_ref("refs/heads/b", "ref: refs/heads/a")
    with pytest.raises(RepoError, match="circular"):
        repo.resolve_ref("refs/heads/a")


def test_resolve_ref_max_depth_exceeded(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    # Build a chain longer than the default max_depth (8)
    for i in range(10):
        repo.write_ref(f"refs/heads/c{i}", f"ref: refs/heads/c{i + 1}")
    with pytest.raises(RepoError):
        repo.resolve_ref("refs/heads/c0")


def test_list_refs_branches_only(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = "d" * 64
    repo.write_ref("refs/heads/main", h)
    repo.write_ref("refs/heads/feature", h)
    repo.write_ref("refs/tags/v1", h)
    branches = repo.list_refs("refs/heads/")
    assert {e.name for e in branches} == {"refs/heads/main", "refs/heads/feature"}
    assert all(e.target == h for e in branches)


def test_list_refs_resolved(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = "e" * 64
    repo.write_ref("refs/heads/main", h)
    refs = repo.list_refs()
    targets = {e.target for e in refs}
    # All targets should be resolved to concrete hashes (no 'ref: ...')
    for target in targets:
        assert len(target) == 64


def test_delete_ref(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    h = "f" * 64
    repo.write_ref("refs/heads/feature", h)
    repo.delete_ref("refs/heads/feature")
    with pytest.raises(RefNotFoundError):
        repo.resolve_ref("refs/heads/feature")


def test_delete_head_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    with pytest.raises(RepoError, match="HEAD cannot be deleted"):
        repo.delete_ref("HEAD")


def test_delete_unknown_ref_raises(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    with pytest.raises(RefNotFoundError):
        repo.delete_ref("refs/heads/nonexistent")


# ---- log --------------------------------------------------------------------


def test_append_log_adds_timestamp(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    repo.append_log({"op": "snapshot", "hash": "a" * 64})
    entries = repo.read_log()
    assert len(entries) == 1
    assert "timestamp" in entries[0]
    # ISO-8601 UTC format check
    assert entries[0]["timestamp"].endswith("+00:00")


def test_append_log_preserves_caller_timestamp(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    ts = "2026-04-29T12:00:00+00:00"
    repo.append_log({"op": "snapshot", "timestamp": ts})
    assert repo.read_log()[0]["timestamp"] == ts


def test_read_log_parses_jsonl(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    repo.append_log({"op": "snapshot", "hash": "a" * 64})
    repo.append_log({"op": "branch", "name": "feature"})
    entries = repo.read_log()
    assert len(entries) == 2
    assert entries[0]["op"] == "snapshot"
    assert entries[1]["op"] == "branch"


def test_read_log_empty_file(tmp_path: Path) -> None:
    repo = _init(tmp_path)
    assert repo.read_log() == []
