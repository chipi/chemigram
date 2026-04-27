# Chemigram

*Agent-driven photo editing as a feedback loop experiment.*

> A chemigram is a cameraless photographic process where an image emerges from a chemical reaction on light-sensitive paper — guided by the artist, but not fully controlled. The name fits: each edit here emerges from a loop between a photographer's intent, an agent's moves, and a tool that responds. Authorship is shared and the result is one-of-a-kind.

## Premise

Not a workflow replacement. A craft research project.

The interesting question isn't *"can an LLM agent edit a photo"* — it's **"can I transmit taste through language and feedback, and does the agent develop something resembling judgment when given good tools?"**

The agent gets a raw file and a verbal brief. It edits, previews, listens to feedback, iterates. I am the photographer, the critic, and the source of intent. The agent is an apprentice with infinite patience and good tooling.

## Chemigram is to photos what Claude Code is to code

The clearest one-line framing of the whole project. If you've used Claude Code (or Cursor, or any agentic-coding tool with a project-aware assistant), you know the shape:

- A working directory is the unit of work
- A `CLAUDE.md` file captures durable context about the project
- The agent reads context, you describe intent, the agent acts
- Tools touch the filesystem; version control captures every step
- Sessions accumulate; the project gets richer over time
- The agent isn't stateless — its state is externalized into files

Chemigram applies this shape to photo editing. A photo is a project. `taste.md` is the durable context. The agent reads, the photographer briefs, the agent edits via vocabulary, previews are the "tests," snapshots are the commits. Across sessions, the project (image + taste + vocabulary + history) accumulates. The agent gets smarter about *this photographer's* work over time.

This isn't just rhetoric — it's the structuring metaphor for everything below. See `agent-context.md` for how the loop actually works.

## One stance with several consequences

Chemigram is **fully agent-driven**. The agent is the only writer; the photographer is the reader and critic. This single stance propagates through the architecture in ways worth naming up front, because it explains decisions that would otherwise look like separate engineering choices:

- **Full library isolation.** The agent must never mutate the photographer's real edits or contaminate the real catalog. Chemigram runs against a separate darktable configdir, separate workspace, separate everything. The isolation is a safety boundary, not a convenience.
- **Replace semantics for primitives, not accumulate.** The agent operates without a human pressing undo. Applying `expo_+0.5` means "exposure is now +0.5", not "exposure is now whatever-plus-0.5". A predictable, idempotent action space is cleaner cognition for the agent than one where it has to track its own history and reason about accumulation.
- **Vocabulary as action space, not sliders.** A finite, named, inspectable set of moves is a better thing for an agent to reason over than a continuous parameter. Same logic as why function-calling beats freeform text for tool use: structure helps. The vocabulary is also where taste lives — articulating it is part of the experiment.

These three are the same decision wearing three hats. The architecture follows from them.

## Two modes

Chemigram operates in two distinct modes, sharing the engine but answering different research questions.

### Mode A — the journey (collaborative)

Photographer uploads an image, articulates intent in language, agent proposes moves and renders previews, photographer responds, loop continues until "yes, that's it." Few iterations (5–30). Rich verbal feedback. Photographer in the loop continuously.

The research question: **how does taste transmit through language and feedback?** Where is the photographer's taste verbal vs. pre-verbal? Does the agent develop session-level heuristics? Where does the loop break?

This is the primary mode and the foundation of the project. Mode A sessions are also where preference data accumulates for Mode B.

### Mode B — the autonomous fine-tuner

Photographer provides image + brief + **evaluation criteria** + budget ("up to 200 iterations, up to 8 hours"). Agent runs the loop alone, branching to explore variants, self-evaluating against the criteria, converging to a winner (or running out of budget). At the end: best result, the explored tree, an evaluation log.

The research question: **can the agent self-evaluate well enough to converge without human feedback?** What's the right eval function — reference-based, vision-model self-eval, or a learned critic from accumulated Mode A history? (See `TODO.md` for that question's status — kept open deliberately.)

Mode B is inspired by the data/eval/iterate pattern (Karpathy-style), and it's only meaningful with **versioning** in place — autonomous exploration produces a tree of variants, not a sequence. Without a way to record and inspect that tree, the agent's reasoning is opaque. See `versioning.md`.

### How they relate

Mode A first. Mode B inherits Mode A's vocabulary and accumulated preference data. Without Mode A, Mode B has nothing of *your* taste to optimize toward. Without Mode B, every image is hours of your time.

The progression is the experimental arc — not just two features.

## Engine and architecture

The technical spec lives in `architecture.md`. Headline summaries here:

**Foundation.** darktable's XMP stores module params as hex-encoded C structs, so we don't manipulate them directly. Instead, the photographer authors (or borrows) a **vocabulary** of named single-module styles. The agent composes edits by selecting from that vocabulary. The vocabulary itself becomes the locus of the experiment — articulating it is part of transmitting taste.

**Layer model.** Edits stack in three layers (`layers.md`): L1 technical correction (lens, denoise; opt-in per-camera/per-lens bindings), L2 look establishment (neutralizing scene templates *or* look-committed film simulations), L3 the agent's vocabulary. L1 and L2 are pre-baked into the image's baseline before the agent starts; L3 is the agent's playground.

**Versioning.** Each image is a content-addressed DAG of XMP snapshots — branches, tags, HEAD pointer, "mini git for photos" (`versioning.md`). Mode A uses it for natural "explore from here" branching. Mode B requires it for tree-shaped autonomous exploration to be inspectable.

**Pipeline stages.** The render pipeline is a sequence of stages, of which v1 has one (`darktable-cli`). Future stages — external CLIs, Python preprocessors, GenAI tools via MCP — implement a small `PipelineStage` contract and slot in. We don't build them speculatively; we keep the door open.

**Disciplines.** Three load-bearing principles:

- *darktable does the photography, Chemigram does the loop.* Every image-processing capability comes from darktable.
- *Bring Your Own AI.* Chemigram doesn't ship AI capabilities; it integrates them via MCP. Maskers, evaluators, the photo agent itself — all photographer-configured. Chemigram is the orchestration layer.
- *Agent is the only writer.* The photographer reads previews and gives feedback; the agent is the sole mutator (covered in "One stance with several consequences" above).

The first keeps Chemigram out of image-processing engineering; the second keeps it out of ML engineering; the third keeps the action space legible. Together they give the project a tractable scope.

## Why darktable, not Lightroom

Lightroom's SDK runs *inside* the GUI app — the app must be open, focused on the right photo, and the SDK can't touch AI masks or brushes cleanly. Workable but fragile.

darktable inverts the model:

- `darktable-cli` runs fully headless. Render a preview = one command, ~1–2s.
- The entire edit state lives in a plain-text XMP sidecar. Read → mutate → re-render → look → repeat.
- `.dtstyle` XML files capture single-module styles in a portable, copyable format that powers the vocabulary approach.
- Recent versions added external raster mask support — the path for AI subject masks via Python-side SAM/FAST-SAM.
- Scene-referred pipeline + color calibration module is genuinely better-suited to underwater color recovery than LR's white balance + HSL dance.
- Rich local-adjustment surface (parametric masks, drawn masks, raster masks, contrast equalizer, diffuse-or-sharpen, haze removal) covers everything LR offers and then some.

Prior art exists: `darktable-mcp` (w1ne on GitHub) is an early MCP wrapper around darktable's Lua API. Different architectural path. We start fresh.

## Open questions the experiment will probe

- Can the photographer articulate "good" well enough in language that the agent's edits converge? Discovering where taste is verbal vs. pre-verbal is itself a finding.
- Does the agent develop session-level heuristics? ("User keeps pulling back highlights I push — bias lower.") Worth instrumenting.
- Where does Mode A fail? Hypothesis: global moves are easy, local intent is hard, and **restraint is hardest** — knowing when to stop. LLMs love to keep tweaking.
- Underwater-specific: can the agent learn the distinction between "removing color cast" (correct) and "killing the underwater feeling" (wrong)? Real craft line, good probe.
- For Fuji film sims: how much of "taste" is the L2 template vs. the L3 refinement? When the look is pre-committed at capture, the agent's job is smaller — different mode of taste transmission than the underwater-from-neutral case.
- Does Mode B's eval function converge to something useful? See TODO.md — kept open deliberately.

## What this is not

- A Lightroom replacement.
- A bulk-editing automation tool.
- A digital asset manager. Chemigram is per-image, not a catalog. Image classification, taxonomy, tagging, and search are deliberately out of scope — possibly a separate sibling project later. See `TODO.md` for that thinking.
- A "make my photos look professional" service.
- A test of whether AI can replace the photographer.

It's a probe into where taste lives, how it transmits, and what an agent can do with good tools and a real craftsperson in the loop.

## Document map

- `chemigram.md` — this doc, the project's framing.
- `agent-context.md` — how the agent works: context files, prompt patterns, behavioral disciplines. The Claude-Code-equivalent for photo work.
- `architecture.md` — engine spec, MCP tool surface, pipeline stages, EXIF auto-binding.
- `layers.md` — the L0–L3 model, with Fuji film sims as worked example.
- `local-adjustments.md` — masking, AI subject isolation, the local-adjustment vocabulary subsystem.
- `versioning.md` — content-addressed DAG of edit snapshots.
- `examples/iguana-galapagos.md` — worked Mode A session demonstrating the full loop.
- `TODO.md` — research backlog, open hypotheses, deferred items.
- `LICENSING.md` — what's MIT, what's separate.
- `CONTRIBUTING.md` — code and vocabulary contribution flows.
