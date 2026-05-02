"""Helpers for the CLI to load an existing :class:`Workspace` from disk.

The MCP server keeps a per-session ``ToolContext.workspaces`` dict of
loaded workspaces — that doesn't fit the subprocess-per-invocation
shape of the CLI. This module provides equivalent lookup against the
filesystem instead.

If/when the engine grows a ``Workspace.from_disk`` factory this module
goes away.
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.versioning import ImageRepo
from chemigram.core.workspace import Workspace


def default_workspace_root() -> Path:
    """Default location, mirroring ``chemigram.mcp.tools.ingest`` (~/Pictures/Chemigram)."""
    return Path.home() / "Pictures" / "Chemigram"


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
