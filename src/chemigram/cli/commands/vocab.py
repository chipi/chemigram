"""``chemigram vocab`` sub-app — list installed entries; show one entry.

Wraps :class:`chemigram.core.vocab.VocabularyIndex`. ``vocab list`` mirrors
the MCP ``list_vocabulary`` tool; ``vocab show`` is a CLI-only helper
(no MCP equivalent) for inspecting a single entry's manifest record +
.dtstyle path.
"""

from __future__ import annotations

from typing import Any, cast

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
            parameterized=entry.parameters is not None,
            parameter_names=([p.name for p in entry.parameters] if entry.parameters else None),
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
        # "did you mean" — surface the closest available names so a typo
        # doesn't require the user to re-list the whole vocabulary.
        import difflib

        all_names = [e.name for e in index.list_all()]
        suggestions = difflib.get_close_matches(name, all_names, n=3, cutoff=0.6)
        suggestion_text = f" did you mean: {', '.join(suggestions)}?" if suggestions else ""
        writer.error(
            f"vocabulary entry not found: {name}.{suggestion_text}",
            ExitCode.NOT_FOUND,
            name=name,
            packs=packs,
            suggestions=suggestions,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    pack_root = index.pack_for(entry.name)
    parameters = _serialize_parameters(entry)
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
        parameters=parameters,
        parameterized=parameters is not None,
    )


@app.command("list-masks")
def list_masks(
    ctx: typer.Context,
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack name (repeatable). Defaults to ['starter'].",
    ),
    tag: list[str] = typer.Option(
        None,
        "--tag",
        help="Filter by tag (repeatable; OR — any matching tag includes the maskdef).",
    ),
) -> None:
    """List named masks (RFC-032) across the loaded packs."""
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

    masks = index.list_masks(tags=tag if tag else None)
    for mask in masks:
        pack_root = index.mask_pack_for(mask.name)
        writer.event(
            "maskdef_entry",
            name=mask.name,
            description=mask.description,
            pack=str(pack_root) if pack_root else None,
            tags=list(mask.tags),
            spec=mask.spec,
            llm_vision_prompt=mask.llm_vision_prompt,
        )

    writer.result(
        message=f"{len(masks)} maskdef(s) across {len(index.pack_roots)} pack(s)",
        count=len(masks),
        packs=packs,
    )


@app.command("show-mask")
def show_mask(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Maskdef name (e.g. mask_sky)."),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack name (repeatable). Defaults to ['starter'].",
    ),
) -> None:
    """Print one maskdef's manifest fields + spec (RFC-032)."""
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

    mask = index.lookup_mask_by_name(name)
    if mask is None:
        import difflib

        all_names = [m.name for m in index.list_masks()]
        suggestions = difflib.get_close_matches(name, all_names, n=3, cutoff=0.6)
        suggestion_text = f" did you mean: {', '.join(suggestions)}?" if suggestions else ""
        writer.error(
            f"maskdef not found: {name}.{suggestion_text}",
            ExitCode.NOT_FOUND,
            name=name,
            packs=packs,
            suggestions=suggestions,
        )
        raise typer.Exit(code=ExitCode.NOT_FOUND.value)

    pack_root = index.mask_pack_for(mask.name)
    writer.result(
        message=f"maskdef: {mask.name}",
        name=mask.name,
        kind="mask",
        description=mask.description,
        pack=str(pack_root) if pack_root else None,
        tags=list(mask.tags),
        spec=mask.spec,
        llm_vision_prompt=mask.llm_vision_prompt,
        darktable_version=mask.darktable_version,
        source=mask.source,
        license=mask.license,
    )


@app.command("validate")
def validate(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Vocabulary entry name to validate."),
    pack: list[str] = typer.Option(
        None,
        "--pack",
        "-p",
        help="Pack name (repeatable). Defaults to ['starter'].",
    ),
) -> None:
    """Run consistency checks on a vocabulary entry.

    Validates: manifest schema, dtstyle file exists + parses, blendop_params
    bytes decode at the expected size, modversion drift between manifest
    and dtstyle, parameters block declarations valid (ranges + offsets).
    Useful mid-authoring to catch drift before commit.

    Per ADR-072: text + --json output modes. Returns NOT_FOUND if entry
    missing; INVALID_INPUT if any check fails; SUCCESS if all pass.
    """
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

    checks = _run_validation_checks(entry)

    failures = [c for c in checks if c["status"] == "fail"]
    for check in checks:
        writer.event(
            "validation_check",
            check=check["check"],
            status=check["status"],
            detail=check.get("detail"),
        )

    if failures:
        writer.error(
            f"{len(failures)}/{len(checks)} checks failed for {name}",
            ExitCode.INVALID_INPUT,
            name=name,
            failed_count=len(failures),
            total_count=len(checks),
        )
        raise typer.Exit(code=ExitCode.INVALID_INPUT.value)

    writer.result(
        message=f"{len(checks)}/{len(checks)} checks passed for {name}",
        name=name,
        passed_count=len(checks),
        total_count=len(checks),
    )


def _check_touches(entry: Any, dtstyle: Any) -> dict[str, Any]:
    plugin_ops = {p.operation for p in dtstyle.plugins}
    missing = [t for t in entry.touches if t not in plugin_ops]
    if missing:
        return {
            "check": "touches_match_plugins",
            "status": "fail",
            "detail": f"declared in manifest but not in dtstyle: {missing}",
        }
    return {"check": "touches_match_plugins", "status": "pass"}


def _check_modversions(entry: Any, dtstyle: Any) -> dict[str, Any]:
    mismatches = []
    for op, expected_mv in (entry.modversions or {}).items():
        for plugin in dtstyle.plugins:
            if plugin.operation == op and plugin.module != expected_mv:
                mismatches.append(f"{op}: manifest={expected_mv}, dtstyle={plugin.module}")
    if mismatches:
        return {
            "check": "modversions_agree",
            "status": "fail",
            "detail": "; ".join(mismatches),
        }
    return {"check": "modversions_agree", "status": "pass"}


def _check_blendop_size(dtstyle: Any) -> dict[str, Any]:
    from chemigram.core.masking.dt_serialize import _decode_default_blendop_blob

    failures = []
    for plugin in dtstyle.plugins:
        try:
            if plugin.blendop_params.startswith("gz"):
                raw = _decode_default_blendop_blob(plugin.blendop_params)
            else:
                raw = bytes.fromhex(plugin.blendop_params)
            if len(raw) != 420:
                failures.append(f"{plugin.operation}: blendop is {len(raw)} bytes (expected 420)")
        except Exception as exc:
            failures.append(f"{plugin.operation}: {exc}")
    if failures:
        return {
            "check": "blendop_params_size",
            "status": "fail",
            "detail": "; ".join(failures),
        }
    return {"check": "blendop_params_size", "status": "pass"}


def _check_parameters(entry: Any, dtstyle: Any) -> dict[str, Any] | None:
    """Returns None if the entry isn't parameterized."""
    if entry.parameters is None:
        return None
    failures = []
    for p in entry.parameters:
        target_plugin = next(
            (plg for plg in dtstyle.plugins if plg.operation == p.field.module), None
        )
        if target_plugin is None:
            failures.append(
                f"parameter {p.name!r}: target module {p.field.module!r} not in dtstyle plugins"
            )
            continue
        if target_plugin.module != p.field.modversion:
            failures.append(
                f"parameter {p.name!r}: modversion={p.field.modversion} "
                f"but dtstyle plugin {p.field.module} is mv{target_plugin.module}"
            )
    if failures:
        return {
            "check": "parameters_consistent",
            "status": "fail",
            "detail": "; ".join(failures),
        }
    return {"check": "parameters_consistent", "status": "pass"}


def _run_validation_checks(entry: Any) -> list[dict[str, Any]]:
    """Execute the standard consistency checks for one entry. Returns a
    list of {check, status, detail?} dicts. Status is 'pass' or 'fail'.

    Checks: dtstyle_exists, dtstyle_parses, touches_match_plugins,
    modversions_agree, blendop_params_size, parameters_consistent
    (only if entry is parameterized).
    """
    from chemigram.core.dtstyle import DtstyleParseError, parse_dtstyle

    checks: list[dict[str, Any]] = []

    # Early-exit checks (subsequent ones depend on dtstyle parsing)
    if not entry.path.exists():
        checks.append({"check": "dtstyle_exists", "status": "fail", "detail": str(entry.path)})
        return checks
    checks.append({"check": "dtstyle_exists", "status": "pass"})

    try:
        dtstyle = parse_dtstyle(entry.path)
    except DtstyleParseError as exc:
        checks.append({"check": "dtstyle_parses", "status": "fail", "detail": str(exc)})
        return checks
    checks.append({"check": "dtstyle_parses", "status": "pass"})

    # Independent checks (each its own helper to keep complexity bounded)
    checks.append(_check_touches(entry, dtstyle))
    checks.append(_check_modversions(entry, dtstyle))
    checks.append(_check_blendop_size(dtstyle))
    param_check = _check_parameters(entry, dtstyle)
    if param_check is not None:
        checks.append(param_check)

    return checks


def _serialize_parameters(entry: Any) -> list[dict[str, Any]] | None:
    """Render an entry's ParameterSpec list as plain dicts for CLI output.

    Returns None for non-parameterized entries (closes #89). Mirrors the
    MCP _serialize_parameters in chemigram.mcp.tools.vocab_edit so CLI
    and MCP report the same shape — useful for agent / human cross-
    reference. The two helpers are deliberately not shared via import
    because the surfaces have independent stability windows.
    """
    if entry.parameters is None:
        return None
    return [
        {
            "name": p.name,
            "type": p.type,
            "range": list(p.range),
            "default": p.default,
            "module": p.field.module,
            "modversion": p.field.modversion,
            "offset": p.field.offset,
        }
        for p in entry.parameters
    ]
