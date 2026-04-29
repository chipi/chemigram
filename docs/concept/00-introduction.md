# 00 — Introduction

*The entry point for the Chemigram concept package. Read this first. Then read the rest in the order it suggests.*

This is the introduction to the **Chemigram concept package** — the set of documents that describe what Chemigram is at the idea level, before formal product or technical specification work begins.

If you're new to the project, read this document first, then read the others in the order suggested below.

---

## What this package is

A concept package is a set of documents that describes a project at the idea level — what it is, what it does, what it uses, how it works, and how it looks — before any formal requirements are written.

This package contains six numbered documents (`00` through `05`), each with a specific purpose:

| # | Name | Purpose |
|-|-|-|
| **00** | Introduction (this document) | What the package is, reading order, glossary |
| **01** | Vision | The soul of the project. The why. |
| **02** | Project Concept | What we're building at the idea level — the loop, the sessions, the modes |
| **03** | Data and Content Catalog | What feeds the system — sources, characteristics, access |
| **04** | Technical Architecture | How to build it. All tech decisions with rationale, plus open questions for Phase 2 |
| **05** | Design System | How it looks and feels. Intentionally minimal because Chemigram v1 is an MCP server, not a UI app. |

The package is the **input** to formal definition work (PRDs, RFCs, ADRs, UXSes), not the output. It exists so that requirements writing has a shared concept to build on.

---

## What this package is not

| Not a... | Because... |
|-|-|
| **PRD** | Product Requirements Documents come after. The package is the input to PRD writing, not the output. |
| **RFC** | Open questions are flagged in `04` but the RFCs themselves come later. |
| **ADR** | Decisions are described with rationale in `04` but the formal ADR documents come later. |
| **Build plan** | The package does not define sprints, milestones, or implementation order. It defines what is being built. |
| **A Lightroom replacement** | See `01`/"What this is not" for the full list of what the project itself is not — distinct from what the package is not. |

---

## How to read this package

Documents are numbered for reading order, not writing order. Read in this order:

| Step | Document | Time | Why |
|-|-|-|-|
| 1 | `00` (this document) | 5 min | Orient yourself; learn the vocabulary |
| 2 | `01` Vision | 10 min | Understand why the project exists |
| 3 | `02` Project Concept | 30-40 min | Understand the full project at idea level |
| 4 | `03` Data Catalog | 15 min | Understand what feeds the system |
| 5 | `04` Technical Architecture | 45-60 min | Understand how it's built and what's still open |
| 6 | `05` Design System | 5 min | Understand the (intentionally minimal) design surface |

Total reading time: roughly two hours. The bulk of the package is `02` (project concept) and `04` (architecture).

If you have less time, the minimum is `00` + `01` + the first three sections of `02`. That gives you the soul of the project plus the structuring metaphor (Chemigram is to photos what Claude Code is to code) and is enough to engage with anyone working on the project.

If you're returning to the package after time away: read `00` again — the glossary section is the fastest way to refresh on terminology.

---

## Where to go after the concept package

After the concept package, the project's other content includes:

| Document | Purpose |
|-|-|
| `docs/LICENSING.md` | What's MIT, what's separate (engine vs. personal vocabularies) |
| `docs/CONTRIBUTING.md` | Code and vocabulary contribution flows (different review processes) |
| `docs/TODO.md` | Research backlog, deferred items, "watch for" items |
| `examples/iguana-galapagos.md` | A worked Mode A session demonstrating the full loop |
| `examples/phase-0-notebook.md` | Hands-on validation lab notebook for Phase 0 |
| `docs/briefs/` | Historical design-conversation artifacts that predate this package |

The definition documents (PRDs, RFCs, ADRs) in `docs/prd/`, `docs/rfc/`, and `docs/adr/` complete the doc system. They were produced after Phase 0 closed, anchoring into the concept package and into the per-plane reference docs (PA for product, TA for tech). The full project phase plan lives in `docs/IMPLEMENTATION.md`.

---

## Document naming convention

Documents in this package are numbered `00` through `05`. Numbers reflect reading order; their topics remain stable across projects following this concept-package process.

When other artifacts reference these documents — RFCs, PRDs, future technical work — references in headers and links use the number-and-section path style (e.g., `04/5` for section 5 of the architecture doc), while references in body prose use topic names (e.g., "see the architecture doc").

---

## Glossary

The vocabulary used across the package. When in doubt about what a term means, find it here.

### Core concepts

**Chemigram** — the project itself. Named after the cameraless photographic process where an image emerges from chemical reaction on light-sensitive paper, guided but not fully controlled. The name fits because each edit emerges from a loop between photographer's intent, agent's moves, and tool's response.

**Engine** — the Python code that does the orchestration. Includes XMP composition, vocabulary loading, render pipeline, versioning, mask registry, and MCP server. See `04`/2.

**Agent** — the AI capability that drives Mode A or Mode B sessions. Per the BYOA principle, the agent is photographer-configured (Claude, GPT, etc.), not bundled with Chemigram.

**Photographer** — the human user of Chemigram. Always in control; always the source of intent and judgment.

**Apprentice model** — the framing for the photographer/agent relationship. The agent is a patient, capable apprentice who reads context, executes vocabulary, surfaces uncertainty. The photographer is the master who provides briefs, judges results, and curates accumulated context.

### Modes

**Mode A** — the journey. Collaborative editing where photographer and agent work through one photo together, conversationally. 5-30 turns per session. The primary mode.

**Mode B** — the autonomous fine-tuner. Agent runs alone with a brief and evaluation criteria, branching to explore variants, self-evaluating, converging to a winner or running out of budget. Future mode, deferred to Phase 4+.

**Session** — one conversation between photographer and agent on one image, from start to end-of-session synthesis. Captured as a JSONL transcript in `sessions/`.

### Vocabulary

**Vocabulary** — the agent's action space. A finite set of named, single-module darktable styles (`.dtstyle` files) that the agent composes to make edits. The bulk of the project's character lives in vocabulary.

**Vocabulary primitive** (or just **primitive**) — one entry in the vocabulary. A single-module darktable style with a name like `expo_+0.5` or `colorcal_underwater_recover_blue_subject`.

**`.dtstyle`** — the file format of a vocabulary primitive. XML, captures one module's parameters and blend operation. Authored by photographer (or community) in darktable's GUI; loaded by Chemigram at session start.

**Manifest** — the JSON metadata accompanying vocabulary entries. Contains layer assignment, modules touched, tags, description, mask kind, and other engine-relevant metadata.

**Vocabulary gap** — when the agent needs a primitive that doesn't exist. Worked around by composing existing primitives, then logged to `vocabulary_gaps.jsonl` for later authoring. Gaps are content, not failure.

**Starter vocabulary** — the minimal OSS vocabulary bundled with Chemigram. Generic, conservative, intended to bootstrap new users. Lives in `vocabulary/starter/`.

**Community packs** — vocabulary collections borrowed from existing community projects (Fuji sims, etc.) and redistributed with attribution. Live in `vocabulary/packs/`.

**Personal vocabulary** — a photographer's private taste, encoded as their own vocabulary entries. Not part of the OSS distribution. Loaded from a separate private repo.

### Layers

**L0** — darktable internals (rawprepare, demosaic, color profiles). Always-on. Not authored by anyone in the Chemigram sense.

**L1** — Technical correction (lens, profiled denoise). Empty by default; opt-in per camera+lens via `config.toml` bindings. Pre-baked into baseline before the agent starts.

**L2** — Look establishment. Either neutralizing (e.g. `underwater_pelagic_blue`) or look-committed (e.g. `fuji_acros`). Photographer-chosen, per-image, pre-baked into baseline.

**L3** — Taste. The agent's vocabulary, mutable in the loop. The agent's playground.

**Layer model** — see `04`/5 for the full model. Layers separate authorship moments, not editing moves.

### Versioning

**Snapshot** — one content-addressed XMP state. SHA-256 hash over canonical XMP serialization. Lives in `objects/`.

**Branch** — a movable ref pointing at a snapshot. Like git branches.

**Tag** — an immutable ref pointing at a snapshot. Used for marking final states (`v1_export`, `instagram_crop`).

**HEAD** — the current ref or hash the working state points at.

**DAG** — directed acyclic graph of snapshots, formed by the parent relationships. The full version history of an image.

**Mode B exploration tree** — the branching tree of variants Mode B produces during autonomous exploration. Inspectable via the versioning DAG.

### Masks

**Mask** — a spatial selection that restricts an effect to part of the frame. Three kinds in Chemigram: parametric, drawn, raster.

**Parametric mask** — a mask defined by pixel-value conditions (luminance range, hue range, etc.) in `blendop_params`. Content-agnostic.

**Drawn mask** — a mask defined by geometric primitives (gradient, circle, ellipse, path) in `blendop_params`. Pre-authored by photographer in GUI.

**Raster mask** — a PNG mask file referenced by darktable. The path for AI-generated subject masks. Resolved symbolically at XMP synthesis time.

**Mask registry** — Chemigram's per-image record of generated masks. Tracks names, generators, prompts, freshness. See `04`/6.3.

**Symbolic mask reference** — a placeholder name like `current_subject_mask` that vocabulary entries use. The engine resolves the symbol to an actual PNG path at synthesis time. Lets multiple primitives reuse the same mask.

**Masking provider** — a pluggable implementation that generates masks. v1 ships a coarse agentic default; production-quality masking via `chemigram-masker-sam` sibling project. Configurable per target type. See `04`/6.4.

### Context files

**`taste.md`** — the photographer's externalized taste. Lives at `~/.chemigram/taste.md`. Read by the agent at every session start. Curated through propose-and-confirm over months.

**`brief.md`** — what a specific image is for. Lives at `<image_id>/brief.md`. Written at session start, sometimes updated mid-session.

**`notes.md`** — what we've learned about a specific image. Lives at `<image_id>/notes.md`. Accumulates across sessions on the same image.

**`config.toml`** — user configuration. Vocabulary sources, masking providers, L1/L2 binding rules, storage paths.

### Disciplines

**Agent is the only writer** — the photographer reads previews and gives feedback; the agent is the sole mutator of edit state. See `04`/1.1.

**darktable does the photography, Chemigram does the loop** — every image-processing capability comes from darktable. Chemigram contributes orchestration, vocabulary, agent loop, versioning, session capture. See `04`/1.2.

**BYOA (Bring Your Own AI)** — Chemigram doesn't ship AI capabilities; it integrates them via MCP. Maskers, evaluators, the photo agent itself are all photographer-configured. See `04`/1.3.

### Engineering terms

**MCP** — Model Context Protocol. Anthropic's protocol for agent tool-calling. Chemigram exposes its capabilities as an MCP server.

**`darktable-cli`** — darktable's headless command-line interface. Runs without GUI. Chemigram's render pipeline invokes it as a subprocess.

**XMP** — Extensible Metadata Platform. The RDF/XML sidecar format darktable uses to store edit state. Each `<rdf:li>` in `<darktable:history>` is one module application.

**`op_params` / `blendop_params`** — hex-encoded C structs in XMP that hold module parameters and blend operation parameters. Treated as opaque blobs by Chemigram; copied verbatim from `.dtstyle` files.

**SET semantics** — when the agent applies a vocabulary primitive, it replaces any existing entry with matching `(operation, multi_priority)` rather than accumulating. Idempotent action space.

**Pipeline stage** — one step in the render pipeline, conforming to the `PipelineStage` protocol. v1 has one stage (darktable-cli); the abstraction admits future stages (external CLIs, GenAI tools, custom processors).

**EXIF auto-binding** — Chemigram's automatic resolution of L1 and L2 bindings from a raw's EXIF data. See `04`/9.

**`modversion`** — darktable's per-module version number. `op_params` encoding is modversion-specific. Vocabulary needs re-capture when darktable bumps a module's modversion.

**`multi_priority`** — darktable's mechanism for having multiple instances of the same module in the history. Chemigram uses `(operation, multi_priority)` as the SET key.

### Project structure

**Photo project** — one image, structured the way a code project is. Per-image directory with raw, briefs, notes, snapshots, sessions, masks. See `02`/4.

**Per-image repo** — synonym for photo project. The structure is content-addressed and ref-based, mirroring git.

**Concept package** — this set of six documents (`00` through `05`). The Phase 1 deliverable.

**Brief** (in process-guide sense) — the photographer's intent statement for an image. Distinct from "concept package" or the historical design-conversation artifacts in `briefs/`.

**Briefs folder** — the `docs/briefs/` directory, holding the original design-conversation documents from before the concept package was formalized. Historical artifacts.

---

## How this package was produced

The Chemigram concept package was produced through a multi-session design conversation between Marko (the photographer who initiated the project) and an AI assistant. The original conversation artifacts are preserved in `docs/briefs/` as historical record.

The transition to the formal numbered structure (this package) happened after the briefs accumulated enough thinking to justify formal organization. The structure follows the Concept Package Process Guide v2 (an external methodology document).

The two main document deliverables, `02` and `04`, draw heavily from the briefs. The briefs are kept available because the formal package abstracts the conversational reasoning that produced the architecture; future-readers wanting to understand *why* a decision was made may find the briefs more illuminating than the package's distilled statements.

If you find a contradiction between the package and a brief, the package is correct (and the brief reflects an earlier moment of thinking).

---

## Status

| Aspect | Status |
|-|-|
| Concept package complete | Yes (v1.0) |
| Phase 0 validation done | ✅ Closed green (8 findings logged) |
| Doc system populated | ✅ Complete (PRDs, RFCs, ADRs in `docs/prd`, `docs/rfc`, `docs/adr`) |
| Phase 1 implementation started | Yes — Slices 1–3 complete (v0.1.0, v0.2.0, v0.3.0). Issues #1–#16 closed; eight RFCs closed: RFC-001/005/006/015 in v0.1.0 → ADR-050/052/051/053; RFC-002/003 in v0.2.0 → ADR-054/055; RFC-010/016 in v0.3.0 → ADR-056 (RFC-016 closure landed in #11). |

For the canonical phase plan and current status, see `docs/IMPLEMENTATION.md`.

Slices 1–3 are complete; the MCP surface is real and exercised end-to-end through an in-memory client. **Slice 4 (real masking provider)** and **Slice 5 (context layer)** are parallel-unblocked — they ran behind Slice 3's tool surface and can now proceed independently. End-to-end gate runs against real darktable + a real raw remain Slice 6's first photographer session. See `docs/IMPLEMENTATION.md` for the full Phase 1 plan.

---

*00 · Introduction · v1.0 · Written last after 01 through 05*
