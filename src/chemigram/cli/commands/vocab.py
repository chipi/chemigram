"""``chemigram vocab`` sub-app — list installed entries; show one entry.

Wraps :class:`chemigram.core.vocab.VocabularyIndex`. ``vocab list`` mirrors
the MCP ``list_vocabulary`` tool; ``vocab show`` is a CLI-only helper
(no MCP equivalent) for inspecting a single entry's manifest record +
.dtstyle path.
"""

from __future__ import annotations

from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.vocab import load_packs

app = typer.Typer(no_args_is_help=True)


def _packs_or_default(pack: list[str] | None) -> list[str]:
    return pack if pack else ["starter"]


@app.command("list")
def list_(
    ctx: typer.Context,
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack name (repeatable). Defaults to ['starter'].",
    ),
    layer: str | None = typer.Option(None, "--layer", help="Filter by layer (L1/L2/L3)."),
) -> None:
    """List vocabulary entries across the loaded packs."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    packs = _packs_or_default(pack)

    try:
        index = load_packs(packs)
    except Exception as exc:
        writer.error(
            f"failed to load packs {packs}: {exc}",
            ExitCode.INVALID_INPUT,
            packs=packs,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    entries = list(index.list_all(layer=layer))
    for entry in entries:
        pack_root = index.pack_for(entry.name)
        writer.event(
            "vocabulary_entry",
            name=entry.name,
            layer=entry.layer,
            description=entry.description,
            pack=str(pack_root) if pack_root else None,
            tags=list(entry.tags),
        )

    writer.result(
        message=f"{len(entries)} entries across {len(index.pack_roots)} pack(s)",
        count=len(entries),
        packs=packs,
    )


@app.command("show")
def show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Vocabulary entry name (e.g. expo_+0.5)."),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack name (repeatable). Defaults to ['starter'].",
    ),
) -> None:
    """Print one entry's manifest fields + .dtstyle path."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    packs = _packs_or_default(pack)

    try:
        index = load_packs(packs)
    except Exception as exc:
        writer.error(
            f"failed to load packs {packs}: {exc}",
            ExitCode.INVALID_INPUT,
            packs=packs,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value) from exc

    entry = index.lookup_by_name(name)
    if entry is None:
        writer.error(
            f"vocabulary entry not found: {name}",
            ExitCode.NOT_FOUND,
            name=name,
            packs=packs,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    pack_root = index.pack_for(entry.name)
    writer.result(
        message=f"entry: {entry.name}",
        name=entry.name,
        layer=entry.layer,
        description=entry.description,
        path=str(entry.path),
        pack=str(pack_root) if pack_root else None,
        touches=list(entry.touches),
        tags=list(entry.tags),
        modversions=dict(entry.modversions),
        darktable_version=entry.darktable_version,
        source=entry.source,
        license=entry.license,
        subtype=entry.subtype,
        mask_spec=entry.mask_spec,
    )
