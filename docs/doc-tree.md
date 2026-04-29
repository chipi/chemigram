# How the docs are organized

The doc tree has three tiers, each answering different kinds of questions. If you're looking for the user guide, that's [Getting started](getting-started.md); this page is the map for everything else.

## Tier 1 — Concept package (`concept/`)

Read end-to-end at least once. Establishes *why* and *what* at the project level. Six numbered documents in reading order:

- `concept/00-introduction.md` — entry point, glossary
- `concept/01-vision.md` — the soul of the project
- `concept/02-project-concept.md` — the loop, sessions, modes
- `concept/03-data-catalog.md` — what feeds the system
- `concept/04-architecture.md` — engine spec
- `concept/05-design-system.md` — voice, vocabulary naming, session format

These are narrative documents — they read as prose, end-to-end. Updated rarely; treated as source-of-truth for intent.

## Tier 2 — Definition documents (`prd/`, `rfc/`, `adr/`, `uxs/`)

Per-artifact docs that argue for, deliberate over, or commit to specific aspects of the project. Read by linking-into them from work in progress.

### Product plane (`prd/`)

PRDs argue for user-value. Each PRD names a surface or experience and makes the case.

- `prd/PA.md` — reference: audiences, promises, principles
- `prd/index.md` — listing
- `prd/PRD-NNN-*.md` — per-experience arguments

### Tech plane (`rfc/` + `adr/`)

Two folders for the same plane. RFCs are the moving tier (open questions, deliberation). ADRs are the settled tier (locked decisions).

- `adr/TA.md` — reference: components, contracts, constraints, stack, state board (`/map`)
- `adr/index.md` — listing
- `adr/ADR-NNN-*.md` — locked decisions
- `rfc/index.md` — listing
- `rfc/RFC-NNN-*.md` — open technical questions

### UX plane (`uxs/`)

N/A in v1 — Chemigram is an MCP server with no UI surfaces. Folder exists for forward-compatibility if a UI ever ships.

## Tier 3 — Operational docs

- `../CLAUDE.md` — operational handbook for AI-assisted work (at repo root)
- `IMPLEMENTATION.md` — canonical phase plan and slice-by-slice implementation guide
- `LICENSING.md` — what's MIT, what's separate
- `CONTRIBUTING.md` — code and vocabulary contribution flows
- `TODO.md` — research backlog, deferred items
- `briefs/` — historical design-conversation artifacts

## How the tiers relate

The concept package sets intent. The definition documents (PRDs, RFCs, ADRs) argue, deliberate, and lock specifics within that intent. When a per-artifact doc would contradict the concept package, one of them is wrong (usually the per-artifact doc, but not always — implementation feedback can require updating the concept package too).

Per-artifact docs anchor to reference docs. The reference docs (PA, TA) are what make the per-artifact docs cohere. A PRD that doesn't anchor to PA is a smell. An RFC that doesn't anchor to TA is a smell.

Reference docs evolve with the project; concept-package docs evolve more slowly.

## How to find what you need

| If you want to... | Go to... |
|-|-|
| Install and use Chemigram | [`getting-started.md`](getting-started.md) |
| Understand the project | `concept/00-introduction.md` |
| See the phase plan / current status | `IMPLEMENTATION.md` |
| Know how to work in this repo (conventions, voice, code rules) | `../CLAUDE.md` (at repo root) |
| Argue for / understand a user-experience | `prd/PRD-NNN-*.md` |
| Look up a settled technical decision | `adr/ADR-NNN-*.md` |
| Understand an open technical question | `rfc/RFC-NNN-*.md` |
| Find what's settled in tech | `adr/TA.md` |
| Find what we promise users | `prd/PA.md` |
| Contribute vocabulary | `CONTRIBUTING.md` § Vocabulary contributions |

## Conventions

- File numbering is sequential within a tier (NN, PRD-NNN, RFC-NNN, ADR-NNN)
- Slugs are lowercase-hyphenated
- Per-artifact docs always anchor to their plane's reference doc
- Documents stand alone — references to external methodology guides are not used in the public docs (the methodology is a private writer's tool, the artifacts are the deliverables)
- Drafts are honest about maturity (see `rfc/index.md` for maturity legend)
