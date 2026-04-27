# Vocabulary

The agent's action space. Each `.dtstyle` file is a single-module darktable style — a named primitive the agent can apply. The vocabulary is structured by layer (L1/L2/L3) per `docs/layers.md`.

Two subdirectories:

- **`starter/`** — the OSS minimal demo vocabulary. Generic, broadly-applicable primitives. Ships with Chemigram. Conservative — its purpose is to demonstrate the system and bootstrap new users, not to encode any particular taste.
- **`packs/`** — borrowed and community-contributed vocabulary packs. Each pack is its own subdirectory with its own `manifest.json`, `.dtstyle` files, and `ATTRIBUTION.md`. Examples: Fuji film simulations, Nikon picture-control emulations.

Personal vocabularies (a photographer's own taste, encoded) belong in **separate private repositories**, loaded into Chemigram via `config.toml`. They are not part of this OSS distribution. See `docs/LICENSING.md` for the split.

## Authoring vocabulary

See `docs/CONTRIBUTING.md` for the contribution flow (different from code — manual review, before/after renders required, longer turnaround).

## Status

Empty for now. Phase 1 lands ~30 starter entries (exposure, white balance, basic tone). Phase 1.5 adds 8-12 pre-baked masked entries. Phase 2 adds 6-10 AI-mask-aware entries.
