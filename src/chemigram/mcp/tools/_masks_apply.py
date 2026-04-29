"""Helper: materialize a registered mask onto the workspace's
``masks/<name>.png`` path.

Used by :func:`apply_primitive` when a mask-bound L3 primitive runs:
darktable's render reads raster masks from disk by filename, so we
write the registered PNG bytes (content-addressed in
``objects/``) to the path darktable expects. Idempotent — skips the
write if the existing file matches the registered hash.
"""

from __future__ import annotations

from pathlib import Path

from chemigram.core.versioning.masks import get_mask
from chemigram.core.workspace import Workspace


def materialize_mask_for_dt(workspace: Workspace, mask_name: str) -> Path:
    """Write the registered PNG to ``<workspace>/masks/<mask_name>.png``.

    Raises:
        MaskNotFoundError: ``mask_name`` not in the registry.
    """
    _entry, png = get_mask(workspace.repo, mask_name)
    target = workspace.masks_dir / f"{mask_name}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() == png:
        return target
    target.write_bytes(png)
    return target


__all__ = ["materialize_mask_for_dt"]
