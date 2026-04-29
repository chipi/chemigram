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
| 0 | Hands-on validation of darktable composition story | ✅ Closed green |
| Doc system | Concept package + PRDs/RFCs/ADRs | ✅ Complete |
| 1 | Core engine + MCP server + starter vocabulary | In progress — Slices 1–5 shipped (v0.1.0–v0.5.0); 13 of 17 RFCs closed (RFC-001/002/003/004/005/006/009/010/011/013/014/015/016 → ADR-050..061). Slice 6 (real-session polish + first photographer evidence + starter pack) is the only remaining Phase 1 work before 1.0.0. |
| 2+ | Vocabulary maturation, AI masks, continuous control | Conditional |

For the canonical phase plan and current status, see `docs/IMPLEMENTATION.md`.

## Documentation

The full doc tree is in `docs/`. Start at `docs/index.md` for the ecosystem overview.

The project's concept package is in `docs/concept/`, six numbered documents you read in order:

1. `docs/concept/00-introduction.md` — entry point, glossary, reading order
2. `docs/concept/01-vision.md` — the soul of the project
3. `docs/concept/02-project-concept.md` — what we're building at idea level (the loop, sessions, modes)
4. `docs/concept/03-data-catalog.md` — what feeds the system
5. `docs/concept/04-architecture.md` — engine spec
6. `docs/concept/05-design-system.md` — minimal because Chemigram is an MCP server, not a UI app

Total reading time: about two hours. If you have less, `00-introduction` + `01-vision` + the first three sections of `02-project-concept` is enough to engage with anyone working on the project.

The definition documents (PRDs, RFCs, ADRs) live in `docs/prd/`, `docs/rfc/`, and `docs/adr/`. Each has its own `index.md`. Anchored by `docs/prd/PA.md` (product reference) and `docs/adr/TA.md` (technical architecture reference).

Supporting documents:

- `docs/IMPLEMENTATION.md` — canonical phase plan
- `docs/LICENSING.md` — what's MIT, what's separate
- `docs/CONTRIBUTING.md` — code and vocabulary contribution flows
- `docs/TODO.md` — research backlog, deferred items
- `docs/briefs/` — historical design-conversation artifacts (predate the formal package)
- `examples/iguana-galapagos.md` — a worked Mode A session
- `examples/phase-0-notebook.md` — Phase 0 lab notebook (closed green)

## Requirements

- darktable 5.x (Apple Silicon native build recommended)
- Python 3.11+
- An MCP-capable agent (Claude, etc.)
- macOS Apple Silicon for v1; Linux best-effort

## Contributing — quick start

```bash
git clone https://github.com/chipi/chemigram.git
cd chemigram
./scripts/setup.sh
```

That checks prerequisites, creates a venv, and installs everything. See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for the full process and [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) for what's being built right now.

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
