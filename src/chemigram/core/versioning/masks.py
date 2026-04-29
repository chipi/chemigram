"""Per-image mask registry and raster mask storage.

Per ADR-021 (three-layer mask pattern), the agent uses raster PNG masks
to scope local adjustments. Per ADR-022, each image has a registry
mapping symbolic names (``current_subject_mask``, etc.) to specific
mask blobs. RFC-003 settled the storage question; **ADR-055 closes it**:

  - PNG bytes live in the same content-addressed ``objects/`` store
    as XMP snapshots. Same dedup, same primitives, same
    :class:`~chemigram.core.versioning.repo.ImageRepo` API.
  - ``masks/registry.json`` is the per-image registry — symbolic
    names → object hashes plus provenance (generator, prompt,
    timestamp).

Symbolic names are how vocabulary entries refer to masks: a primitive
like ``tone_lifted_shadows_subject`` declares ``mask_ref:
current_subject_mask`` in its manifest, and at synthesis time the
engine resolves the name to PNG bytes via :func:`get_mask`.

PNG validation in v0.2.0 is byte-magic only (no Pillow dep). Per
ADR-021 we expect 8-bit grayscale, but full format validation can be
added when a masking provider that needs it lands.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chemigram.core.versioning.repo import ImageRepo, ObjectNotFoundError

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_REGISTRY_FILENAME = "registry.json"


class MaskError(Exception):
    """Base class for mask registry errors."""


class MaskNotFoundError(MaskError):
    """Raised when a symbolic mask name isn't in the registry."""


class InvalidMaskError(MaskError):
    """Raised when bytes aren't a recognizable PNG."""


@dataclass(frozen=True)
class MaskEntry:
    """A registry entry: symbolic name + content hash + provenance."""

    name: str
    hash: str
    generator: str
    prompt: str | None
    timestamp: datetime


# ---------- registry I/O ----------------------------------------------------


def _registry_path(repo: ImageRepo) -> Path:
    masks_dir = repo.root / "masks"
    masks_dir.mkdir(parents=True, exist_ok=True)
    return masks_dir / _REGISTRY_FILENAME


def _read_registry(repo: ImageRepo) -> dict[str, dict[str, Any]]:
    path = _registry_path(repo)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _write_registry(repo: ImageRepo, registry: dict[str, dict[str, Any]]) -> None:
    path = _registry_path(repo)
    path.write_text(
        json.dumps(registry, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _entry_from_raw(name: str, raw: dict[str, Any]) -> MaskEntry:
    return MaskEntry(
        name=name,
        hash=raw["hash"],
        generator=raw["generator"],
        prompt=raw.get("prompt"),
        timestamp=datetime.fromisoformat(raw["timestamp"]),
    )


def _entry_to_raw(entry: MaskEntry) -> dict[str, Any]:
    return {
        "hash": entry.hash,
        "generator": entry.generator,
        "prompt": entry.prompt,
        "timestamp": entry.timestamp.isoformat(),
    }


# ---------- PNG validation --------------------------------------------------


def _validate_png(data: bytes) -> None:
    if len(data) < len(PNG_MAGIC):
        raise InvalidMaskError(
            f"too short to be a PNG ({len(data)} bytes; need at least {len(PNG_MAGIC)})"
        )
    if not data.startswith(PNG_MAGIC):
        raise InvalidMaskError("bytes do not start with the PNG magic number")


# ---------- public API ------------------------------------------------------


def register_mask(
    repo: ImageRepo,
    name: str,
    png_bytes: bytes,
    *,
    generator: str,
    prompt: str | None = None,
) -> MaskEntry:
    """Store ``png_bytes`` in the object store and bind ``name`` to its
    hash in the registry.

    Replaces any existing entry under the same name (the typical case —
    re-running a masker overwrites ``current_subject_mask``). The
    underlying PNG bytes are content-addressed in ``objects/``, so
    repeated registrations of the same bytes deduplicate.

    Raises:
        InvalidMaskError: bytes don't start with the PNG magic.
    """
    _validate_png(png_bytes)
    hash_ = repo.write_object(png_bytes)
    entry = MaskEntry(
        name=name,
        hash=hash_,
        generator=generator,
        prompt=prompt,
        timestamp=datetime.now(UTC),
    )
    registry = _read_registry(repo)
    registry[name] = _entry_to_raw(entry)
    _write_registry(repo, registry)
    return entry


def get_mask(repo: ImageRepo, name: str) -> tuple[MaskEntry, bytes]:
    """Look up ``name``, return its registry entry plus the PNG bytes.

    Raises:
        MaskNotFoundError: name not in registry.
        MaskError: registry references an object that's not in the store.
    """
    registry = _read_registry(repo)
    if name not in registry:
        raise MaskNotFoundError(f"mask {name!r} not in registry")
    entry = _entry_from_raw(name, registry[name])
    try:
        png = repo.read_object(entry.hash)
    except ObjectNotFoundError as exc:
        raise MaskError(
            f"mask {name!r} registry references missing object {entry.hash}: {exc}"
        ) from exc
    return entry, png


def list_masks(repo: ImageRepo) -> list[MaskEntry]:
    """All registered masks, ordered by timestamp (newest first).

    Returns an empty list if the registry doesn't exist yet.
    """
    registry = _read_registry(repo)
    entries = [_entry_from_raw(name, raw) for name, raw in registry.items()]
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries


def invalidate_mask(repo: ImageRepo, name: str) -> None:
    """Drop ``name`` from the registry. PNG bytes remain in
    ``objects/`` (content-addressed storage doesn't reference-count;
    the bytes may be reused under another name).

    Raises:
        MaskNotFoundError: name not in registry.
    """
    registry = _read_registry(repo)
    if name not in registry:
        raise MaskNotFoundError(f"mask {name!r} not in registry")
    del registry[name]
    _write_registry(repo, registry)


def tag_mask(
    repo: ImageRepo,
    source_name: str,
    new_name: str,
) -> MaskEntry:
    """Copy the registry entry for ``source_name`` under ``new_name``.

    Useful for snapshotting the current mask before regenerating, e.g.
    ``tag_mask(repo, "current_subject_mask",
    "subject_mask_v1_export")``. The underlying PNG isn't duplicated —
    both names point at the same content hash.

    Raises:
        MaskNotFoundError: ``source_name`` not in registry.
        MaskError: ``new_name`` already exists.
    """
    registry = _read_registry(repo)
    if source_name not in registry:
        raise MaskNotFoundError(f"mask {source_name!r} not in registry")
    if new_name in registry:
        raise MaskError(f"mask {new_name!r} already exists; refusing to overwrite")
    source_raw = registry[source_name]
    # Same hash (same content), but new timestamp captures the tagging moment.
    new_entry = MaskEntry(
        name=new_name,
        hash=source_raw["hash"],
        generator=source_raw["generator"],
        prompt=source_raw.get("prompt"),
        timestamp=datetime.now(UTC),
    )
    registry[new_name] = _entry_to_raw(new_entry)
    _write_registry(repo, registry)
    return new_entry


__all__ = [
    "PNG_MAGIC",
    "InvalidMaskError",
    "MaskEntry",
    "MaskError",
    "MaskNotFoundError",
    "get_mask",
    "invalidate_mask",
    "list_masks",
    "register_mask",
    "tag_mask",
]
