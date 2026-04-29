"""Rendering tools (batch 2 of Slice 3).

Wraps :func:`chemigram.core.pipeline.render` plus XMP resolution for an
arbitrary ref-or-hash. Output paths are deterministic (hash-based) so a
re-render of the same state hits the cache.

``compare`` uses Pillow to stitch two single-state renders into one
side-by-side JPEG; the dependency rationale is in ``pyproject.toml`` — pure
infrastructure, no AI / no image processing logic, just composition.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import uuid4

from PIL import Image, ImageDraw, ImageFont

from chemigram.core.pipeline import render
from chemigram.core.versioning import (
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
)
from chemigram.core.versioning.ops import VersioningError
from chemigram.core.workspace import Workspace
from chemigram.core.xmp import write_xmp
from chemigram.mcp._state import resolve_workspace
from chemigram.mcp.errors import (
    ErrorCode,
    ToolError,
    ToolResult,
    error_invalid_input,
    error_not_found,
)
from chemigram.mcp.registry import ToolContext, register_tool
from chemigram.mcp.tools.versioning import parse_xmp_at

_VALID_FORMATS = {"jpeg", "png"}


def _render_to(
    workspace: Workspace,
    ref_or_hash: str,
    output_path: Path,
    *,
    width: int,
    height: int,
    high_quality: bool,
) -> ToolResult[dict[str, Any]]:
    try:
        xmp = parse_xmp_at(workspace.repo, ref_or_hash)
    except (RefNotFoundError, ObjectNotFoundError, RepoError, VersioningError) as exc:
        return ToolResult.fail(ToolError(code=ErrorCode.VERSIONING_ERROR, message=str(exc)))

    xmp_path = workspace.previews_dir / f"_render_{uuid4().hex}.xmp"
    write_xmp(xmp, xmp_path)
    try:
        result = render(
            raw_path=workspace.raw_path,
            xmp_path=xmp_path,
            output_path=output_path,
            width=width,
            height=height,
            high_quality=high_quality,
            configdir=workspace.configdir,
        )
    finally:
        xmp_path.unlink(missing_ok=True)

    if not result.success:
        return ToolResult.fail(
            ToolError(
                code=ErrorCode.DARKTABLE_ERROR,
                message=result.error_message or "render failed",
                details={"stderr": result.stderr[-2000:]},
            )
        )
    return ToolResult.ok(
        {
            "output_path": str(output_path),
            "duration_seconds": result.duration_seconds,
        }
    )


# --- render_preview -----------------------------------------------------


async def _render_preview(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    size = int(args.get("size", 1024))
    ref_or_hash = args.get("ref_or_hash", "HEAD")
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    output_path = workspace.previews_dir / f"preview_{ref_or_hash[:16]}_{size}.jpg"
    inner = _render_to(
        workspace,
        ref_or_hash,
        output_path,
        width=size,
        height=size,
        high_quality=False,
    )
    if not inner.success:
        return inner
    assert inner.data is not None
    return ToolResult.ok(
        {
            "jpeg_path": inner.data["output_path"],
            "duration_seconds": inner.data["duration_seconds"],
        }
    )


register_tool(
    name="render_preview",
    description=(
        "Render the current XMP (or a specified ref/hash) to a JPEG preview "
        "in the workspace's previews/ directory."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "size": {"type": "integer", "minimum": 64, "maximum": 8192},
            "ref_or_hash": {"type": "string"},
        },
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_render_preview,
)


# --- compare ------------------------------------------------------------


def _stitch_side_by_side(
    left: Path, right: Path, output: Path, *, label_left: str, label_right: str
) -> None:
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


async def _compare(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    hash_a = args["hash_a"]
    hash_b = args["hash_b"]
    size = int(args.get("size", 1024))
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    a_out = workspace.previews_dir / f"_compare_{hash_a[:8]}_{size}.jpg"
    b_out = workspace.previews_dir / f"_compare_{hash_b[:8]}_{size}.jpg"

    a_res = _render_to(workspace, hash_a, a_out, width=size, height=size, high_quality=False)
    if not a_res.success:
        return a_res
    b_res = _render_to(workspace, hash_b, b_out, width=size, height=size, high_quality=False)
    if not b_res.success:
        return b_res

    output = workspace.previews_dir / f"compare_{hash_a[:8]}_{hash_b[:8]}_{size}.jpg"
    _stitch_side_by_side(a_out, b_out, output, label_left=hash_a[:8], label_right=hash_b[:8])
    return ToolResult.ok({"jpeg_path": str(output)})


register_tool(
    name="compare",
    description=(
        "Render two snapshot states and stitch them side-by-side as one labeled comparison JPEG."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "hash_a": {"type": "string"},
            "hash_b": {"type": "string"},
            "size": {"type": "integer", "minimum": 64, "maximum": 8192},
        },
        "required": ["image_id", "hash_a", "hash_b"],
        "additionalProperties": False,
    },
    handler=_compare,
)


# --- export_final -------------------------------------------------------


async def _export_final(args: dict[str, Any], ctx: ToolContext) -> ToolResult[dict[str, Any]]:
    image_id = args["image_id"]
    ref_or_hash = args.get("ref_or_hash", "HEAD")
    fmt = args.get("format", "jpeg")
    if fmt not in _VALID_FORMATS:
        return ToolResult.fail(
            error_invalid_input(
                f"format must be one of {sorted(_VALID_FORMATS)}, got {fmt!r}",
                got=fmt,
            )
        )
    size = args.get("size")
    workspace = resolve_workspace(ctx, image_id)
    if workspace is None:
        return ToolResult.fail(error_not_found(f"image {image_id!r}"))

    extension = "jpg" if fmt == "jpeg" else "png"
    output_path = workspace.exports_dir / f"export_{ref_or_hash[:16]}.{extension}"
    # `size = None` ⇒ caller wants full-resolution. Pipeline takes width/height
    # ints so we pass a sentinel huge value (16384) — darktable-cli treats this
    # as "fit to source"; ADR-004 documents that the flags are upper bounds.
    width = height = size if size is not None else 16384
    inner = _render_to(
        workspace,
        ref_or_hash,
        output_path,
        width=width,
        height=height,
        high_quality=True,
    )
    if not inner.success:
        return inner
    assert inner.data is not None
    return ToolResult.ok(
        {
            "output_path": inner.data["output_path"],
            "duration_seconds": inner.data["duration_seconds"],
            "format": fmt,
        }
    )


register_tool(
    name="export_final",
    description=(
        "Export at high quality to the workspace's exports/ directory. "
        "format ∈ {jpeg, png}; size omitted = full resolution."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "image_id": {"type": "string"},
            "ref_or_hash": {"type": "string"},
            "size": {"type": "integer", "minimum": 64, "maximum": 16384},
            "format": {"type": "string", "enum": ["jpeg", "png"]},
        },
        "required": ["image_id"],
        "additionalProperties": False,
    },
    handler=_export_final,
)
