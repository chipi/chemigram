# Changelog

All notable changes to Chemigram will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
per ADR-041.

## [Unreleased]

### Added
- `chemigram.core.versioning` package with `canonical_bytes(xmp) -> bytes`
  and `xmp_hash(xmp) -> str` (issue #6). Deterministic byte form of an
  `Xmp` for content addressing per RFC-002 (closes via **ADR-054**).
  Snapshot tests pin the v3 reference and minimal fixture hashes against
  literal expected values, so any drift in the canonicalization rules
  fails CI loudly. 12 unit tests; 98 unit + 9 integration total.

### Changed
- **Post-Slice-1 cleanup (2026-04-29):**
  - Removed `SynthesisError` from `chemigram.core.xmp` — defined but never raised; YAGNI.
    ADR-050 and ADR-051 amended with implementation notes documenting the removal.
  - Added module docstring to `chemigram.core/__init__.py` (was empty).
  - `parse_xmp` now validates `darktable:history_end ≤ len(history)`; raises
    `XmpParseError` on mismatch (was previously silent).
  - `xmp.label` is now whitespace-stripped on parse to match `dtstyle.description`.
  - `dtstyle.py` adds explicit comment on `multi_name`'s "element required, text
    optional" semantics (ADR-010 user-entry identity marker).
  - `Pipeline.run` replaces `assert` with explicit `RuntimeError` so the invariant
    check survives `python -O`.
  - `DarktableCliStage.clear_locks()` classmethod added for long-running processes
    that cycle through many configdirs (lock-table cleanup).
  - `exif._stringify_tag` strips leading NUL bytes too (was trailing-only).
  - `exif.read_exif` narrows the catch-all `except Exception` to known exifread
    failure modes; truly unexpected exceptions propagate.
  - `render()` docstring documents the tempdir-leak when `configdir=None`.
  - 6 new tests cover error paths previously uncovered (parser missing-element,
    invalid-int, whitespace-only blob, wrong-root; XMP history_end overflow,
    invalid rating, missing description; EXIF malformed focal length, leading-NUL
    stripping; deterministic concurrent-render serialization via mocked subprocess).
  - Coverage: 90% → 96% (line); branch coverage 81% → 88%.
- `chemigram.core.dtstyle.parse_dtstyle` filters `_builtin_*` plugins per ADR-010
  (safety-net per the Phase 0 working notebook). Empty post-filter raises
  `DtstyleParseError`. Two new fixtures cover the filter and the all-filtered case.
- Added two hex-edited dtstyle fixtures (`expo_plus_1p0`, `expo_minus_0p5`) to
  reach Slice 1 gate's "5 different vocabulary primitives" requirement.
- `pyproject.toml` `[project.scripts]` removed `chemigram-mcp` entry point —
  pointed at non-existent `chemigram.mcp.server:main` and would fail at runtime.
  Will re-add when Slice 3 ships the MCP server.
- `docs/IMPLEMENTATION.md`, `README.md`, `docs/concept/00-introduction.md`,
  `CLAUDE.md`: Phase 1 / Slice 1 status updated from "not started" to
  "in progress (3/5 issues; RFC-001 + RFC-006 closed)".
- `docs/adr/TA.md`: `components/synthesizer` "(planned)" → "(shipped)".
- `docs/TODO.md`: new "Slice 1 deferrals" section tracking Path B,
  dtstyle-internal collision validation, and the MCP entry-point re-add.

### Added
- `chemigram.core.exif` + `chemigram.core.binding` — EXIF auto-binding (Slice 1,
  Issue #5). `read_exif` extracts make/model/lens_model/focal_length via
  `exifread`; `bind_l1` resolves L1 vocabulary entries by exact-match on
  `(make, model, lens_model)`. RFC-015 closes into **ADR-053**. 14 unit
  tests + 1 integration test (real D850 NEF).
- `exifread>=3.0` added to runtime deps (pure-Python, no native deps;
  fits BYOA + minimal-core spirit per ADR-007).
- `chemigram.core.pipeline` + `chemigram.core.stages.darktable_cli` — render pipeline
  with `PipelineStage` Protocol, `Pipeline` orchestrator, `DarktableCliStage`
  invoking `darktable-cli` per CLAUDE.md form, and a `render()` convenience entry
  point (Slice 1, Issue #4). Per-configdir threading lock per ADR-005;
  `$DARKTABLE_CLI` env-var override for the macOS .app-bundle case. 13 unit +
  4 integration tests; RFC-005 closes into **ADR-052**.
- `chemigram.core.xmp.synthesize_xmp` — XMP synthesizer (Slice 1, Issue #3).
  Path A only (SET-replace by `(operation, multi_priority)`; last-writer-wins on
  input order; preserves baseline `num` and `iop_order`). Path B raises
  `NotImplementedError` until RFC-001's iop_order question resolves. Closes
  **RFC-001** (parser/synthesizer API → ADR-050) and **RFC-006** (same-module
  collision → ADR-051). 10 unit tests + 1 integration test against real Phase 0
  fixtures.
- `chemigram.core.xmp` — parser + writer for darktable XMP sidecars (Slice 1, Issue #2).
  Public API: `parse_xmp`, `write_xmp`, `Xmp`, `HistoryEntry`, `XmpParseError`.
  Round-trip property (semantic equality) verified against the v3 Phase 0 reference
  (11-entry history with mixed user-authored and `_builtin_*` entries) plus minimal,
  single-entry, and unknown-field fixtures. `iop_order` modeled `Optional[int]` per
  Phase 0 finding (absent in dt 5.4.1 XMPs).
- `chemigram.core.dtstyle` — parser for darktable `.dtstyle` files (Slice 1, Issue #1).
  Public API: `parse_dtstyle`, `DtstyleEntry`, `PluginEntry`, `DtstyleParseError`.
  Calibrated to darktable 5.4.1; opaque blob preservation per ADR-008; user-entry
  identity via empty `<multi_name>` per ADR-010. Uses `defusedxml`.
- Slice 1 prep: `tests/fixtures/{dtstyles,xmps}/` with Phase 0 artifacts;
  hand-stitched `multi_module_synthetic.dtstyle`; `make ci` target mirroring
  `.github/workflows/ci.yml`; smoke tests in `tests/unit/` and `tests/integration/`.
- Phase 2 doc system: PRDs, RFCs, ADRs, reference docs (TA, PA), templates, indexes
- ROADMAP/IMPLEMENTATION plan with slice-by-slice closure-as-gate mapping
- Initial CLAUDE.md operational handbook
- Python project conventions locked via 9 ADRs (ADR-034 through ADR-042)
- Bootstrap project scaffolding (pyproject.toml, pre-commit, CI, release scripts)

### Status

Pre-Phase 1. No published releases yet. The `0.0.x` versions are scaffolding;
the first publishable release will be `0.1.0` at the close of Phase 1 Slice 1.

---

<!--
Format reminder for future releases:

## [0.1.0] - YYYY-MM-DD

### Added
- New features

### Changed
- Behavior changes (still backward-compatible during 0.x)

### Deprecated
- Features marked for removal

### Removed
- Features removed

### Fixed
- Bug fixes

### Security
- Security-relevant changes

### Breaking
- Breaking changes (expected during 0.x; bump minor; document loudly at 1.0+)

[0.1.0]: https://github.com/chipi/chemigram/releases/tag/v0.1.0
-->
