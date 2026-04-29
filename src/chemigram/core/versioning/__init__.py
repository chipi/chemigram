"""Versioning subsystem.

Per-image content-addressed DAG of XMP snapshots. "Mini git for photos"
per ADR-018 / ADR-019. The package decomposes into:

- :mod:`chemigram.core.versioning.canonical` — deterministic byte form
  of an :class:`Xmp` plus the SHA-256 content-address hash. Foundation
  for everything else; closes RFC-002.

Future modules in this package (later issues in the v0.2.0 milestone):

- ``repo`` — per-image filesystem layout (objects/, refs/, HEAD, log.jsonl)
- ``ops`` — high-level snapshot/checkout/branch/log/diff/tag operations
- ``masks`` — mask registry + raster mask storage (closes RFC-003)
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
