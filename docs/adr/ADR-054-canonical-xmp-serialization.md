# ADR-054 — Canonical XMP serialization for stable content hashing

> Status · Accepted
> Date · 2026-04-29
> TA anchor ·/components/versioning
> Related RFC · RFC-002 (closes here)
> Related ADR · ADR-008 (opaque blobs), ADR-018 (per-image content-addressed DAG), ADR-050 (parser API + error contract)

## Context

The versioning subsystem keys snapshots by SHA-256 over a canonical byte form of an `Xmp`. For the hash to be stable, the byte form must be deterministic — independent of attribute order, namespace prefix choices, whitespace, or any other XML serialization quirk. RFC-002 framed the determinism rules; this issue (#6) implemented and verified them.

## Decision

`chemigram.core.versioning.canonical_bytes(xmp: Xmp) -> bytes` is the single source of truth for the canonical byte form. `chemigram.core.versioning.xmp_hash(xmp: Xmp) -> str` returns its lowercase 64-char SHA-256 hex digest.

**Determinism rules:**

1. **Namespace prefix map is fixed.** Reuses `chemigram.core.xmp._NS` (`x`, `rdf`, `xmp`, `xmpMM`, `darktable`, `dc`, `lr`, `exif`).
2. **`<rdf:Description>` attribute order is fixed:**
   - `rdf:about=""` first
   - `raw_extra_fields` attrs in their stored order
   - First-class attrs: `xmp:Rating`, then `xmp:Label` (only if non-empty), then `darktable:auto_presets_applied`, `darktable:history_end`, `darktable:iop_order_version`
3. **`<rdf:li>` history entries** emit attributes in `HistoryEntry` field declaration order (`num`, `operation`, `enabled`, `modversion`, `params`, `multi_name`, `multi_name_hand_edited`, `multi_priority`, `blendop_version`, `blendop_params`, then `iop_order` only if not None).
4. **`raw_extra_fields` elem children** are emitted verbatim from their stored XML strings. They were already fixed-point normalized at parse time (`_parse_description_children` in `xmp.py` does one parse-and-re-serialize cycle on capture), so re-serialization is stable.
5. **Encoding:** UTF-8, no BOM, LF line endings. The XML declaration `<?xml version="1.0" encoding="UTF-8"?>\n` is emitted manually rather than via `ET.tostring(xml_declaration=True)` to avoid platform-dependent `\r` injection.
6. **Indentation:** 1 space per level via `ET.indent(tree, space=" ", level=0)`. This matches `write_xmp`'s human-readable output, so users inspecting an object on disk see something familiar.

**Verification:** 12 unit tests in `tests/unit/core/versioning/test_canonical.py` cover hex format, byte-level encoding properties, intra-process stability, equality across equivalent `Xmp` instances, hash sensitivity to every field type, round-trip through `parse_xmp`/`write_xmp`, and snapshot tests against the v3 reference fixture and the minimal fixture (literal expected hashes that fail loudly on regression).

## Rationale

- **`canonical_bytes` is independent of `write_xmp`** rather than a refactored shared implementation. They produce equivalent (in our test snapshots, byte-identical) output today, but their *contracts* differ: `canonical_bytes` guarantees stability for hashing; `write_xmp` produces a file darktable can re-read. Coupling them risks subordinating one contract to the other.
- **Snapshot tests against literal hex hashes** are loud and prevent silent drift. Each future change to canonical rules must update the snapshots intentionally.
- **Reuse of `chemigram.core.xmp` private helpers** (`_NS`, `_clark`, `_qname_to_clark`) keeps two tightly-coupled modules from duplicating XML knowledge. Promoting those helpers to public surface would expose XML internals callers shouldn't depend on.

## Alternatives considered

- **Refactor `write_xmp` to call `canonical_bytes`.** Rejected. The two functions serve different consumers (versioning hash vs. human-readable file output); making one a wrapper of the other entangles their evolution. Snapshot tests will catch any divergence.
- **Use `lxml` for guaranteed canonical output.** Rejected. `lxml` is a native dep; the project's "minimal core, pure Python" stance (per ADR-007 BYOA + ADR-014 dt-orchestration-only) doesn't justify it for one feature.
- **Sort `<rdf:li>` history by content hash to make order irrelevant.** Rejected. History order is semantically meaningful in darktable (later entries override earlier same-`(operation, multi_priority)` slots). Sorting would change semantics.
- **Hash a JSON projection of `Xmp` instead of XML bytes.** Rejected. Adds a translation layer (and its own determinism rules) without simplifying anything; the XML form already exists and is what darktable consumes.
- **Skip indentation for marginally smaller bytes.** Rejected. Indentation is deterministic and the on-disk inspectability matters more than ~10% bytes.

## Consequences

Positive:
- Snapshot hashes are reproducible across CI runs and Python versions
- Regression detection is loud (snapshot tests fail with the new hash printed)
- Pure Python implementation; no new runtime deps
- Round-trip through `parse_xmp` → `canonical_bytes` is byte-stable

Negative:
- `canonical_bytes` and `write_xmp` are two functions that "look like they should be one." Documented; tests verify they don't drift.
- The snapshot tests embed literal hex values that need updating intentionally on rule changes. That's the point — but it adds friction to *legitimate* canonical-rule revisions. Acceptable; rule changes should be rare and deliberate.
- Reaching into `chemigram.core.xmp`'s underscore-prefixed names is a coupling smell that mypy strict and ruff don't flag today. If we add `mypy --no-implicit-reexport` later, the import line will need explicit `__all__` updates in `xmp.py`. Track in TODO if it surfaces.

## Implementation notes

- `src/chemigram/core/versioning/canonical.py` — implementation
- `src/chemigram/core/versioning/__init__.py` — re-exports `canonical_bytes`, `xmp_hash`
- `tests/unit/core/versioning/test_canonical.py` — 12 unit tests
- RFC-002 status moves to `Decided`; remains as historical record
- The next versioning issues (per-image repo, snapshot/checkout/branch ops, mask registry) build on this primitive
