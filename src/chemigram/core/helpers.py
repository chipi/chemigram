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
- :func:`apply_with_mask` — synthesize an XMP with one vocab
  entry + a mask binding. Handles drawn masks, parametric range_filter,
  and drawn+parametric composition (ADR-076 / ADR-084 / ADR-085).
  Old name ``apply_with_drawn_mask`` remains as a backcompat alias.
- :func:`apply_spot_retouch` — synthesize an XMP with a single retouch
  form (heal or clone) at the given coordinate (RFC-025 / ADR-087).

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

    # Axis 2: mask binding (ADR-076 drawn / ADR-085 parametric / both) —
    # composes with parameter overrides
    if mask_spec is not None:
        return apply_with_mask(
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


def apply_with_mask(
    baseline: Xmp,
    dtstyle: Any,  # DtstyleEntry — unannotated to avoid circular import
    mask_spec: dict[str, Any],
    *,
    mask_id_seed: int | None = None,
    opacity: float = 100.0,
) -> Xmp:
    """Synthesize a new XMP applying ``dtstyle`` with a mask bound.

    Renamed from ``apply_with_drawn_mask`` after ADR-085 generalized the
    function to handle parametric (range_filter) and drawn+parametric
    composition. The old name remains available as a backcompat alias
    at module level for callers that haven't migrated.

    Handles three valid mask compositions per ADR-085:

    1. **Drawn only**: ``mask_spec`` has ``dt_form`` / ``dt_params`` →
       writes the form into ``masks_history`` and binds via mask_id.
       ``mask_mode = ENABLED | MASK = 3``.
    2. **Parametric only** (range filter): ``mask_spec`` has
       ``range_filter`` (no ``dt_form``) → no ``masks_history``; just
       patches ``blendop_params`` with the parametric mask fields.
       ``mask_mode = ENABLED | CONDITIONAL = 5``.
    3. **Drawn + parametric** (intersection): ``mask_spec`` has both
       ``dt_form`` and ``range_filter`` → writes the form to
       ``masks_history`` AND patches the parametric fields. The edit
       applies to the AND of the two masks. ``mask_mode = 7``,
       ``mask_combine = 0`` (intersection per ADR-085).

    Args:
        baseline: The current XMP to apply onto.
        dtstyle: A ``DtstyleEntry`` (typically ``vocab_entry.dtstyle``);
            its plugins' ``blendop_params`` are patched to bind the mask.
        mask_spec: One of the three forms above. Schema:

            ``{"dt_form": "gradient"|"ellipse"|"rectangle"|"path",``
            `` "dt_params": {<form-kwargs>},``
            `` "range_filter": {"kind": "luminance"|"color_h"|"color_s"|"color_l",``
            ``                  "min": <0..1>, "max": <0..1>,``
            ``                  "feather": <0..0.5>, "invert": <bool>}}``

            ``dt_form`` and ``range_filter`` are both optional; at
            least one must be present. See ``mask-shapes-from-words.md``
            and RFC-024 / ADR-085 for parameter semantics.
        mask_id_seed: Optional explicit mask_id (drawn-mask path only;
            ignored for parametric-only). Default is a hash of the
            spec for determinism within a session.
        opacity: 0..100; default 100.

    Returns:
        A new :class:`Xmp` with the requested mask + edit applied.

    Raises:
        ValueError: ``mask_spec`` is malformed, names an unknown form,
            or has neither ``dt_form`` nor ``range_filter``.
        TypeError: ``dtstyle`` is not a DtstyleEntry.
    """
    import dataclasses

    from chemigram.core.dtstyle import DtstyleEntry
    from chemigram.core.masking.dt_serialize import (
        _decode_default_blendop_blob,
        _encode_blendop_blob,
        encode_blendop_with_parametric_mask,
        patch_blendop_params_string,
    )
    from chemigram.core.xmp import synthesize_xmp

    if not isinstance(dtstyle, DtstyleEntry):
        raise TypeError(f"dtstyle must be a DtstyleEntry, got {type(dtstyle).__name__}")

    has_drawn = "dt_form" in mask_spec
    range_filter = mask_spec.get("range_filter")
    has_parametric = range_filter is not None
    if not has_drawn and not has_parametric:
        raise ValueError("mask_spec must have at least one of 'dt_form' or 'range_filter'")

    # Compute deterministic mask_id only when we have a drawn form.
    if has_drawn and mask_id_seed is None:
        from hashlib import blake2b

        h = blake2b(repr(sorted(mask_spec.items())).encode(), digest_size=4).digest()
        mask_id_seed = 0x10000000 | int.from_bytes(h, "big")

    # ---------------------------------------------------------------
    # Patch every plugin's blendop_params with the right mask binding.
    # ---------------------------------------------------------------

    def _patch_plugin_blendop(blendop_str: str) -> str:
        """Decode → patch → re-encode one plugin's blendop_params."""
        if blendop_str.startswith("gz"):
            raw = _decode_default_blendop_blob(blendop_str)
        else:
            raw = bytes.fromhex(blendop_str)

        if has_parametric:
            assert isinstance(range_filter, dict)
            patched = encode_blendop_with_parametric_mask(
                range_kind=str(range_filter["kind"]),
                range_min=float(range_filter["min"]),
                range_max=float(range_filter["max"]),
                feather=float(range_filter.get("feather", 0.05)),
                invert=bool(range_filter.get("invert", False)),
                mask_id=mask_id_seed if has_drawn else None,
                opacity=opacity,
                base_blendop=raw,
            )
        else:
            # Drawn-only path: same as before, via the existing helper.
            return patch_blendop_params_string(
                blendop_str, mask_id=mask_id_seed or 0, opacity=opacity
            )
        return _encode_blendop_blob(patched)

    patched_plugins = tuple(
        dataclasses.replace(p, blendop_params=_patch_plugin_blendop(p.blendop_params))
        for p in dtstyle.plugins
    )
    patched_dtstyle = dataclasses.replace(dtstyle, plugins=patched_plugins)

    new_xmp = synthesize_xmp(baseline, [patched_dtstyle])

    # ---------------------------------------------------------------
    # Inject masks_history (drawn-form path only; parametric carries
    # everything inline in blendop_params).
    # ---------------------------------------------------------------

    if has_drawn:
        assert mask_id_seed is not None
        return _inject_masks_history_for_drawn(new_xmp, mask_spec=mask_spec, mask_id=mask_id_seed)

    # Parametric-only: no masks_history; the new_xmp already has the
    # patched blendop_params, that's all darktable needs.
    return new_xmp


def _inject_masks_history_for_drawn(
    new_xmp: Xmp, *, mask_spec: dict[str, Any], mask_id: int
) -> Xmp:
    """Inject the drawn-form ``masks_history`` element into the synthesized
    XMP (replacing any existing one, or appending). Helper for
    :func:`apply_with_mask`'s drawn-path branches."""
    import dataclasses

    from chemigram.core.masking.dt_serialize import (
        build_form_from_spec,
        build_masks_history_xml,
    )

    drawn_spec = {
        "dt_form": mask_spec["dt_form"],
        "dt_params": mask_spec.get("dt_params", {}),
    }
    form = build_form_from_spec(mask_id, drawn_spec)
    masks_history_xml = build_masks_history_xml([form])

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


# Backcompat alias: pre-ADR-085 the function was named apply_with_drawn_mask
# (only handled drawn-form masks). After ADR-085 generalized it for
# parametric range_filter + drawn+parametric composition, the canonical
# name is apply_with_mask. Keep the old name resolvable so existing
# callers / tests / external scripts don't break.
apply_with_drawn_mask = apply_with_mask


# ---------------------------------------------------------------------------
# Apply with retouch (spot heal/clone) — RFC-025 / ADR-087
# ---------------------------------------------------------------------------


def _validate_spot_args(
    *,
    kind: str,
    x: float,
    y: float,
    radius: float,
    source_x: float | None,
    source_y: float | None,
    opacity: float,
) -> None:
    """Validate apply_spot_retouch arguments. Raises ValueError on any
    out-of-range or missing-required input. Extracted from the main
    function to keep its complexity bounded (per ADR-038's mypy/ruff
    strictness on chemigram.core)."""
    if kind not in ("heal", "clone"):
        raise ValueError(f"kind must be 'heal' or 'clone', got {kind!r}")
    if not 0.0 <= x <= 1.0:
        raise ValueError(f"x must be in [0, 1], got {x}")
    if not 0.0 <= y <= 1.0:
        raise ValueError(f"y must be in [0, 1], got {y}")
    if not 0.0 < radius <= 1.0:
        raise ValueError(f"radius must be in (0, 1], got {radius}")
    if not 0.0 <= opacity <= 100.0:
        raise ValueError(f"opacity must be in [0, 100], got {opacity}")
    if kind == "clone":
        if source_x is None or source_y is None:
            raise ValueError("clone requires source_x and source_y")
        if not 0.0 <= source_x <= 1.0 or not 0.0 <= source_y <= 1.0:
            raise ValueError("source_x and source_y must be in [0, 1]")


def apply_spot_retouch(
    baseline: Xmp,
    *,
    kind: str,  # "heal" or "clone"
    x: float,
    y: float,
    radius: float,
    source_x: float | None = None,
    source_y: float | None = None,
    opacity: float = 100.0,
    border: float = 0.02,
) -> Xmp:
    """Synthesize an XMP applying a single retouch form (heal or clone).

    Implements the RFC-025 / ADR-087 wire: builds a CIRCLE mask form,
    a retouch op_params with one form referencing the mask_id, and a
    blendop_params with mask binding. Injects the masks_history element
    and snapshots.

    Args:
        baseline: The current XMP to apply onto.
        kind: ``"heal"`` (darktable picks the source via wavelet
            decomposition) or ``"clone"`` (caller specifies source).
        x, y: Spot center in normalized [0, 1] image coords.
        radius: Spot radius in normalized [0, 1] image coords.
        source_x, source_y: Required for ``"clone"``; ignored for
            ``"heal"``. Source region center in normalized coords.
        opacity: 0..100; default 100.
        border: Mask falloff width in normalized coords; default 0.02
            (subtle soft edge, natural blending).

    Returns:
        A new :class:`Xmp` with the retouch plugin appended and
        ``masks_history`` injected.

    Raises:
        ValueError: kind is not "heal" or "clone"; clone with missing
            source_x/source_y; coordinates / radius out of [0, 1];
            opacity out of [0, 100].
    """
    import dataclasses
    from hashlib import blake2b

    from chemigram.core.dtstyle import DtstyleEntry, PluginEntry
    from chemigram.core.masking.dt_serialize import (
        DT_IOP_RETOUCH_CLONE,
        DT_IOP_RETOUCH_HEAL,
        DT_MASKS_CIRCLE,
        DT_MASKS_VERSION,
        DrawnMaskForm,
        build_masks_history_xml,
        empty_mask_src,
        encode_blendop_with_drawn_mask,
        encode_circle_mask_points,
        encode_clone_mask_src,
        encode_mask_blob_for_xmp,
        encode_retouch_form,
        encode_retouch_op_params,
    )
    from chemigram.core.xmp import synthesize_xmp

    _validate_spot_args(
        kind=kind,
        x=x,
        y=y,
        radius=radius,
        source_x=source_x,
        source_y=source_y,
        opacity=opacity,
    )

    # 1. Deterministic mask_id from the spec — same scheme as drawn masks
    spec_repr = repr(
        sorted(
            {
                "kind": kind,
                "x": round(x, 6),
                "y": round(y, 6),
                "radius": round(radius, 6),
                "source_x": round(source_x, 6) if source_x is not None else None,
                "source_y": round(source_y, 6) if source_y is not None else None,
            }.items()
        )
    )
    h = blake2b(spec_repr.encode(), digest_size=4).digest()
    mask_id = 0x10000000 | int.from_bytes(h, "big")

    # 2. Build the CIRCLE mask form
    circle_points = encode_circle_mask_points(center_x=x, center_y=y, radius=radius, border=border)
    if kind == "clone":
        assert source_x is not None and source_y is not None
        mask_src = encode_clone_mask_src(source_x=source_x, source_y=source_y)
    else:
        mask_src = empty_mask_src()
    form = DrawnMaskForm(
        mask_id=mask_id,
        mask_type=DT_MASKS_CIRCLE,
        mask_version=DT_MASKS_VERSION,
        mask_name=f"spot_{kind}",
        mask_points=circle_points,
        mask_nb=1,
        mask_src=mask_src,
    )
    masks_history_xml = build_masks_history_xml([form])

    # 3. Build the retouch op_params: one form, the rest empty
    algorithm = DT_IOP_RETOUCH_CLONE if kind == "clone" else DT_IOP_RETOUCH_HEAL
    retouch_form = encode_retouch_form(formid=mask_id, algorithm=algorithm)
    retouch_op_params = encode_retouch_op_params([retouch_form])
    retouch_op_params_str = encode_mask_blob_for_xmp(retouch_op_params)

    # 4. Build the blendop_params with mask_id binding
    blendop_bytes = encode_blendop_with_drawn_mask(mask_id=mask_id, opacity=opacity)
    blendop_str = encode_mask_blob_for_xmp(blendop_bytes)

    # 5. Build a retouch PluginEntry + DtstyleEntry
    retouch_plugin = PluginEntry(
        operation="retouch",
        num=0,
        module=3,  # retouch mv3
        op_params=retouch_op_params_str,
        blendop_params=blendop_str,
        blendop_version=14,
        multi_priority=0,
        multi_name="",
        enabled=True,
    )
    dtstyle = DtstyleEntry(
        name=f"spot_{kind}",
        description=f"v1.9.0 retouch: {kind} at ({x:.3f}, {y:.3f}) r={radius:.3f}",
        iop_list=None,
        plugins=(retouch_plugin,),
    )

    # 6. Synthesize + inject masks_history
    new_xmp = synthesize_xmp(baseline, [dtstyle])

    new_extra: list[tuple[str, str, str]] = []
    replaced = False
    for fkind, qname, value in new_xmp.raw_extra_fields:
        if fkind == "elem" and qname == "darktable:masks_history":
            new_extra.append((fkind, qname, masks_history_xml))
            replaced = True
        else:
            new_extra.append((fkind, qname, value))
    if not replaced:
        new_extra.append(("elem", "darktable:masks_history", masks_history_xml))

    return dataclasses.replace(new_xmp, raw_extra_fields=tuple(new_extra))
