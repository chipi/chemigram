"""Versioning tools (batch 2 of Slice 3).

Thin wrappers over :mod:`chemigram.core.versioning.ops`. Each tool is one
delegation plus the standard error mapping (``RefNotFoundError``,
``VersioningError``, ``RepoError``) → ``ErrorCode``.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from chemigram.core.helpers import current_xmp, summarize_state
from chemigram.core.versioning import (
    ImageRepo,
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
)
from chemigram.core.versioning.ops import (
    VersioningError,
    branch,
    checkout,
    diff,
    log,
    snapshot,
    tag,
)
from chemigram.core.xmp import Xmp, parse_xmp_from_bytes
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
)
from chemigram.mcp.registry import ToolContext, register_tool


def _versioning_error(exc: Exception) -> ToolError:
    return ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc))


# --- snapshot -----------------------------------------------------------


async def _snapshot(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    label = args.get("label")
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    xmp = current_xmp(workspace)
    if xmp is None:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.STATE_ERROR,
                message="cannot snapshot: no current XMP on this workspace",
            )
        )
    try:
        h = snapshot(workspace.repo, xmp, label=label)
    except VersioningError as exc:
        return ToolResult.fail(_versioning_error(exc))
    return ToolResult.ok({"hash": h})


register_tool(
    name="snapshot",
    description="Snapshot the current XMP state. Optional human label.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "label": {"type": "string"},
        },
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_snapshot,
)


# --- checkout -----------------------------------------------------------


async def _checkout(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    ref_or_hash = args["ref_or_hash"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    try:
        xmp = checkout(workspace.repo, ref_or_hash)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        return ToolResult.fail(_versioning_error(exc))
    return ToolResult.ok(summarize_state(xmp))


register_tool(
    name="checkout",
    description="Checkout a ref (branch/tag) or hash; updates HEAD.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "ref_or_hash": {"type": "string"},
        },
        "required": ["image_id", "ref_or_hash"],
        "additionalProperties": False,
    },
    handler=_checkout,
)


# --- branch -------------------------------------------------------------


async def _branch(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    name = args["name"]
    from_ = args.get("from_", "HEAD")
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    try:
        ref = branch(workspace.repo, name, from_=from_)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        return ToolResult.fail(_versioning_error(exc))
    return ToolResult.ok({"ref": ref})


register_tool(
    name="branch",
    description="Create a branch ref pointing at the resolved hash of `from_`.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "name": {"type": "string"},
            "from_": {"type": "string"},
        },
        "required": ["image_id", "name"],
        "additionalProperties": False,
    },
    handler=_branch,
)


# --- log ----------------------------------------------------------------


async def _log(args: dict[str, Any], ctx: ToolContext) -> ToolResult[list[dict[str, Any]]]:
    image_id = args["image_id"]
    limit = args.get("limit", 20)
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    try:
        entries = log(workspace.repo, limit=limit)
    except (VersioningError, RepoError) as exc:
        return ToolResult.fail(_versioning_error(exc))
    return ToolResult.ok([asdict(e) for e in entries])


register_tool(
    name="log",
    description="Recent operation log entries (newest first); respects limit.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 200},
        },
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_log,
)


# --- diff ---------------------------------------------------------------


async def _diff(args: dict[str, Any], ctx: ToolContext) -> ToolResult[list[dict[str, Any]]]:
    image_id = args["image_id"]
    hash_a = args["hash_a"]
    hash_b = args["hash_b"]
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    try:
        diffs = diff(workspace.repo, hash_a, hash_b)
    except (VersioningError, ObjectNotFoundError, RepoError) as exc:
        return ToolResult.fail(_versioning_error(exc))
    return ToolResult.ok([asdict(d) for d in diffs])


register_tool(
    name="diff",
    description="Compare two snapshot hashes; returns per-primitive diffs.",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "hash_a": {"type": "string"},
            "hash_b": {"type": "string"},
        },
        "required": ["image_id", "hash_a", "hash_b"],
        "additionalProperties": False,
    },
    handler=_diff,
)


# --- tag ----------------------------------------------------------------


async def _tag(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    name = args["name"]
    hash_ = args.get("hash")
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))
    if not name:
        return ToolResult.fail(error_invalid_input("tag name must be non-empty"))
    try:
        ref = tag(workspace.repo, name, hash_) if hash_ else tag(workspace.repo, name)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        return ToolResult.fail(_versioning_error(exc))
    return ToolResult.ok({"ref": ref})


register_tool(
    name="tag",
    description="Create an immutable tag at `hash` (or HEAD if omitted).",
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "name": {"type": "string"},
            "hash": {"type": "string"},
        },
        "required": ["image_id", "name"],
        "additionalProperties": False,
    },
    handler=_tag,
)


# Read-only XMP byte loader exposed for rendering.py — kept here to colocate
# with the snapshot/checkout machinery it relies on.
def load_xmp_bytes_at(workspace_repo: ImageRepo, ref_or_hash: str) -> bytes:
    """Read the canonical XMP bytes for ``ref_or_hash`` without moving HEAD."""
    if ref_or_hash == "HEAD":
        h = workspace_repo.resolve_ref("HEAD")
    else:
        # Reuse versioning.ops._resolve_input semantics by trying refs first
        # and falling back to a hex hash check on the way through `read_object`.
        try:
            h = workspace_repo.resolve_ref(f"refs/heads/{ref_or_hash}")
        except RefNotFoundError:
            try:
                h = workspace_repo.resolve_ref(f"refs/tags/{ref_or_hash}")
            except RefNotFoundError:
                h = ref_or_hash  # assume hex; read_object will raise if not
    return workspace_repo.read_object(h)


def parse_xmp_at(workspace_repo: ImageRepo, ref_or_hash: str) -> Xmp:
    raw = load_xmp_bytes_at(workspace_repo, ref_or_hash)
    return parse_xmp_from_bytes(raw, source=f"sha256:{ref_or_hash}")
