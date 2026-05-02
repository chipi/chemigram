"""``chemigram export-final`` (#57).

Mirrors MCP ``export_final`` (per ADR-033/056). Calls
:func:`chemigram.core.pipeline.render` directly with ``high_quality=True``
and the workspace's exports/ directory as the destination.
"""

from __future__ import annotations

from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.commands.render import _render_to
from chemigram.cli.exit_codes import ExitCode

_VALID_FORMATS = ("jpeg", "png")
_FULL_RES_SENTINEL = 16384


def export_final(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    ref_or_hash: str = typer.Option(
        "HEAD", "--ref", help="Ref name or hash to export. Defaults to HEAD."
    ),
    format_: str = typer.Option("jpeg", "--format", help="Output format: jpeg or png."),
    size: int | None = typer.Option(
        None,
        "--size",
        min=64,
        max=16384,
        help="Max width/height in pixels. Omit for full resolution.",
    ),
) -> None:
    """High-quality export to the workspace's exports/ directory."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    if format_ not in _VALID_FORMATS:
        writer.error(
            f"--format must be one of {list(_VALID_FORMATS)}, got {format_!r}",
            ExitCode.INVALID_INPUT,
            got=format_,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    workspace = resolve_workspace_or_fail(ctx, image_id)
    extension = "jpg" if format_ == "jpeg" else "png"
    output_path = workspace.exports_dir / f"export_{ref_or_hash[:16]}.{extension}"
    width = height = size if size is not None else _FULL_RES_SENTINEL

    ok, err, details = _render_to(
        workspace, ref_or_hash, output_path, width=width, height=height, high_quality=True
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
            raise typer.Exit(code=ExitCode.VERSIONING_ERROR.value)
        writer.error(
            err or "export failed",
            ExitCode.DARKTABLE_ERROR,
            image_id=image_id,
            **details,
        )
        raise typer.Exit(code=ExitCode.DARKTABLE_ERROR.value)

    writer.result(
        message=f"exported {ref_or_hash[:8]} as {format_}",
        image_id=image_id,
        ref_or_hash=ref_or_hash,
        format=format_,
        output_path=details["output_path"],
        duration_seconds=details["duration_seconds"],
    )
