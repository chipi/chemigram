"""Shared helpers used by both MCP and CLI adapters.

Lifted out of ``chemigram.mcp._state`` and ``chemigram.mcp.tools.*`` in v1.4.0
per the ADR-071 follow-up commitment. Each helper here was previously
imported cross-adapter (CLI imported from MCP), which violated the spirit
of the thin-wrapper rule even though it didn't violate the letter (no
domain logic in the adapter — but the helper was *located* in the
adapter). Moving them to core makes the dependency graph clean: both
adapters import from core only.

Contents:

- :func:`summarize_state` — state summary dict for mutating tools
- :func:`current_xmp` — read-only HEAD → :class:`Xmp` resolution
- :func:`load_xmp_bytes_at`, :func:`parse_xmp_at` — read XMP bytes / parse
  at a ref or hash without moving HEAD
- :func:`materialize_mask_for_dt` — write a registered mask PNG to
  ``<workspace>/masks/<name>.png`` for darktable to read
- :func:`stitch_side_by_side` — Pillow-based two-up image composition
  (used by the ``compare`` verb in both adapters)
- :func:`serialize_mask_entry` — :class:`MaskEntry` → JSON-friendly dict
- :func:`ensure_preview_render` — render a current-state preview JPEG
  for the masking pipeline (hash-cached)

What stays in ``chemigram.mcp._state``:

- :func:`resolve_workspace` — looks up a workspace by ``image_id`` against
  the per-MCP-session ``ToolContext.workspaces`` registry. MCP-only by
  shape (the CLI loads workspaces from disk via
  ``chemigram.cli._workspace.load_workspace`` instead).
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from chemigram.core.versioning import (
    ImageRepo,
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
    xmp_hash,
)
from chemigram.core.versioning.masks import get_mask
from chemigram.core.workspace import Workspace
from chemigram.core.xmp import Xmp, parse_xmp_from_bytes

# ---------------------------------------------------------------------------
# State summary
# ---------------------------------------------------------------------------


def summarize_state(xmp: Xmp) -> dict[str, Any]:
    """Compact ``state_after`` summary returned by mutating tools.

    Per RFC-010 (closing in v0.3.0): head_hash + entry_count + per-layer
    presence flags. Agents call ``get_state`` for full detail; this is
    the cheap return-value shape for mutating tools.
    """
    layers = {p.multi_priority for p in xmp.history if p.enabled}
    return {
        "head_hash": xmp_hash(xmp),
        "entry_count": len(xmp.history),
        "enabled_count": sum(1 for p in xmp.history if p.enabled),
        "layers_present": {
            "L1": 0 in layers,
            "L2": 1 in layers,
            "L3": any(level >= 2 for level in layers),
        },
    }


def current_xmp(workspace: Workspace) -> Xmp | None:
    """Read-only: resolve HEAD to an :class:`Xmp`, or ``None``.

    Doesn't move HEAD. Versioning's ``checkout`` is the write path (it
    touches HEAD). This helper is for tools that read state without
    intending to detach.
    """
    try:
        head_hash = workspace.repo.resolve_ref("HEAD")
        raw = workspace.repo.read_object(head_hash)
    except (RefNotFoundError, ObjectNotFoundError, RepoError):
        return None
    try:
        return parse_xmp_from_bytes(raw, source=f"sha256:{head_hash}")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# XMP resolution at arbitrary refs/hashes
# ---------------------------------------------------------------------------


def load_xmp_bytes_at(workspace_repo: ImageRepo, ref_or_hash: str) -> bytes:
    """Read the canonical XMP bytes for ``ref_or_hash`` without moving HEAD.

    Resolution order:

    1. ``"HEAD"`` → resolves the HEAD ref
    2. ``refs/heads/<ref_or_hash>`` (branch)
    3. ``refs/tags/<ref_or_hash>`` (tag)
    4. Treat as raw hex hash (``read_object`` raises if not valid)
    """
    if ref_or_hash == "HEAD":
        h = workspace_repo.resolve_ref("HEAD")
    else:
        try:
            h = workspace_repo.resolve_ref(f"refs/heads/{ref_or_hash}")
        except RefNotFoundError:
            try:
                h = workspace_repo.resolve_ref(f"refs/tags/{ref_or_hash}")
            except RefNotFoundError:
                h = ref_or_hash  # assume hex; read_object will raise if not
    return workspace_repo.read_object(h)


def parse_xmp_at(workspace_repo: ImageRepo, ref_or_hash: str) -> Xmp:
    """Resolve ``ref_or_hash`` and parse to :class:`Xmp`."""
    raw = load_xmp_bytes_at(workspace_repo, ref_or_hash)
    return parse_xmp_from_bytes(raw, source=f"sha256:{ref_or_hash}")


# ---------------------------------------------------------------------------
# Mask materialization (PNG → disk for darktable)
# ---------------------------------------------------------------------------


def materialize_mask_for_dt(workspace: Workspace, mask_name: str) -> Path:
    """Write the registered PNG to ``<workspace>/masks/<mask_name>.png``.

    darktable-cli reads raster masks from disk by filename; we write the
    registered PNG bytes (content-addressed in ``objects/``) to the
    expected path. Idempotent — skips the write if the existing file
    matches the registered hash.

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


# ---------------------------------------------------------------------------
# Image composition
# ---------------------------------------------------------------------------


def stitch_side_by_side(
    left: Path,
    right: Path,
    output: Path,
    *,
    label_left: str,
    label_right: str,
) -> None:
    """Stitch two JPEGs side-by-side with text labels into one labeled JPEG.

    Used by the ``compare`` verb in both adapters. Pillow-based, pure
    composition — no image-processing logic (per ADR-014 / BYOA-007).
    """
    img_a = Image.open(left).convert("RGB")
    img_b = Image.open(right).convert("RGB")
    h = max(img_a.height, img_b.height)
    sep = 8
    canvas = Image.new("RGB", (img_a.width + sep + img_b.width, h + 24), "white")
    canvas.paste(img_a, (0, 24))
    canvas.paste(img_b, (img_a.width + sep, 24))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.load_default()
    except OSError:  # pragma: no cover — load_default() is robust
        font = None
    draw.text((4, 4), label_left, fill="black", font=font)
    draw.text((img_a.width + sep + 4, 4), label_right, fill="black", font=font)
    canvas.save(output, "JPEG", quality=92)


# ---------------------------------------------------------------------------
# Mask entry serialization
# ---------------------------------------------------------------------------


def serialize_mask_entry(entry: Any) -> dict[str, Any]:
    """:class:`MaskEntry` → JSON-friendly dict.

    Just :func:`dataclasses.asdict` plus ISO-formatting the timestamp.
    Used by both adapters when emitting mask info to the agent or NDJSON.
    """
    raw = asdict(entry)
    if "timestamp" in raw and raw["timestamp"] is not None:
        raw["timestamp"] = raw["timestamp"].isoformat()
    return raw


# ---------------------------------------------------------------------------
# Preview render for masking pipeline
# ---------------------------------------------------------------------------


def ensure_preview_render(workspace: Workspace) -> Path:
    """Return a path to a current-state preview JPEG; render if absent.

    Hash-keyed so two consecutive mask generations against the same XMP
    reuse the file. Auto-rendering uses the workspace's configdir via
    :func:`chemigram.core.pipeline.render`. If no current XMP exists
    (fresh workspace, no baseline yet), raises :class:`RuntimeError`.

    Used by both the MCP and CLI mask-generation paths so the preview
    cache key (`_for_mask_<hash[:8]>.jpg`) is shared between adapters.
    """
    from uuid import uuid4

    from chemigram.core.pipeline import render
    from chemigram.core.xmp import write_xmp

    xmp = current_xmp(workspace)
    if xmp is None:
        raise RuntimeError("workspace has no current XMP; cannot render preview for masking")

    cache_path = workspace.previews_dir / f"_for_mask_{xmp_hash(xmp)[:8]}.jpg"
    if cache_path.exists():
        return cache_path

    workspace.previews_dir.mkdir(parents=True, exist_ok=True)
    xmp_path = workspace.previews_dir / f"_render_{uuid4().hex}.xmp"
    write_xmp(xmp, xmp_path)
    try:
        result = render(
            raw_path=workspace.raw_path,
            xmp_path=xmp_path,
            output_path=cache_path,
            width=1024,
            height=1024,
            high_quality=False,
            configdir=workspace.configdir,
        )
    finally:
        xmp_path.unlink(missing_ok=True)

    if not result.success:
        raise RuntimeError(
            f"render failed for masking preview: {result.error_message or 'unknown'}"
        )
    return cache_path
