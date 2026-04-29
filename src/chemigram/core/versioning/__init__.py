"""Versioning subsystem.

Per-image content-addressed DAG of XMP snapshots. "Mini git for photos"
per ADR-018 / ADR-019. The package is organized as:

- :mod:`chemigram.core.versioning.canonical` — deterministic byte form
  of an :class:`~chemigram.core.xmp.Xmp` plus the SHA-256
  content-address hash. Foundation for everything else.
  (RFC-002 → ADR-054.)
- :mod:`chemigram.core.versioning.repo` — per-image filesystem layout
  (``objects/``, ``refs/heads``, ``refs/tags``, ``HEAD``, ``log.jsonl``)
  with the low-level read/write/resolve primitives. ADR-019.
- :mod:`chemigram.core.versioning.ops` — high-level versioning
  operations (``snapshot``, ``checkout``, ``branch``, ``log``,
  ``diff``, ``tag``). ADR-018.
- :mod:`chemigram.core.versioning.masks` — mask registry + raster mask
  storage. (RFC-003 → ADR-055.)

**Error hierarchy.** The package exposes three sibling exception roots:

- :class:`RepoError` (with subclasses :class:`ObjectNotFoundError`,
  :class:`RefNotFoundError`) — low-level filesystem / repo-shape errors.
- :class:`VersioningError` — high-level operation errors (``snapshot``
  from a detached HEAD, unknown ref, etc.).
- :class:`MaskError` (with subclasses :class:`MaskNotFoundError`,
  :class:`InvalidMaskError`) — mask registry errors.

To catch any error from the versioning subsystem uniformly,
``except (RepoError, VersioningError, MaskError)``. The split mirrors
the modular structure (each module owns its error space); a future
ADR may consolidate these under a common base if call sites
repeatedly need the unified catch.
"""

from chemigram.core.versioning.canonical import canonical_bytes, xmp_hash
from chemigram.core.versioning.masks import (
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
from chemigram.core.versioning.ops import (
    LogEntry,
    PrimitiveDiff,
    VersioningError,
    branch,
    checkout,
    diff,
    log,
    snapshot,
    tag,
)
from chemigram.core.versioning.repo import (
    ImageRepo,
    ObjectNotFoundError,
    RefEntry,
    RefNotFoundError,
    RepoError,
)

__all__ = [
    "ImageRepo",
    "InvalidMaskError",
    "LogEntry",
    "MaskEntry",
    "MaskError",
    "MaskNotFoundError",
    "ObjectNotFoundError",
    "PrimitiveDiff",
    "RefEntry",
    "RefNotFoundError",
    "RepoError",
    "VersioningError",
    "branch",
    "canonical_bytes",
    "checkout",
    "diff",
    "get_mask",
    "invalidate_mask",
    "list_masks",
    "log",
    "register_mask",
    "snapshot",
    "tag",
    "tag_mask",
    "xmp_hash",
]
