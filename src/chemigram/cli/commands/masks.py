"""``chemigram masks ...`` sub-app (#58).

Mirrors the five MCP mask tools: ``list_masks``, ``generate_mask``,
``regenerate_mask``, ``tag_mask``, ``invalidate_mask`` (per ADR-033/056).

**Generate / regenerate need a masking provider.** The MCP server gets
one via ``build_server(masker=...)`` (ADR-057/058). The CLI is
subprocess-per-invocation and has no comparable wiring path today:
those two verbs return ``MASKING_ERROR`` with a clear "no masker
configured" hint, mirroring what MCP returns when nothing is injected.
A future follow-up adds config-driven provider selection so scripts
can use a masker too. List / tag / invalidate work without a provider.
"""

from __future__ import annotations

from typing import cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.versioning.masks import (
    MaskError,
    MaskNotFoundError,
)
from chemigram.core.versioning.masks import (
    invalidate_mask as core_invalidate_mask,
)
from chemigram.core.versioning.masks import (
    list_masks as core_list_masks,
)
from chemigram.core.versioning.masks import (
    tag_mask as core_tag_mask,
)
from chemigram.mcp.tools.masks import _serialize_entry

app = typer.Typer(no_args_is_help=True)

_NO_MASKER_HINT = (
    "no masker configured on the CLI; mask generation requires a provider. "
    "Use the MCP server (`chemigram-mcp`) for now — RFC-020 follow-up will "
    "add a config-driven CLI masker."
)


# ---------------------------------------------------------------------------
# masks list
# ---------------------------------------------------------------------------


@app.command("list")
def list_(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
) -> None:
    """List registered masks (newest first)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    entries = core_list_masks(workspace.repo)
    payload = [_serialize_entry(e) for e in entries]
    writer.result(
        message=f"{len(payload)} mask(s) for {image_id}",
        image_id=image_id,
        count=len(payload),
        masks=payload,
    )


# ---------------------------------------------------------------------------
# masks generate / regenerate (require provider — return MASKING_ERROR)
# ---------------------------------------------------------------------------


@app.command("generate")
def generate(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    target: str = typer.Option(..., "--target", help="Subject for the masker (e.g. 'manta')."),
    prompt: str | None = typer.Option(
        None, "--prompt", help="Free-form refinement prompt for the provider."
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Mask registry name (defaults to current_<target>_mask).",
    ),
) -> None:
    """Generate a raster mask via the configured provider.

    The CLI has no provider wiring today (see module docstring). Both
    generate and regenerate exit ``MASKING_ERROR`` (7) with a clear hint.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    # Validate the workspace exists (mirrors MCP: NOT_FOUND for missing image_id)
    resolve_workspace_or_fail(ctx, image_id)
    writer.error(
        _NO_MASKER_HINT,
        ExitCode.MASKING_ERROR,
        image_id=image_id,
        target=target,
        prompt=prompt,
        name=name,
    )
    raise typer.Exit(code=ExitCode.MASKING_ERROR.value)


@app.command("regenerate")
def regenerate(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    name: str = typer.Option(..., "--name", help="Existing mask name to refine."),
    target: str | None = typer.Option(
        None, "--target", help="Override the target (defaults to inferred from name)."
    ),
    prompt: str | None = typer.Option(None, "--prompt", help="Refinement prompt."),
) -> None:
    """Refine an existing mask via the configured provider. (Same MASKING_ERROR
    constraint as ``generate`` — see module docstring.)
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    resolve_workspace_or_fail(ctx, image_id)
    writer.error(
        _NO_MASKER_HINT,
        ExitCode.MASKING_ERROR,
        image_id=image_id,
        name=name,
        target=target,
        prompt=prompt,
    )
    raise typer.Exit(code=ExitCode.MASKING_ERROR.value)


# ---------------------------------------------------------------------------
# masks tag
# ---------------------------------------------------------------------------


@app.command("tag")
def tag(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    source: str = typer.Option(..., "--source", help="Existing mask name."),
    new_name: str = typer.Option(..., "--new-name", help="New name (must be non-empty)."),
) -> None:
    """Copy a mask registry entry under a new name (snapshot-before-regenerate pattern)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    if not new_name.strip():
        writer.error("--new-name must be non-empty", ExitCode.INVALID_INPUT)
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        entry = core_tag_mask(workspace.repo, source, new_name)
    except MaskNotFoundError as exc:
        writer.error(str(exc), ExitCode.NOT_FOUND, image_id=image_id, source=source)
        raise typer.Exit(code=ExitCode.NOT_FOUND.value) from exc
    except MaskError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, image_id=image_id, source=source)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    writer.result(
        message=f"tagged mask {source} as {new_name}",
        image_id=image_id,
        **_serialize_entry(entry),
    )


# ---------------------------------------------------------------------------
# masks invalidate
# ---------------------------------------------------------------------------


@app.command("invalidate")
def invalidate(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    name: str = typer.Option(..., "--name", help="Mask registry name to drop."),
) -> None:
    """Drop a mask from the registry (PNG bytes remain content-addressed)."""
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]

    workspace = resolve_workspace_or_fail(ctx, image_id)
    try:
        core_invalidate_mask(workspace.repo, name)
    except MaskNotFoundError as exc:
        writer.error(str(exc), ExitCode.NOT_FOUND, image_id=image_id, name=name)
        raise typer.Exit(code=ExitCode.NOT_FOUND.value) from exc
    except MaskError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, image_id=image_id, name=name)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    writer.result(
        message=f"invalidated mask {name}",
        image_id=image_id,
        name=name,
        ok=True,
    )
