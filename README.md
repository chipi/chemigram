# Chemigram

> Chemigram is to photos what Claude Code is to code.

A craft-research project for agent-driven photo editing. The agent reads
your taste, you describe intent, the agent edits via a vocabulary of
named moves on top of darktable. Sessions accumulate; the project gets
richer over time.

**Status:** v1.1.0 shipped April 2026 — Phase 1 closed; comprehensive
validation milestone shipped (519 tests, real-darktable e2e suite, three
engine bugs fixed); Phase 2 (use-driven vocabulary maturation) in progress. Not a Lightroom replacement. Not a
digital asset manager. A probe into where photographic taste lives and
how it transmits through language and feedback.

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
| 1 | Core engine + MCP server + starter vocabulary | ✅ Closed (v1.0.0) — Slices 1–6 shipped (ADR-050..061). |
| 1.1 | Comprehensive validation — capability matrix + real-darktable e2e | ✅ Closed (v1.1.0) — 519 tests; 3 engine bugs fixed (ADR-062). |
| 1.2 | Engine unblock + reference-image validation infrastructure | ✅ Closing (v1.2.0) — Path B synthesizer + assertion library + Mode A v3 (ADR-063..068). |
| 1.3 | Command-line interface | In flight (v1.3.0) — RFC-020 + PRD-005; mirrors MCP tool surface. |
| 1.4 | `expressive-baseline` vocabulary authoring (35 entries) | Planned (v1.4.0) — hands-on darktable work; engine already unblocked. |
| 2 | Vocabulary maturation — grow vocab from session evidence | Begins post-v1.4.0 (use-driven; intermittent). |
| 3+ | AI masks, continuous control | Conditional |

For the canonical phase plan and current status, see `docs/IMPLEMENTATION.md`.

## Quickstart — conversational (MCP)

For interactive editing through Claude Desktop, Claude Code, and other MCP clients.

```bash
# 1. install
pip install chemigram

# 2. set up your taste (cross-image preferences)
mkdir -p ~/.chemigram/tastes
$EDITOR ~/.chemigram/tastes/_default.md   # what you generally like

# 3. point your AI client at chemigram-mcp.  e.g. for Claude Code, drop this
#    into .mcp.json (project) or ~/.claude/mcp.json (global):
#
#    {"mcpServers": {"chemigram": {"command": "chemigram-mcp"}}}

# 4. start a conversation in your client:
#    "Ingest /path/to/photo.NEF.  Read context.  Render a preview."
```

For the full flow — darktable setup, MCP-client matrix (Claude Code / Desktop, Cursor, Continue, Cline, Zed, OpenAI), 10-turn worked session, troubleshooting — read **[`docs/getting-started.md`](docs/getting-started.md)**.

## Quickstart — scripts and agent loops (CLI, v1.3.0+)

For batch processing, shell scripts, and agent loops where MCP's session model is the wrong shape. The CLI mirrors the MCP tool surface verb-for-verb (`chemigram apply-primitive` ↔ MCP `apply_primitive`); see PRD-005 / RFC-020 for the design.

```bash
# 1. install — same as above
pip install chemigram   # also lands `chemigram` on $PATH

# 2. inspect the runtime
chemigram status

# 3. ingest a raw + apply a vocabulary entry
export CHEMIGRAM_DT_CONFIGDIR=~/chemigram-phase0/dt-config   # see getting-started for setup
chemigram ingest ~/Pictures/raw/iguana.NEF
chemigram apply-primitive iguana --entry expo_+0.5
chemigram render-preview iguana --size 1024
chemigram export-final iguana --format jpeg

# 4. machine-readable output for scripts and agents (NDJSON)
chemigram --json apply-primitive iguana --entry wb_warm_subtle
# {"event":"result","status":"ok","image_id":"iguana","entry":"wb_warm_subtle", ...}
```

The CLI is stateless per invocation — parallel calls against different images are safe. The image_id derives from the raw filename's stem (case-preserving): `iguana.NEF` → `iguana`, `IMG_2041.ARW` → `IMG_2041`. **Concurrent calls against the same image are not tested**; the engine writes refs without an explicit fcntl lock, so serialize at the caller level if a single image is touched by multiple subprocesses simultaneously. For the full verb surface, see [`docs/guides/cli-reference.md`](docs/guides/cli-reference.md). For driving Chemigram from a custom agent loop, see the "Agent loops" section of [`docs/getting-started.md`](docs/getting-started.md).

## How it works

```
       ┌────────────────────┐         ┌──────────────────────────────┐
       │  Your AI client    │  MCP    │  chemigram-mcp (this package) │
       │  Claude Code, etc. │◄───────►│                              │
       └────────────────────┘ stdio   │   ┌─────────────────────┐    │
                  ▲                   │   │ chemigram.core      │    │
                  │ vision + sampling │   │   vocab │ versioning │    │
                  │ (for masks)       │   │   masking│ context    │    │
                  ▼                   │   │   pipeline │ session  │    │
       ┌────────────────────┐         │   └──────────┬──────────┘    │
       │  ~/.chemigram/     │         │              │               │
       │   tastes/          │         │              ▼               │
       │   vocabulary/      │         │       ┌──────────────┐       │
       │     personal/      │         │       │ darktable-cli│       │
       └────────────────────┘         │       │  (rendering) │       │
                                      │       └──────────────┘       │
                                      └──────────────┬───────────────┘
                                                     │ writes
                                                     ▼
                              ~/Pictures/Chemigram/<image_id>/
                                snapshots/  exports/  sessions/  masks/
```

The agent reads your context and the brief, drives darktable through a vocabulary of named moves, manages snapshots and masks, and proposes updates to your taste files at session end. Every tool call is recorded to a JSONL transcript so sessions are auditable and replayable.

A typical 6-turn opening:

```
You:    Ingest /tmp/manta.NEF.  Read context.

Agent:  Ingested as image_id "manta".  Tastes loaded:
        natural tone curves, lifted shadows, restrained colors.
        EOS R5, no L1 templates yet.  Notes empty.

You:    Render preview.  The water feels too cyan.

Agent:  [render → wb_warm_subtle → render]  Slate-blue now.

You:    Lift the shadows on the manta belly.  Use a subject mask.

Agent:  [generate_mask → apply tone_lifted_shadows_subject]  Edge
        too sharp?  I can regenerate with softer feathering.

You:    Yes.  Then export at full res.  Tag this v1-export.

Agent:  [regenerate_mask → re-apply → tag → export_final]  Done.
        Two propose-and-confirms before we wrap?
```

See **[`docs/getting-started.md`](docs/getting-started.md#your-first-session)** for a full 10-turn walkthrough.

## Growing your vocabulary

The starter vocabulary that ships with `chemigram` is deliberately small — five entries. Phase 2 grows it from real session evidence: the agent logs gaps when it reaches for moves you don't have; once a month or so, you open darktable, capture the missing primitives as `.dtstyle` files, and drop them into `~/.chemigram/vocabulary/personal/`. After 3 months of regular use most photographers reach 30–60 personal entries; after 6 months, 80–120. The vocabulary becomes an articulation of *your* craft.

Full procedure in **[`docs/getting-started.md`](docs/getting-started.md#growing-your-vocabulary)** and **[`vocabulary/starter/README.md`](vocabulary/starter/README.md)**.

## Documentation

For users:

- **[`docs/getting-started.md`](docs/getting-started.md)** — install, MCP-client config, first session, troubleshooting
- **[`vocabulary/starter/README.md`](vocabulary/starter/README.md)** — what ships in the bundled pack, how to grow your personal pack

For people engaging with the project deeper:

- **`docs/concept/`** — six numbered concept documents (read end-to-end, ~2h):
  `00-introduction.md`, `01-vision.md`, `02-project-concept.md`,
  `03-data-catalog.md`, `04-architecture.md`, `05-design-system.md`
- **`docs/prd/`**, **`docs/rfc/`**, **`docs/adr/`** — definition documents (PRDs argue user-value; RFCs argue open technical questions; ADRs commit to settled decisions). Anchored by `docs/prd/PA.md` and `docs/adr/TA.md`.
- **`docs/IMPLEMENTATION.md`** — canonical phase plan
- **`docs/CONTRIBUTING.md`** — code + vocabulary contribution flows
- **`docs/LICENSING.md`** — what's MIT, what's separate
- **`docs/TODO.md`** — research backlog, deferred items
- **`examples/iguana-galapagos.md`** — a worked Mode A session, prose form

## Requirements

- darktable 5.x (Apple Silicon native build recommended)
- Python 3.11+
- An MCP-capable AI client — Claude Code, Claude Desktop, Cursor, Continue, Cline, Zed, or anything that supports MCP stdio servers
- macOS Apple Silicon for v1; Linux best-effort

## Contributing

If you want to work on the engine itself (not just use it):

```bash
git clone https://github.com/chipi/chemigram.git
cd chemigram
./scripts/setup.sh
```

That checks prerequisites, creates a venv, and installs everything. See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for the full process and [`docs/IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) for what's being worked on now.

If you want to contribute vocabulary entries (Phase 2 path), see [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) § Vocabulary contributions.

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
