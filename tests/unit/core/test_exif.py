"""Unit tests for chemigram.core.exif.read_exif.

Real-NEF integration test lives in tests/integration/core/test_exif_integration.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from chemigram.core.exif import ExifData, ExifReadError, read_exif


class _FakeTag:
    """Stand-in for exifread.IfdTag — str() yields the value."""

    def __init__(self, value: Any) -> None:
        self.values = value

    def __str__(self) -> str:
        return str(self.values)


def _patch_exifread(monkeypatch: pytest.MonkeyPatch, tags: dict[str, Any]) -> None:
    monkeypatch.setattr(
        "chemigram.core.exif.exifread.process_file",
        lambda fh, **_kw: tags,
    )


def test_read_exif_returns_dataclass(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw = tmp_path / "fake.nef"
    raw.write_bytes(b"not really a raw")
    _patch_exifread(
        monkeypatch,
        {
            "Image Make": _FakeTag("NIKON CORPORATION"),
            "Image Model": _FakeTag("NIKON D850"),
            "EXIF LensModel": _FakeTag("NIKKOR Z 24-70mm f/2.8 S"),
        },
    )
    result = read_exif(raw)
    assert isinstance(result, ExifData)
    assert result.make == "NIKON CORPORATION"
    assert result.model == "NIKON D850"
    assert result.lens_model == "NIKKOR Z 24-70mm f/2.8 S"


def test_read_exif_missing_lens_returns_empty_string(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw = tmp_path / "fake.nef"
    raw.write_bytes(b"not really a raw")
    _patch_exifread(
        monkeypatch,
        {
            "Image Make": _FakeTag("CANON"),
            "Image Model": _FakeTag("EOS R5"),
            # No LensModel — manual lens
        },
    )
    result = read_exif(raw)
    assert result.lens_model == ""


def test_read_exif_strips_trailing_nulls_and_whitespace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw = tmp_path / "fake.nef"
    raw.write_bytes(b"x")
    _patch_exifread(
        monkeypatch,
        {
            "Image Make": _FakeTag("NIKON CORPORATION  \x00\x00"),
            "Image Model": _FakeTag("\tNIKON D850\n"),
        },
    )
    result = read_exif(raw)
    assert result.make == "NIKON CORPORATION"
    assert result.model == "NIKON D850"


def test_read_exif_falls_back_to_makernote_lens(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw = tmp_path / "fake.nef"
    raw.write_bytes(b"x")
    _patch_exifread(
        monkeypatch,
        {
            "Image Make": _FakeTag("NIKON"),
            "Image Model": _FakeTag("D850"),
            "MakerNote LensModel": _FakeTag("AF-S NIKKOR 24-70mm f/2.8E ED VR"),
        },
    )
    result = read_exif(raw)
    assert result.lens_model == "AF-S NIKKOR 24-70mm f/2.8E ED VR"


def test_read_exif_focal_length_parsed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw = tmp_path / "fake.nef"
    raw.write_bytes(b"x")
    _patch_exifread(
        monkeypatch,
        {
            "Image Make": _FakeTag("X"),
            "Image Model": _FakeTag("Y"),
            "EXIF FocalLength": _FakeTag([70.0]),
        },
    )
    result = read_exif(raw)
    assert result.focal_length_mm == 70.0


def test_read_exif_missing_focal_length_is_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw = tmp_path / "fake.nef"
    raw.write_bytes(b"x")
    _patch_exifread(
        monkeypatch,
        {"Image Make": _FakeTag("X"), "Image Model": _FakeTag("Y")},
    )
    result = read_exif(raw)
    assert result.focal_length_mm is None


def test_read_exif_invalid_file_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw = tmp_path / "junk.nef"
    raw.write_bytes(b"x")

    def _raises(*_args: Any, **_kw: Any) -> Any:
        raise ValueError("not a recognizable image format")

    monkeypatch.setattr("chemigram.core.exif.exifread.process_file", _raises)
    with pytest.raises(ExifReadError, match="failed to read EXIF"):
        read_exif(raw)


def test_read_exif_file_not_found(tmp_path: Path) -> None:
    nonexistent = tmp_path / "missing.nef"
    with pytest.raises(FileNotFoundError):
        read_exif(nonexistent)
