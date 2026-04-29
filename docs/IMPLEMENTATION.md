# Implementation

> The slice-by-slice implementation guide for Chemigram.
> Names slices, gates, RFC closures.
> Source of truth for "what gets built when."
> Last updated · 2026-04-27

This document describes the implementation phases for building Chemigram, decomposed where possible into concrete slices with acceptance gates. Each slice's gate is the moment when a set of RFCs gets closed into ADRs — closure is not a continuous process, it's a checkpoint.

This document supersedes earlier phase descriptions in `docs/briefs/architecture.md` (now historical) and consolidates references previously scattered across `concept/`, `TODO.md`, and ADRs.

---

## Status snapshot

| Phase | Description | Status |
|-|-|-|
| **Phase 0** | Validation — manual XMP composition end-to-end | ✅ Closed green (8 findings logged) |
| **Phase 1** | Minimum viable loop — Python engine, MCP server, starter vocabulary | ✅ **Closed (v1.0.0)** — Slices 1–6 shipped. Issues #1–#29 closed; 13 RFCs closed → ADR-050..061. |
| **Phase 2** | Vocabulary maturation — grow vocab from session evidence | **In progress (use-driven)** — begins post-1.0.0; intermittent, not slice-and-gate work. |
| **Phase 3** | Parametric masks in vocabulary | Conditional — when Phase 2 surfaces gaps |
| **Phase 4** | AI masks via external raster module | Conditional — when local adjustments demand it |
| **Phase 5** | Continuous control via hex encoders (Path C) | Conditional — when discrete vocabulary becomes a bottleneck |

Phases 3–5 are deliberately conditional. They happen only if Phase 2 evidence shows they're worth doing. The project may converge before Phase 5 ever ships; that's a feature, not a failure.

---

## A note on "Phase" naming collisions

Two unrelated senses of "Phase N" exist in this project. To avoid confusion:

- **Implementation phases** (0–5) — the build sequence described in this document. The dominant use of "Phase" going forward.
- **Doc methodology phases** (Phase 1 = concept package, Phase 2 = definition documents) — a methodological layer used to produce `docs/concept/`, `docs/prd/`, `docs/rfc/`, `docs/adr/`. The doc methodology was followed; that work is complete; the term is no longer in active use.

If "Phase 2" appears unqualified in this project from now on, it means the implementation phase (vocabulary maturation), not the doc methodology phase.

---

## Closure-as-gate

A core principle for this project: **RFCs don't close on judgment, they close at slice-gate events.**

Every RFC names which slice's gate produces the evidence that closes it. When a slice's gate is met, the team writes the closing ADRs as part of the slice's wrap-up. This protects against two failure modes:

- **Premature closure** — committing to a schema before any code has exercised it
- **Drift** — RFCs lingering in Draft state because nobody can tell when the moment to close has arrived

Phase 1 has six slices (described below). Each names which RFCs close at its gate.

---

## Phase 0 — Validation [CLOSED GREEN]

**Goal:** prove the vocabulary-composition approach works end-to-end before writing any Python.

**Method:** Author 4 single-module styles by hand in darktable, manually compose them into an XMP, render with `darktable-cli`, confirm the output matches expectations.

**Outcome:** Validated. Lab notebook at `examples/phase-0-notebook.md`. Eight findings closed into ADRs:

- ADR-002 — SET semantics: replace by `(operation, multi_priority)`
- ADR-009 — Path A vs Path B for synthesis
- ADR-010 — Vocabulary parser identifies user entries by empty `<multi_name>`
- ADR-011 — Reject `darktable-cli --style` for vocabulary application
- ADR-012 — `--apply-custom-presets false` always
- ADR-024 — Authoring discipline: uncheck non-target modules in dialog
- ADR-025 — WB and color calibration coupling
- ADR-026 — Vocabulary modversion-pinned to darktable version

**Evidence:** Render time ~2s for 1024px on Apple Silicon (darktable 5.4.1, M-series). Composition works as expected. Same-module collisions handled by SET-replace semantics in our synthesis layer.

**One unexpected result:** Phase 0 testing demonstrated that hex `op_params` manipulation is feasible for exposure (one float at predictable byte offset). This is direct evidence for Path C (Phase 5) — strengthening the case to build it earlier than originally planned. See TODO.md.

---

## Phase 1 — Minimum viable loop

**Goal:** the simplest working Chemigram. One real session, one real image, the loop converges.

**Reference docs:** PRD-001 (Mode A), PRD-003 (Vocabulary as voice), PRD-004 (Local adjustments), TA (full component map).

**Definition of done:** A photographer opens an image, has a 10-turn session, branches once, snapshots three states, applies at least two mask-bound primitives, exports a final JPEG. The session transcript reads cleanly. Context is loaded at start, taste update proposed and confirmed at end, vocabulary gaps logged.

Phase 1 is decomposed into six slices. Slices roughly follow dependency order — earlier slices unblock later ones — but slices 4 and 5 can run in parallel after slice 3 completes.

---

### Slice 1 — Synthesizer + render

**Scope:**

- `chemigram.core.dtstyle` parser — read `.dtstyle` XML into Python objects
- `chemigram.core.xmp` synthesizer — compose XMPs from baseline + vocabulary entries (Path A and Path B per ADR-009)
- `chemigram.core.pipeline` with `DarktableCliStage` — single-stage render pipeline invoking `darktable-cli`
- A handful of hand-rolled `.dtstyle` vocabulary entries (5–10) for testing
- A CLI script (not MCP yet) that takes `image + primitive_name`, applies it, renders a preview
- EXIF auto-binding stub (camera + lens detection from EXIF, no user-prompting yet)

**Gate:** Apply 5 different vocabulary primitives to a real raw, get correct rendered output. Same-module collisions handled correctly (replace, not append). Render times ≤3s for 1024px on Apple Silicon. EXIF auto-bind correctly identifies camera + lens for at least 3 different test images.

**RFCs that close at this gate:**

- ✅ **RFC-001** (XMP synthesizer architecture) — closed via Issue #3; closes into **ADR-050** (parser API + error contract). Open follow-up: Path B / iop_order origin.
- ✅ **RFC-005** (pipeline stage protocol) — closed via Issue #4; closes into **ADR-052** (PipelineStage Protocol + v1 single-stage DarktableCliStage)
- ✅ **RFC-006** (same-module collision behavior) — closed via Issue #3; closes into **ADR-051** (SET-replace, last-writer-wins, Path B deferred)
- ✅ **RFC-015** (EXIF auto-binding rules) — closed via Issue #5; closes into **ADR-053** (exact-match on `(make, model, lens_model)`)

**Sketch of what comes out:**

- ADRs locking parser API, error shapes, synthesizer composition algorithm
- A working `chemigram.core` package that's useful in isolation (without MCP)
- ~600–900 lines of Python

---

### Slice 2 — Versioning + mask registry

**Scope:**

- `chemigram.core.versioning` — content-addressed DAG of XMP snapshots (per-image)
- Per-image repo creation: `~/Pictures/Chemigram/<image_id>/` with `objects/`, `refs/heads/`, `refs/tags/`, `HEAD`, `log.jsonl`
- Snapshot, checkout, branch, log, diff, tag operations
- `chemigram.core.masks` — mask registry per image with symbolic refs (current_subject_mask, etc.)
- Mask storage in `objects/` (raster PNGs, content-addressed)

**Gate:** Apply primitives, snapshot, branch, checkout — get the same rendered state every time. Mask registry survives across sessions. Branching three from one parent and checking out each produces three correct previews.

**RFCs that close at this gate:**

- ✅ **RFC-002** (canonical XMP serialization for stable hashing) — closed via Issue #6; closes into **ADR-054** (canonical XMP serialization). Snapshot tests pin the v3 reference and minimal fixture hashes against literal expected values.
- ✅ **RFC-003** (mask storage in versioning) — closed via Issue #9; closes into **ADR-055** (raster masks share `objects/`; `masks/registry.json` maps symbolic names to hashes plus provenance).

**Sketch of what came out:**

- ADR-054 (canonical XMP serialization), ADR-055 (mask storage)
- `chemigram.core.versioning` package: `canonical.py`, `repo.py`, `ops.py`, `masks.py`
- ~1,500 lines of Python (well above the 400–600 estimate — the surface was richer than projected)

---

### Slice 3 — MCP server + tool surface ✅ shipped (v0.3.0)

**Scope (shipped):**

- `chemigram.core.vocab` (`VocabularyIndex` + `load_starter`) — manifest-driven vocabulary loader (#10).
- `chemigram.mcp.prompts` (`PromptStore` + `MANIFEST.toml` + `mode_a/system_v1.j2` migrated from `docs/agent-prompt.md`) — closes RFC-016 (#11).
- `chemigram.mcp.server` framework — stdio transport, tool registry, error-contract types, in-memory test harness, re-added `chemigram-mcp` console script (#12).
- 27 MCP tools across vocab/edit + context-stubs (#13), versioning + rendering (#14), and ingest + workspace + masks (#15).
- `chemigram.core.workspace.Workspace` orchestrator + `ingest_workspace` flow.
- End-to-end Mode A gate test (`tests/integration/mcp/test_full_session.py`).

**Gate:** an MCP client drives ingest → bind_layers → list_vocabulary → apply_primitive → snapshot → branch/checkout → diff → tag → log → log_vocabulary_gap end-to-end through the in-memory harness; render-dependent tools surface a clean `darktable_error` against placeholder rawb-bytes (real-render gate runs in Slice 6 when a real raw fixture is available).

**RFCs closed at this gate:**

- **RFC-010** (MCP tool surface) → ADR-056. Surface evidence: 27 tools, structured `ToolResult` envelope, closed `ErrorCode` enum, `state_after` shape canonicalized.
- **RFC-016** (versioned prompt system) → already closed in #11; index updates landed alongside the gate.

**Out of scope (deferred):**

- Real masking provider — Slice 4 (`generate_mask`/`regenerate_mask` are stubs returning `NOT_IMPLEMENTED` with `slice=4`).
- Real context layer — Slice 5 (context-read tools are stubs with `slice=5`).
- Real darktable-cli baseline generation — currently uses a bundled `_baseline_v1.xmp` stand-in so vocabulary primitives have a real history to SET-replace against (Path A).

---

### Slice 4 — Coarse masking + local adjustments ✅ shipped (v0.4.0)

**Scope (shipped):**

- `chemigram.core.masking` — `MaskingProvider` Protocol + `MaskResult` (ADR-057, #17).
- `chemigram.core.masking.coarse_agent.CoarseAgentProvider` — sampling-based bundled default per ADR-058. Pillow rasterizer for bbox + polygon descriptors (#17).
- Real `generate_mask` / `regenerate_mask` MCP tool implementations replacing v0.3.0 slice=4 stubs. Auto-renders preview, calls provider, registers PNG (#18).
- Mask-bound L3 vocabulary entries: `tone_lifted_shadows_subject` (`mask_kind: "raster"`, `mask_ref: "current_subject_mask"`) added to test pack. `apply_primitive(mask_override=...)` real path materializes registered PNG to `<workspace>/masks/<name>.png` for darktable consumption (#19).
- End-to-end gate test (`tests/integration/mcp/test_full_session_with_masks.py`) drives ingest → generate_mask → list_masks → apply_primitive(mask_override) → regenerate_mask → log through the harness with a fake sampling-based masker (#20).

**Gate met:** mask-bound primitive applied successfully end-to-end; mask refinement loop works; mechanism proven. Mask quality target (≥70% accept-on-first-generation) is a Slice 6 manual-evidence concern; not blocking.

**RFCs closed:**

- **RFC-004** → ADR-058 (default masking provider = `CoarseAgentProvider`; `chemigram-masker-sam` remains the recommended production upgrade).
- **RFC-009** → ADR-057 (Protocol shape, error categories, sampling-based pattern).

**Out of scope (deferred):**

- Real `chemigram-masker-sam` SAM-backed provider — Phase 4 sibling project.
- Composite Layer 3 mask operations (ADR-021) — Phase 2+ once session evidence shows utility.
- Async `MaskingProvider.generate_async` — reserved for a follow-up RFC.
- Mode A prompt v2 with mask refinement specifics — deferred to Slice 6.

---

### Slice 5 — Context layer + sessions ✅ shipped (v0.5.0)

**Scope (shipped):**

- `chemigram.core.context` — multi-scope `Tastes` loader (per ADR-048: `_default.md` + brief-declared genres), `Brief` parser, `Notes` with line-truncation summarization (10 + 30 + ellision per RFC-011), `RecentLog`, `RecentGaps` (handles both v0.3.0 minimal and post-#24 RFC-013 records). Tolerant of missing files (#21).
- `chemigram.core.session.SessionTranscript` — JSONL writer per ADR-029. `start_session()` factory; `build_server(transcript=...)` plumbs into the MCP server's tool dispatch so every tool call auto-logs `tool_call` + `tool_result` entries (#22).
- Real `read_context` + propose/confirm tools (`propose_taste_update`, `confirm_taste_update`, `propose_notes_update`, `confirm_notes_update`) replacing the v0.3.0 slice=5 stubs. Proposals live in-memory in `ToolContext.proposals`; confirmation appends to the target file (`~/.chemigram/tastes/<file>.md` or `<workspace>/notes.md`) and clears the proposal (#23).
- Vocabulary gap schema upgrade to RFC-013 shape: `session_id` (auto from `ctx.transcript`), `snapshot_hash` (auto from HEAD), `intent`, `intent_category`, `missing_capability`, `operations_involved`, `vocabulary_used`, `satisfaction`, `notes`. Backwards-compat reader handles both shapes (#24).
- End-to-end gate test (`tests/integration/mcp/test_full_session_with_context.py`) drives read_context → apply ×2 → propose/confirm taste → log_gap → propose/confirm notes → read_context (sees gap + log entries) (#25).

**Gate met:** full Mode A flow exercised end-to-end through the in-memory MCP harness with a real transcript writer attached. Tastes file + notes file gain confirmed lines; transcript JSONL contains header + tool_call/tool_result/proposal/confirmation + footer in order.

**RFCs closed:**

- **RFC-011** → ADR-059 (loading order tastes→brief→notes→recent_log→recent_gaps; structured-top + prose-body shape; line-truncation summarization).
- **RFC-013** → ADR-060 (full JSONL schema; `session_id` + `snapshot_hash` auto-population; backwards-compat reader).
- **RFC-014** → ADR-061 (end-of-session is agent-orchestrated; no engine `end_session` tool).

**Out of scope (deferred):**

- LLM-based notes summarization — Phase 2 if line-truncation proves inadequate.
- Auto-classification of `intent_category` — Phase 2; defaults to `"uncategorized"`.
- Cross-session reflection ("across the last 3 sessions you've reached for X") — future tool.
- Mode A prompt v2 with end-of-session refinements — Slice 6 evidence-driven.

---

### Slice 6 — Starter vocabulary + Phase 1 close ✅ shipped (v1.0.0)

**Scope (shipped):**

- Minimal starter vocabulary pack populated at `vocabulary/starter/` — five entries (`expo_+0.5`, `expo_-0.5`, `wb_warm_subtle`, `look_neutral`, `tone_lifted_shadows_subject`) (#26). Deliberately small per the project's "starter is small; Phase 2 grows from session evidence" framing.
- `scripts/verify-vocab.sh` CI check (#27) catches manifest drift fast.
- Mode A prompt v2 (#28) refined for the now-real masking + context flows; v1 stays loadable for eval reproducibility.
- Phase 1 closeout: pyproject `0.5.0` → `1.0.0`; classifier `Pre-Alpha` → `Beta`; doc surfaces synced; tag v1.0.0 + milestone close (#29).

**Gate met:** framework-complete release per the project decision (RFC-014's manual photographer-session evidence is Phase 2 use-driven, not a 1.0.0 blocker).

**Out of scope (deferred to Phase 2):**

- Authoring 30–50 vocabulary entries from real session evidence — Phase 2 is the use-phase that grows the pack.
- The `iguana-galapagos.md` real-session walkthrough — Phase 2 evidence-collection.
- RFC-007 (modversion drift) — stays open until a darktable update forces the question.

---

### RFCs that don't close in Phase 1

| RFC | Why |
|-|-|
| RFC-008 (vocabulary discovery at scale) | Speculative — only relevant after vocabulary grows past ~100 entries (Phase 2 mid-stage) |
| RFC-012 (programmatic generation Path C) | Deferred — closes when discrete vocabulary granularity becomes a bottleneck (Phase 5 trigger) |
| RFC-007 (modversion drift) | May or may not close in Phase 1 depending on whether a darktable update lands during the phase |

---

### Phase 1 risks

**Same-module collision edge cases.** Phase 0 validated the common case; Phase 1 may surface edge cases (different `multi_priority`, masked vs unmasked variants). Cheap to handle when they appear; addressed in Slice 1's gate.

**Coarse masking quality.** PRD-004's sharpest threat applies — if the default masker isn't usable, Phase 1's local-adjustment story is weak. Slice 4's gate is where this risk gets validated; if the gate doesn't pass, the response is to document SAM (Phase 4) more aggressively as the production path, not to delay Phase 1.

**Performance on first real session.** ~2s renders are fine in isolation; sustained over a session with branching, the loop has to feel responsive. Worth profiling in Slice 6.

**Slice 4/5 parallelism.** They're designed to run independently after Slice 3, but if Slice 4 surfaces a need for context (e.g., the masker reading the photographer's taste), the parallelism breaks. Watch for this.

---

## Phase 2 — Vocabulary maturation

**Goal:** Grow the vocabulary from what real sessions surface, not from what we imagined upfront.

**This is a use-phase, not a build-phase.** The starter vocabulary is deliberately small and generic. Real sessions will surface gaps — moves the photographer wanted that the vocabulary didn't have. Each gap, captured properly (vocabulary gap log + later authoring), grows the personal vocabulary.

Phase 2 doesn't decompose into slices the way Phase 1 does, because the work is intermittent and use-driven, not a build sequence with gates.

**Activity:**

- Run real sessions in the Phase 1 engine
- Log gaps as they surface (the agent flags them automatically per Slice 5's tooling)
- Periodically (a vocabulary-authoring evening per month, roughly) open darktable, capture missing primitives as `.dtstyle` files, drop them into personal vocabulary
- Watch which primitives get used heavily, which never get used at all
- Refine, retire, and rename as understanding deepens

**Reference docs:**

- PRD-003 — Vocabulary as voice (the central thesis being tested)
- ADR-023 — Vocabulary primitives are `.dtstyle` + manifest entries
- ADR-024 — Authoring discipline
- CONTRIBUTING.md, vocabulary contributions section

**Markers of maturation:**

- After 3 months: ~30–60 personal entries beyond the starter pack
- After 6 months: ~80–120 personal entries; starter pack additions submitted upstream
- After 1 year: ~150–200 personal entries; vocabulary feels like it captures *the photographer's* craft

**Phase 2 ends when:** the photographer hits a class of need the vocabulary architecture itself can't satisfy. That's the trigger for Phase 3, 4, or 5 (whichever applies).

---

## Phase 3 — Parametric masks in vocabulary [conditional]

**Trigger:** Phase 2 sessions repeatedly surface needs for *masked* vocabulary entries that pre-baked parametric masks (luminance / chroma / hue ranges) can satisfy.

**Goal:** Add a tier of vocabulary entries with darktable-native parametric masks captured in the GUI as part of the style.

**Examples:** `expo_+0.5_subject_only`, `wb_warm_water_only`, `tone_lift_shadows_subject` — each authored by setting up the parametric mask in darktable's GUI, then capturing the style.

**Engine work:** None new. Parametric masks are part of `blendop_params`, which the synthesizer already treats as opaque. The contribution is purely vocabulary.

**Reference docs:**

- PRD-004 — Local adjustments (Layer 1 in the three-layer mask pattern)
- ADR-021 — Three-layer mask pattern

**Phase 3 may be implicit.** It's possible Phase 2 vocabulary growth already includes parametric-masked entries from day one (since darktable supports them natively). In that case Phase 3 dissolves into Phase 2 with no formal transition.

---

## Phase 4 — AI masks via external raster module [conditional]

**Trigger:** Phase 2 sessions repeatedly surface needs for subject-aware local adjustments that parametric masks can't cleanly express. Specifically: needing to mask "the manta" or "the bird's eye" without the limits of luminance/hue thresholds.

**Goal:** Ship at least one production-quality AI-masking provider. The masking abstraction itself is built in Phase 1 Slice 4; Phase 4 is when the SAM-based provider lands.

**Scope:**

- `chemigram-masker-sam` sibling project (separate repo) wrapping Segment Anything
- Distribution path: pip-installable, model-weight-download script
- Configuration in user's MCP setup
- Documentation update: shift the "production path" prose from coarse-agent to SAM

**Reference docs:**

- PRD-004 — Local adjustments through AI masking
- RFC-004, RFC-009 — closed in Phase 1 Slice 4

**Note on dependency:** `chemigram-masker-sam` lives in its own repo (per ADR-032). Building it is independent of the engine's roadmap. It can ship anytime after Phase 1 Slice 4 has locked the MaskingProvider protocol.

---

## Phase 5 — Continuous control via hex encoders (Path C) [conditional]

**Trigger:** Phase 2 sessions show that discrete vocabulary granularity is genuinely insufficient for taste expression — the photographer wants `expo_+0.42` not `expo_+0.3` or `expo_+0.5`, *and* the workaround (authoring more granular vocabulary entries) doesn't scale.

**Goal:** Build hex encoder/decoder pairs for one or two high-value modules. Most likely candidates:

- `exposure` — single float, predictable byte offset, demonstrated feasible in Phase 0
- `colorbalancergb` shadows/highlights lift — a few floats with non-trivial layout

**Scope:** ~50 lines of Python per module supported. Plus tools like `set_exposure(image_id, ev: float)` exposed via MCP. Closes RFC-012 (programmatic vocabulary generation Path C).

**Reference docs:**

- RFC-012 — Programmatic vocabulary generation (Path C) [currently deferred]
- TODO.md — Path C extended discussion
- ADR-008 — XMP and `.dtstyle` as opaque-blob carriers (this phase is the principled exception)

**Important:** Path C is a deliberate exception to the "opaque hex blobs" principle. It's reserved for high-value modules where continuous control matters and where the param struct is stable across darktable versions. It is *not* a general direction; the vocabulary approach remains the dominant path.

**Updated outlook (post Phase 0):** Phase 0 evidence strengthened the case for building exposure's encoder earlier — possibly during a Phase 1 polish slice rather than waiting for Phase 5. The official "Phase 5" naming preserves the original sequencing for now; in practice, exposure-specific Path C work may slot in as Phase 1.5.

---

## Recalibrations from the original plan

The original plan in `docs/briefs/architecture.md` had six phases with rough time estimates ("a few hours," "a weekend," "a week, intermittent"). Some have been validated; some need adjustment.

| Brief estimate | Now we think |
|-|-|
| Phase 0: a few hours | ✅ Took ~6 hours including unexpected findings — accurate |
| Phase 1: a weekend | Likely 2–3 weekends — the brief underestimated. Six slices, ~2,000–3,000 lines total. |
| Phase 2: a week, intermittent | This was always going to be open-ended. "A week" was misleading — vocabulary maturation runs indefinitely. |
| Phase 3: when needed | Likely already happens implicitly inside Phase 2. May not exist as a distinct phase. |
| Phase 4: if needed | Probably needed within 6 months of real Phase 1 use. The marine-photography use case demands AI masks. |
| Phase 5: if needed | Phase 0 evidence suggests starting on exposure earlier. May fragment into 5a (exposure now) + 5b (other modules later). |

These are estimates, not commitments. The phasing is conditional on what use surfaces.

---

## Maintenance

This document is updated when:

- A slice's gate is met and RFCs close (update the slice's status, the closed RFCs' status in `rfc/index.md`, and `adr/TA.md` `map`)
- A phase status changes (started, blocked, closed)
- The phasing itself revises (a slice splits, merges, or is deleted; a phase changes scope)
- A trigger condition gets met for a conditional phase
- An RFC closes into an ADR that affects phasing assumptions

Status changes should ripple to: `docs/concept/00-introduction.md` (the "Project status" section near the bottom), `CLAUDE.md` (the "Phase awareness" section), and `docs/TODO.md` (if relevant items are unblocked).

Phase descriptions themselves are stable — they describe intent, not progress. The status snapshot at the top is what changes most often.

---

*IMPLEMENTATION · v0.1 · The slice-by-slice plan. Closure-as-gate.*
