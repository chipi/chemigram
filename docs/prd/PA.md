# PA — Product Reference

> Reference document for the product plane.
> Version · v0.1 · 2026-04-27
> Sources · `docs/concept/01-vision.md`, `docs/concept/02-project-concept.md`

The reference document for who Chemigram is for, what it commits to, and how decisions get made when they're hard. PRDs anchor into this with paths like `PA/audiences/photographer` or `PA/promises/compounding-context`.

This document is **read by linking-into specific sections** — never end-to-end. Amended whenever the project's audience, commitments, or decision principles shift.

---

## audiences

Who Chemigram serves, ranked by primacy. Decisions tilt toward the higher-ranked audience when they conflict.

### audiences/photographer

The primary audience. A serious photographer who wants depth on individual images rather than throughput across many. Three sub-shapes:

- **The expedition photographer** — works through demanding raws (underwater, wildlife, harsh light) where the editing surface is large and the right edit is non-obvious. Wants vocabulary they can reach for and an apprentice to test moves with.
- **The taste-articulator** — interested in externalizing how they edit, building a vocabulary that captures their craft, watching their `taste.md` accumulate over months. Treats the system as a research project on their own work.
- **The exploratory editor** — uses Mode A for the conversation, branches to try variants, tags the result they want. Often returns to images across sessions; the per-image notes file is alive.

What unites them: they care about *one photo at a time, deeply*. Daily-driver volume work happens elsewhere.

### audiences/contributor

Photographers who contribute vocabulary to the OSS repo (starter pack additions, community packs). Or developers contributing to the engine.

The vocabulary contribution path is genuinely different from typical OSS — `.dtstyle` files are opaque, review requires running darktable, the discipline (uncheck non-target modules in the create-style dialog) has to be communicated. PA bears this in mind when decisions affect contributor experience.

### audiences/researcher

Implicit but real. Someone studying how AI assists creative work, examining session transcripts and `taste.md` evolutions for what they reveal about taste transmission. Chemigram's outputs (anonymized session transcripts, vocabulary-as-artifact) become research data for this audience.

This audience never directly drives PRDs but shapes principles. Decisions that protect session inspectability or vocabulary versionability are partly for them.

### Not an audience

| Not... | Because... |
|-|-|
| **Bulk-edit users** | Chemigram is per-image research, not throughput tooling. People wanting to process 500 wedding photos in an evening are looking for Lightroom or Capture One, not this. |
| **Beginners learning photo editing** | The vocabulary system assumes the photographer already has taste they're trying to articulate. A beginner without a vocabulary of their own gets little from the project. |
| **Generalist AI-edits-my-photos users** | Chemigram doesn't have taste of its own. It has *your* taste, articulated through use. Users who want "make my photos look professional" should use a service that ships opinionated defaults. |

---

## promises

What the project commits to delivering. These are the test for whether a feature earns being built — does it deliver a promise, or expand scope?

### promises/compounding-context

> The fiftieth session is faster and more aligned than the first because the project accumulates context.

`taste.md` grows. Vocabulary grows. Per-image `notes.md` accumulates. The agent reads richer context at every session start. Sessions get shorter (12 turns instead of 25) because the agent doesn't have to re-learn things.

This is *the* central promise. Most other promises serve this one.

### promises/vocabulary-as-voice

> The photographer's vocabulary captures how they actually edit, in named, portable, inspectable artifacts they (or another photographer) can read.

After a year of use, the photographer has 100-200 named moves encoded as `.dtstyle` files. The vocabulary is *theirs* — articulated through use, not inherited from a starter pack. It's also a research artifact: a portrait of how one photographer edits.

### promises/agent-as-apprentice

> The agent has bearings (read context first), opinions (raise composition tensions), and limits (defer to the photographer on judgment). Not subservient, not autonomous — apprentice.

This shapes voice rules in the design system doc, the behavioral disciplines in the project concept doc (section 6), and the agent's prompt template. When the agent feels too sycophantic or too confident, it's drifting from this promise.

### promises/inspectable-state

> Every state the photographer or agent has been in is recoverable. Every snapshot is content-addressed. Every session is transcribed. Nothing is silent.

This delivers two values: trust (the photographer can audit what happened), and research-readiness (the project's state is its own corpus).

### promises/photographer-controls-everything

> The agent never silently mutates lasting state. Vocabulary applications snapshot. Context updates propose-and-confirm. Sessions log every turn. The photographer always knows what's accumulating.

This is downstream of the *agent is the only writer* discipline (TA/constraints/agent-only-writes), but spelled out at the user-experience level.

### promises/byoa-extensibility

> The photographer chooses which AI capabilities to use. Maskers, evaluators, the photo agent itself — all configurable. The engine is the substrate.

Practically: anyone can swap providers. Future masking providers, future evaluators, alternative photo agents all integrate via MCP without touching engine code.

### promises/the-loop-is-fast

> Render previews are 1–3 seconds. Snapshots are cheap. Branching is cheap. The conversational loop never stalls on infrastructure.

This is a performance promise that affects implementation: caching, subprocess management, render-pipeline efficiency. Phase 0 confirmed it (~2s for 1024px on Apple Silicon).

### promises/gracefully-bounded

> Chemigram doesn't try to be everything. It is per-image research. Daily-driver workflow is somewhere else. Catalog management is somewhere else. The bounded scope is part of what makes it work.

Every "could we add X" question gets tested against this. If X is daily-driver tooling, the answer is no.

---

## principles

How decisions get made when they're hard. Principles cite each other and TA/constraints frequently.

### principles/agent-is-the-only-writer

The photographer reads previews and judges. The agent is the sole mutator of edit state. When in doubt about whether the photographer or the agent should perform an action, default to the agent doing it through tooling — even if it would be slightly more convenient for the photographer to do it directly.

This propagates into: SET-not-ADD semantics, vocabulary not slider parameters, isolated configdir, propose-and-confirm for context.

Anchored from: TA/constraints/agent-only-writes, ADR-024

### principles/darktable-does-the-photography

Chemigram contributes orchestration, vocabulary, agent loop, versioning, session capture. Every image-processing capability comes from darktable. When the question is "should we build X?" and X is color science, lens correction, denoise, tone, mask logic — the answer is no. darktable already has it.

Anchored from: TA/constraints/dt-orchestration-only, ADR-025

### principles/byoa

No AI capabilities bundled with the engine. No PyTorch dependency in `chemigram_core`. No model weights. Every AI capability is one MCP call away to a photographer-configured provider. Quality, speed, and cost are explicit tradeoffs the photographer makes, not engine decisions.

Anchored from: TA/constraints/byoa, ADR-007

### principles/restraint-before-push

When in doubt about whether to add a feature, vocabulary entry, or capability — restrain. The starter vocabulary is deliberately small. The MCP tool surface is intentionally narrow. The engine is intentionally bounded.

This is a bias against scope expansion. New surfaces have to earn their place by delivering a promise.

### principles/opaque-where-possible

`op_params` and `blendop_params` are hex/base64 blobs. We don't decode them. The vocabulary primitive is the abstraction; the underlying bytes are darktable's concern. We resist the pull toward "it would be cleaner if we parsed the C struct" — that path leads to per-module engineering and modversion drift maintenance.

Programmatic generation (Path C) exists as a future refinement for high-value modules only, not as a default approach.

Anchored from: TA/constraints/opaque-hex-blobs

### principles/local-and-private

Session data, taste evolution, vocabulary gaps stay on the photographer's machine. No telemetry. No cloud dependency. No "anonymized analytics." The photographer owns the entire artifact.

If a future feature would publish session insights or taste data, that's an explicit photographer choice, never a default.

Anchored from: TA/constraints/local-only-data, ADR-027

### principles/vocabulary-grows-with-use

The vocabulary is not supposed to be complete on day one. It grows as sessions surface gaps. Gap-surfacing is part of the loop, not a failure. The mature vocabulary captures the photographer's craft *because* they authored what they reached for, not because someone shipped a comprehensive starter.

This shapes the starter pack scope (small), the gap-surfacing ergonomics (always present in tooling), and the feature priority for programmatic generation (lower-priority than gap surfacing).

### principles/honest-about-limits

When the system can't do something well, say so. When a render takes longer than a session feels like it should. When a mask is imprecise. When a vocabulary is wrong for the photographer's intent. Surface the limit, don't hide it.

This shapes voice (the design system doc), the agent's behavioral disciplines (project concept, section 6), and error-handling style throughout.

### principles/compounding-over-throughput

Optimize for the fiftieth session, not the first. A small ergonomics annoyance that pays off in compounding context (e.g., propose-and-confirm `taste.md` updates) wins over a frictionless one-time experience that doesn't compound.

This is the principle that justifies the ergonomic costs in the system. They're not bugs; they're load-bearing.

---

## Changelog

- **v0.1** · 2026-04-27 · Initial population from 01 + 02. Audiences, promises, principles distilled into anchorable form.

---

*PA · v0.1 · This is a reference document. Read by linking-into specific sections.*
