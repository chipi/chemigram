# Architecture diagrams

> Visual one-pagers of the chemigram stack, the mask architecture, the
> vocabulary layers, and the release timeline. All sources are
> Mermaid markdown; GitHub + MkDocs render them inline.

Closes [#118](https://github.com/chipi/chemigram/issues/118).

## The four diagrams

- **[Stack](stack.md)** — `chemigram-mcp` + CLI as adapters over `chemigram.core`; darktable as the external pixel-processing engine; filesystem as state.
- **[Mask trilogy](mask-trilogy.md)** — the four mask sources (drawn / parametric / LLM-vision / retouch) + named-mask references, all converging on one `mask_spec` wire that serializes to XMP `masks_history`.
- **[Vocabulary layers](vocabulary-layers.md)** — L1 / L2 / L3 + maskdefs; how the 123 catalog records (114 vocab primitives + 9 named maskdefs) compose.
- **[Phase 1 timeline](phase-1-timeline.md)** — release sequence from Phase 0 validation through v1.10.0 ship.

## When to update which

- **Stack** — when the subsystem set in `chemigram.core` changes, or when an adapter layer is added/retired (CLI v1.3.0; the v1.5.0 PNG-mask removal).
- **Mask trilogy** — when the mask sources change. RFC-030 (deployed sibling-provider precision tier) would add a fifth source if shipped.
- **Vocabulary layers** — when counts shift meaningfully, or when a new layer is introduced (don't — the 3-layer structure is settled per ADR-001).
- **Phase 1 timeline** — every release.

## Why Mermaid

Source format is plain text — diffs cleanly in git; renders natively on GitHub + MkDocs; doesn't require an authoring tool. Trade-off: precise layout control is limited; for fine-grained visual diagrams a vector tool (Figma / draw.io / Excalidraw) with SVG export would be better. The cost-benefit favors plain text here.

## Embedded references

Each diagram is referenced from the surrounding doc tree:

- README — [Stack](stack.md) embedded in "What this is"
- `docs/concept/04-architecture.md` — [Stack](stack.md) + [Vocabulary layers](vocabulary-layers.md)
- `docs/IMPLEMENTATION.md` — [Phase 1 timeline](phase-1-timeline.md)
- `docs/guides/mask-applicable-controls.md` — [Mask trilogy](mask-trilogy.md)
