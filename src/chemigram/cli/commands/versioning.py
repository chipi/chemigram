"""Versioning CLI verbs (issue #55).

Mirrors MCP ``snapshot``, ``branch``, ``tag``, ``checkout``, ``log``,
``diff`` (per ADR-033/056). Calls :mod:`chemigram.core.versioning.ops`
directly per ADR-071.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.helpers import current_xmp, summarize_state
from chemigram.core.versioning import (
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
    VersioningError,
)
from chemigram.core.versioning import (
    snapshot as core_snapshot,
)
from chemigram.core.versioning.ops import (
    branch as core_branch,
)
from chemigram.core.versioning.ops import (
    checkout as core_checkout,
)
from chemigram.core.versioning.ops import (
    diff as core_diff,
)
from chemigram.core.versioning.ops import (
    log as core_log,
)
from chemigram.core.versioning.ops import (
    tag as core_tag,
)

# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------


def snapshot(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    label: str | None = typer.Option(
        None, "--label", help="Optional human-readable label for the log entry."
    ),
) -> None:
    """Snapshot the current XMP, return the new content hash."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    xmp = current_xmp(workspace)
    if xmp is None:
        writer.error(
            "workspace has no current XMP to snapshot",
            ExitCode.STATE_ERROR,
            image_id=image_id,
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value)

    try:
        new_hash = core_snapshot(workspace.repo, xmp, label=label)
    except VersioningError as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"snapshot {new_hash[:8]}",
        image_id=image_id,
        hash=new_hash,
        label=label,
    )


# ---------------------------------------------------------------------------
# branch
# ---------------------------------------------------------------------------


def branch(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    name: str = typer.Option(..., "--name", help="Branch name (no slashes)."),
    from_ref: str = typer.Option(
        "HEAD", "--from", help="Ref or hash to branch from. Defaults to HEAD."
    ),
) -> None:
    """Create a branch at ``from_ref`` (default HEAD)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        ref = core_branch(workspace.repo, name, from_=from_ref)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id, name=name)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"branch {name}",
        image_id=image_id,
        name=name,
        ref=ref,
        from_ref=from_ref,
    )


# ---------------------------------------------------------------------------
# tag
# ---------------------------------------------------------------------------


def tag(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    name: str = typer.Option(..., "--name", help="Tag name (immutable; cannot retag)."),
    hash_: str | None = typer.Option(
        None, "--hash", help="Snapshot hash to tag. Defaults to HEAD."
    ),
) -> None:
    """Create an immutable tag at ``hash`` (default HEAD)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    if not name.strip():
        writer.error("--name must be non-empty", ExitCode.INVALID_INPUT)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        ref = core_tag(workspace.repo, name, hash_=hash_)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id, name=name)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    writer.result(
        message=f"tag {name}",
        image_id=image_id,
        name=name,
        ref=ref,
        hash=hash_,
    )


# ---------------------------------------------------------------------------
# checkout
# ---------------------------------------------------------------------------


def checkout(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    ref_or_hash: str = typer.Argument(
        ..., help="Branch name, tag name, or snapshot hash to check out."
    ),
) -> None:
    """Move HEAD to ``ref_or_hash``; return the new state summary."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        xmp = core_checkout(workspace.repo, ref_or_hash)
    except (VersioningError, RefNotFoundError, RepoError) as exc:
        # Mirror MCP: unknown ref/hash collapses to VERSIONING_ERROR
        # (chemigram.mcp.tools.versioning._versioning_error).
        writer.error(
            str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id, ref_or_hash=ref_or_hash
        )
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    summary = summarize_state(xmp)
    writer.result(
        message=f"checked out {ref_or_hash}",
        image_id=image_id,
        ref_or_hash=ref_or_hash,
        **summary,
    )


# ---------------------------------------------------------------------------
# log
# ---------------------------------------------------------------------------


def log(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    limit: int = typer.Option(
        20, "--limit", min=1, max=200, help="Max number of log entries to return."
    ),
) -> None:
    """Print the operation log (newest first)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        entries = core_log(workspace.repo, limit=limit)
    except (VersioningError, RepoError) as exc:
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    # Single summary payload (mirrors the rest of the CLI + MCP shape).
    payload = [asdict(e) for e in entries]
    writer.result(
        message=f"{len(payload)} log entries",
        image_id=image_id,
        count=len(payload),
        entries=payload,
    )


# ---------------------------------------------------------------------------
# diff
# ---------------------------------------------------------------------------


def diff(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    hash_a: str = typer.Argument(..., help="First snapshot hash."),
    hash_b: str = typer.Argument(..., help="Second snapshot hash."),
) -> None:
    """Diff two snapshots — return added/removed/changed primitives."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        diffs = core_diff(workspace.repo, hash_a, hash_b)
    except (VersioningError, ObjectNotFoundError, RepoError) as exc:
        # Mirror MCP: unknown hash → VERSIONING_ERROR (per
        # chemigram.mcp.tools.versioning._diff).
        writer.error(str(exc), ExitCode.VERSIONING_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value) from exc

    # Single summary payload (mirrors the rest of the CLI + MCP shape).
    payload = [asdict(d) for d in diffs]
    writer.result(
        message=f"{len(payload)} differences",
        image_id=image_id,
        hash_a=hash_a,
        hash_b=hash_b,
        count=len(payload),
        diffs=payload,
    )
