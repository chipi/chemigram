# Guides

Reference and methodology guides — companions to the design docs (RFCs/ADRs/concept package). Where the design docs argue *what* and *why*, guides explain *how* a topic is approached in practice.

## For users

Day-to-day usage:

- [**Tastes quickstart**](tastes-quickstart.md) — your first taste file in 5 minutes; what goes in `_default.md`, when to add genre files
- [**Vocabulary patterns**](vocabulary-patterns.md) — recipes for combining primitives ("for *X* intent, reach for *Y* composition")
- [**Visual proofs**](visual-proofs.md) — auto-generated before/after gallery for every vocabulary entry, rendered against the synthetic ColorChecker + grayscale chart in isolation. For human visual validation that each primitive does what its description claims.
- [**Mask-applicable controls**](mask-applicable-controls.md) — what every vocabulary primitive does through a drawn mask: the engine path, a per-module compatibility matrix, and how to mask an arbitrary primitive (CLI / authoring / Python).
- [**Recipes / common how-do-I**](recipes.md) — cross-cutting tasks: reset to baseline, find by tag, export multiple sizes, replay a session

CLI reference (the scripting / agent-loop surface):

- [**CLI reference**](cli-reference.md) — auto-generated; every verb, every flag, every exit code
- [**CLI output schema**](cli-output-schema.md) — NDJSON event format reference for callers that parse `--json` output
- [**CLI env vars**](cli-env-vars.md) — every `CHEMIGRAM_*` env var the CLI and engine respect
- [**`config.toml` reference**](config-toml.md) — `~/.chemigram/config.toml` schema (vocabulary sources, L1 bindings)

## For contributors

Authoring vocabulary:

- [**Authoring vocabulary entries**](authoring-vocabulary-entries.md) — daily-use Phase 2 flow: open darktable → capture move → drop into personal pack
- [**Expressive-baseline authoring methodology**](expressive-baseline-authoring.md) — companion to RFC-012 / ADR-073; the programmatic struct-RE approach used to ship the 35-entry pack

Testing:

- [**Standardized testing**](standardized-testing.md) — companion to RFC-019 / ADR-067. Industry methodology for reference-image validation, the Calibrite ColorChecker reference values, Delta E 2000 interpretation, and synthetic-fixture generation.

## Time-bound (delete when no longer applicable)

- [**Closing #62 + #63 (v1.6.0 carry)**](closing-62-and-63.md) — step-by-step for the v1.4.0 carry items: close #62 (resolved by retirement) + ship #63 (channelmixerrgb B&W trio). Delete after v1.6.0 ships.

## Adding a guide

A guide is appropriate when:

- A topic spans multiple design docs and a single landing reference helps readers connect them.
- An external standard, methodology, or tooling reference is cited often enough to deserve a curated summary.
- A how-to is non-trivial and benefits from being a stable, linkable artifact rather than scattered comments.

Conventions:

- One topic per file. Slug-cased filename.
- Lead with a one-line summary identifying the design doc this guide companions (if any).
- Cross-link from the originating RFC/ADR.
- Treat external references as canonical — link out, don't restate.
- Group in this index by audience (users vs. contributors), not by alphabetical order.
