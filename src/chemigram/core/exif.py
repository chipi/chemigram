"""Read camera/lens metadata from raw files for L1 vocabulary binding.

Uses ``exifread`` (pure-Python, no native deps) to extract the EXIF
fields chemigram cares about: ``Make``, ``Model``, ``LensModel``,
``FocalLength``. Per RFC-015 / ADR-053, downstream binding
(:mod:`chemigram.core.binding`) is exact-match on
``(make, model, lens_model)`` — this module only extracts.

Per ADR-007 (BYOA), the dependency stays in ``chemigram.core``'s
graph because EXIF is structural metadata, not AI capability — every
raw a photographer drops in needs identity resolution before any
vocabulary applies. PyExifTool (faster, more complete) is rejected for
v1 because it requires the ``exiftool`` binary as an external dep.

Public API:
    - :func:`read_exif` — extract EXIF from a raw file
    - :class:`ExifData` — frozen dataclass with the four fields we model
    - :class:`ExifReadError` — exception raised on unreadable input
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import exifread


class ExifReadError(Exception):
    """Raised when EXIF cannot be read from a file."""


@dataclass(frozen=True)
class ExifData:
    """The EXIF fields chemigram cares about for L1 binding.

    String fields are whitespace- and null-stripped. Missing string
    fields become empty strings (not ``None``) so callers don't need
    to special-case absence vs. presence-of-empty.
    """

    make: str
    model: str
    lens_model: str
    focal_length_mm: float | None


def _stringify_tag(tag: Any) -> str:
    """Coerce an exifread IfdTag (or absent value) into a clean string.

    EXIF strings often have trailing ``\\x00`` from C-string encoding
    plus whitespace on either side; strip both in one pass.
    """
    if tag is None:
        return ""
    return str(tag).strip("\x00 \t\r\n\v\f")


def _focal_length_mm(tag: Any) -> float | None:
    """Parse an EXIF FocalLength tag into millimetres.

    exifread returns FocalLength as ``IfdTag`` whose ``.values`` is a
    list of ``Ratio`` objects (numerator/denominator). We take the
    first ratio and coerce to float.
    """
    if tag is None:
        return None
    try:
        values = tag.values
        first = values[0] if isinstance(values, list) else values
        return float(first)
    except (TypeError, ValueError, IndexError, AttributeError):
        return None


def read_exif(path: Path) -> ExifData:
    """Read relevant EXIF tags from a raw file.

    Args:
        path: path to a raw (NEF, ARW, RAF, CR2, ...).

    Returns:
        :class:`ExifData` with whitespace-stripped strings; missing
        string fields become ``""``; missing ``focal_length_mm``
        becomes ``None``.

    Raises:
        ExifReadError: corrupt or unreadable file.
        FileNotFoundError: ``path`` does not exist.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    try:
        with path.open("rb") as fh:
            tags = exifread.process_file(fh, details=False)
    except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        # exifread doesn't expose a single error type; these cover the
        # families we've observed (corrupt files, malformed IFD pointers,
        # truncated streams). Letting other exceptions propagate is
        # intentional — they signal genuine bugs, not bad input.
        raise ExifReadError(f"failed to read EXIF from {path}: {exc}") from exc

    make = _stringify_tag(tags.get("Image Make"))
    model = _stringify_tag(tags.get("Image Model"))
    lens_model = _stringify_tag(tags.get("EXIF LensModel")) or _stringify_tag(
        tags.get("MakerNote LensModel")
    )
    focal_length = _focal_length_mm(tags.get("EXIF FocalLength"))

    return ExifData(
        make=make,
        model=model,
        lens_model=lens_model,
        focal_length_mm=focal_length,
    )
