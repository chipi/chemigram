# Roadmap

> The canonical phase plan for Chemigram.
> Source of truth for "what gets built when."
> Last updated · 2026-04-27

This document describes the implementation phases for building Chemigram. It supersedes earlier phase descriptions in `docs/briefs/architecture.md` (now historical) and consolidates references previously scattered across `concept/`, `TODO.md`, and ADRs.

---

## Status snapshot

| Phase | Description | Status |
|-|-|-|
| **Phase 0** | Validation — manual XMP composition end-to-end | ✅ Closed green (8 findings logged) |
| **Phase 1** | Minimum viable loop — Python engine, MCP server, starter vocabulary | Not started |
| **Phase 2** | Vocabulary maturation — grow vocab from session evidence | Not started (begins after Phase 1) |
| **Phase 3** | Parametric masks in vocabulary | Conditional — when Phase 2 surfaces gaps |
| **Phase 4** | AI masks via external raster module | Conditional — when local adjustments demand it |
| **Phase 5** | Continuous control via hex encoders (Path C) | Conditional — when discrete vocabulary becomes a bottleneck |

Phases 3–5 are deliberately conditional. They happen only if Phase 2 evidence shows they're worth doing. The project may converge before Phase 5 ever ships; that's a feature, not a failure.

---

## A note on "Phase" naming collisions

Two unrelated senses of "Phase N" exist in this project. To avoid confusion:

- **Implementation phases** (0–5) — the build sequence described in this document. The dominant use of "Phase" going forward.
- **Doc methodology phases** (Phase 1 = concept package, Phase 2 = definition documents) — a methodological layer from the doc-system process guide used to produce `docs/concept/`, `docs/prd/`, `docs/rfc/`, `docs/adr/`. The doc methodology was followed; that work is complete; the term is no longer in active use.

If "Phase 2" appears unqualified in this project from now on, it means the implementation phase (vocabulary maturation), not the doc methodology phase.

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

**Scope:**

- Python engine (`chemigram_core`): XMP synthesizer, render pipeline, versioning, mask registry
- MCP server (`chemigram_mcp`): the tool surface defined in ADR-033
- Starter vocabulary (~30–50 entries) — the OSS `chemigram-vocabulary-starter` package
- Default coarse-agent masking provider (no SAM dependency)
- Per-image repo structure (`~/Pictures/Chemigram/<image_id>/`)
- Three-tier context model (taste/brief/notes)
- Session transcripts as JSONL

**Reference docs:**

- PRD-001 — Mode A (the conversational loop this enables)
- PRD-003 — Vocabulary as voice (the substrate)
- TA — full component map and contracts

**Definition of done:** A photographer opens an image, has a 10-turn session, branches once, snapshots three states, exports a final JPEG. The session transcript reads cleanly. The agent reaches for vocabulary primitives and applies them. At least one vocabulary gap is logged.

**Closing evidence for open RFCs:** RFC-001 (XMP synthesizer architecture), RFC-002 (canonical XMP serialization), RFC-005 (pipeline stage protocol), RFC-009 (mask provider protocol), RFC-010 (MCP tool surface parameter shapes), RFC-011 (agent context loading). These should close into ADRs during Phase 1 implementation.

**Risks:**

- **Same-module collision edge cases.** Phase 0 validated the common case; Phase 1 may surface edge cases (different `multi_priority`, masked vs unmasked variants). Cheap to handle when they appear.
- **Coarse masking quality.** PRD-004's sharpest threat applies — if the default masker isn't usable, Phase 1's local-adjustment story is weak. Phase 1 should ship with honest expectations about masking, with the SAM upgrade path documented.
- **Performance on first real session.** ~2s renders are fine in isolation; sustained over a session with branching, the loop has to feel responsive. Worth profiling early.

---

## Phase 2 — Vocabulary maturation

**Goal:** Grow the vocabulary from what the photographer's actual sessions surface, not from what we imagined upfront.

**This is a use-phase, not a build-phase.** The starter vocabulary is deliberately small and generic. Real sessions will surface gaps — moves the photographer wanted that the vocabulary didn't have. Each gap, captured properly (vocabulary gap log + later authoring), grows the personal vocabulary.

**Activity:**

- Run real sessions in Phase 1 engine
- Log gaps as they surface (the agent flags them automatically)
- Periodically (a vocabulary-authoring evening per month, roughly) open darktable, capture the missing primitives as `.dtstyle` files, drop them into personal vocabulary
- Watch which primitives get used heavily, which never get used at all
- Refine, retire, and rename as understanding deepens

**Reference docs:**

- PRD-003 — Vocabulary as voice (the central thesis being tested)
- ADR-023 — Vocabulary primitives are `.dtstyle` + manifest entries
- ADR-024 — Authoring discipline
- CONTRIBUTING.md § Vocabulary contributions

**Markers of maturation:**

- After 3 months: ~30–60 personal entries beyond the starter pack
- After 6 months: ~80–120 personal entries; starter pack additions submitted upstream
- After 1 year: ~150–200 personal entries; vocabulary feels like it captures *the photographer's* craft

**What Phase 2 is not:**

- A coding phase. Almost no engine work happens here.
- A throughput phase. Vocabulary growth is *intermittent* — a few entries per session, captured deliberately.
- A scheduled phase. It runs in the background of normal use, indefinitely.

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

**Goal:** Ship the masking provider abstraction with at least one production-quality provider.

**Scope:**

- `MaskingProvider` protocol (RFC-009 closure)
- Default coarse-agent provider in `chemigram_core` (vision-only)
- `chemigram-masker-sam` sibling project (separate repo) wrapping Segment Anything
- Mask registry per image with symbolic refs (ADR-022)
- Mask refinement loop in the agent's prompt template
- "First-session masker disclosure" UX

**Reference docs:**

- PRD-004 — Local adjustments through AI masking
- RFC-004 — Default masking provider (coarse vs SAM)
- RFC-009 — Mask provider protocol shape
- ADR-007 — BYOA principle

**Sharpest threat:** Default masker quality (see PRD-004). The phase succeeds only if the photographer's first-session experience clears the bar.

**Note on dependency:** `chemigram-masker-sam` lives in its own repo (per ADR-032). Building the engine's masking abstraction (Phase 4 in the engine) and building the SAM masker (a sibling project) are independent tracks. The engine work blocks; the masker can ship anytime after.

---

## Phase 5 — Continuous control via hex encoders (Path C) [conditional]

**Trigger:** Phase 2 sessions show that discrete vocabulary granularity is genuinely insufficient for taste expression — the photographer wants `expo_+0.42` not `expo_+0.3` or `expo_+0.5`, *and* the workaround (authoring more granular vocabulary entries) doesn't scale.

**Goal:** Build hex encoder/decoder pairs for one or two high-value modules. Most likely candidates:

- `exposure` — single float, predictable byte offset, demonstrated feasible in Phase 0
- `colorbalancergb` shadows/highlights lift — a few floats with non-trivial layout

**Scope:** ~50 lines of Python per module supported. Plus tools like `set_exposure(image_id, ev: float)` exposed via MCP.

**Reference docs:**

- RFC-012 — Programmatic vocabulary generation (Path C) [currently deferred]
- TODO.md — Path C extended discussion
- ADR-008 — XMP and `.dtstyle` as opaque-blob carriers (this phase is the principled exception)

**Important:** Path C is a deliberate exception to the "opaque hex blobs" principle. It's reserved for high-value modules where continuous control matters and where the param struct is stable across darktable versions. It is *not* a general direction; the vocabulary approach remains the dominant path.

**Updated outlook (post Phase 0):** Phase 0 evidence strengthened the case for building exposure's encoder earlier — possibly during Phase 1's polish work rather than waiting for Phase 5. Recorded in TODO.md. The official "Phase 5" naming preserves the original sequencing for now; in practice, exposure-specific Path C work may slot into Phase 1.5.

---

## Recalibrations from the original plan

The original plan in `docs/briefs/architecture.md` had six phases with rough time estimates ("a few hours," "a weekend," "a week, intermittent"). Some of those estimates have been validated; some need adjustment with what we know now.

| Brief estimate | Now we think |
|-|-|
| Phase 0: a few hours | ✅ Took ~6 hours including unexpected findings — accurate |
| Phase 1: a weekend | Likely 2–3 weekends — the brief underestimated. Engine plus MCP plus starter vocabulary is more code than implied. |
| Phase 2: a week, intermittent | This was always going to be open-ended. "A week" was misleading — vocabulary maturation runs indefinitely. |
| Phase 3: when needed | Likely already happens implicitly inside Phase 2. May not exist as a distinct phase. |
| Phase 4: if needed | Probably needed within 6 months of real Phase 1 use. The marine-photography use case demands AI masks. |
| Phase 5: if needed | Phase 0 evidence suggests starting on exposure earlier. May fragment into 5a (exposure now) + 5b (other modules later). |

These are estimates, not commitments. The phasing is conditional on what use surfaces.

---

## What "next" looks like

After this Phase 2 doc system pass (now complete), the immediate next step is **Phase 1 — Minimum viable loop**. The closure work for several Phase-1-blocking RFCs happens during implementation, not before.

A reasonable sequencing inside Phase 1:

1. Synthesizer + render pipeline (closes RFC-001, RFC-002)
2. Versioning subsystem (closes RFC-002 for canonical serialization)
3. Mask registry (closes parts of RFC-003)
4. MCP server skeleton + tool surface (closes RFC-010)
5. Coarse-agent masking provider (closes RFC-009)
6. Context-loading layer (closes RFC-011)
7. Starter vocabulary authoring + manifest validation
8. End-to-end first session with a real image

This is approximate. The actual sequence emerges from running into the next blocker.

---

## Maintenance

This document is updated when:

- A phase status changes (started, blocked, closed)
- The phasing itself revises (a phase splits, merges, or is deleted)
- A trigger condition gets met for a conditional phase
- An RFC closes into an ADR that affects phasing assumptions

Status changes should ripple to: `docs/concept/00-introduction.md` (the "Project status" section near the bottom) and `docs/TODO.md` (the roadmap reference).

Phase descriptions themselves are stable — they describe intent, not progress. The status snapshot at the top is what changes most often.

---

*ROADMAP · v0.1 · The canonical phase plan. Reference, not roadmap-as-promise.*
