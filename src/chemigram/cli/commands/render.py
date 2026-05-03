"""Render CLI verbs (#57): render-preview, compare.

Mirrors MCP ``render_preview`` and ``compare`` (per ADR-033/056). Both
call :func:`chemigram.core.pipeline.render` directly (per ADR-071);
subprocess invocation lives inside core.

``compare``'s side-by-side stitch logic lives in
:func:`chemigram.core.helpers.stitch_side_by_side` (Pillow); both the
MCP and CLI adapters import from there.
"""

from __future__ import annotations

from pathlib import Path
from typing import cast
from uuid import uuid4

import typer

from chemigram.cli._batch import aggregate_exit_code, iter_image_ids
from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.helpers import parse_xmp_at, stitch_side_by_side
from chemigram.core.pipeline import render as core_render
from chemigram.core.versioning import (
    ObjectNotFoundError,
    RefNotFoundError,
    RepoError,
)
from chemigram.core.versioning.ops import VersioningError
from chemigram.core.workspace import Workspace
from chemigram.core.xmp import write_xmp


def _render_to(
    workspace: Workspace,
    ref_or_hash: str,
    output_path: Path,
    *,
    width: int,
    height: int,
    high_quality: bool,
) -> tuple[bool, str | None, dict[str, object]]:
    """Render workspace's ref/hash to ``output_path``. Returns
    ``(ok, error_message, details)`` so the caller can map to a writer.

    Mirrors the MCP ``_render_to`` path in
    ``chemigram.mcp.tools.rendering`` — same ref-resolution + temp-XMP
    sequence, same darktable-cli invocation via
    :func:`chemigram.core.pipeline.render`.
    """
    try:
        xmp = parse_xmp_at(workspace.repo, ref_or_hash)
    except (RefNotFoundError, ObjectNotFoundError, RepoError, VersioningError) as exc:
        return False, str(exc), {"kind": "versioning"}

    xmp_path = workspace.previews_dir / f"_render_{uuid4().hex}.xmp"
    write_xmp(xmp, xmp_path)
    output_path.unlink(missing_ok=True)
    try:
        result = core_render(
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
        return (
            False,
            result.error_message or "render failed",
            {"kind": "darktable", "stderr": result.stderr[-2000:]},
        )
    return (
        True,
        None,
        {"output_path": str(output_path), "duration_seconds": result.duration_seconds},
    )


def _do_render_preview(ctx: typer.Context, image_id: str, *, size: int, ref_or_hash: str) -> int:
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    try:
        workspace = resolve_workspace_or_fail(ctx, image_id)
    except typer.Exit as exc:
        return int(exc.exit_code)
    output_path = workspace.previews_dir / f"preview_{ref_or_hash[:16]}_{size}.jpg"
    ok, err, details = _render_to(
        workspace, ref_or_hash, output_path, width=size, height=size, high_quality=False
    )
    if not ok:
        kind = details.get("kind")
        if kind == "versioning":
            writer.error(
                err or "ref not resolvable",
                ExitCode.VERSIONING_ERROR,
                image_id=image_id,
                ref_or_hash=ref_or_hash,
            )
            return ExitCode.VERSIONING_ERROR.value
        writer.error(
            err or "render failed",
            ExitCode.DARKTABLE_ERROR,
            image_id=image_id,
            **details,
        )
        return ExitCode.DARKTABLE_ERROR.value
    writer.result(
        message=f"rendered {ref_or_hash[:8]}",
        image_id=image_id,
        ref_or_hash=ref_or_hash,
        jpeg_path=details["output_path"],
        duration_seconds=details["duration_seconds"],
    )
    return ExitCode.SUCCESS.value


def render_preview(
    ctx: typer.Context,
    image_id: str = typer.Argument(None, help="Image ID (or '-' with --stdin for batch)."),
    size: int = typer.Option(1024, "--size", min=64, max=8192, help="Max width/height in pixels."),
    ref_or_hash: str = typer.Option(
        "HEAD",
        "--ref",
        help="Ref name or content hash to render (defaults to HEAD).",
    ),
    stdin: bool = typer.Option(
        False, "--stdin", help="Read image_ids from stdin (one per line); render each."
    ),
) -> None:
    """Render one snapshot to a JPEG preview in the workspace's previews/."""
    codes = [
        _do_render_preview(ctx, img, size=size, ref_or_hash=ref_or_hash)
        for img in iter_image_ids(stdin, image_id)
    ]
    final = aggregate_exit_code(codes)
    if final != ExitCode.SUCCESS.value:
        raise typer.Exit(code=final)


def compare(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    hash_a: str = typer.Argument(..., help="First ref or hash."),
    hash_b: str = typer.Argument(..., help="Second ref or hash."),
    size: int = typer.Option(1024, "--size", min=64, max=8192, help="Max width/height per side."),
) -> None:
    """Render two snapshots and stitch them side-by-side as a labeled comparison JPEG."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    a_out = workspace.previews_dir / f"_compare_{hash_a[:8]}_{size}.jpg"
    b_out = workspace.previews_dir / f"_compare_{hash_b[:8]}_{size}.jpg"

    for ref, target in ((hash_a, a_out), (hash_b, b_out)):
        ok, err, details = _render_to(
            workspace, ref, target, width=size, height=size, high_quality=False
        )
        if not ok:
            kind = details.get("kind")
            if kind == "versioning":
                writer.error(
                    err or "ref not resolvable",
                    ExitCode.VERSIONING_ERROR,
                    image_id=image_id,
                    ref_or_hash=ref,
                )
                raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value)
            writer.error(
                err or "render failed",
                ExitCode.DARKTABLE_ERROR,
                image_id=image_id,
                **details,
            )
            raise typer.Exit(code=ExitCode.DARKTABLE_ERROR.value)

    output = workspace.previews_dir / f"compare_{hash_a[:8]}_{hash_b[:8]}_{size}.jpg"
    stitch_side_by_side(a_out, b_out, output, label_left=hash_a[:8], label_right=hash_b[:8])

    writer.result(
        message=f"compared {hash_a[:8]} vs {hash_b[:8]}",
        image_id=image_id,
        hash_a=hash_a,
        hash_b=hash_b,
        jpeg_path=str(output),
    )
