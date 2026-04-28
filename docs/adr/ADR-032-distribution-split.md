# ADR-032 — Distribution split (OSS engine, OSS starter, OSS packs, private personal)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/stack
> Related RFC · None (project-level distribution decision)

## Context

The project comprises multiple kinds of artifacts with different distribution and licensing needs:

- **The engine itself** (XMP synthesizer, render pipeline, versioning, MCP server, masking interfaces) — code, MIT-able, intended for community use.
- **The starter vocabulary** — pre-authored generic primitives that ship with v1 so users have something to start with. Should be MIT.
- **Community vocabulary packs** (e.g., a "Fuji film simulation pack" contributed by a Fuji shooter) — vocabulary collections others might want; need clear attribution and permissive licensing.
- **A specific photographer's personal vocabulary** — their accumulated `.dtstyle` files, calibrated to their gear, expressing their taste. May reference proprietary references (their personal photographs, their custom workflow assumptions). Should NOT be in the public repo by default.

Mixing all of these into one repo would either pollute the public artifact with personal content or contaminate the personal collection with public-coordination overhead.

## Decision

Four-way split:

1. **Public OSS monorepo** (`chemigram/` on GitHub, MIT license):
   - Engine source (`src/chemigram_core/`, `src/chemigram_mcp/`)
   - Starter vocabulary (`vocabulary/starter/`)
   - Community packs (`vocabulary/packs/<pack_name>/` with per-pack `ATTRIBUTION.md` and inherited license info)
   - Documentation, briefs, examples, contributing guide
   - Optional sibling project: `chemigram-masker-sam` (separate repo, separate release cadence) for production-quality subject masking

2. **Private personal repo** (per photographer): their personal vocabulary, their session transcripts, their per-image data. Not in the public repo. Photographer can choose to publish anonymized/curated subsets if they wish.

3. **Per-image data** (per photographer's filesystem): `~/Pictures/Chemigram/<image_id>/` directories containing snapshots, masks, notes, sessions. Local only (per ADR-027). Photographers can sync via standard tools but Chemigram doesn't build sync.

4. **The Phase 2 process guide and other private writer's tools**: not in the repo; methodology is private, the artifacts the methodology produces are public (per the guide/21).

## Rationale

- **Clean public artifact.** OSS users get a focused engine + starter + packs without personal noise.
- **Protect personal vocabularies.** Photographers shouldn't have to scrub their work to contribute to OSS; their personal repo is where they iterate freely.
- **Community pack onboarding.** Clear path for community contribution (ATTRIBUTION + license discipline) without forcing community packs to be MIT (some borrowed work has different upstream licenses).
- **BYOA fits naturally.** Sibling projects like `chemigram-masker-sam` are OSS-able but separate; users opt-in via configuration.

## Alternatives considered

- **One monorepo for everything (engine + all vocabularies + a curated personal pack):** rejected — pollution, license conflicts, contributor friction.
- **Engine in repo A, all vocabularies in repo B, personal stuff in repo C (per photographer):** considered. The engine + starter + packs in one repo is more discoverable for users; splitting engine and vocab adds onboarding friction.
- **Engine in repo, vocabulary as completely user-managed (no starter shipped):** rejected — first-time users would face an empty vocabulary; the starter is the ramp.

## Consequences

Positive:
- Public repo is focused and clean
- Personal vocabularies stay private without effort
- Community contribution path is well-defined
- Sibling projects (maskers, evaluators, future tooling) compose without coupling

Negative:
- Photographers who want to share their personal vocabulary need to extract and clean it (this is a feature; vocabularies that "just work" for everyone are different from one photographer's idiosyncratic collection)
- License management for community packs requires per-pack attention (mitigated: ATTRIBUTION.md template + CI check)

## Implementation notes

`docs/CONTRIBUTING.md` documents the contribution paths and what belongs in `vocabulary/starter/` vs `vocabulary/packs/`. `docs/LICENSING.md` describes the per-component licensing (MIT for engine, starter, MIT-by-default for community packs, per-pack overrides allowed with attribution). Personal vocabularies have no presence in the public repo by design.
