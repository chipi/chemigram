# CLAUDE.md — Conventions for AI-Assisted Work

> Project conventions compiled into actionable rules.
> For AI agents (and humans) doing work on the Chemigram codebase and doc tree.
> Last updated · 2026-04-27

This document is the operational handbook. It tells you *how* to work in this repo: where things go, what patterns to follow, what to avoid, how to add new artifacts. It compiles rules that are scattered across the doc tree into a single place you can scan in five minutes.

If you're new to the project, read `docs/concept/00-introduction.md` first for *what* Chemigram is. This file is *how* to work on it.

---

## The three foundational disciplines

Three rules apply to every decision and every line of code. If something violates one of these, it's wrong even if it's clever.

### 1. Agent is the only writer

The photographer reads previews and judges. The agent is the sole mutator of edit state. Vocabulary applications snapshot. Context updates propose-and-confirm. The engine never silently mutates state outside an agent-initiated tool call.

This means: no "auto-save" of taste updates. No background mutations. No "smart" agent moves the photographer didn't see coming. Every change has a tool call behind it.

### 2. darktable does the photography, Chemigram does the loop

Chemigram contributes orchestration: vocabulary, agent loop, versioning, session capture. Every image-processing capability comes from darktable. When a question is "should we build X?" and X is color science, lens correction, denoise, tone, mask logic — the answer is no. darktable already has it.

This means: no Python image-processing dependencies in `chemigram.core`. No reimplementation of capabilities darktable provides. No Lua bridge for things darktable already exposes via XMP.

### 3. BYOA — Bring Your Own AI

No AI capabilities bundled with the engine. No PyTorch dependency in `chemigram.core`. No model weights. Every AI capability is one MCP call away to a photographer-configured provider.

This means: maskers, evaluators, the photo agent itself — all configurable via MCP. Any capability that requires AI is a separate provider, often a sibling project (e.g., `chemigram-masker-sam`).

---

## Doc system at a glance

```
chemigram/
├── README.md                     ← repo landing page
├── CLAUDE.md                     ← this file (operational handbook)
└── docs/
    ├── index.md                  ← ecosystem overview, "start here"
    ├── IMPLEMENTATION.md         ← canonical phase plan + slice-by-slice guide
    ├── CONTRIBUTING.md           ← code & vocabulary contribution flows
    ├── LICENSING.md
    ├── TODO.md                   ← deferred items, research backlog
    ├── concept/                  ← Tier 1: founding narrative (read end-to-end)
    │   ├── 00-introduction.md
    │   ├── 01-vision.md
    │   ├── 02-project-concept.md
    │   ├── 03-data-catalog.md
    │   ├── 04-architecture.md
    │   └── 05-design-system.md
    ├── prd/                      ← Tier 2: product arguments
    │   ├── PA.md                 ← product reference (audiences/promises/principles)
    │   ├── PRD_TEMPLATE.md
    │   ├── index.md
    │   └── PRD-NNN-*.md
    ├── rfc/                      ← Tier 2: open technical questions
    │   ├── RFC_TEMPLATE.md
    │   ├── index.md
    │   └── RFC-NNN-*.md
    ├── adr/                      ← Tier 2: settled technical decisions
    │   ├── TA.md                 ← technical architecture reference (with `map` state board)
    │   ├── ADR_TEMPLATE.md
    │   ├── index.md
    │   └── ADR-NNN-*.md
    └── briefs/                   ← historical artifacts (frozen)
        ├── index.md
        └── *.md
```

### What anchors to what

- **PRDs** anchor into `prd/PA.md` via `PA/audiences/...`, `PA/promises/...`, `PA/principles/...`
- **RFCs** anchor into `adr/TA.md` via `TA/components/...`, `TA/contracts/...`, `TA/constraints/...`
- **ADRs** anchor into `adr/TA.md` and reference the closing RFC if there was one
- **Reference docs** (PA, TA) are read by linking-into specific sections, never end-to-end

### State board

`adr/TA.md` has a `## map` section that lists every RFC and ADR with status and closure. **When state changes, update TA/map and the relevant `index.md` together** — they must agree.

---

## Adding a new artifact

### Adding a PRD

When user-value for a surface or experience needs arguing:

1. Copy `prd/PRD_TEMPLATE.md` to `prd/PRD-NNN-slug.md` (next sequential number, lowercase-hyphenated slug)
2. Fill in the gating sentence (`Why this is a PRD`). If the gating sentence is hard to write, this isn't a PRD — it's something else.
3. Anchor to PA: name specific audiences, promises, principles
4. Write the magazine-style lede — specific person, specific actions, present tense
5. Fill in the `Sharpest threat` section (impact-level, not build-risk)
6. Update `prd/index.md`

PRDs are not feature lists, not user stories, not implementation specs. They are arguments.

### Adding an RFC

When a genuinely open technical question needs deliberation:

1. Copy `rfc/RFC_TEMPLATE.md` to `rfc/RFC-NNN-slug.md` (next sequential number)
2. Fill in `Why this is an RFC` — the genuinely open question being argued. **If the answer is mostly known, skip the RFC and write an ADR directly.**
3. Anchor to TA — name the affected component, contract, or constraint
4. Write `Alternatives considered` honestly — not feature comparisons, but real reasons each was set aside
5. Name what it `Closes into` (which ADRs come out of it)
6. Update `rfc/index.md` and `adr/TA.md` `map` state board

### Adding an ADR

ADRs come from two streams:

- **Direct ADRs** — small decisions with no real alternatives, no need for an RFC
- **RFC-closure ADRs** — written when an RFC closes; one RFC may close into multiple ADRs

Either way:

1. Copy `adr/ADR_TEMPLATE.md` to `adr/ADR-NNN-slug.md` (next sequential number)
2. Reference the TA anchor and the related RFC (if any)
3. State the decision clearly — one paragraph, no hedging
4. List `Alternatives considered` with one-line reasons for rejection
5. Update `adr/index.md` and `adr/TA.md` `map` state board

**ADRs are append-only after acceptance.** Never edit an accepted ADR. If circumstances change, write a new ADR and mark the old one `Superseded by ADR-NNN`.

### Closing an RFC

When an RFC's question gets answered (usually through implementation evidence):

1. Write the closing ADR(s) in `adr/`
2. Update the RFC's status to `Decided` (don't delete it — it stays as historical record)
3. Update `rfc/index.md` and `adr/TA.md` `map` state board together

---

## Voice rules

### Don't use

- **"The user shall"** / "The user must" / "The user can". Replace with specific person, specific action ("a photographer working through a difficult underwater shot...").
- **SaaS-speak filler.** Avoid: "in order to" (use "to"), "It is worth noting that" (just say it), "At this point in time" (use "now"), "Going forward" (use "from now on"), "In an effort to" (use "to").
- **"Best practices"** as a justification. Either name the principle or cite the evidence; "best practice" by itself is hand-waving.
- **The §  symbol** for section references. Use natural English in prose ("see the architecture doc, section 3.1") and slash paths in headers and code blocks (`TA/components/synthesizer`, `04/3.1`).
- **CG- prefix** on concept-doc filenames. The package is in `docs/concept/`; the prefix is redundant.

### Do use

- **Magazine-style ledes** in PRDs. Vivid, present-tense paragraph putting the reader inside the experience. No "the user can…"
- **Specific people, specific actions.** "The expedition photographer cleaning up a manta shot" beats "users editing photos."
- **Honest alternatives.** When listing alternatives considered, say *why* each was rejected, not just *that* it was. The reader should see the actual reasoning.
- **References by topic in prose, by number in headers.** In headers/footers/links: `04/3.1`, `01/The work`. In body prose: "the architecture doc", "the project concept doc, section 6".
- **The word "section"** for in-doc references in prose ("section 3.1 of the architecture doc"). It's clearer than path notation when reading sentences.

### Tone

- Direct. No throat-clearing.
- Honest about limits. When the system can't do something well, say so. Don't paper over.
- Restrained. The starter vocabulary is small on purpose. The MCP tool surface is intentionally narrow. New surfaces have to earn their place.

---

## Naming conventions

### Filenames

- Concept docs: `NN-topic.md` (e.g., `04-architecture.md`)
- PRDs: `PRD-NNN-slug.md`
- RFCs: `RFC-NNN-slug.md`
- ADRs: `ADR-NNN-slug.md`
- Folder landing pages: **always `index.md`** (not `README.md`). Top-level repo `README.md` is the only exception (GitHub convention).
- Slugs are lowercase-hyphenated

### Numbering

- Sequential within a tier; never reuse a number, even if a doc is deleted (mark it superseded instead)
- The number doesn't reflect priority or sequencing — only authoring order

### Vocabulary primitives

`.dtstyle` filenames follow the convention from `02-project-concept.md`:

- `tone_lifted_shadows_subject` (action_quality_target)
- `wb_warming_pelagic` (module_intention_context)
- `colorcal_underwater_recover_blue` (module_intention_context)

Three-part is typical; longer is acceptable when the move is specific. See the design system doc for the full convention.

---

## Code conventions

### Stack (locked)

**Runtime stack:**
- **Python 3.11+** — engine and MCP server (ADR-013)
- **darktable 5.x** for all image processing (ADR-014)
- **MCP** as the agent protocol (ADR-006)
- **TOML** for config files; **JSON** for manifests (ADR-028)
- **JSONL** for session transcripts (ADR-029)
- **Filesystem-based content-addressed storage** for versioning (ADR-018)
- **PNG (8-bit grayscale)** for masks (ADR-021)
- **Jinja2** for prompt templates (ADR-043)

**Build and package:**
- **`pyproject.toml` + hatchling** as build backend (ADR-034)
- **`src/`-layout**, single distribution, two modules: `chemigram.core` (engine, no AI deps) and `chemigram.mcp` (MCP server adapter) (ADR-034)
- **PyPI primary** for distribution; GitHub releases supplement (ADR-042)
- **SemVer** for versioning, 0.x during Phase 1, 1.0.0 at Phase 1 done (ADR-041)
- **Prompt versions are independent of package SemVer** (ADR-045)

**Dev tooling:**
- **uv** for venv + dependencies + lockfile (ADR-035)
- **pytest** with three tiers: `tests/unit/`, `tests/integration/`, `tests/e2e/` (ADR-036)
- **ruff** for lint and format — single tool, configured in `pyproject.toml` (ADR-037)
- **mypy** for type checking, strict on `chemigram.core`, looser elsewhere (ADR-038)
- **pre-commit** framework with ruff + mypy + unit tests (opt-in but recommended) (ADR-039)
- **GitHub Actions** for CI, Python 3.11/3.12/3.13 matrix, macOS-only for v1 (ADR-040)

### Structural rules

- **Single Python process, no daemon, no IPC** between subsystems (ADR-006). State is the filesystem.
- **One `darktable-cli` instance per configdir at a time.** Render pipeline must serialize subprocess calls (ADR-005).
- **No PyTorch, no model weights, no AI dependencies in `chemigram.core`.** AI is provided via MCP-configured providers (ADR-007).
- **All edit state mutations through the engine's API**, called by the agent. The engine never silently mutates state.
- **`op_params` and `blendop_params` are opaque hex/base64 blobs.** Do not decode them in v1 (ADR-008). The exception is Path C — limited to high-value modules (currently exposure), only when there's a clear bottleneck.
- **Prompt templates are append-only** (ADR-043). Once `<task>_v<N>.j2` ships, never edit it. New iterations go to new files. Active versions are declared in `MANIFEST.toml` (ADR-044) — the single source of truth.

### `darktable-cli` invocation form

Always include these flags (ADR-004, ADR-012):

```
darktable-cli <raw> <xmp> <output> \
  --width <N> --height <N> \
  --hq false \                         # for previews; true for final exports
  --apply-custom-presets false \
  --core --configdir <chemigram-config>
```

Never:
- Use `--style` for vocabulary application (ADR-011) — synthesize the XMP ourselves
- Run with `--apply-custom-presets true` — risks contaminating renders
- Share configdir between concurrent renders — darktable holds an exclusive lock on `library.db`

### Per-image repo structure

Every image lives at `~/Pictures/Chemigram/<image_id>/` with the layout in `TA/contracts/per-image-repo`. The structure is:

```
raw/                    symlink to original
brief.md
notes.md
metadata.json           EXIF cache, layer bindings
current.xmp             synthesized from current snapshot
objects/                content-addressed snapshot store (NN/HHHH...xmp)
refs/heads/<branch>     text file containing snapshot hash
refs/tags/<tag>         text file containing snapshot hash
refs/HEAD               text file: "ref: refs/heads/main" or hash
log.jsonl               append-only operation log
sessions/               session transcripts (JSONL per session)
previews/               render cache (regenerable)
exports/                final outputs
masks/                  registered masks + registry.json
vocabulary_gaps.jsonl   gaps surfaced this image
```

### MCP tool surface

The agent-callable tool surface is defined in ADR-033 and detailed in `TA/contracts/mcp-tools`. Don't add tools without an ADR. The narrow surface is a feature.

---

## Workflow conventions

### When to write what

| Situation | Write |
|-|-|
| User-value for a surface needs arguing | PRD |
| Open technical question with real alternatives | RFC |
| Settled decision, no real alternatives | ADR (direct) |
| RFC's question gets answered | ADR(s) closing the RFC |
| Discovery during implementation contradicts a doc | Update the doc; if it's an ADR, write a superseding ADR |
| Idea worth keeping but not building | TODO.md entry |
| Phase plan changes | Update IMPLEMENTATION.md |

### What "settled" means

A decision is settled when:

- The alternatives have been genuinely considered (not pattern-matched)
- The chosen path has at least one piece of supporting evidence (Phase 0 finding, prior project, established library, etc.)
- The trade-offs are known and documented

If you can't articulate why an alternative was rejected, the decision isn't settled — it's an RFC.

### Cross-doc consistency

When state changes, several files must update together. Common cases:

| Change | Updates |
|-|-|
| RFC closes into ADR(s) | RFC status, ADR file(s), `rfc/index.md`, `adr/index.md`, `adr/TA.md` `map` state board |
| New component or contract | `TA/components` or `TA/contracts`, related ADR(s) or RFC(s), `adr/index.md` |
| New constraint | `TA/constraints`, the principle in PA if user-facing, related ADR |
| Phase status change | `IMPLEMENTATION.md`, `concept/00-introduction.md` status block |
| Vocabulary contribution | New `.dtstyle` file, manifest entry, `CONTRIBUTING.md` if process changes |

Don't commit a partial state change. Either all related files update together, or none do.

---

## Phase awareness

The project is currently between phases:

- **Phase 0** (validation) — closed green, 8 findings logged into ADRs
- **Doc system** — complete (PRDs, RFCs, ADRs, references all populated)
- **Phase 1** (minimum viable loop) — **in progress**. Slices 1–3 shipped (v0.1.0, v0.2.0, v0.3.0). v0.1.0: dtstyle parser, XMP r/w + synthesizer, render pipeline, EXIF binding. v0.2.0: `chemigram.core.versioning` package (canonical_bytes/xmp_hash, ImageRepo, snapshot/checkout/branch/log/diff/tag, mask registry). v0.3.0: `chemigram.core.vocab` (manifest-driven vocabulary index), `chemigram.mcp.prompts` (PromptStore + MANIFEST + mode_a/system_v1), `chemigram.mcp.server` framework (stdio + registry + error contract + in-memory harness), 27 MCP tools across vocab/edit/versioning/rendering/ingest/mask/context-stubs, `chemigram.core.workspace` orchestrator. 8 of 17 RFCs closed: RFC-001 → ADR-050, RFC-002 → ADR-054, RFC-003 → ADR-055, RFC-005 → ADR-052, RFC-006 → ADR-051, RFC-010 → ADR-056, RFC-015 → ADR-053, RFC-016 → ADR-043/044/045. Slices 4 (real masking provider) and 5 (context layer) parallel-unblocked.

If you're doing implementation work, you're at the end of Phase 1 Slice 3 (MCP surface complete and exercised end-to-end through the in-memory harness). Slice 4 (masking) and Slice 5 (context) run in parallel next; both are unblocked by Slice 3's tool surface. The slices are described in `IMPLEMENTATION.md`'s Phase 1 section (Slices 1 through 6, each with its scope, gate, and the RFCs that close at that gate).

If you're doing doc work, you're maintaining the system, not bootstrapping it. Most additions are ADRs (closing RFCs as evidence comes in) or new PRDs (when scope expands).

If you're doing vocabulary work, you're in Phase 2 (vocabulary maturation) — but only after Phase 1 ships.

---

## Things that are easy to get wrong

### Don't

- **Don't decode `op_params` or `blendop_params`.** They're hex/base64 blobs we shuffle around as opaque strings. The opacity is load-bearing — decoding leads to per-module engineering and modversion-drift maintenance. Path C exists for the rare exceptions.
- **Don't add AI dependencies to `chemigram.core`.** PyTorch belongs in sibling projects (e.g., `chemigram-masker-sam`), behind the MCP provider abstraction.
- **Don't use `darktable-cli --style`.** It only takes one style, and we need composition. We synthesize the XMP ourselves (RFC-001 closure → ADR-011).
- **Don't propagate masks across images.** Each mask is per-image. Multi-image masking is bulk-edit territory; out of scope.
- **Don't reimplement darktable capabilities** in Python. If darktable does it, we delegate. The 'orchestration only' constraint is structural, not stylistic.
- **Don't edit accepted ADRs.** Append-only. Write a superseding ADR if you need to change a decision.

### Do

- **Do treat the filesystem as state.** No daemon, no in-memory state that needs persistence beyond what's on disk.
- **Do check `darktable-cli --apply-custom-presets false`** in every invocation.
- **Do snapshot every state change** that mutates edit history. Cheap, reversible, content-addressed.
- **Do log vocabulary gaps** when the agent reaches for something that doesn't exist. The gap log is how the vocabulary grows.
- **Do propose-and-confirm for context updates.** `taste.md` and `notes.md` updates are never silent.
- **Do read `docs/IMPLEMENTATION.md`** when planning what to work on next.

---

## When in doubt

- For *what* Chemigram is and why: `docs/concept/00-introduction.md`
- For *how* it works: `docs/concept/04-architecture.md`
- For *what's settled* technically: `docs/adr/TA.md`
- For *what's promised* to users: `docs/prd/PA.md`
- For *what to build next*: `docs/IMPLEMENTATION.md`
- For *open questions still being argued*: `docs/rfc/index.md`
- For *deferred ideas*: `docs/TODO.md`

If a question isn't answered there, it might be the start of a new RFC or PRD.

---

*CLAUDE.md · v0.1 · The operational handbook. Stand-alone by design.*
