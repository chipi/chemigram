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
- :func:`stitch_side_by_side` — Pillow-based two-up image composition
  (used by the ``compare`` verb in both adapters)
- :func:`apply_with_drawn_mask` — synthesize an XMP with one vocab
  entry + a drawn mask binding (the only mask path that actually wires
  to darktable; the earlier PNG-file path was a silent no-op)

What stays in ``chemigram.mcp._state``:

- :func:`resolve_workspace` — looks up a workspace by ``image_id`` against
  the per-MCP-session ``ToolContext.workspaces`` registry. MCP-only by
  shape (the CLI loads workspaces from disk via
  ``chemigram.cli._workspace.load_workspace`` instead).
"""

from __future__ import annotations

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
# Apply with parameter overrides (RFC-021 / ADR-077)
# ---------------------------------------------------------------------------


def _apply_parameter_values_to_dtstyle(
    dtstyle: Any,  # DtstyleEntry; unannotated to avoid circular import
    parameters: tuple[Any, ...],  # tuple[ParameterSpec, ...]
    values: dict[str, float],
) -> Any:
    """Return a new ``DtstyleEntry`` with each parameter's ``op_params``
    field patched per the supplied ``values`` dict.

    For each :class:`ParameterSpec` in ``parameters``: if the parameter's
    name appears in ``values``, locate the plugin in the dtstyle whose
    ``operation`` matches the parameter's ``field.module``, decode its
    ``op_params`` via :mod:`chemigram.core.parameterize`, edit the field,
    re-encode, and substitute the patched plugin into the dtstyle's
    plugins tuple. Parameters whose name isn't in ``values`` are skipped
    (the dtstyle's existing default field value carries through).

    Modversion mismatches between the dtstyle's plugin and the parameter
    spec raise :class:`PatchError`. Callers should validate values
    against the parameter declaration's range before reaching this code;
    this function applies whatever values it's given.
    """
    import dataclasses

    from chemigram.core.parameterize import patch_op_params

    # Group parameter values by target module so each plugin's op_params
    # is decoded/encoded at most once.
    values_by_module: dict[str, dict[str, float]] = {}
    spec_by_module: dict[str, Any] = {}
    for spec in parameters:
        if spec.name not in values:
            continue
        mod = spec.field.module
        values_by_module.setdefault(mod, {})[spec.name] = values[spec.name]
        spec_by_module[mod] = spec  # any spec for the module is fine for modversion lookup

    if not values_by_module:
        return dtstyle

    new_plugins = []
    for plug in dtstyle.plugins:
        if plug.operation in values_by_module:
            spec = spec_by_module[plug.operation]
            patched_hex = patch_op_params(
                plug.op_params,
                module=plug.operation,
                modversion=spec.field.modversion,
                values=values_by_module[plug.operation],
            )
            new_plugins.append(dataclasses.replace(plug, op_params=patched_hex))
        else:
            new_plugins.append(plug)
    return dataclasses.replace(dtstyle, plugins=tuple(new_plugins))


def apply_entry(
    baseline: Xmp,
    entry: Any,  # VocabEntry; unannotated to avoid circular import
    *,
    parameter_values: dict[str, float] | None = None,
    mask_spec: dict[str, Any] | None = None,
    mask_id_seed: int | None = None,
    opacity: float = 100.0,
) -> Xmp:
    """Apply a vocabulary entry to a baseline XMP, with optional parameter
    overrides and/or drawn-mask binding.

    Composes three orthogonal axes:

    1. **Plain apply** (no parameters, no mask) — synthesizes the entry's
       dtstyle directly onto baseline. Same shape as ``synthesize_xmp(
       baseline, [entry.dtstyle])``.
    2. **Parameterized apply** (``parameter_values`` supplied) — patches
       the dtstyle's plugins' ``op_params`` per the entry's declared
       parameters before synthesizing (RFC-021 / ADR-077).
    3. **Drawn-mask apply** (``mask_spec`` supplied) — binds the mask
       form to every plugin's ``blendop_params`` and injects
       ``masks_history`` (ADR-076).

    All three combinations are valid; (2) and (3) compose by editing
    ``op_params`` first, then ``blendop_params``, on the same plugins.

    Args:
        baseline: The current XMP to apply onto.
        entry: A :class:`~chemigram.core.vocab.VocabEntry`.
        parameter_values: Optional dict mapping parameter name to value.
            Must match names declared in ``entry.parameters``.
        mask_spec: Optional drawn-mask spec per ADR-076.
        mask_id_seed: Optional explicit mask_id (mask path only).
        opacity: Mask opacity (0..100; mask path only).

    Returns:
        A new :class:`Xmp` with the requested transformations applied.

    Raises:
        TypeError: ``entry`` is not a VocabEntry, or ``entry.parameters``
            is None when ``parameter_values`` is supplied.
        chemigram.core.parameterize.PatchError: parameter patching failed
            (modversion mismatch, no decoder registered, blob size
            mismatch).
        ValueError: ``mask_spec`` is malformed or names an unknown form.
    """
    from chemigram.core.vocab import VocabEntry
    from chemigram.core.xmp import synthesize_xmp

    if not isinstance(entry, VocabEntry):
        raise TypeError(f"entry must be a VocabEntry, got {type(entry).__name__}")

    dtstyle = entry.dtstyle

    # Axis 1: parameter overrides (RFC-021)
    if parameter_values:
        if entry.parameters is None:
            raise TypeError(
                f"entry {entry.name!r} has no 'parameters' declaration; "
                f"cannot apply parameter_values={parameter_values!r}"
            )
        dtstyle = _apply_parameter_values_to_dtstyle(dtstyle, entry.parameters, parameter_values)

    # Axis 2: drawn-mask binding (ADR-076) — composes with parameter overrides
    if mask_spec is not None:
        return apply_with_drawn_mask(
            baseline,
            dtstyle,
            mask_spec,
            mask_id_seed=mask_id_seed,
            opacity=opacity,
        )

    # Plain (or parameter-only) apply
    return synthesize_xmp(baseline, [dtstyle])


# ---------------------------------------------------------------------------
# Apply with drawn-mask binding
# ---------------------------------------------------------------------------


def apply_with_drawn_mask(
    baseline: Xmp,
    dtstyle: Any,  # DtstyleEntry — unannotated to avoid circular import
    mask_spec: dict[str, Any],
    *,
    mask_id_seed: int | None = None,
    opacity: float = 100.0,
) -> Xmp:
    """Synthesize a new XMP applying ``dtstyle`` with a drawn mask bound.

    Replaces the failing PNG-file path: instead of writing a PNG to
    ``<workspace>/masks/`` (which darktable never reads), this encodes
    the mask directly as a darktable drawn form in the XMP's
    ``masks_history`` and modifies the entry's ``blendop_params`` to
    bind the form via ``mask_id``.

    Args:
        baseline: The current XMP to apply onto.
        dtstyle: A ``DtstyleEntry`` (typically ``vocab_entry.dtstyle``);
            its plugins' ``blendop_params`` are patched to bind the mask.
        mask_spec: ``{"dt_form": "gradient"|"ellipse"|"rectangle",
            "dt_params": {<form-kwargs>}}``.
        mask_id_seed: Optional explicit mask_id; default is a hash of the
            spec + content for determinism within a session.
        opacity: 0..100; default 100.

    Returns:
        A new :class:`Xmp` with: (a) every plugin's ``blendop_params``
        patched to bind the mask, (b) ``masks_history`` injected into
        ``raw_extra_fields`` with the form encoded.

    Raises:
        ValueError: ``mask_spec`` is malformed or names an unknown form.
    """
    import dataclasses

    from chemigram.core.dtstyle import DtstyleEntry
    from chemigram.core.masking.dt_serialize import (
        build_form_from_spec,
        build_masks_history_xml,
        patch_blendop_params_string,
    )
    from chemigram.core.xmp import synthesize_xmp

    if not isinstance(dtstyle, DtstyleEntry):
        raise TypeError(f"dtstyle must be a DtstyleEntry, got {type(dtstyle).__name__}")

    if mask_id_seed is None:
        # Deterministic per spec — high range to avoid colliding with any
        # ids darktable would naturally allocate (those start at 1).
        from hashlib import blake2b

        h = blake2b(repr(sorted(mask_spec.items())).encode(), digest_size=4).digest()
        mask_id_seed = 0x10000000 | int.from_bytes(h, "big")

    form = build_form_from_spec(mask_id_seed, mask_spec)
    masks_history_xml = build_masks_history_xml([form])

    # Patch every plugin's blendop_params to bind this mask
    patched_plugins = tuple(
        dataclasses.replace(
            p,
            blendop_params=patch_blendop_params_string(
                p.blendop_params, mask_id=mask_id_seed, opacity=opacity
            ),
        )
        for p in dtstyle.plugins
    )
    patched_dtstyle = dataclasses.replace(dtstyle, plugins=patched_plugins)

    new_xmp = synthesize_xmp(baseline, [patched_dtstyle])

    # Replace any existing masks_history elem; otherwise append it.
    new_extra: list[tuple[str, str, str]] = []
    replaced = False
    for kind, qname, value in new_xmp.raw_extra_fields:
        if kind == "elem" and qname == "darktable:masks_history":
            new_extra.append((kind, qname, masks_history_xml))
            replaced = True
        else:
            new_extra.append((kind, qname, value))
    if not replaced:
        new_extra.append(("elem", "darktable:masks_history", masks_history_xml))

    return dataclasses.replace(new_xmp, raw_extra_fields=tuple(new_extra))
