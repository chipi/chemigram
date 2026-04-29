"""Per-image repository: low-level objects/refs/HEAD/log filesystem ops.

The directory layout is fixed by ADR-019 and ``contracts/per-image-repo``::

    <root>/
      objects/                content-addressed snapshot store
        NN/HHHHH...           SHA-256 sharded by first 2 hex chars
      refs/
        heads/<branch>        text file containing snapshot hash
        tags/<tag>            text file containing snapshot hash
        HEAD                  text file: "ref: refs/heads/main" or 64-hex hash
      log.jsonl               append-only operation log

This module is purely filesystem primitives — no XMP, no mask, no
semantic understanding of what gets stored. Higher-level operations
(snapshot, checkout, branch, etc.) build on this.

Single-writer assumption per ADR-006: one chemigram process per repo
at a time. Cross-process concurrent writes are unsupported.

Per ADR-019, the structure mirrors git but is **not** git-compatible.
We don't use git's wire format, blob/tree/commit headers, or pack
files. Simplicity over compatibility.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RepoError(Exception):
    """Base class for image-repo errors."""


class ObjectNotFoundError(RepoError):
    """Raised when an object hash isn't in the store."""


class RefNotFoundError(RepoError):
    """Raised when a ref doesn't exist."""


@dataclass(frozen=True)
class RefEntry:
    """A ref's name and the hash it ultimately resolves to."""

    name: str
    target: str


_INITIAL_HEAD = "ref: refs/heads/main\n"


class ImageRepo:
    """Per-image storage at ``<root>/``."""

    def __init__(self, root: Path) -> None:
        if not root.is_dir():
            raise RepoError(f"{root}: not a directory")
        if not (root / "objects").is_dir():
            raise RepoError(f"{root}: missing objects/ — not an image repo")
        if not (root / "refs").is_dir():
            raise RepoError(f"{root}: missing refs/ — not an image repo")
        if not (root / "HEAD").is_file():
            raise RepoError(f"{root}: missing HEAD — not an image repo")
        self._root = root

    @classmethod
    def init(cls, root: Path) -> ImageRepo:
        """Create a fresh repo at ``root``. Idempotent: re-init on an
        existing repo is a no-op (no error, no overwrite). Initial HEAD
        is ``"ref: refs/heads/main"`` (the branch ref doesn't exist
        until the first snapshot)."""
        root.mkdir(parents=True, exist_ok=True)
        (root / "objects").mkdir(exist_ok=True)
        (root / "refs").mkdir(exist_ok=True)
        (root / "refs" / "heads").mkdir(exist_ok=True)
        (root / "refs" / "tags").mkdir(exist_ok=True)
        head = root / "HEAD"
        if not head.exists():
            head.write_text(_INITIAL_HEAD, encoding="utf-8")
        log = root / "log.jsonl"
        if not log.exists():
            log.touch()
        return cls(root)

    # ------------------------------------------------------------ paths

    @property
    def root(self) -> Path:
        return self._root

    @property
    def objects_dir(self) -> Path:
        return self._root / "objects"

    @property
    def refs_dir(self) -> Path:
        return self._root / "refs"

    @property
    def head_path(self) -> Path:
        return self._root / "HEAD"

    @property
    def log_path(self) -> Path:
        return self._root / "log.jsonl"

    # ---------------------------------------------------------- objects

    def _object_path(self, hash_: str) -> Path:
        if len(hash_) != 64 or any(c not in "0123456789abcdef" for c in hash_):
            raise RepoError(f"invalid object hash: {hash_!r}")
        return self.objects_dir / hash_[:2] / hash_[2:]

    def write_object(self, content: bytes) -> str:
        hash_ = hashlib.sha256(content).hexdigest()
        path = self._object_path(hash_)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return hash_

    def read_object(self, hash_: str) -> bytes:
        path = self._object_path(hash_)
        if not path.exists():
            raise ObjectNotFoundError(f"object {hash_} not found")
        return path.read_bytes()

    def has_object(self, hash_: str) -> bool:
        try:
            return self._object_path(hash_).exists()
        except RepoError:
            return False

    # ------------------------------------------------------------- refs

    def _ref_path(self, name: str) -> Path:
        if name == "HEAD":
            return self.head_path
        if not name.startswith("refs/"):
            raise RepoError(f"ref name must start with 'refs/' or be 'HEAD': {name!r}")
        return self._root / name

    def write_ref(self, name: str, target: str) -> None:
        path = self._ref_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not target.endswith("\n"):
            target = target + "\n"
        path.write_text(target, encoding="utf-8")

    def read_ref_raw(self, name: str) -> str:
        path = self._ref_path(name)
        if not path.exists():
            raise RefNotFoundError(f"ref {name!r} not found")
        return path.read_text(encoding="utf-8").strip()

    def resolve_ref(self, name: str, *, max_depth: int = 8) -> str:
        seen: list[str] = []
        current = name
        for _ in range(max_depth):
            if current in seen:
                raise RepoError(f"circular ref chain: {' -> '.join([*seen, current])}")
            seen.append(current)
            raw = self.read_ref_raw(current)
            if raw.startswith("ref: "):
                current = raw[len("ref: ") :].strip()
                continue
            if len(raw) == 64 and all(c in "0123456789abcdef" for c in raw):
                return raw
            raise RepoError(
                f"ref {current!r} has invalid content: {raw!r} (expected hash or 'ref: ...')"
            )
        raise RepoError(f"ref {name!r}: max depth {max_depth} exceeded")

    def list_refs(self, prefix: str = "") -> list[RefEntry]:
        entries: list[RefEntry] = []
        for path in sorted(self.refs_dir.rglob("*")):
            if not path.is_file():
                continue
            ref_name = "refs/" + path.relative_to(self.refs_dir).as_posix()
            if prefix and not ref_name.startswith(prefix):
                continue
            try:
                target = self.resolve_ref(ref_name)
            except (RefNotFoundError, RepoError):
                continue
            entries.append(RefEntry(name=ref_name, target=target))
        return entries

    def delete_ref(self, name: str) -> None:
        if name == "HEAD":
            raise RepoError("HEAD cannot be deleted")
        path = self._ref_path(name)
        if not path.exists():
            raise RefNotFoundError(f"ref {name!r} not found")
        path.unlink()

    # -------------------------------------------------------------- log

    def append_log(self, entry: dict[str, Any]) -> None:
        if "timestamp" not in entry:
            entry = {
                **entry,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        line = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def read_log(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
        return entries
