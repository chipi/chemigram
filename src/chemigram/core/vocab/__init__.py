"""Vocabulary index: load .dtstyle packs, expose by name / layer / tags / identity.

Each pack is a directory containing a ``manifest.json`` (per
``contracts/vocabulary-manifest`` in TA) and a tree of ``.dtstyle`` files.
The index loads everything eagerly at construction time and validates manifest
entries against the actual files on disk.

**Multi-pack loading (RFC-018, v1.2.0):** :class:`VocabularyIndex` accepts
either a single ``pack_root: Path`` (legacy single-pack form) or a
``list[Path]`` (multi-pack form). When multiple packs are loaded, entries are
merged into a single namespace; cross-pack name collisions raise
``ManifestError`` because pack names should be namespaces and a collision
indicates an authoring bug. :func:`load_packs` is the conventional entry point
for multi-pack loading by name.

Implements the :class:`~chemigram.core.binding.VocabularyIndex` Protocol
(declared in v0.1.0) plus name and layer/tag lookup methods needed by the
MCP tool surface (``list_vocabulary``, ``apply_primitive``, ``bind_layers``).

**Tag-filter convention:** :meth:`VocabularyIndex.list_all` treats the ``tags``
parameter as an OR filter — an entry matches if *any* of its tags appear in
the requested set. Recorded here because it's a load-bearing API choice the
agent surface relies on; revisit if Phase 2 evidence shows AND is preferable.

**``applies_to`` shape:** L1 manifest entries declare a top-level
``applies_to`` object with ``make``/``model``/``lens_model`` strings. Per
ADR-053 the match is exact (case-sensitive, no fuzzy) — see
:meth:`VocabularyIndex.lookup_l1`.

Public API:
    - :class:`VocabEntry` — full primitive/look entry record (manifest fields + parsed dtstyle)
    - :class:`MaskdefEntry` — named-mask vocabulary entry (RFC-032)
    - :class:`VocabularyIndex` — loaded, validated pack(s)
    - :func:`load_starter` — bundled starter-pack loader
    - :func:`load_packs` — multi-pack loader by name
    - :func:`resolve_named_mask_spec` — named-mask resolution helper (RFC-032)
    - :class:`VocabError`, :class:`ManifestError` — exceptions
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib.resources import files as resource_files
from pathlib import Path
from typing import Any, cast

from chemigram.core.dtstyle import DtstyleEntry, DtstyleParseError, parse_dtstyle


class VocabError(Exception):
    """Base class for vocabulary loading errors."""


class ManifestError(VocabError):
    """Raised when ``manifest.json`` is malformed or references missing files."""


_REQUIRED_FIELDS = (
    "name",
    "layer",
    "path",
    "touches",
    "tags",
    "description",
    "modversions",
    "darktable_version",
    "source",
    "license",
)
_VALID_LAYERS = ("L1", "L2", "L3")

# Maskdef entries (RFC-032) — fourth vocabulary kind. Distinguished by
# top-level ``kind: "mask"`` discriminator. Different shape from primitive/
# look entries: no dtstyle, no touches, no modversions.
_MASKDEF_REQUIRED_FIELDS = (
    "name",
    "kind",
    "description",
    "tags",
    "darktable_version",
    "source",
    "license",
    "spec",
)


@dataclass(frozen=True)
class ParameterField:
    """Byte-level location declaration for a parameterized op_params field.

    Identifies which module's op_params blob contains the field, the pinned
    modversion the offset is valid against, the byte offset (0-based), and
    the on-wire encoding. Per ADR-078.
    """

    module: str
    modversion: int
    offset: int
    encoding: str  # "le_f32" | "le_i32" | "le_u32"


@dataclass(frozen=True)
class ParameterSpec:
    """One parameter declaration on a parameterized vocabulary entry.

    The schema closes RFC-021 / ADR-078. ``parameters`` on :class:`VocabEntry`
    is always an array (multi-parameter from day one); single-parameter
    entries carry an array of one. The ``field`` block declares the byte-
    level patch location used by :mod:`chemigram.core.parameterize`.
    """

    name: str
    type: str  # "float" today; "int" / "bool" / "enum" reserved
    range: tuple[float, float]  # [min, max] inclusive
    default: float
    field: ParameterField


@dataclass(frozen=True)
class MaskdefEntry:
    """One named-mask vocabulary entry (RFC-032).

    Named masks turn the v1.9.0 mask primitives (drawn / parametric / LLM-
    vision) into composable vocabulary. ``spec`` carries the apply-time mask
    spec (the ``{"dt_form": ..., "range_filter": ...}`` shape that
    :func:`chemigram.core.helpers.apply_with_mask` consumes); resolving a
    named-mask reference is a lookup-and-substitute.

    For LLM-vision-backed masks (sky, subject, eye_region), ``spec`` is the
    parametric *fallback* — what runs when the LLM-vision provider is
    unconfigured. The optional ``llm_vision_prompt`` field declares the
    canonical prompt to route through the masker (ADR-086) when configured;
    LLM-vision integration ships as a follow-up. Phase-1 resolution always
    uses ``spec`` directly.
    """

    name: str
    description: str
    tags: tuple[str, ...]
    darktable_version: str
    source: str
    license: str
    spec: dict[str, Any]
    llm_vision_prompt: str | None = None


@dataclass(frozen=True)
class VocabEntry:
    """One vocabulary primitive: manifest metadata plus parsed dtstyle.

    Note on ``iop_order``: per the empirical evidence in
    ``tests/fixtures/preflight-evidence/`` (RFC-018 finalization), darktable
    5.4.1 does not require per-entry ``iop_order`` for Path B (new-instance
    addition). The synthesizer leaves new entries' ``iop_order`` as ``None``
    and darktable resolves the pipeline position from the description-level
    ``iop_order_version`` + its internal iop_list. The ``VocabEntry`` doesn't
    carry an ``iop_order`` field; the ``HistoryEntry`` it produces has
    ``iop_order=None`` for new instances.
    """

    name: str
    layer: str
    path: Path
    touches: tuple[str, ...]
    tags: tuple[str, ...]
    description: str
    modversions: dict[str, int]
    darktable_version: str
    source: str
    license: str
    dtstyle: DtstyleEntry
    subtype: str | None = None
    global_variant: str | None = None
    applies_to: dict[str, str] = field(default_factory=dict)
    # mask_spec: presence triggers the drawn-mask apply path
    # (chemigram.core.helpers.apply_with_drawn_mask). Shape:
    # ``{"dt_form": "gradient" | "ellipse" | "rectangle",
    #   "dt_params": {<form-kwargs>}}``. The earlier raster-PNG path
    # (mask_kind/mask_ref + MaskingProvider) was removed in v1.5.0 —
    # darktable never reads external PNGs.
    mask_spec: dict[str, Any] | None = None
    # parameters: presence triggers the parameterized apply path per
    # RFC-021 / ADR-077..080. Each parameter declares a byte-level field
    # in the touched module's op_params blob; callers supply values at
    # apply time via ``apply-primitive --value V`` / ``--param NAME=V``
    # (CLI) or the ``value`` argument on the ``apply_primitive`` MCP tool.
    # Multi-parameter from day one (always a tuple, never a scalar).
    parameters: tuple[ParameterSpec, ...] | None = None


class VocabularyIndex:
    """Loaded, validated vocabulary pack(s). Eagerly read at construction.

    Implements :class:`~chemigram.core.binding.VocabularyIndex` Protocol
    (`lookup_l1` only — extended methods are additive).

    Accepts either a single ``Path`` (single-pack form, legacy) or a
    ``list[Path]`` (multi-pack form, RFC-018). Multi-pack loading merges
    entries into one namespace; cross-pack name collisions raise
    ``ManifestError``.
    """

    def __init__(self, pack_root: Path | list[Path]) -> None:
        """Load and validate one or more packs at ``pack_root``.

        Raises:
            ManifestError: ``manifest.json`` missing, malformed, references a
                file that doesn't exist, the dtstyle fails to parse, its
                user-authored plugin's operation isn't in the manifest's
                ``touches`` list, or two packs declare the same entry name.
        """
        if isinstance(pack_root, Path):
            pack_roots: list[Path] = [pack_root]
        else:
            pack_roots = list(pack_root)
        if not pack_roots:
            raise ManifestError("VocabularyIndex requires at least one pack_root")

        self._pack_roots: tuple[Path, ...] = tuple(pack_roots)
        by_name, provenance, l1_entries, masks_by_name, mask_provenance = self._load_all_packs(
            pack_roots
        )
        self._by_name = by_name
        self._provenance = provenance
        self._l1_entries = tuple(l1_entries)
        self._all_entries = tuple(by_name.values())
        self._masks_by_name = masks_by_name
        self._mask_provenance = mask_provenance
        self._all_masks = tuple(masks_by_name.values())

        # Modversion drift detection (RFC-007 closure / ADR-082).
        # Walks the loaded entries; warns on mismatches between manifest
        # declared modversions and the parameterize registry's pinned
        # versions. Strict mode (env var) raises ManifestError instead.
        from chemigram.core.vocab._modversion_drift import emit_drift_signals

        emit_drift_signals(list(self._all_entries))

        # Dtstyle-modversion drift detection (v1.10.0; sister to the
        # manifest-drift check above). Walks each plugin's <module> byte
        # and warns when it disagrees with the engine pin — catches the
        # bug class where dtstyle bytes lie even if the manifest is
        # honest. Same strict-mode env var.
        from chemigram.core.vocab._dtstyle_modversion_drift import emit_dtstyle_drift_signals

        emit_dtstyle_drift_signals(list(self._all_entries))

    def _load_all_packs(
        self, pack_roots: list[Path]
    ) -> tuple[
        dict[str, VocabEntry],
        dict[str, Path],
        list[VocabEntry],
        dict[str, MaskdefEntry],
        dict[str, Path],
    ]:
        by_name: dict[str, VocabEntry] = {}
        provenance: dict[str, Path] = {}
        l1_entries: list[VocabEntry] = []
        masks_by_name: dict[str, MaskdefEntry] = {}
        mask_provenance: dict[str, Path] = {}

        for root in pack_roots:
            manifest_path = root / "manifest.json"
            entries_raw = self._read_manifest(manifest_path)
            for raw_entry in entries_raw:
                self._classify_and_register(
                    raw_entry,
                    manifest_path,
                    root,
                    by_name=by_name,
                    provenance=provenance,
                    l1_entries=l1_entries,
                    masks_by_name=masks_by_name,
                    mask_provenance=mask_provenance,
                )
        return by_name, provenance, l1_entries, masks_by_name, mask_provenance

    def _classify_and_register(
        self,
        raw_entry: Any,
        manifest_path: Path,
        root: Path,
        *,
        by_name: dict[str, VocabEntry],
        provenance: dict[str, Path],
        l1_entries: list[VocabEntry],
        masks_by_name: dict[str, MaskdefEntry],
        mask_provenance: dict[str, Path],
    ) -> None:
        """Discriminate a manifest entry by ``kind`` and register it in the
        right index. ``kind: "mask"`` (RFC-032) routes to the maskdef path;
        any other kind (or absence) routes to the primitive/look path."""
        kind = raw_entry.get("kind", "primitive") if isinstance(raw_entry, dict) else None
        if kind == "mask":
            self._register_maskdef(
                raw_entry, manifest_path, root, by_name, provenance, masks_by_name, mask_provenance
            )
            return
        entry = self._build_entry(raw_entry, manifest_path, root)
        if entry.name in by_name:
            prior = provenance[entry.name]
            if prior == root:
                raise ManifestError(f"{manifest_path}: duplicate entry name {entry.name!r}")
            raise ManifestError(
                f"name collision across packs: {entry.name!r} declared in {prior} and {root}"
            )
        if entry.name in masks_by_name:
            raise ManifestError(
                f"{manifest_path}: entry name {entry.name!r} collides with a maskdef "
                f"of the same name (declared in {mask_provenance[entry.name]})"
            )
        by_name[entry.name] = entry
        provenance[entry.name] = root
        if entry.layer == "L1":
            l1_entries.append(entry)

    def _register_maskdef(
        self,
        raw_entry: Any,
        manifest_path: Path,
        root: Path,
        by_name: dict[str, VocabEntry],
        provenance: dict[str, Path],
        masks_by_name: dict[str, MaskdefEntry],
        mask_provenance: dict[str, Path],
    ) -> None:
        mask_entry = self._build_mask_entry(raw_entry, manifest_path)
        if mask_entry.name in masks_by_name:
            prior = mask_provenance[mask_entry.name]
            if prior == root:
                raise ManifestError(f"{manifest_path}: duplicate maskdef name {mask_entry.name!r}")
            raise ManifestError(
                f"maskdef name collision across packs: {mask_entry.name!r} "
                f"declared in {prior} and {root}"
            )
        if mask_entry.name in by_name:
            raise ManifestError(
                f"{manifest_path}: maskdef name {mask_entry.name!r} collides with "
                f"a primitive/look entry of the same name (declared in "
                f"{provenance[mask_entry.name]})"
            )
        masks_by_name[mask_entry.name] = mask_entry
        mask_provenance[mask_entry.name] = root

    def _read_manifest(self, manifest_path: Path) -> list[Any]:
        if not manifest_path.exists():
            raise ManifestError(f"manifest.json not found at {manifest_path}")
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ManifestError(f"{manifest_path}: malformed JSON: {exc}") from exc
        entries_raw = raw.get("entries")
        if not isinstance(entries_raw, list):
            raise ManifestError(f"{manifest_path}: top-level 'entries' must be a list")
        return entries_raw

    @property
    def pack_roots(self) -> tuple[Path, ...]:
        """Pack roots loaded by this index, in load order."""
        return self._pack_roots

    def pack_for(self, name: str) -> Path | None:
        """Return the pack root that contributed ``name``, or ``None``."""
        return self._provenance.get(name)

    def _build_mask_entry(self, raw: Any, manifest_path: Path) -> MaskdefEntry:
        """Build a :class:`MaskdefEntry` from a manifest entry with
        ``kind: "mask"`` (RFC-032). Validates required fields, the ``spec``
        shape, and the optional ``llm_vision_prompt`` declaration.
        """
        if not isinstance(raw, dict):
            raise ManifestError(
                f"{manifest_path}: maskdef entry must be an object, got {type(raw).__name__}"
            )
        for required in _MASKDEF_REQUIRED_FIELDS:
            if required not in raw:
                raise ManifestError(
                    f"{manifest_path}: maskdef entry missing required field {required!r}: {raw!r}"
                )
        if raw["kind"] != "mask":
            raise ManifestError(
                f"{manifest_path}: maskdef entry {raw['name']!r} has kind "
                f"{raw['kind']!r}; expected 'mask'"
            )
        spec = raw["spec"]
        if not isinstance(spec, dict):
            raise ManifestError(
                f"{manifest_path}: maskdef entry {raw['name']!r} 'spec' must be an object"
            )
        # The ``spec`` here is the apply-time mask_spec — it must have at
        # least one of ``dt_form`` (drawn) or ``range_filter`` (parametric)
        # per ADR-085. This validation matches the apply-time check in
        # ``apply_with_mask`` so authors get errors at load time, not apply
        # time.
        if "dt_form" not in spec and "range_filter" not in spec:
            raise ManifestError(
                f"{manifest_path}: maskdef entry {raw['name']!r} 'spec' must "
                f"have at least one of 'dt_form' (drawn) or 'range_filter' "
                f"(parametric); got {sorted(spec.keys())}"
            )
        llm_prompt = raw.get("llm_vision_prompt")
        if llm_prompt is not None and not isinstance(llm_prompt, str):
            raise ManifestError(
                f"{manifest_path}: maskdef entry {raw['name']!r} "
                f"'llm_vision_prompt' must be a string"
            )
        return MaskdefEntry(
            name=str(raw["name"]),
            description=str(raw["description"]),
            tags=tuple(raw["tags"]),
            darktable_version=str(raw["darktable_version"]),
            source=str(raw["source"]),
            license=str(raw["license"]),
            spec=dict(spec),
            llm_vision_prompt=llm_prompt,
        )

    def _build_entry(self, raw: Any, manifest_path: Path, pack_root: Path) -> VocabEntry:
        self._validate_shape(raw, manifest_path)
        layer = raw["layer"]
        dtstyle_path, dtstyle = self._load_dtstyle(raw, manifest_path, pack_root)
        touches = self._validate_touches(raw, dtstyle, manifest_path)
        applies_to = self._extract_applies_to(raw, layer, manifest_path)
        parameters = self._extract_parameters(raw, manifest_path)

        return VocabEntry(
            name=str(raw["name"]),
            layer=layer,
            path=dtstyle_path,
            touches=touches,
            tags=tuple(raw["tags"]),
            description=str(raw["description"]),
            modversions=dict(raw["modversions"]),
            darktable_version=str(raw["darktable_version"]),
            source=str(raw["source"]),
            license=str(raw["license"]),
            dtstyle=dtstyle,
            subtype=raw.get("subtype"),
            global_variant=raw.get("global_variant"),
            applies_to=applies_to,
            mask_spec=raw.get("mask_spec"),
            parameters=parameters,
        )

    def _validate_shape(self, raw: Any, manifest_path: Path) -> None:
        if not isinstance(raw, dict):
            raise ManifestError(
                f"{manifest_path}: manifest entry must be an object, got {type(raw).__name__}"
            )
        for required in _REQUIRED_FIELDS:
            if required not in raw:
                raise ManifestError(
                    f"{manifest_path}: entry missing required field {required!r}: {raw!r}"
                )
        layer = raw["layer"]
        if layer not in _VALID_LAYERS:
            raise ManifestError(
                f"{manifest_path}: entry {raw['name']!r} has invalid layer {layer!r}; "
                f"expected one of {_VALID_LAYERS}"
            )

    def _load_dtstyle(
        self, raw: dict[str, Any], manifest_path: Path, pack_root: Path
    ) -> tuple[Path, DtstyleEntry]:
        dtstyle_path = (pack_root / raw["path"]).resolve()
        if not dtstyle_path.exists():
            raise ManifestError(
                f"{manifest_path}: entry {raw['name']!r} references missing file {dtstyle_path}"
            )
        try:
            dtstyle = parse_dtstyle(dtstyle_path)
        except DtstyleParseError as exc:
            raise ManifestError(
                f"{manifest_path}: entry {raw['name']!r} dtstyle failed to parse: {exc}"
            ) from exc
        return dtstyle_path, dtstyle

    def _validate_touches(
        self, raw: dict[str, Any], dtstyle: DtstyleEntry, manifest_path: Path
    ) -> tuple[str, ...]:
        touches = tuple(raw["touches"])
        if not touches:
            raise ManifestError(f"{manifest_path}: entry {raw['name']!r} has empty 'touches' list")
        plugin_ops = {p.operation for p in dtstyle.plugins}
        unknown_ops = plugin_ops - set(touches)
        if unknown_ops:
            raise ManifestError(
                f"{manifest_path}: entry {raw['name']!r} dtstyle has plugin operations "
                f"{sorted(unknown_ops)} not declared in 'touches' {list(touches)}"
            )
        return touches

    def _extract_applies_to(
        self, raw: dict[str, Any], layer: str, manifest_path: Path
    ) -> dict[str, str]:
        applies_to_raw = raw.get("applies_to", {})
        if applies_to_raw and not isinstance(applies_to_raw, dict):
            raise ManifestError(
                f"{manifest_path}: entry {raw['name']!r} 'applies_to' must be an object"
            )
        applies_to = {k: str(v) for k, v in applies_to_raw.items()}
        if layer == "L1" and not applies_to:
            raise ManifestError(
                f"{manifest_path}: L1 entry {raw['name']!r} requires 'applies_to' "
                f"with make/model/lens_model"
            )
        return applies_to

    def _extract_parameters(
        self, raw: dict[str, Any], manifest_path: Path
    ) -> tuple[ParameterSpec, ...] | None:
        """Parse the optional ``parameters`` array on a manifest entry.

        Returns ``None`` if the field is absent (entry is not parameterized);
        otherwise validates the shape per ADR-078 and returns a tuple of
        :class:`ParameterSpec`. Raises :class:`ManifestError` on any
        validation failure (name uniqueness within entry, range non-empty,
        default in range, encoding width matches type, field offset is a
        non-negative int).
        """
        params_raw = raw.get("parameters")
        if params_raw is None:
            return None
        if not isinstance(params_raw, list) or not params_raw:
            raise ManifestError(
                f"{manifest_path}: entry {raw['name']!r} 'parameters' must be "
                f"a non-empty list (multi-parameter from day one per ADR-078)"
            )
        seen_names: set[str] = set()
        out: list[ParameterSpec] = []
        for idx, p in enumerate(params_raw):
            if not isinstance(p, dict):
                raise ManifestError(
                    f"{manifest_path}: entry {raw['name']!r} parameters[{idx}] must be an object"
                )
            self._validate_parameter_shape(p, raw["name"], idx, manifest_path)
            name = str(p["name"])
            if name in seen_names:
                raise ManifestError(
                    f"{manifest_path}: entry {raw['name']!r} parameters duplicate name {name!r}"
                )
            seen_names.add(name)
            range_ = (float(p["range"][0]), float(p["range"][1]))
            default = float(p["default"])
            if not (range_[0] <= default <= range_[1]):
                raise ManifestError(
                    f"{manifest_path}: entry {raw['name']!r} parameter {name!r} "
                    f"default {default} outside range {range_}"
                )
            field_raw = p["field"]
            field = ParameterField(
                module=str(field_raw["module"]),
                modversion=int(field_raw["modversion"]),
                offset=int(field_raw["offset"]),
                encoding=str(field_raw["encoding"]),
            )
            out.append(
                ParameterSpec(
                    name=name,
                    type=str(p["type"]),
                    range=range_,
                    default=default,
                    field=field,
                )
            )
        return tuple(out)

    def _validate_parameter_shape(
        self, p: dict[str, Any], entry_name: str, idx: int, manifest_path: Path
    ) -> None:
        prefix = f"{manifest_path}: entry {entry_name!r} parameters[{idx}]"
        for key in ("name", "type", "range", "default", "field"):
            if key not in p:
                raise ManifestError(f"{prefix} missing required key {key!r}")
        if p["type"] not in ("float",):
            raise ManifestError(
                f"{prefix} unsupported type {p['type']!r} (only 'float' currently supported)"
            )
        self._validate_range(p["range"], prefix)
        self._validate_field(p["field"], prefix)

    def _validate_range(self, rng: Any, prefix: str) -> None:
        if not (isinstance(rng, list) and len(rng) == 2):
            raise ManifestError(f"{prefix} 'range' must be a [min, max] list of length 2")
        if rng[0] >= rng[1]:
            raise ManifestError(f"{prefix} 'range' min {rng[0]} must be < max {rng[1]}")

    def _validate_field(self, field: Any, prefix: str) -> None:
        if not isinstance(field, dict):
            raise ManifestError(f"{prefix} 'field' must be an object")
        for key in ("module", "modversion", "offset", "encoding"):
            if key not in field:
                raise ManifestError(f"{prefix}.field missing required key {key!r}")
        if field["encoding"] not in ("le_f32", "le_i32", "le_u32"):
            raise ManifestError(f"{prefix}.field unsupported encoding {field['encoding']!r}")
        if not isinstance(field["offset"], int) or field["offset"] < 0:
            raise ManifestError(f"{prefix}.field 'offset' must be a non-negative integer")

    def lookup_l1(
        self,
        make: str,
        model: str,
        lens_model: str,
    ) -> list[DtstyleEntry]:
        """Exact-match L1 lookup per ADR-053.

        Returns the parsed :class:`DtstyleEntry` of every L1 entry whose
        ``applies_to`` exactly matches ``(make, model, lens_model)``. Returns
        ``[]`` if nothing matches — the expected default during Phase 1
        (ADR-016: starter pack ships no L1 entries).
        """
        matches: list[DtstyleEntry] = []
        for entry in self._l1_entries:
            applies = entry.applies_to
            if (
                applies.get("make") == make
                and applies.get("model") == model
                and applies.get("lens_model") == lens_model
            ):
                matches.append(entry.dtstyle)
        return matches

    def lookup_by_name(self, name: str) -> VocabEntry | None:
        """Return the :class:`VocabEntry` for a symbolic name, or ``None``."""
        return self._by_name.get(name)

    def lookup_mask_by_name(self, name: str) -> MaskdefEntry | None:
        """Return the :class:`MaskdefEntry` for a symbolic name, or ``None``
        (RFC-032). Maskdef and primitive namespaces are unified at the loader
        level (collisions raise) but stored separately for type clarity.
        """
        return self._masks_by_name.get(name)

    def list_masks(
        self,
        *,
        tags: list[str] | None = None,
    ) -> list[MaskdefEntry]:
        """All maskdef entries (RFC-032); optionally filtered by tag.

        ``tags`` is OR — a maskdef matches if any of its tags appears in the
        request list (same convention as :meth:`list_all`).
        """
        result = list(self._all_masks)
        if tags is not None:
            tag_set = set(tags)
            result = [m for m in result if tag_set.intersection(m.tags)]
        return result

    def mask_pack_for(self, name: str) -> Path | None:
        """Return the pack root that contributed maskdef ``name``, or ``None``."""
        return self._mask_provenance.get(name)

    def list_all(
        self,
        *,
        layer: str | None = None,
        tags: list[str] | None = None,
    ) -> list[VocabEntry]:
        """All entries; optionally filtered.

        ``layer`` is exact-match (one of L1/L2/L3). ``tags`` is OR — an entry
        matches if any of its tags appears in the request list (see module
        docstring for the rationale).
        """
        result = list(self._all_entries)
        if layer is not None:
            result = [e for e in result if e.layer == layer]
        if tags is not None:
            tag_set = set(tags)
            result = [e for e in result if tag_set.intersection(e.tags)]
        return result


def resolve_named_mask_spec(
    spec: dict[str, Any] | None,
    vocab: VocabularyIndex,
) -> dict[str, Any] | None:
    """Resolve a named mask reference to a concrete apply-time mask_spec.

    Implements the RFC-032 named-mask resolution layer that sits between the
    caller-provided ``mask_spec`` and the apply-time
    :func:`chemigram.core.helpers.apply_with_mask`. Three cases:

    1. **None** → returned as-is (no mask binding).
    2. **Named reference** — ``{"kind": "named", "name": "<maskdef-name>",
       "invert": <bool>}`` → looks up the maskdef in ``vocab`` and returns a
       deep copy of its ``spec`` field, with optional inversion applied
       (RFC-034). The resolved spec is the same shape that
       ``apply_with_mask`` accepts (drawn / parametric / drawn-and-parametric).
    3. **Already-resolved spec** — anything else passes through unchanged
       (the apply-time validator catches malformed specs).

    Inversion semantics (RFC-034):
    - Parametric specs: toggles ``range_filter.invert`` (XOR).
    - Drawn specs: injects ``invert_drawn: true`` (the apply path flips the
      masks_history ``inverted`` attribute).
    - Drawn + parametric: both — the resulting mask is the inverse of the
      combined region.
    - LLM-vision-routed maskdefs: the parametric fallback inverts; the LLM
      prompt itself is not automatically inverted (the photographer
      constructs the inverse mask by hand via Pattern 7 if needed).

    Phase-1 resolution does not honor ``llm_vision_prompt`` on maskdefs;
    every named-mask reference resolves to the maskdef's parametric/drawn
    ``spec`` field. LLM-vision routing through the ADR-086 masker is a
    follow-up implementation.

    Raises:
        VocabError: ``spec`` is a named reference but the named maskdef
            does not exist in ``vocab``.
    """
    if spec is None:
        return None
    if spec.get("kind") != "named":
        return spec
    if "name" not in spec:
        raise VocabError(
            "named-mask reference is missing 'name' field; "
            "expected {'kind': 'named', 'name': '<maskdef-name>'}"
        )
    target = str(spec["name"])
    maskdef = vocab.lookup_mask_by_name(target)
    if maskdef is None:
        raise VocabError(
            f"named-mask reference {target!r} not found in loaded packs; "
            f"check 'list_masks_vocabulary' or pack manifests"
        )
    # Deep copy so callers can't mutate the maskdef's stored spec dict.
    # Shallow copy is insufficient because mask specs nest (range_filter is
    # itself a dict).
    import copy

    resolved = copy.deepcopy(maskdef.spec)

    # RFC-034 invert flag. Apply at resolution time so downstream call sites
    # (apply_with_mask, the parametric blendop encoder) see the right shape.
    if spec.get("invert", False):
        _apply_inversion(resolved)
    return resolved


def _apply_inversion(spec: dict[str, Any]) -> None:
    """Toggle the inversion field of a resolved parametric mask spec in
    place (RFC-034 v1).

    Parametric inversion is XOR of ``range_filter.invert``. Drawn-only
    inversion is **not yet supported** — would require extending
    DrawnMaskForm + masks_history XML emission to flip darktable's
    ``inverted`` attribute. Tracked as a deferred follow-up; no current
    maskdef is drawn-only (all carry at least a parametric spec or
    parametric fallback), so v1 is sufficient for the named-mask
    catalogue shipped to date.

    Raises ``VocabError`` on a drawn-only spec asked to invert — fail
    loud rather than silently no-op so the user sees the limitation.
    """
    if "range_filter" in spec and isinstance(spec["range_filter"], dict):
        rf = spec["range_filter"]
        rf["invert"] = not bool(rf.get("invert", False))
        return
    if "dt_form" in spec:
        raise VocabError(
            "RFC-034 v1: 'invert: true' is only supported on parametric "
            "(range_filter) maskdef specs. Drawn-only inversion would "
            "require extending masks_history XML emission and is deferred. "
            "Workaround: re-author the maskdef to include a parametric "
            "fallback, or invert the drawn form by-hand at apply time."
        )
    # No range_filter and no dt_form is unreachable per RFC-032 maskdef
    # validation; defensive no-op.


def _resolve_starter_path() -> Path:
    """Locate the starter pack directory (bundled resource or editable install)."""
    try:
        bundled = resource_files("chemigram") / "_starter_vocabulary"
        bundled_path = Path(cast(Any, bundled))
        if (bundled_path / "manifest.json").exists():
            return bundled_path
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    repo_pack = Path(__file__).resolve().parents[4] / "vocabulary" / "starter"
    if (repo_pack / "manifest.json").exists():
        return repo_pack

    raise VocabError(
        "Starter vocabulary pack not found. Looked in the bundled "
        "_starter_vocabulary resource and at vocabulary/starter/manifest.json. "
        "Reinstall the package or construct VocabularyIndex against a "
        "custom pack_root."
    )


def _resolve_pack_path(name: str) -> Path:
    """Resolve a non-starter pack name to a directory.

    Search order:
    1. ``~/.chemigram/packs/<name>/`` — user-installed personal pack
    2. ``vocabulary/packs/<name>/`` — in-repo (editable install)

    Future: bundled-resource fallback once shipped packs are bundled
    alongside the starter resource.
    """
    home = Path.home() / ".chemigram" / "packs" / name
    if (home / "manifest.json").exists():
        return home

    repo_pack = Path(__file__).resolve().parents[4] / "vocabulary" / "packs" / name
    if (repo_pack / "manifest.json").exists():
        return repo_pack

    raise VocabError(
        f"Vocabulary pack {name!r} not found. Looked in {home} and {repo_pack}. "
        f"Install the pack to ~/.chemigram/packs/<name>/ or construct "
        f"VocabularyIndex against a custom pack_root."
    )


def load_starter() -> VocabularyIndex:
    """Load the bundled starter pack as a single-pack index.

    Equivalent to ``load_packs(["starter"])`` but kept as a stable alias
    for the common case (single-pack default).
    """
    return VocabularyIndex(_resolve_starter_path())


def load_packs(pack_names: list[str]) -> VocabularyIndex:
    """Load and merge the named vocabulary packs (RFC-018, v1.2.0).

    Resolution: ``"starter"`` resolves to the bundled starter pack; any
    other name resolves to ``~/.chemigram/packs/<name>/`` (user override)
    or ``vocabulary/packs/<name>/`` (editable install). Cross-pack name
    collisions raise ``ManifestError``.

    Pack order matters for explanation only — the resulting index has a
    flat namespace, so collisions are reported in input order.
    """
    if not pack_names:
        raise VocabError("load_packs requires at least one pack name")
    pack_roots: list[Path] = []
    for name in pack_names:
        if name == "starter":
            pack_roots.append(_resolve_starter_path())
        else:
            pack_roots.append(_resolve_pack_path(name))
    return VocabularyIndex(pack_roots)
