# Changelog

All notable changes to Chemigram will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
per ADR-041.

## [Unreleased]

### Added
- `apply_primitive(mask_override=…)` real path replacing the v0.3.0
  slice=4 stub. Mask-bound L3 entries (`mask_kind: "raster"`) now require
  a registered mask matching `entry.mask_ref` (or the override) to be
  present in the per-image registry; the tool materializes the PNG to
  `<workspace>/masks/<name>.png` (where darktable-cli reads raster
  masks) before snapshotting.
- `chemigram.mcp.tools._masks_apply.materialize_mask_for_dt(workspace,
  mask_name)` helper. Idempotent — skips the write if the file already
  matches the registered hash.
- Test pack gained `tone_lifted_shadows_subject` mask-bound L3 entry
  (`mask_kind: "raster"`, `mask_ref: "current_subject_mask"`).

### Changed
- `apply_primitive(mask_override=...)` no longer returns
  `NOT_IMPLEMENTED slice=4`; now returns `INVALID_INPUT` if passed on a
  non-mask-bound entry, `NOT_FOUND` if the referenced mask isn't
  registered, or success with the mask materialized otherwise. (Pre-
  release; no migration concerns.)

### Added
- `chemigram.core.session` package per ADR-029. `SessionTranscript`
  writes JSONL transcripts to `<workspace>/sessions/<session_id>.jsonl`:
  header line on open, per-turn entries (`tool_call`, `tool_result`,
  `proposal`, `confirmation`, `note`), footer on close. Append-only,
  flushed per write — crashes lose ≤1 entry. `start_session(workspace,
  …)` factory; uuid4 hex session_id by default.
- `chemigram.mcp.registry.ToolContext.transcript: Any = None` field.
  When a transcript is configured, the server's tool dispatch auto-
  appends `tool_call` (with arguments) + `tool_result` (with success +
  error_code) entries. Transcript I/O failures are caught and logged —
  they never abort tool dispatch.
- `chemigram.mcp.server.build_server(transcript=...)` kwarg.
- `chemigram.mcp.server._dispatch_tool` extracted from the call_tool
  handler so transcript wiring + spec lookup + handler call sit in one
  place; reduces mccabe complexity below the project threshold.
- 14 unit tests (transcript shape + idempotency + serialize-failure
  resilience) + 2 integration tests (transcript wired through MCP
  dispatch + transcript-failure-doesn't-abort-dispatch).

### Added
- MCP `generate_mask` / `regenerate_mask` real implementations replacing
  the v0.3.0 slice=4 stubs. Tools render the current XMP to a cached
  preview (hash-keyed in `<workspace>/previews/_for_mask_*.jpg`), pass it
  to the configured `MaskingProvider`, register the result via
  `chemigram.core.versioning.masks.register_mask`. `regenerate_mask`
  passes the prior PNG to the provider for refinement; `target` is
  inferred from the `current_<target>_mask` name convention or required
  explicitly.
- `chemigram.mcp.registry.ToolContext.masker: Any = None` field. When
  unset, `generate_mask` / `regenerate_mask` surface `MASKING_ERROR`
  ("no masker configured") rather than silently failing.
- `chemigram.mcp.server.build_server(masker=...)` kwarg — production
  callers wire `CoarseAgentProvider` against the MCP session's sampling
  callback at server startup; tests inject fakes.

### Changed
- The two mask-generation tools no longer return `NOT_IMPLEMENTED slice=4`;
  callers that relied on the v0.3.0 stub behavior get clean
  `MASKING_ERROR` instead. (Pre-release; no migration concerns.)

### Added
- `chemigram.core.context` package — loaders for the agent's first turn:
  `Tastes` (multi-scope per ADR-048: `_default.md` + brief-declared genres
  with conflict surfacing), `Brief` (parses `Tastes:` line + intent),
  `Notes` (line-truncation summarization per RFC-011: first 10 + last 30
  + ellision marker), `RecentLog` (tail of `log.jsonl`, newest first,
  partial-line tolerant), `RecentGaps` (handles both v0.3.0 minimal and
  post-#24 RFC-013 schemas).
- `chemigram.core.workspace.tastes_dir()` — resolves the global tastes
  directory; defaults to `~/.chemigram/tastes/`, override via
  `CHEMIGRAM_TASTES_DIR` env var.
- 22 unit tests covering all loaders + the env override + backwards-compat
  for legacy gap records.
- `chemigram.core.masking` package — `MaskingProvider` Protocol, `MaskResult`
  dataclass, exception hierarchy (`MaskingError`, `MaskGenerationError`,
  `MaskFormatError`). Sync contract; async path reserved for a follow-up RFC.
- `chemigram.core.masking.coarse_agent.CoarseAgentProvider` — bundled default
  masker. Uses an injected `ask_agent` callable (production: MCP sampling
  round-trip; tests: a fake) to get a region descriptor, rasterizes via
  Pillow to a grayscale PNG matching the render's dimensions. No PyTorch,
  no model weights — satisfies ADR-007 (BYOA). The MCP wiring lands in
  #18; this issue ships the abstraction in isolation per the v0.4.0 plan.
- `polygon_hint` (≥3 points) takes precedence over `bbox`; under-3 points
  fall back to the bbox; neither-present raises `MaskGenerationError`.
- 16 unit tests cover the Protocol shape and the rasterizer (bbox /
  polygon precedence / dimension matching / failure modes).

## [0.3.0] — 2026-04-29

Slice 3 of Phase 1 — agent-callable MCP tool surface.

### Added
- **End-to-end Mode A gate test** (`tests/integration/mcp/test_full_session.py`)
  drives ingest → bind_layers → list_vocabulary → apply_primitive (×2 across
  branches) → snapshot → branch + checkout → diff → tag → log →
  log_vocabulary_gap → read_context (stub) end-to-end through the in-memory
  client/server harness. The render path is exercised conditionally on
  `darktable-cli` availability; with placeholder raw bytes the contract still
  holds (clean `darktable_error`).
- **ADR-056** — closes RFC-010 with the v0.3.0 surface as evidence. Locks the
  return contract (`{success, data, error}`), the closed `ErrorCode` enum
  (9 codes), the `state_after` shape, and tool-naming conventions. ADR-033
  is preserved; ADR-056 supersedes its implementation-path note.
- ADR-033 implementation-note errata: shipped paths use the `chemigram.mcp`
  / `chemigram.core` namespaces (not the underscore forms in earlier drafts).
- **Doc surface sync:**
  - `docs/concept/04-architecture.md` gained paragraphs on the MCP component,
    prompt system, and workspace orchestrator.
  - `docs/adr/TA.md` `components/mcp-server` and `components/prompts` move
    from `(planned)` → `(shipped)`; `## map` updated for RFC-010 / RFC-016
    closure and ADR-056 acceptance.
  - `docs/IMPLEMENTATION.md`, `docs/concept/00-introduction.md`, `README.md`,
    `CLAUDE.md` — Phase 1 status synced to "Slices 1–3 shipped; Slices 4
    (masking) and 5 (context) parallel-unblocked."
- **Version bump** `0.2.0` → `0.3.0` in `pyproject.toml`.

### Added
- **MCP tool batch 3 (ingest + workspace + masks):**
  - `chemigram.core.workspace.ingest_workspace` plus `workspace_id_for`
    helper. Bootstraps a per-image workspace: creates the directory
    layout, initializes `ImageRepo`, symlinks the raw, reads EXIF,
    suggests L1 bindings, builds + snapshots a baseline XMP (using a
    bundled `_baseline_v1.xmp` stand-in until darktable-cli baseline
    generation lands in a later slice), and tags `baseline`.
  - `ingest(raw_path, image_id?, workspace_root?)` MCP tool wraps the
    bootstrap, returns `{image_id, root, exif_summary, suggested_bindings}`,
    and registers the workspace with the server context.
  - `bind_layers(image_id, l1_template?, l2_template?)` validates layer
    membership, synthesizes the templates onto the current XMP, and
    snapshots. With both omitted, returns the current state.
  - `log_vocabulary_gap(image_id, description, workaround?)` appends a
    JSONL record to the image's `vocabulary_gaps.jsonl`.
  - `list_masks` / `tag_mask` / `invalidate_mask` — real wrappers over
    `chemigram.core.versioning.masks` (useful when masks are registered
    out-of-band).
  - `generate_mask` / `regenerate_mask` — stubs returning
    `NOT_IMPLEMENTED` with `slice=4`.
- `Workspace` gained `exif`/`suggested_bindings` fields populated by
  `ingest_workspace`.
- **MCP tool batch 2 (versioning + rendering):**
  - `snapshot(image_id, label?)` → `{hash}`. Wraps `versioning.ops.snapshot`.
  - `checkout(image_id, ref_or_hash)` → `state_after`-shaped summary. Wraps
    `versioning.ops.checkout` (which moves HEAD).
  - `branch(image_id, name, from_?)` → `{ref}`. `from_` must be HEAD or
    fully qualified (`refs/...`); per `ImageRepo.resolve_ref`.
  - `log(image_id, limit?)` → list of `LogEntry` dicts (newest-first).
  - `diff(image_id, hash_a, hash_b)` → list of `PrimitiveDiff` dicts.
  - `tag(image_id, name, hash?)` → `{ref}`. Re-tag with same name returns
    `VERSIONING_ERROR` per ADR-019 immutability.
  - `render_preview(image_id, size=1024, ref_or_hash?)` → `{jpeg_path,
    duration_seconds}`. Renders to `<workspace>/previews/`.
  - `compare(image_id, hash_a, hash_b, size=1024)` → `{jpeg_path}`.
    Renders both states and stitches into one labeled side-by-side JPEG
    via Pillow.
  - `export_final(image_id, ref_or_hash?, size=None, format="jpeg")` →
    `{output_path, duration_seconds, format}`. Writes to
    `<workspace>/exports/`. `format` ∈ {jpeg, png}; size omitted means
    full resolution (16384 sentinel — darktable-cli treats `--width/--height`
    as upper bounds per ADR-004).
- `Pillow>=10.0` added to runtime deps for the `compare` stitch (pure
  composition; rationale comment in `pyproject.toml`).
- **MCP tool batch 1 (vocab + edit + context stubs):**
  - `list_vocabulary(layer?, tags?)` — wraps
    `VocabularyIndex.list_all` (tags filter is OR per the established
    convention). Returns serialized `VocabEntry` records.
  - `get_state(image_id)` — head_hash + entry_count + per-layer presence
    flags; the canonical `state_after` shape per RFC-010.
  - `apply_primitive(image_id, primitive_name, mask_override?)` —
    synthesizes the entry onto current XMP and snapshots; `mask_override`
    is parameter-stable but returns `NOT_IMPLEMENTED` with `slice=4` until
    the masking provider lands.
  - `remove_module(image_id, module_name)` — strips history entries by
    operation, snapshots; `NOT_FOUND` if no entries match.
  - `reset(image_id)` — checkout the workspace's `baseline_ref` (defaults
    to the `baseline` tag) and return its state summary.
  - 5 context-read stubs (`read_context`, `propose_taste_update`,
    `confirm_taste_update`, `propose_notes_update`,
    `confirm_notes_update`) — return `NOT_IMPLEMENTED` with `slice=5`. The
    surface is shape-stable from v0.3.0 forward.
- `chemigram.core.workspace.Workspace` — runtime per-image handle
  (image_id, root, repo, raw_path, baseline_ref, configdir) plus the
  `init_workspace_root(root)` helper that creates the directory shape
  declared in `contracts/per-image-repo`.
- `chemigram.mcp._state` — shared helpers (`summarize_state`,
  `resolve_workspace`, `current_xmp`) reused across tool batches.
- `chemigram.mcp.tools.register_all()` — idempotent registration of every
  tool batch via `importlib.reload`; called from `build_server()`.
- `chemigram.mcp.server` framework — boots the official `mcp` SDK over stdio,
  loads `VocabularyIndex` and `PromptStore` at startup, and dispatches
  registered tools via `chemigram.mcp.registry`. **Partial RFC-010 closure:**
  the error contract types and parameter validation pipeline lock here; full
  closure is the v0.3.0 gate (#16) once tools land.
- `chemigram.mcp.errors` — `ToolResult`, `ToolError`, `ErrorCode` (per
  RFC-010), helper constructors (`error_invalid_input`, `error_not_found`,
  `error_not_implemented`).
- `chemigram.mcp.registry` — global tool registry (`register_tool`,
  `list_registered`, `get_tool`, `clear_registry`) plus `ToolContext`
  carrier for vocabulary/prompts/workspaces.
- `chemigram.mcp._test_harness.in_memory_session` — async context manager
  that pairs the server with an `mcp.client.session.ClientSession` over
  in-memory streams. Used by per-batch integration tests (#13/#14/#15).
- `pyproject.toml` re-adds `chemigram-mcp = "chemigram.mcp.server:main"` as a
  console script. Bumps `mcp` minimum to 1.27 (the SDK API we're integrating
  against; `>=0.9` was a placeholder).
- `chemigram.mcp.prompts.PromptStore` — Jinja2 prompt loader / renderer driven
  by a top-level `MANIFEST.toml` registry. Closes **RFC-016** (versioned
  prompt system) by landing the implementation behind ADR-043, ADR-044, and
  ADR-045. Public API: `render(path, context, *, version=None, provider=None)`,
  `active_version(path)`, `context_schema(path)`, `list_templates()`. Errors
  exposed as `PromptError` / `PromptNotFoundError` /
  `PromptVersionNotFoundError` / `PromptContextError`.
- `src/chemigram/mcp/prompts/MANIFEST.toml` — active-version registry; first
  entry is `mode_a/system` → `v1`.
- `src/chemigram/mcp/prompts/mode_a/system_v1.j2` — Mode A v1 system prompt,
  migrated verbatim from `docs/agent-prompt.md`. Required context: `image_id`,
  `vocabulary_size`. Optional: `masker_available` (gates the local-adjustments
  guidance).
- `src/chemigram/mcp/prompts/mode_a/system_v1.changelog.md` — per-version
  rationale log; new versions append below.
- `scripts/verify-prompts.sh` — CI consistency check that every active-version
  MANIFEST entry resolves to a `<task>_v<N>.j2` file on disk. Wired into
  `make ci` step 7/7 and `.github/workflows/ci.yml`.
- `chemigram.core.vocab.VocabularyIndex` — eager-loading, validated vocabulary
  pack reader. Reads `manifest.json` (per
  `docs/adr/TA.md::contracts/vocabulary-manifest`) plus the referenced
  `.dtstyle` files, validates entry shape + `touches` ↔ plugin operation
  consistency, and exposes `lookup_by_name`, `list_all(layer=, tags=)`, and
  `lookup_l1(make, model, lens_model)` (satisfying the
  `chemigram.core.binding.VocabularyIndex` Protocol per ADR-053).
- `chemigram.core.vocab.load_starter()` resolves the bundled
  `chemigram/_starter_vocabulary/` resource (ADR-049), with a development
  fallback to in-repo `vocabulary/starter/` for editable installs.
- Tag filter on `list_all` is OR (any-match) — documented in the module
  docstring.
- `tests/fixtures/vocabulary/test_pack/` — hand-stitched validation pack
  symlinking existing `tests/fixtures/dtstyles/` files.
- `docs/CONTRIBUTING.md` — new "v0.3.0+ — registry layout" section in the
  Vocabulary contributions area.
- `docs/agent-prompt.md` reduced to a redirect note pointing at the runtime
  source tree (RFC-016 Open Question #4 answered).
- RFC-016 status moved `Accepted → Decided` in `docs/rfc/index.md` and
  `docs/adr/TA.md` `## map`.

### Changed
- **v0.2.0 polish (pre-tag cleanup):**
  - `chemigram.core.xmp` gains `parse_xmp_from_bytes(data, *, source="<bytes>")`
    so callers with in-memory XMP bytes (e.g., content-addressed reads from
    `chemigram.core.versioning`) avoid a filesystem round-trip. `parse_xmp`
    now delegates its post-find logic to a shared private helper, so both
    paths produce identical output.
  - `chemigram.core.versioning.ops.checkout` and `_load_xmp_for_diff`
    refactored to use `parse_xmp_from_bytes` instead of the
    `tempfile.NamedTemporaryFile + parse_xmp + unlink` pattern. ~16 lines
    of duplicated boilerplate removed.
  - `chemigram.core.versioning.canonical.canonical_bytes` no longer
    re-registers namespaces on every call — the `chemigram.core.xmp` import
    triggers registration once at module load. Defensive but redundant.
  - `chemigram.core.versioning.masks._registry_path` return type annotated
    as `Path` (was `Any`) — closes the type-erasure gap.
  - `chemigram.core.versioning.__init__` docstring rewritten: drops the
    "Future modules" framing (the modules are shipped) and adds a section
    documenting the three sibling exception roots (`RepoError`,
    `VersioningError`, `MaskError`) and how to catch the union.
  - `chemigram.core.versioning.ops._resolve_input` docstring documents
    branch-vs-tag precedence on name collision (branch wins).
  - `tests/integration/core/versioning/test_versioning_integration.py`
    tightened: the ops list assertion is now exact-ordered match (catches
    future regressions that add or reorder log entries) instead of the
    previous "in" / count-based weak assertion.
  - `tests/unit/core/versioning/test_ops.py::test_log_entry_dataclass_shape`
    replaced `dataclasses.MISSING` (a sentinel, not a datetime) with a real
    `datetime.now(UTC)`; added assertions that all default fields are None
    and that `LogEntry` rejects mutation (frozen).
  - 5 new tests for `parse_xmp_from_bytes` (round-trip, source label in
    errors, invalid UTF-8, missing rdf:Description, default source).
  - Doc surfaces synced to v0.2.0: `TA.md` `components/versioning` now
    `(shipped)` with full file list and ADR-054/055 anchored; `README.md`
    Phase 1 row mentions Slice 2; `concept/00`, `CLAUDE.md`,
    `IMPLEMENTATION.md` reflect Slice 3 as next; IMPLEMENTATION.md Slice 2
    section marks RFC-002 / RFC-003 ✅ closed.
  - `pyproject.toml` version bumped `0.0.1` → `0.2.0`.
  - Tests now: 175 unit + 10 integration = 185 passing (was 180); coverage
    94% line / 89% branch.

### Added
- `chemigram.core.versioning.masks` — per-image mask registry + raster
  mask storage (issue #9). Closes **RFC-003** via **ADR-055**: PNG bytes
  share the `objects/` store with XMP snapshots (same content-addressed
  primitives, automatic dedup); `masks/registry.json` maps symbolic
  names to hashes plus provenance (generator, prompt, timestamp).
  Public API: `register_mask`, `get_mask`, `list_masks`, `invalidate_mask`,
  `tag_mask` (immutable alias). PNG validation is byte-magic only in
  v0.2.0 (no Pillow dep; full format validation lands with a masking
  provider that needs it). 17 unit tests + inline `make_test_png`
  fixture (~80-byte 8-bit grayscale PNG via `zlib`+`struct`).
- `chemigram.core.versioning` operations: `snapshot`, `checkout`, `branch`,
  `log`, `diff`, `tag` (issue #8). Pure functions over an `ImageRepo` that
  resolve refs, read/write XMP objects via `canonical_bytes`, and append
  structured `LogEntry` records to `log.jsonl`. Branch checkout sets HEAD
  symbolically; tag/hash checkout detaches. `diff` is the per-(operation,
  multi_priority) symmetric difference between two snapshots, sorted for
  stable output. `tag` is immutable. Detached-HEAD snapshots are refused
  (clear `VersioningError`). 26 unit tests + 1 integration test against
  the v3 reference XMP exercising the full snapshot → branch → checkout
  → modify-via-synthesize → diff → tag flow.
- `chemigram.core.versioning.repo.ImageRepo` — per-image filesystem layout
  + low-level objects/refs/HEAD/log primitives (issue #7). Locks ADR-019's
  git-shaped storage into code: content-addressed `objects/NN/REST...`,
  symbolic `HEAD` (resolves through `refs/heads/<branch>` chains),
  branch + tag refs, append-only `log.jsonl` with auto-timestamping.
  Single-writer per ADR-006; cross-process locking out of scope. 29 unit
  tests covering layout, idempotent init, object dedup, ref resolution
  (incl. circular and depth-exceeded paths), delete semantics, log
  round-trip. No new ADR — implementation matches existing decisions.
- `chemigram.core.versioning` package with `canonical_bytes(xmp) -> bytes`
  and `xmp_hash(xmp) -> str` (issue #6). Deterministic byte form of an
  `Xmp` for content addressing per RFC-002 (closes via **ADR-054**).
  Snapshot tests pin the v3 reference and minimal fixture hashes against
  literal expected values, so any drift in the canonicalization rules
  fails CI loudly. 12 unit tests; 127 unit + 9 integration total.

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
