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
| **Phase 1** | Minimum viable loop — Python engine, MCP server, starter vocabulary | **In progress** — Slice 1 components shipped (Issues #1–#5 closed; all 4 Slice 1 RFCs closed → ADR-050, ADR-051, ADR-052, ADR-053). End-to-end gate run pending — see Slice 6. |
| **Phase 2** | Vocabulary maturation — grow vocab from session evidence | Not started (begins after Phase 1) |
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

- **RFC-002** (canonical XMP serialization for stable hashing) — closes because hashing gets exercised; canonicalization choices either hold or get revised
- **RFC-003** (mask storage in versioning) — closes because mask storage gets exercised by real snapshots that reference masks

**Sketch of what comes out:**

- ADR-018 amendment locking canonical XMP serialization
- ADR-022 amendment locking mask storage details
- ~400–600 lines of Python for the versioning subsystem

---

### Slice 3 — MCP server + tool surface

**Scope:**

- `chemigram.mcp.server` — MCP server adapting `chemigram.core` as agent-callable tools
- All tools from ADR-033: vocabulary, edit operations, rendering, versioning, ingestion, context (stub for context — actual implementation in Slice 5)
- Error contracts and parameter shape validation
- Local-first transport (stdio MCP)
- **Prompt system bootstrap** (per RFC-016): `chemigram.mcp.prompts` package, `PromptStore` class, `MANIFEST.toml`, `mode_a/system_v1.j2` migrated from `docs/agent-prompt.md`. Loaded at session start and provided to the agent as the system prompt.

**Gate:** Claude Code (or another MCP client) can drive a multi-turn editing session through the server: list vocabulary, apply primitives, render previews, snapshot, branch, checkout, export. Tool errors surface cleanly to the agent.

**RFCs that close at this gate:**

- **RFC-010** (MCP tool surface — parameter shapes and error contracts) — closes because the surface is exercised by a real agent in a real session
- **RFC-016** (versioned prompt system) — closes because PromptStore is built, `mode_a/system_v1` is loaded by the MCP server, and active-version registry works as designed

**Sketch of what comes out:**

- ADRs locking parameter shapes, error contracts, tool naming
- Working MCP server, ~300–500 lines
- Working `chemigram.mcp.prompts` package with PromptStore + MANIFEST.toml + first prompt
- The first end-to-end Mode A interaction (even if vocabulary is small and masks are fake)

---

### Slice 4 — Coarse masking + local adjustments

**Scope:** *(can run in parallel with Slice 5 after Slice 3)*

- `MaskingProvider` Protocol in `chemigram.core.masking`
- `CoarseAgentProvider` — vision-only default masker (no PyTorch)
- Mask-bound vocabulary entries (L3 layer per ADR-021)
- `generate_mask`, `regenerate_mask`, `list_masks`, `invalidate_mask`, `tag_mask` MCP tools
- Mask refinement loop in agent prompt template
- "First-session masker disclosure" UX

**Gate:** Apply at least 2 mask-bound primitives in a session. Mask quality is usable for clear-subject case (≥70% accept-on-first-generation for marine animals against contrasting water). Refinement prompt regenerates the mask correctly.

**RFCs that close at this gate:**

- **RFC-004** (default masking provider — coarse vs SAM) — closes because real session evidence shows whether coarse-agent masking clears the bar
- **RFC-009** (mask provider protocol shape) — closes because the protocol gets exercised by `CoarseAgentProvider` and dictates what `chemigram-masker-sam` (Phase 4) will need to implement

**Sketch of what comes out:**

- ADRs locking the MaskingProvider Protocol and the v1 default choice
- Working `CoarseAgentProvider`, ~200–400 lines
- Documented expectations for mask quality
- Foundation for `chemigram-masker-sam` sibling project (Phase 4)

---

### Slice 5 — Context layer + sessions

**Scope:** *(can run in parallel with Slice 4 after Slice 3)*

- `chemigram.core.context` — read taste.md, brief.md, notes.md per ADR-030's three-tier model
- `read_context`, `propose_taste_update`, `confirm_taste_update`, `propose_notes_update`, `confirm_notes_update` MCP tools
- Session transcripts as JSONL per ADR-029 (header metadata + per-turn entries)
- Vocabulary gap surfacing: `log_vocabulary_gap` tool, `vocabulary_gaps.jsonl` per image
- End-of-session synthesis flow (the agent's wrap-up turn)

**Gate:** Complete a real Mode A session with: context loaded at start (taste + brief + notes + recent log), taste update proposed and confirmed at end, vocabulary gaps logged when they arise, full session transcript written to `sessions/<timestamp>.jsonl`.

**RFCs that close at this gate:**

- **RFC-011** (agent context loading order and format) — closes because the actual loading sequence gets exercised; ordering choices either hold or get revised
- **RFC-013** (vocabulary gap surfacing format) — closes because real sessions surface real gaps; the format proves usable or gets revised
- **RFC-014** (end-of-session synthesis flow) — closes because the wrap-up sequence runs in real sessions

**Sketch of what comes out:**

- ADRs locking context-loading order, gap format, end-of-session sequence
- Working context layer, ~300–500 lines
- The first session whose transcript reads cleanly end-to-end

---

### Slice 6 — Starter vocabulary + first real session

**Scope:**

- Author the starter vocabulary pack — ~30–50 entries per PRD-003 — into `vocabulary/starter/` in the main repo (per ADR-049)
- Bundle in the `chemigram` PyPI distribution as package data
- Manifest validation in CI
- Run the full `iguana-galapagos.md` scenario from start to finish on a real underwater raw
- Document session findings (what worked, what didn't, what gaps surfaced)

**Gate:** A photographer (Marko) opens a real La Ventana raw, has a 10-turn session, branches once, snapshots three states, applies at least two mask-bound primitives, exports a final JPEG. The session transcript reads cleanly. The starter vocabulary covered enough of the moves needed; gaps were logged for what it didn't cover.

**RFCs that may close at this gate (depending on what surfaces):**

- **RFC-007** (modversion drift handling) — closes only if a darktable update lands during Phase 1 and forces the question; otherwise stays open through Phase 2

**Sketch of what comes out:**

- The starter vocabulary directory (`vocabulary/starter/`) populated and committed
- The first `chemigram` release that ships with a populated vocabulary out of the box
- A real Phase 1 session log proving Mode A works
- Phase 1 declared closed; Phase 2 (vocabulary maturation) begins

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
