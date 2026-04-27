# Chemigram — Licensing

*What's open, what's not, why.*

Chemigram is a permissive open-source project: engine, MCP server, documentation, starter vocabulary, and bundled community packs are MIT-licensed. Personal vocabularies and session data live outside the project by design.

## TL;DR

| Component | License | Repo |
|-|-|-|
| Engine (`chemigram_core`) | MIT | this monorepo |
| MCP server (`chemigram_mcp`) | MIT | this monorepo |
| Documentation (`docs/`) | MIT | this monorepo |
| Starter vocabulary (`vocabulary/starter/`) | MIT | this monorepo |
| Borrowed / community vocabulary packs (`vocabulary/packs/`) | Per-pack (typically MIT/CC) | this monorepo with attribution |
| Personal vocabularies | Photographer's choice | separate, non-public repos |
| User session data | Local-only, never uploaded | the user's machine |

## What's MIT-licensed

The MIT license covers everything in this repository unless explicitly noted otherwise. That includes:

- All Python source code (engine, MCP server, supporting tooling).
- All documentation files (`*.md`).
- The starter vocabulary in `vocabulary/starter/` — a minimal demonstration set sufficient to validate the system and give first-time users a working starting point.
- Test fixtures, example configurations, and any tooling that ships with the engine.

You can use this code and content for any purpose — personal, commercial, modified, redistributed — as long as you preserve the copyright notice. See the `LICENSE` file at the repo root for the full text.

## What's borrowed (and how)

Some vocabulary content in `vocabulary/packs/` is borrowed from existing community projects (Fuji film simulation packs, Nikon picture-control emulations, etc.). Each borrowed pack:

- Lives in its own subdirectory under `vocabulary/packs/`.
- Includes an `ATTRIBUTION.md` crediting the upstream source(s).
- Preserves the upstream license (typically MIT or CC variants).
- Is version-pinned to a specific upstream commit so changes are auditable.

If you contribute a new pack derived from existing community work, follow the same pattern. Don't relicense someone else's content; redistribute under their terms with proper credit.

## What's deliberately not in this repository

### Personal vocabularies

The vocabulary that captures *a specific photographer's taste* is not part of this OSS project. Vocabulary entries calibrated to one photographer's craft are personal artifacts — they encode that person's choices and visual identity.

Photographers using Chemigram are encouraged to author their own vocabulary in private repositories. The project's research thesis is that *articulating taste is part of the experiment* — being handed someone else's fully-formed vocabulary defeats the point.

The starter vocabulary in this repo is deliberately minimal and generic, intended as scaffolding rather than a finished toolkit.

### Session data

Mode A transcripts and Mode B exploration logs are personal — they record how a photographer talks about photos, what choices they make, how their taste develops over time.

**Chemigram never uploads session data anywhere automatically.** No telemetry. No phone-home. No cloud dependency. All session data lives in `~/Pictures/Chemigram/<image_id>/sessions/` on the user's machine.

If a user chooses to publish anonymized insights from their own session data, that's their decision. The project provides no infrastructure for publishing session data and no encouragement to do so by default.

## Contributions

Contributions to OSS components (engine, docs, starter vocabulary, community packs) are welcome under the same MIT terms. By submitting a pull request, you agree your contribution is licensed under MIT.

We don't require a CLA at this stage. If the project's needs evolve, this may change with notice.

See `CONTRIBUTING.md` for the contribution workflow, including the special review process for vocabulary contributions.

## Frequently asked

**"Can I use Chemigram in a commercial product?"** Yes, MIT allows this freely.

**"Can I keep my own vocabulary private?"** Yes — that's the expected pattern. Keep your vocabulary in a private repo and load it via `config.toml`.

**"Can I redistribute the starter vocabulary as part of my own product?"** Yes, MIT allows this. Preserve the copyright notice.

**"Will the project ever change to a non-permissive license?"** Not currently planned. If the project's structure evolves, any license change would apply to new versions only — code already released under MIT stays under MIT.

**"Do I have to credit Chemigram in my product?"** MIT requires preserving the copyright notice in distributed source. Visible in-product attribution is not required by the license but is welcome as a matter of culture.

**"Can other content authors choose different licenses for their vocabulary packs?"** Yes — content authors choose licenses for their content independently of the engine's license. The engine is MIT; specific packs may not be.
