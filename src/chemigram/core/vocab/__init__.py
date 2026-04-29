"""Vocabulary index: load .dtstyle packs, expose by name / layer / tags / identity.

Each pack is a directory containing a ``manifest.json`` (per
``contracts/vocabulary-manifest`` in TA) and a tree of ``.dtstyle`` files.
The index loads everything eagerly at construction time and validates manifest
entries against the actual files on disk.

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
    - :class:`VocabEntry` — full entry record (manifest fields + parsed dtstyle)
    - :class:`VocabularyIndex` — loaded, validated pack
    - :func:`load_starter` — bundled-pack loader
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


@dataclass(frozen=True)
class VocabEntry:
    """One vocabulary primitive: manifest metadata plus parsed dtstyle."""

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
    mask_kind: str | None = None
    mask_ref: str | None = None
    global_variant: str | None = None
    applies_to: dict[str, str] = field(default_factory=dict)


class VocabularyIndex:
    """Loaded, validated vocabulary pack. Eagerly read at construction.

    Implements :class:`~chemigram.core.binding.VocabularyIndex` Protocol
    (`lookup_l1` only — extended methods are additive).
    """

    def __init__(self, pack_root: Path) -> None:
        """Load and validate the pack at ``pack_root``.

        Raises:
            ManifestError: ``manifest.json`` missing, malformed, references a
                file that doesn't exist, the dtstyle fails to parse, or its
                user-authored plugin's operation isn't in the manifest's
                ``touches`` list.
        """
        self._pack_root = pack_root
        manifest_path = pack_root / "manifest.json"
        if not manifest_path.exists():
            raise ManifestError(f"manifest.json not found at {manifest_path}")

        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ManifestError(f"{manifest_path}: malformed JSON: {exc}") from exc

        entries_raw = raw.get("entries")
        if not isinstance(entries_raw, list):
            raise ManifestError(f"{manifest_path}: top-level 'entries' must be a list")

        by_name: dict[str, VocabEntry] = {}
        l1_entries: list[VocabEntry] = []

        for raw_entry in entries_raw:
            entry = self._build_entry(raw_entry, manifest_path)
            if entry.name in by_name:
                raise ManifestError(f"{manifest_path}: duplicate entry name {entry.name!r}")
            by_name[entry.name] = entry
            if entry.layer == "L1":
                l1_entries.append(entry)

        self._by_name = by_name
        self._l1_entries = tuple(l1_entries)
        self._all_entries = tuple(by_name.values())

    def _build_entry(self, raw: Any, manifest_path: Path) -> VocabEntry:
        self._validate_shape(raw, manifest_path)
        layer = raw["layer"]
        dtstyle_path, dtstyle = self._load_dtstyle(raw, manifest_path)
        touches = self._validate_touches(raw, dtstyle, manifest_path)
        applies_to = self._extract_applies_to(raw, layer, manifest_path)

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
            mask_kind=raw.get("mask_kind"),
            mask_ref=raw.get("mask_ref"),
            global_variant=raw.get("global_variant"),
            applies_to=applies_to,
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

    def _load_dtstyle(self, raw: dict[str, Any], manifest_path: Path) -> tuple[Path, DtstyleEntry]:
        dtstyle_path = (self._pack_root / raw["path"]).resolve()
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


def load_starter() -> VocabularyIndex:
    """Load the bundled starter pack.

    Resolves via :mod:`importlib.resources`; falls back to the in-repo
    ``vocabulary/starter/`` directory for editable installs (``uv sync``)
    where the bundled copy may not be on the filesystem.
    """
    try:
        bundled = resource_files("chemigram") / "_starter_vocabulary"
        bundled_path = Path(cast(Any, bundled))
        if (bundled_path / "manifest.json").exists():
            return VocabularyIndex(bundled_path)
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    repo_pack = Path(__file__).resolve().parents[3] / "vocabulary" / "starter"
    if (repo_pack / "manifest.json").exists():
        return VocabularyIndex(repo_pack)

    raise VocabError(
        "Starter vocabulary pack not found. Looked in the bundled "
        "_starter_vocabulary resource and at vocabulary/starter/manifest.json. "
        "Phase 1 Slice 6 populates the starter pack; until then, construct "
        "VocabularyIndex against a custom pack_root."
    )
