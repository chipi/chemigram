# ADR-050 — Parser API and synthesizer error contract

> Status · Accepted
> Date · 2026-04-28
> TA anchor ·/components/synthesizer
> Related RFC · RFC-001 (closes here)
> Related ADR · ADR-008 (opaque blobs), ADR-009 (Path A vs Path B), ADR-010 (multi_name identity), ADR-051 (collision behavior)

## Context

RFC-001 framed the open question as "the concrete code surface" for the synthesizer — the specific dataclasses, function signatures, error types, and edge-case behaviors. ADR-008/009/010 had settled the macro-architecture (opaque blobs, Path A primary, user-entry identity by empty `<multi_name>`) but the API was still aspirational.

Slice 1 Issues #1–#3 implemented and tested the surface end-to-end against real Phase 0 fixtures. The shape held; this ADR locks it.

## Decision

The `chemigram.core.dtstyle` and `chemigram.core.xmp` modules expose:

**`chemigram.core.dtstyle`**
- `parse_dtstyle(path: Path) -> DtstyleEntry` — pure parser; raises `DtstyleParseError` on malformed input; lets `FileNotFoundError` propagate
- `DtstyleEntry` (frozen): `name: str`, `description: str`, `iop_list: str | None`, `plugins: tuple[PluginEntry, ...]`
- `PluginEntry` (frozen): `operation`, `num`, `module` (modversion in dtstyle XML), `op_params` (opaque), `blendop_params` (opaque), `blendop_version`, `multi_priority`, `multi_name`, `enabled`
- `DtstyleParseError(Exception)` — single error type for malformed XML, missing required elements, invalid `<enabled>` values

**`chemigram.core.xmp`**
- `parse_xmp(path: Path) -> Xmp` — `XmpParseError` on malformed input; `FileNotFoundError` propagates
- `write_xmp(xmp: Xmp, path: Path) -> None` — round-trip property: `parse_xmp(write_xmp(x, p)) == x` (semantic equality)
- `synthesize_xmp(baseline: Xmp, entries: list[DtstyleEntry]) -> Xmp` — Path A only; Path B raises `NotImplementedError`
- `Xmp` (frozen): `rating`, `label`, `auto_presets_applied`, `history_end`, `iop_order_version`, `history: tuple[HistoryEntry, ...]`, `raw_extra_fields: tuple[tuple[str, str, str], ...]`
- `HistoryEntry` (frozen): all `<rdf:li>` darktable attributes plus `iop_order: int | None = None` for forward compatibility (absent in dt 5.4.1)
- `XmpParseError` — error hierarchy

**Error contract**

- One exception type per module surface (`DtstyleParseError`, `XmpParseError`)
- Errors include the file path and a specific diagnostic message
- `FileNotFoundError` propagates unwrapped from public functions (Pythonic; callers can catch separately)
- `NotImplementedError` is the explicit signal for Path B until RFC-001's iop_order question resolves; messages name the offending `(operation, multi_priority)` tuple
- Binary blobs (`op_params`, `blendop_params`, `params`, `blendop_params`) flow through as opaque strings; never decoded (ADR-008)

**XML safety**

- `defusedxml` for parsing (untrusted input from contributor packs); standard library `xml.etree.ElementTree` for output (we control)
- `defusedxml` is adopted as a defensive default with no separate ADR; the choice is documented in module docstrings

## Rationale

The shape stabilized through implementation against Phase 0 fixtures and the v3 reference XMP. Specific load-bearing choices:

- **Frozen dataclasses with tuple-typed sequences** make instances hashable and immutable. Hashability matters for collision detection in `synthesize_xmp` (ADR-051) and for upcoming versioning content-addressing (ADR-018).
- **`raw_extra_fields` as opaque round-trip carrier** preserves darktable XMP metadata (timestamps, hashes, masks_history, dc:creator etc.) without modeling each field. Future XMP fields gained from darktable upgrades round-trip automatically.
- **Single error class per module** keeps the surface narrow; sub-classing on demand is cheap to add later.
- **`FileNotFoundError` propagates** rather than being wrapped — Pythonic, and callers may want to differentiate "missing file" from "malformed file" without parsing exception messages.

## Alternatives considered

- **Result-type error returns instead of exceptions**: rejected. Python idiom is exceptions; call sites (MCP server, vocabulary CI) want to log specific failures, which exceptions enable cleanly.
- **Mutate-in-place synthesis**: rejected. Frozen dataclasses + return-new is safer, easier to test, and synthesis is fast enough that the copy cost is irrelevant.
- **Single combined `apply_dtstyle_to_xmp(dtstyle_path, xmp_path) -> xmp_path`**: rejected. Couples parsing and writing, hard to compose multiple primitives in one synthesis pass, hard to test in isolation.
- **Strict XML stub-types (`xml.etree.ElementTree.Element`) on helpers**: rejected. Mixing defusedxml's input tree with stdlib output tree would force explicit type annotations across the module boundary; using `Any` on internal helpers is pragmatic and doesn't leak.
- **Rich error hierarchy (`DtstyleSchemaError`, `DtstyleValidationError` etc.)**: deferred. RFC-001 sketched these; the implementation found one error type per module sufficient for v1. Add subclasses when call sites need to distinguish.

## Consequences

Positive:
- Stable, narrow API surface for `chemigram.core.dtstyle` and `chemigram.core.xmp`
- Frozen dataclasses are safe to share across threads and use as dict keys
- Round-trip property holds against real darktable 5.4.1 XMPs
- Path B's `NotImplementedError` is loud — surfaces gaps as failures, not silent wrong renders

Negative:
- Path B is a real feature gap until iop_order origin is settled (tracked in TODO and RFC-001)
- Single error class per module limits programmatic dispatch on error subtype; mitigation is to subclass when needed
- `Any`-typed XML element helpers lose some mypy precision; mitigation: helpers are private, public surface is fully typed

## Implementation notes

- `src/chemigram/core/dtstyle.py` — parser, dataclasses, `DtstyleParseError`
- `src/chemigram/core/xmp.py` — parser, writer, synthesizer, dataclasses, `XmpParseError`, `_plugin_to_history` helper

**Implementation note (post-Slice-1 cleanup, 2026-04-29):** an earlier draft of this ADR listed `SynthesisError(Exception)` as part of the public error hierarchy. The class was defined but never raised — Path B uses `NotImplementedError`, and no other synthesis-error condition exists today. Per the project's "no dead code" stance, the class was removed in the cleanup commit. Re-introduce when a real synthesis-error condition surfaces.
- Tests: `tests/unit/core/test_dtstyle.py` (10), `tests/unit/core/test_xmp.py` (13), `tests/unit/core/test_synthesize.py` (10), `tests/integration/core/test_synthesis_integration.py` (1)
- ADR-051 separately captures the SET-replace collision rule
- RFC-001 status moves to `Decided`; remains as historical record of the deliberation
