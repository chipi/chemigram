"""``chemigram ingest`` — bootstrap a workspace from a raw file.

Mirrors the MCP ``ingest`` tool. Calls :func:`chemigram.core.workspace.ingest_workspace`
directly (per ADR-071 — CLI does not go through the MCP tool handler).
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import default_workspace_root
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.vocab import load_packs
from chemigram.core.workspace import ingest_workspace


def ingest(
    ctx: typer.Context,
    raw_path: Path = typer.Argument(
        ...,
        help="Path to the raw image file. Must exist.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        resolve_path=True,
    ),
    image_id: str | None = typer.Option(
        None,
        "--image-id",
        help="Override the derived image_id (default: raw filename stem, sanitized).",
    ),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Vocabulary pack(s) for L1 binding. Defaults to ['starter'].",
    ),
) -> None:
    """Create the per-image repo, snapshot a baseline, suggest L1 bindings."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace_root = obj["workspace"] or default_workspace_root()
    pack_names = pack if pack else ["starter"]

    try:
        vocabulary = load_packs(pack_names)
    except Exception as exc:
        writer.error(
            f"failed to load packs {pack_names}: {exc}",
            ExitCode.INVALID_INPUT,
            packs=pack_names,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    try:
        workspace = ingest_workspace(
            raw_path,
            workspace_root=workspace_root,
            image_id=image_id,
            vocabulary=vocabulary,
        )
    except FileNotFoundError as exc:
        writer.error(str(exc), ExitCode.NOT_FOUND, raw_path=str(raw_path))
        raise typer.Exit(code=ExitCode.NOT_FOUND.value) from exc
    except FileExistsError as exc:
        writer.error(
            str(exc),
            ExitCode.STATE_ERROR,
            hint="pass a fresh --image-id to ingest the same raw twice",
        )
        raise typer.Exit(code=ExitCode.STATE_ERROR.value) from exc

    exif_summary: dict[str, object] | None = None
    if workspace.exif is not None:
        exif_summary = {
            "make": workspace.exif.make,
            "model": workspace.exif.model,
            "lens_model": workspace.exif.lens_model,
            "focal_length_mm": workspace.exif.focal_length_mm,
        }

    writer.result(
        message=f"ingested {workspace.image_id}",
        image_id=workspace.image_id,
        root=str(workspace.root),
        exif_summary=exif_summary,
        suggested_bindings=[
            {"name": entry.name, "description": entry.description or ""}
            for entry in workspace.suggested_bindings
        ],
    )
