# Vocabulary

The agent's action space. Each `.dtstyle` file is a single-module darktable style — a named primitive the agent can apply. The vocabulary is structured by layer (L1/L2/L3) per `docs/concept/04-architecture.md` § 5 (the three-layer model) and ADR-015.

Two subdirectories ship in this repo:

- **`starter/`** — the OSS minimal demo vocabulary (4 entries). Generic, broadly-applicable primitives. Ships with `pip install chemigram`. Conservative on purpose — its job is to demonstrate the system and bootstrap new users, not encode any particular taste. See [`starter/README.md`](starter/README.md).
- **`packs/`** — comprehensive and community-contributed vocabulary packs. Currently ships [`packs/expressive-baseline/`](packs/expressive-baseline/README.md) (35 entries: 31 programmatic via Path C reverse-engineering + 4 drawn-mask-bound entries via path 4a per ADR-076). See [`packs/README.md`](packs/README.md) for the packs framework and roadmap.

Personal vocabularies (a photographer's own taste, encoded) belong in **separate private repositories**, loaded into Chemigram via `config.toml`. They are not part of this OSS distribution. See `docs/LICENSING.md` for the split.

## Discovering what's available

- Static catalog: each pack's `README.md` lists its entries with descriptions, tags, and intensity ladders.
- Runtime listing: `chemigram vocab list --pack <pack-name>` (CLI) or `list_vocabulary` (MCP tool).
- Patterns and recipes: see [`docs/guides/vocabulary-patterns.md`](../docs/guides/vocabulary-patterns.md) for "for X intent, reach for Y composition" examples.

## Authoring vocabulary

For the daily-use Phase 2 path (open darktable → capture move → drop in personal pack), see [`docs/guides/authoring-vocabulary-entries.md`](../docs/guides/authoring-vocabulary-entries.md). For the programmatic struct-RE path used to ship the expressive-baseline pack, see [`docs/guides/expressive-baseline-authoring.md`](../docs/guides/expressive-baseline-authoring.md). For the contribution flow (manual review, before/after renders required), see `docs/CONTRIBUTING.md` § Vocabulary contributions.

## Status

Phase 1 closed at v1.0.0 with the 4-entry starter pack as a teaching artifact. v1.4.0 added the 35-entry `expressive-baseline` pack including 4 drawn-mask-bound entries. v1.5.0 retired the PNG-mask architecture (ADR-076 supersedes ADR-021/022/055/057/058/074); mask-bound entries now declare `mask_spec` for drawn-form geometry (gradient / ellipse / rectangle). Phase 2 grows personal vocabulary use-driven; see `docs/IMPLEMENTATION.md`.
