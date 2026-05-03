"""``chemigram masks ...`` sub-app (#58).

Mirrors the five MCP mask tools: ``list_masks``, ``generate_mask``,
``regenerate_mask``, ``tag_mask``, ``invalidate_mask`` (per ADR-033/056).

**Generate / regenerate use built-in geometric providers** (ADR-074)
when ``--provider`` is set. The CoarseAgentProvider (sampling-based,
ADR-058) is MCP-only because it needs an in-loop agent; the CLI's
provider surface is restricted to the BYOA-compatible geometric
providers (``gradient``, ``radial``, ``rectangle``).

When ``--provider`` is omitted, both verbs exit ``MASKING_ERROR`` with
a hint to set one — preserves the v1.3.0 surface for scripts that
expect that error.
"""

from __future__ import annotations

import json
from typing import Any, cast

import typer

from chemigram.cli._context import CliContext
from chemigram.cli._workspace import resolve_workspace_or_fail
from chemigram.cli.exit_codes import ExitCode
from chemigram.core.helpers import (
    ensure_preview_render,
    serialize_mask_entry,
)
from chemigram.core.masking import MaskingError, MaskingProvider
from chemigram.core.masking.geometric import (
    GradientMaskProvider,
    RadialMaskProvider,
    RectangleMaskProvider,
)
from chemigram.core.versioning.masks import (
    MaskError,
    MaskNotFoundError,
    get_mask,
    register_mask,
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

app = typer.Typer(no_args_is_help=True)

_NO_MASKER_HINT = (
    "no masker configured on the CLI; mask generation requires a provider. "
    "Pass --provider {gradient|radial|rectangle} to use a built-in "
    "geometric provider, or invoke via the MCP server "
    "(`chemigram-mcp`) for the agent-sampling provider."
)


_PROVIDER_BUILDERS: dict[str, type] = {
    "gradient": GradientMaskProvider,
    "radial": RadialMaskProvider,
    "rectangle": RectangleMaskProvider,
}


def _build_provider(provider_name: str, config_json: str | None) -> MaskingProvider:
    """Construct a built-in geometric provider from CLI flags.

    ``config_json`` is a JSON object whose keys map to the provider's
    constructor kwargs (see ``chemigram.core.masking.geometric``).
    Validation errors raise ``MaskingError`` so the CLI maps them
    cleanly to ``MASKING_ERROR``.
    """
    cls = _PROVIDER_BUILDERS.get(provider_name)
    if cls is None:
        raise MaskingError(
            f"unknown provider {provider_name!r}; one of: {sorted(_PROVIDER_BUILDERS)}"
        )
    config: dict[str, Any] = {}
    if config_json:
        try:
            parsed = json.loads(config_json)
        except json.JSONDecodeError as exc:
            raise MaskingError(f"--config is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise MaskingError("--config JSON must be an object/dict")
        config = parsed
    try:
        return cast(MaskingProvider, cls(**config))
    except TypeError as exc:
        raise MaskingError(f"{provider_name} provider rejects config: {exc}") from exc


def _default_mask_name(target: str) -> str:
    safe = target.strip().replace(" ", "_") or "subject"
    return f"current_{safe}_mask"


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
    payload = [serialize_mask_entry(e) for e in entries]
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
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Built-in provider: gradient | radial | rectangle. "
        "Omit for the v1.3.0 'no provider configured' error.",
    ),
    config: str | None = typer.Option(
        None,
        "--config",
        help="JSON object of provider kwargs (e.g. '{\"angle_degrees\": 270}').",
    ),
    prompt: str | None = typer.Option(
        None, "--prompt", help="Free-form prompt; provenance only for geometric providers."
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        help="Mask registry name (defaults to current_<target>_mask).",
    ),
) -> None:
    """Generate a raster mask via a built-in provider; register the result.

    With ``--provider`` set, instantiates the named geometric provider
    (ADR-074) with optional ``--config`` JSON, renders a preview at the
    current XMP, runs the provider, and registers the produced PNG in
    the workspace's mask registry.

    Without ``--provider``, exits ``MASKING_ERROR`` with a hint —
    preserves the v1.3.0 surface for scripts that expect that error.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace = resolve_workspace_or_fail(ctx, image_id)

    if provider is None:
        writer.error(
            _NO_MASKER_HINT,
            ExitCode.MASKING_ERROR,
            image_id=image_id,
            target=target,
            prompt=prompt,
            name=name,
        )
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value)

    try:
        masker = _build_provider(provider, config)
    except MaskingError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, provider=provider)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    try:
        preview = ensure_preview_render(workspace)
    except RuntimeError as exc:
        writer.error(str(exc), ExitCode.STATE_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.STATE_ERROR.value) from exc

    try:
        result = masker.generate(target=target, render_path=preview, prompt=prompt)
    except MaskingError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, provider=provider)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc
    except Exception as exc:
        writer.error(
            f"{provider} provider raised {type(exc).__name__}: {exc}",
            ExitCode.MASKING_ERROR,
            provider=provider,
        )
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    mask_name = name or _default_mask_name(target)
    entry = register_mask(
        workspace.repo,
        mask_name,
        result.png_bytes,
        generator=result.generator,
        prompt=result.prompt,
    )
    writer.result(
        message=f"generated mask {mask_name} via {provider}",
        image_id=image_id,
        provider=provider,
        **serialize_mask_entry(entry),
    )


@app.command("regenerate")
def regenerate(
    ctx: typer.Context,
    image_id: str = typer.Argument(..., help="Image ID."),
    name: str = typer.Option(..., "--name", help="Existing mask name to refine."),
    target: str | None = typer.Option(
        None, "--target", help="Override the target (defaults to inferred from name)."
    ),
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="Built-in provider: gradient | radial | rectangle. "
        "Omit for the v1.3.0 'no provider configured' error.",
    ),
    config: str | None = typer.Option(
        None,
        "--config",
        help="JSON object of provider kwargs.",
    ),
    prompt: str | None = typer.Option(None, "--prompt", help="Refinement prompt."),
) -> None:
    """Refine an existing mask via a built-in provider; re-register under the same name.

    Geometric providers' ``regenerate`` delegates to ``generate`` — the
    prior mask is loaded only to satisfy the Protocol contract.
    """
    obj = cast(CliContext, ctx.obj)
    writer = obj["writer"]
    workspace = resolve_workspace_or_fail(ctx, image_id)

    if provider is None:
        writer.error(
            _NO_MASKER_HINT,
            ExitCode.MASKING_ERROR,
            image_id=image_id,
            name=name,
            target=target,
            prompt=prompt,
        )
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value)

    try:
        _entry, prior_bytes = get_mask(workspace.repo, name)
    except MaskNotFoundError as exc:
        writer.error(str(exc), ExitCode.NOT_FOUND, name=name)
        raise typer.Exit(code=ExitCode.NOT_FOUND.value) from exc
    except MaskError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, name=name)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    effective_target = target or _target_from_name(name)
    if not effective_target:
        writer.error(
            f"cannot infer target for mask {name!r}; pass --target explicitly",
            ExitCode.INVALID_INPUT,
            name=name,
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    try:
        masker = _build_provider(provider, config)
    except MaskingError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, provider=provider)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    try:
        preview = ensure_preview_render(workspace)
    except RuntimeError as exc:
        writer.error(str(exc), ExitCode.STATE_ERROR, image_id=image_id)
        raise typer.Exit(code=ExitCode.STATE_ERROR.value) from exc

    try:
        result = masker.regenerate(
            target=effective_target,
            render_path=preview,
            prior_mask=prior_bytes,
            prompt=prompt,
        )
    except MaskingError as exc:
        writer.error(str(exc), ExitCode.MASKING_ERROR, provider=provider)
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc
    except Exception as exc:
        writer.error(
            f"{provider} provider raised {type(exc).__name__}: {exc}",
            ExitCode.MASKING_ERROR,
            provider=provider,
        )
        raise typer.Exit(code=ExitCode.MASKING_ERROR.value) from exc

    entry = register_mask(
        workspace.repo,
        name,
        result.png_bytes,
        generator=result.generator,
        prompt=result.prompt,
    )
    writer.result(
        message=f"regenerated mask {name} via {provider}",
        image_id=image_id,
        provider=provider,
        **serialize_mask_entry(entry),
    )


def _target_from_name(name: str) -> str:
    """Recover ``target`` from the default-name convention.

    ``"current_manta_mask"`` → ``"manta"``. Returns ``""`` if the name
    doesn't match the convention.
    """
    if name.startswith("current_") and name.endswith("_mask"):
        middle = name[len("current_") : -len("_mask")]
        return middle.replace("_", " ")
    return ""


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
        **serialize_mask_entry(entry),
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
