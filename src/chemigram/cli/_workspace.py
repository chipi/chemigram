"""Helpers for the CLI to load an existing :class:`Workspace` from disk.

The MCP server keeps a per-session ``ToolContext.workspaces`` dict of
loaded workspaces — that doesn't fit the subprocess-per-invocation
shape of the CLI. This module provides equivalent lookup against the
filesystem instead, plus a shared "resolve or NOT_FOUND" helper used
by every CLI verb that takes an ``image_id``.

If/when the engine grows a ``Workspace.from_disk`` factory this module
goes away.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.versioning import ImageRepo
from chemigram.core.workspace import Workspace


def default_workspace_root() -> Path:
    """Default location, mirroring ``chemigram.mcp.tools.ingest`` (~/Pictures/Chemigram)."""
    return Path.home() / "Pictures" / "Chemigram"


def discover_workspace_from_cwd(start: Path | None = None) -> tuple[Path, str] | None:
    """Walk up from ``start`` (defaults to cwd) looking for an image root.

    An image root is a directory containing both ``objects/`` and
    ``raw/`` (the chemigram per-image-repo signature). Returns
    ``(workspace_root, image_id)`` where ``workspace_root`` is the
    image root's parent and ``image_id`` is the image root's basename
    — matching the layout :func:`load_workspace` expects.

    Returns ``None`` if no image root is found before reaching the
    filesystem root. Closes RFC-020 §Q3.
    """
    candidate = (start or Path.cwd()).resolve()
    for current in (candidate, *candidate.parents):
        if (current / "objects").is_dir() and (current / "raw").is_dir():
            return current.parent, current.name
    return None


def load_workspace(workspace_root: Path, image_id: str) -> Workspace | None:
    """Load an existing workspace from disk; return ``None`` if not present.

    Reconstructs the :class:`Workspace` dataclass from the filesystem
    layout. **Two fields are intentionally left at their defaults**:

    - ``exif`` stays ``None``. ``metadata.json`` caches EXIF on disk;
      re-reading is the agent loop's concern, not stateless CLI ops.
    - ``suggested_bindings`` stays ``[]``. L1 binding suggestions are
      ingest-time output, recorded in ``log.jsonl``; verbs that need
      them later should look there.

    None of the v1.3.0 verb groups (#54..#59) read these fields. If a
    future verb does, populate from ``metadata.json`` here rather than
    growing a separate accessor.
    """
    root = workspace_root / image_id
    if not (root / "objects").exists():
        return None

    repo = ImageRepo(root)
    raw_dir = root / "raw"
    raw_files: list[Path] = sorted(raw_dir.iterdir()) if raw_dir.exists() else []
    raw_path = raw_files[0] if raw_files else root

    return Workspace(
        image_id=image_id,
        root=root,
        repo=repo,
        raw_path=raw_path,
    )


def resolve_workspace_or_fail(ctx: typer.Context, image_id: str) -> Workspace:
    """Load workspace by image_id; emit a NOT_FOUND error and ``typer.Exit`` if absent.

    Shared helper for every CLI verb that takes an ``image_id``. Pulls
    the workspace root from the global ``--workspace`` flag (default
    ``~/Pictures/Chemigram``) and the darktable configdir from the
    global ``--configdir`` flag / ``CHEMIGRAM_DT_CONFIGDIR`` env var.

    Auto-discovery (B4 / RFC-020 §Q3): when ``image_id == "."``, walks
    up from cwd looking for an image root (a dir containing both
    ``objects/`` and ``raw/``); the discovered workspace_root + image_id
    take precedence over ``--workspace``. Lets a photographer ``cd`` into
    an image dir and run ``chemigram get-state .`` without flags.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    if image_id == ".":
        discovered = discover_workspace_from_cwd()
        if discovered is None:
            writer.error(
                "auto-discover (image_id='.'): cwd is not inside a chemigram workspace",
                ExitCode.NOT_FOUND,
                cwd=str(Path.cwd()),
            )
            raise typer.Exit(code=ExitCode.NOT_FOUND.value)
        workspace_root, image_id = discovered
    else:
        workspace_root = obj["workspace"] or default_workspace_root()

    workspace = load_workspace(workspace_root, image_id)
    if workspace is None:
        writer.error(
            f"workspace not found: {image_id}",
            ExitCode.NOT_FOUND,
            image_id=image_id,
            workspace_root=str(workspace_root),
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)
    # Inject the global --configdir into the workspace so render verbs
    # (and any future verbs that need it) pick it up via workspace.configdir.
    if obj["configdir"] is not None:
        workspace.configdir = obj["configdir"]
    return workspace
