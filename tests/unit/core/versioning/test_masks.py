"""Unit tests for chemigram.core.versioning.masks."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import pytest

from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.masks import (
    PNG_MAGIC,
    InvalidMaskError,
    MaskEntry,
    MaskError,
    MaskNotFoundError,
    get_mask,
    invalidate_mask,
    list_masks,
    register_mask,
    tag_mask,
)


def make_test_png(width: int = 16, height: int = 16, value: int = 128) -> bytes:
    """Hand-rolled tiny 8-bit-grayscale PNG. No Pillow dep.

    Real PNG (PIL/exiftool can read it); ~80 bytes for 16x16.
    """

    def _chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes([value] * width) for _ in range(height))
    idat = zlib.compress(raw)
    return sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _repo(tmp_path: Path) -> ImageRepo:
    return ImageRepo.init(tmp_path / "repo")


def test_register_mask_writes_object_and_registry(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    png = make_test_png()
    entry = register_mask(repo, "current_subject_mask", png, generator="coarse_agent")
    assert isinstance(entry, MaskEntry)
    assert entry.name == "current_subject_mask"
    assert repo.has_object(entry.hash)
    assert (repo.root / "masks" / "registry.json").is_file()


def test_register_mask_invalid_bytes_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(InvalidMaskError, match="magic"):
        register_mask(repo, "bad", b"not a png", generator="manual")


def test_register_mask_too_short_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(InvalidMaskError, match="too short"):
        register_mask(repo, "tiny", b"\x89PN", generator="manual")


def test_register_mask_overwrites_same_name(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    png_a = make_test_png(value=100)
    png_b = make_test_png(value=200)
    a = register_mask(repo, "current_subject_mask", png_a, generator="coarse_agent")
    b = register_mask(repo, "current_subject_mask", png_b, generator="coarse_agent")
    assert a.hash != b.hash
    # registry now points at b
    fetched, _ = get_mask(repo, "current_subject_mask")
    assert fetched.hash == b.hash


def test_register_mask_dedup_via_object_store(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    png = make_test_png()
    a = register_mask(repo, "name_a", png, generator="manual")
    b = register_mask(repo, "name_b", png, generator="manual")
    assert a.hash == b.hash  # same content, same object


def test_get_mask_returns_entry_and_bytes(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    png = make_test_png()
    register_mask(repo, "subject", png, generator="coarse_agent", prompt="the manta")
    entry, fetched_png = get_mask(repo, "subject")
    assert entry.prompt == "the manta"
    assert fetched_png == png
    assert fetched_png.startswith(PNG_MAGIC)


def test_get_mask_unknown_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(MaskNotFoundError):
        get_mask(repo, "nonexistent")


def test_get_mask_orphan_object_raises(tmp_path: Path) -> None:
    """Registry references a hash that's no longer in objects/."""
    repo = _repo(tmp_path)
    register_mask(repo, "subject", make_test_png(), generator="coarse_agent")
    # Forcibly delete the object file
    entry, _ = get_mask(repo, "subject")
    obj_path = repo.objects_dir / entry.hash[:2] / entry.hash[2:]
    obj_path.unlink()
    with pytest.raises(MaskError, match="missing object"):
        get_mask(repo, "subject")


def test_list_masks_newest_first(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    register_mask(repo, "first", make_test_png(value=10), generator="manual")
    register_mask(repo, "second", make_test_png(value=20), generator="manual")
    register_mask(repo, "third", make_test_png(value=30), generator="manual")
    entries = list_masks(repo)
    assert [e.name for e in entries] == ["third", "second", "first"]


def test_list_masks_empty_when_no_registry(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    assert list_masks(repo) == []


def test_invalidate_mask_drops_registry_entry(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    entry = register_mask(repo, "subject", make_test_png(), generator="manual")
    invalidate_mask(repo, "subject")
    with pytest.raises(MaskNotFoundError):
        get_mask(repo, "subject")
    # PNG still in objects/ (content-addressed; unrefcounted)
    assert repo.has_object(entry.hash)


def test_invalidate_mask_unknown_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(MaskNotFoundError):
        invalidate_mask(repo, "nonexistent")


def test_tag_mask_creates_immutable_alias(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    src = register_mask(repo, "current_subject_mask", make_test_png(), generator="coarse_agent")
    aliased = tag_mask(repo, "current_subject_mask", "subject_v1_export")
    assert aliased.hash == src.hash
    fetched, _ = get_mask(repo, "subject_v1_export")
    assert fetched.hash == src.hash


def test_tag_mask_refuses_to_overwrite(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    register_mask(repo, "a", make_test_png(value=1), generator="manual")
    register_mask(repo, "b", make_test_png(value=2), generator="manual")
    with pytest.raises(MaskError, match="already exists"):
        tag_mask(repo, "a", "b")


def test_tag_mask_unknown_source_raises(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    with pytest.raises(MaskNotFoundError):
        tag_mask(repo, "nope", "new_name")


def test_registry_json_round_trip_through_disk(tmp_path: Path) -> None:
    """Registry survives close + reopen of the repo."""
    repo1 = _repo(tmp_path)
    register_mask(repo1, "subject", make_test_png(), generator="coarse_agent")

    # Reopen the repo from disk
    repo2 = ImageRepo(repo1.root)
    entries = list_masks(repo2)
    assert len(entries) == 1
    assert entries[0].name == "subject"


def test_registry_json_is_sorted_by_key(tmp_path: Path) -> None:
    """For stable git diffs."""
    repo = _repo(tmp_path)
    # Insert in non-alphabetical order
    register_mask(repo, "zebra", make_test_png(value=1), generator="manual")
    register_mask(repo, "alpha", make_test_png(value=2), generator="manual")
    register_mask(repo, "middle", make_test_png(value=3), generator="manual")
    raw = (repo.root / "masks" / "registry.json").read_text()
    assert raw.find('"alpha"') < raw.find('"middle"') < raw.find('"zebra"')
