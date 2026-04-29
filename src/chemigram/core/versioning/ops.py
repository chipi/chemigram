"""High-level versioning operations on top of the per-image repo.

All operations are pure functions over an :class:`ImageRepo`. Each
op resolves refs to hashes via the repo's ``resolve_ref``, reads or
writes objects via canonical XMP bytes (:func:`canonical_bytes`,
:func:`xmp_hash`), updates ``HEAD`` or the relevant branch ref, and
appends a structured entry to ``log.jsonl``.

Pattern for snapshot:
    canonical_bytes(xmp) -> repo.write_object -> resolve HEAD ->
    if symbolic, advance the branch ref; if detached, refuse.

Pattern for checkout:
    interpret input as branch -> tag -> raw hash, in that order.
    Branch checkout makes HEAD symbolic ("ref: refs/heads/<name>");
    tag/hash checkout makes HEAD detached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from chemigram.core.versioning.canonical import canonical_bytes, xmp_hash
from chemigram.core.versioning.repo import (
    ImageRepo,
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
)
from chemigram.core.xmp import Xmp, parse_xmp_from_bytes


class VersioningError(Exception):
    """Raised when a high-level versioning operation cannot complete."""


@dataclass(frozen=True)
class LogEntry:
    """One operation recorded in ``log.jsonl``."""

    timestamp: datetime
    op: str
    hash: str | None = None
    ref: str | None = None
    parent: str | None = None
    label: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PrimitiveDiff:
    """One per-(operation, multi_priority) difference between two XMPs."""

    operation: str
    multi_priority: int
    kind: str  # "added" | "removed" | "changed"
    a_params: str | None
    b_params: str | None


# ---------- helpers ---------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_hex_hash(s: str) -> bool:
    return len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def _resolve_input(repo: ImageRepo, ref_or_hash: str) -> tuple[str, str | None]:
    """Resolve user input into (hash, branch_name_or_None).

    Accepted shapes:
    - bare branch name (``"main"``) — resolves via ``refs/heads/<name>``
    - bare tag name (``"baseline"``) — resolves via ``refs/tags/<name>``
    - full branch ref (``"refs/heads/main"``)
    - full tag ref (``"refs/tags/baseline"``)
    - 64-char hex hash, if the object exists

    Returns the resolved hash plus, when input names a branch, the
    branch's full ref name (so the caller can set HEAD symbolically).

    **Precedence on bare-name collision:** if a name exists as both a
    branch AND a tag, the branch wins. ADR-019's namespace split makes
    this collision unlikely in practice, but the rule is here so
    callers can rely on it. Full-ref-form input bypasses this lookup
    chain entirely — ``"refs/tags/main"`` always resolves to a tag.
    """
    if ref_or_hash.startswith("refs/heads/"):
        try:
            h = repo.resolve_ref(ref_or_hash)
            return h, ref_or_hash
        except RefNotFoundError as exc:
            raise VersioningError(
                f"unknown ref or hash: {ref_or_hash!r} (not a branch, tag, or known object)"
            ) from exc

    if ref_or_hash.startswith("refs/tags/"):
        try:
            h = repo.resolve_ref(ref_or_hash)
            return h, None
        except RefNotFoundError as exc:
            raise VersioningError(
                f"unknown ref or hash: {ref_or_hash!r} (not a branch, tag, or known object)"
            ) from exc

    branch_ref = f"refs/heads/{ref_or_hash}"
    try:
        h = repo.resolve_ref(branch_ref)
        return h, branch_ref
    except RefNotFoundError:
        pass

    tag_ref = f"refs/tags/{ref_or_hash}"
    try:
        h = repo.resolve_ref(tag_ref)
        return h, None
    except RefNotFoundError:
        pass

    if _is_hex_hash(ref_or_hash) and repo.has_object(ref_or_hash):
        return ref_or_hash, None

    raise VersioningError(
        f"unknown ref or hash: {ref_or_hash!r} (not a branch, tag, or known object)"
    )


# ---------- public API ------------------------------------------------------


def snapshot(
    repo: ImageRepo,
    xmp: Xmp,
    *,
    label: str | None = None,
    parent: str = "HEAD",
    metadata: dict[str, Any] | None = None,
) -> str:
    """Write the canonical bytes of ``xmp`` to the object store and
    advance HEAD's branch (or create the branch if HEAD is symbolic
    and the branch ref doesn't exist yet).

    Returns the snapshot hash.

    Raises:
        VersioningError: HEAD is detached (literal hash). Caller must
            ``checkout`` a branch first.
    """
    head_raw = repo.read_ref_raw("HEAD")
    if not head_raw.startswith("ref: "):
        raise VersioningError(
            "cannot snapshot from a detached HEAD; "
            "checkout a branch first (e.g. via `branch` then `checkout`)"
        )
    branch_ref = head_raw[len("ref: ") :].strip()

    parent_hash: str | None = None
    if parent:
        try:
            parent_hash = repo.resolve_ref(parent)
        except (RefNotFoundError, RepoError):
            # First snapshot on a fresh branch — no parent yet
            parent_hash = None

    new_hash = repo.write_object(canonical_bytes(xmp))
    repo.write_ref(branch_ref, new_hash)

    repo.append_log(
        {
            "timestamp": _now_iso(),
            "op": "snapshot",
            "hash": new_hash,
            "ref": branch_ref,
            "parent": parent_hash,
            "label": label,
            "metadata": metadata or {},
        }
    )
    return new_hash


def checkout(repo: ImageRepo, ref_or_hash: str) -> Xmp:
    """Resolve to a hash, load the object, parse as :class:`Xmp`, and
    update ``HEAD``. Branch input → symbolic HEAD; tag or raw hash →
    detached HEAD.

    Raises:
        VersioningError: ref/hash unknown or object can't be parsed.
    """
    target_hash, branch_ref = _resolve_input(repo, ref_or_hash)

    try:
        raw = repo.read_object(target_hash)
    except ObjectNotFoundError as exc:
        raise VersioningError(str(exc)) from exc

    xmp = parse_xmp_from_bytes(raw, source=f"sha256:{target_hash}")

    if branch_ref is not None:
        repo.write_ref("HEAD", f"ref: {branch_ref}")
    else:
        repo.write_ref("HEAD", target_hash)

    repo.append_log(
        {
            "timestamp": _now_iso(),
            "op": "checkout",
            "hash": target_hash,
            "ref": branch_ref,
        }
    )
    return xmp


_DEFAULT_PRIMARY_BRANCH = "refs/heads/main"


def reset_to(repo: ImageRepo, ref_or_hash: str) -> Xmp:
    """Rewind the current branch to ``ref_or_hash`` and ensure HEAD is
    symbolic on a branch (per ADR-062).

    Resolves the input as branch / tag / hash. If HEAD is symbolic,
    force-writes the current branch's ref to the resolved hash. If
    HEAD is detached, attaches HEAD to ``refs/heads/main`` and
    force-writes that branch to the resolved hash. Either way, after
    the call, HEAD is symbolic and the current branch's tip is the
    resolved hash. ``"HEAD"`` is rejected as input — resetting HEAD
    to itself is meaningless and almost certainly a caller bug.

    Returns the parsed :class:`Xmp` at the resolved hash, mirroring
    :func:`checkout` so the caller can summarize state without an
    extra read.

    Raises:
        VersioningError: input unresolvable, input is "HEAD", or the
            object can't be read/parsed.
    """
    if ref_or_hash == "HEAD":
        raise VersioningError("reset target cannot be 'HEAD' (ambiguous self-reference)")

    target_hash, _ = _resolve_input(repo, ref_or_hash)

    try:
        raw = repo.read_object(target_hash)
    except ObjectNotFoundError as exc:
        raise VersioningError(str(exc)) from exc
    xmp = parse_xmp_from_bytes(raw, source=f"sha256:{target_hash}")

    head_raw = repo.read_ref_raw("HEAD")
    if head_raw.startswith("ref: "):
        current_branch_ref = head_raw[len("ref: ") :].strip()
    else:
        current_branch_ref = _DEFAULT_PRIMARY_BRANCH
        repo.write_ref("HEAD", f"ref: {current_branch_ref}")

    try:
        prior_hash: str | None = repo.resolve_ref(current_branch_ref)
    except (RefNotFoundError, RepoError):
        prior_hash = None

    repo.write_ref(current_branch_ref, target_hash)

    repo.append_log(
        {
            "timestamp": _now_iso(),
            "op": "reset",
            "hash": target_hash,
            "ref": current_branch_ref,
            "parent": prior_hash,
            "metadata": {"prior_hash": prior_hash, "target": ref_or_hash},
        }
    )
    return xmp


def branch(repo: ImageRepo, name: str, from_: str = "HEAD") -> str:
    """Create ``refs/heads/<name>`` pointing at the resolved hash of
    ``from_``. Does NOT switch HEAD to the new branch.

    ``from_`` accepts the same shapes as :func:`checkout` and the
    ``ref_or_hash`` arguments of other ops: a branch name (``"main"``),
    a tag name (``"baseline"``), a full ref (``"refs/heads/main"``,
    ``"refs/tags/v1"``), ``"HEAD"``, or a 64-char hex hash. Unresolvable
    input raises ``VersioningError``.

    Returns the full ref name.

    Raises:
        VersioningError: name already exists, or ``from_`` unknown.
    """
    new_ref = f"refs/heads/{name}"
    try:
        existing = repo.read_ref_raw(new_ref)
    except RefNotFoundError:
        existing = None
    if existing is not None:
        raise VersioningError(f"branch {name!r} already exists")

    if from_ == "HEAD":
        try:
            target_hash = repo.resolve_ref("HEAD")
        except (RefNotFoundError, RepoError) as exc:
            raise VersioningError(f"cannot resolve {from_!r}: {exc}") from exc
    else:
        target_hash, _ = _resolve_input(repo, from_)

    repo.write_ref(new_ref, target_hash)
    repo.append_log(
        {
            "timestamp": _now_iso(),
            "op": "branch",
            "hash": target_hash,
            "ref": new_ref,
            "parent": from_,
        }
    )
    return new_ref


def log(
    repo: ImageRepo,
    *,
    ref: str | None = None,
    limit: int | None = None,
) -> list[LogEntry]:
    """Read ``log.jsonl`` and return entries newest first.

    If ``ref`` is given, filter to entries that touched that ref.
    If ``limit`` is given, return at most that many.
    """
    raw = repo.read_log()
    entries = [_log_entry_from_dict(d) for d in raw]
    if ref is not None:
        entries = [e for e in entries if e.ref == ref]
    entries.reverse()  # newest first
    if limit is not None:
        entries = entries[:limit]
    return entries


def diff(repo: ImageRepo, hash_a: str, hash_b: str) -> list[PrimitiveDiff]:
    """Compute per-(operation, multi_priority) deltas between two snapshots.

    Returns entries sorted by (operation, multi_priority). Top-level
    metadata, raw_extra_fields, and history ordering are NOT compared
    — only per-(op, prio) param deltas.
    """
    xmp_a = _load_xmp_for_diff(repo, hash_a)
    xmp_b = _load_xmp_for_diff(repo, hash_b)

    a_map = {(h.operation, h.multi_priority): h.params for h in xmp_a.history}
    b_map = {(h.operation, h.multi_priority): h.params for h in xmp_b.history}

    diffs: list[PrimitiveDiff] = []
    for key in a_map.keys() - b_map.keys():
        op, prio = key
        diffs.append(PrimitiveDiff(op, prio, "removed", a_map[key], None))
    for key in b_map.keys() - a_map.keys():
        op, prio = key
        diffs.append(PrimitiveDiff(op, prio, "added", None, b_map[key]))
    for key in a_map.keys() & b_map.keys():
        if a_map[key] != b_map[key]:
            op, prio = key
            diffs.append(PrimitiveDiff(op, prio, "changed", a_map[key], b_map[key]))

    diffs.sort(key=lambda d: (d.operation, d.multi_priority))
    return diffs


def tag(
    repo: ImageRepo,
    name: str,
    hash_: str | None = None,
) -> str:
    """Create ``refs/tags/<name>`` pointing at ``hash_`` (default: HEAD).
    Tags are immutable: re-tagging an existing name raises
    :class:`VersioningError`.
    """
    tag_ref = f"refs/tags/{name}"
    try:
        repo.read_ref_raw(tag_ref)
        raise VersioningError(f"tag {name!r} already exists; tags are immutable")
    except RefNotFoundError:
        pass

    if hash_ is None:
        try:
            hash_ = repo.resolve_ref("HEAD")
        except (RefNotFoundError, RepoError) as exc:
            raise VersioningError(f"cannot resolve HEAD for tag {name!r}: {exc}") from exc

    if not _is_hex_hash(hash_):
        raise VersioningError(f"tag target must be a 64-hex hash: {hash_!r}")
    if not repo.has_object(hash_):
        raise VersioningError(f"tag target object not found: {hash_}")

    repo.write_ref(tag_ref, hash_)
    repo.append_log(
        {
            "timestamp": _now_iso(),
            "op": "tag",
            "hash": hash_,
            "ref": tag_ref,
        }
    )
    return tag_ref


# ---------- private helpers -------------------------------------------------


def _log_entry_from_dict(d: dict[str, Any]) -> LogEntry:
    return LogEntry(
        timestamp=datetime.fromisoformat(d["timestamp"]),
        op=d["op"],
        hash=d.get("hash"),
        ref=d.get("ref"),
        parent=d.get("parent"),
        label=d.get("label"),
        metadata=d.get("metadata") or {},
    )


def _load_xmp_for_diff(repo: ImageRepo, hash_: str) -> Xmp:
    try:
        raw = repo.read_object(hash_)
    except ObjectNotFoundError as exc:
        raise VersioningError(str(exc)) from exc
    return parse_xmp_from_bytes(raw, source=f"sha256:{hash_}")


# Re-export the hash function so callers don't need to know about canonical/
__all__ = [
    "LogEntry",
    "PrimitiveDiff",
    "VersioningError",
    "branch",
    "checkout",
    "diff",
    "log",
    "reset_to",
    "snapshot",
    "tag",
    "xmp_hash",
]
