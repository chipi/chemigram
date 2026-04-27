# Chemigram

> Chemigram is to photos what Claude Code is to code.

A craft-research project for agent-driven photo editing. The agent reads
your taste, you describe intent, the agent edits via a vocabulary of
named moves on top of darktable. Sessions accumulate; the project gets
richer over time.

**Status:** early-stage research project. v1 in active development.
Not a Lightroom replacement. Not a digital asset manager. A probe into
where photographic taste lives and how it transmits through language
and feedback.

## What this is

A photo is a project, structured the way a code project is. The agent
reads your context (`taste.md`, the brief, accumulated notes), drives
darktable headlessly through composable vocabulary primitives, manages
masks and snapshots, and learns across sessions. Two modes:

- **Mode A (the journey)** — collaborative editing where you and the
  agent work through one photo together, conversationally.
- **Mode B (autonomous fine-tuning)** — agent runs alone, branching to
  explore variants, self-evaluating against criteria you provide.

## What makes it different

- **Vocabulary, not sliders.** The agent's action space is a finite
  set of named moves you (or the community) author as `.dtstyle`
  files. Articulating the vocabulary is part of the experiment.
- **Three foundational disciplines** in the architecture:
  - *darktable does the photography, Chemigram does the loop*
  - *Bring Your Own AI* — maskers, evaluators, the photo agent itself
    are all configurable via MCP
  - *Agent is the only writer* — full library isolation, replace
    semantics, predictable action space
- **Mini git for photos.** Content-addressed DAG of edit snapshots
  per image. Branches, tags, the works.
- **Compounding context.** Each session reads your `taste.md` and
  per-image notes; agent proposes additions; you confirm. Future
  sessions are faster and more aligned because context accumulates.

## Status and roadmap

| Phase | What | Status |
|-|-|-|
| 0 | Hands-on validation of darktable composition story | spec ready |
| 1 | Core engine + MCP server (~1,800 lines) | not started |
| 2 | Local adjustments via BYOA masking providers | spec ready |
| 3 | Agent context layer (`taste.md`, sessions, gaps) | spec ready |
| 4 | Polish, tests, packaging | future |
| 5+ | Mode B, programmatic vocabulary, color science fitting | TODO.md |

See `docs/TODO.md` for deferred items, `examples/phase-0-notebook.md`
for what to do first.

## Documentation

Read in this order if you're new:

1. `docs/chemigram.md` — the project's framing
2. `docs/agent-context.md` — how the agent works (Claude Code analog)
3. `docs/architecture.md` — engine spec
4. `examples/iguana-galapagos.md` — a worked Mode A session

For going deeper:

- `docs/layers.md` — the L0–L3 model
- `docs/local-adjustments.md` — masking, AI subject isolation
- `docs/versioning.md` — content-addressed snapshot DAG
- `docs/LICENSING.md` — what's MIT, what's separate
- `docs/CONTRIBUTING.md` — code and vocabulary contribution flows
- `docs/TODO.md` — research backlog, deferred items

## Requirements

- darktable 5.x (Apple Silicon native build recommended)
- Python 3.11+
- An MCP-capable agent (Claude, etc.)
- macOS Apple Silicon for v1; Linux best-effort

## License

MIT. Engine, MCP server, docs, starter vocabulary, and borrowed community
packs are all permissively licensed. Personal vocabularies are kept in
separate private repos by photographers' choice. See `docs/LICENSING.md`
for the full picture.

## Why "Chemigram"?

A chemigram is a cameraless photographic process where an image emerges
from a chemical reaction on light-sensitive paper — guided by the
artist, but not fully controlled. The name fits: each edit here emerges
from a loop between a photographer's intent, an agent's moves, and a
tool that responds. Authorship is shared and the result is one-of-a-kind.
