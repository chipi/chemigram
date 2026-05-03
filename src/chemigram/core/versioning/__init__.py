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

**Error hierarchy.** The package exposes two sibling exception roots:

- :class:`RepoError` (with subclasses :class:`ObjectNotFoundError`,
  :class:`RefNotFoundError`) — low-level filesystem / repo-shape errors.
- :class:`VersioningError` — high-level operation errors (``snapshot``
  from a detached HEAD, unknown ref, etc.).

To catch any error from the versioning subsystem uniformly,
``except (RepoError, VersioningError)``.
"""

from chemigram.core.versioning.canonical import canonical_bytes, xmp_hash
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
    "LogEntry",
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
    "log",
    "snapshot",
    "tag",
    "xmp_hash",
]
