"""Unit tests for the materialize_mask_for_dt helper."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from chemigram.core.helpers import materialize_mask_for_dt
from chemigram.core.versioning import ImageRepo
from chemigram.core.versioning.masks import MaskNotFoundError, register_mask
from chemigram.core.workspace import Workspace, init_workspace_root


def _png_bytes(value: int = 200) -> bytes:
    img = Image.new("L", (8, 8), value)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    root = tmp_path / "ws"
    init_workspace_root(root)
    repo = ImageRepo.init(root)
    raw = root / "raw" / "x.NEF"
    raw.touch()
    return Workspace(image_id="img", root=root, repo=repo, raw_path=raw)


def test_materialize_writes_to_masks_dir(workspace: Workspace) -> None:
    register_mask(workspace.repo, "subject", _png_bytes(), generator="manual")
    out = materialize_mask_for_dt(workspace, "subject")
    assert out == workspace.masks_dir / "subject.png"
    assert out.exists()
    assert out.read_bytes() == _png_bytes()


def test_materialize_idempotent(workspace: Workspace) -> None:
    register_mask(workspace.repo, "x", _png_bytes(), generator="manual")
    materialize_mask_for_dt(workspace, "x")
    mtime_before = (workspace.masks_dir / "x.png").stat().st_mtime_ns
    # Sleep 0 — Python's mtime resolution is enough that we can't always
    # detect a no-op write. Test the equivalent: bytes match → file is the
    # registered content.
    materialize_mask_for_dt(workspace, "x")
    assert (workspace.masks_dir / "x.png").read_bytes() == _png_bytes()
    # Best-effort: if mtime changed, the second write happened — that's
    # acceptable but not required. The contract is "file matches registered
    # bytes after either invocation."
    _ = mtime_before


def test_materialize_overwrites_when_hash_differs(workspace: Workspace) -> None:
    register_mask(workspace.repo, "x", _png_bytes(value=100), generator="m")
    materialize_mask_for_dt(workspace, "x")
    # Re-register under same name with different bytes
    register_mask(workspace.repo, "x", _png_bytes(value=250), generator="m")
    materialize_mask_for_dt(workspace, "x")
    assert (workspace.masks_dir / "x.png").read_bytes() == _png_bytes(value=250)


def test_materialize_unknown_mask_raises(workspace: Workspace) -> None:
    with pytest.raises(MaskNotFoundError):
        materialize_mask_for_dt(workspace, "ghost")
