# RFC-008 — Vocabulary discovery at scale

> Status · Draft v0.1 (speculative)
> TA anchor ·/components/synthesizer ·/components/mcp-server
> Related · ADR-001, ADR-023, ADR-033
> Closes into · — (deferred until evidence accumulates)
> Why this is an RFC · The agent reads vocabulary listings via `list_vocabulary(layer?, tags?)`. At v1 scale (~30-100 entries), this works fine. At larger scale (a year of personal vocabulary growth + multiple community packs = potentially 500-1000 entries), the agent's context window becomes a bottleneck. The discovery problem becomes real. We don't yet have evidence of when this kicks in, what shape it takes, or what mitigation works best. This RFC captures the question and outlines plausible approaches.

## The question

When vocabulary grows to many hundreds of entries, the agent's `list_vocabulary` call returns a payload that strains context windows or buries useful entries in noise. How does discovery scale?

This is genuinely speculative — v1 doesn't have this problem. But the problem shape is foreseeable, and choosing implementation directions early (e.g., "tag entries with semantic categories from day one") affects what's possible later.

## Use cases

- Year-2 photographer with 800 entries asks "warm the highlights on the fish." The agent needs to find the 3-5 entries that are "warm-leaning highlight moves on the subject" without retrieving all 800.
- A photographer adopts a community pack with 200 new entries. They need to evaluate which ones are useful without listing all 200.
- The agent surfaces vocabulary gaps. With 800 entries, "we don't have anything for X" requires understanding the shape of what's already covered.

## Goals

- Discovery remains effective as vocabulary grows
- Implementation choices in v1 don't preclude later discovery improvements
- The agent's context window stays bounded as vocabulary scales

## Constraints

- TA/components/synthesizer — vocabulary lives in `.dtstyle` + manifest entries
- ADR-023 — manifest entries already have `tags`, `description`, `subtype`
- ADR-033 — `list_vocabulary` is the v1 tool

## Proposed approach (when needed)

**Multi-strategy discovery, layered:**

1. **Tag-and-category filtering** (v1; works now). `list_vocabulary(tags=["warm", "highlights", "subject"])` returns entries matching. Already in v1's tool surface.

2. **Semantic search over descriptions** (mid-scale, ~200+ entries). Index manifest descriptions; the agent's query (or a reduced query) is matched semantically (embeddings). Returns top-N relevant entries. Implementation: build embeddings at vocabulary-load time; cache them; semantic-similarity-search per query.

3. **Hierarchical browsing** (large-scale, ~500+ entries). Group entries by category (exposure, WB, color, structure, masks); the agent navigates structurally. Implementation: derive groups from `subtype` and operation classes.

4. **Recency / usage-weighting** (long-term). Entries the photographer used recently or frequently get surfaced first. Implementation: per-entry usage counter in `~/.chemigram/usage.json`.

For v1, only strategy 1 is implemented. Strategies 2-4 land if and when scale evidence makes them necessary.

## Alternatives considered

- **Implement semantic search now (v1):** rejected — adds an embeddings dependency (ML model or hosted service) and infrastructure for indexes. Premature for the actual scale of v1 vocabulary.

- **Force fixed-size manifests (cap at ~100 entries per pack):** rejected — artificial constraint that doesn't solve the discovery problem; just splits one pack into many.

- **Build categorization into the manifest schema (mandatory hierarchy):** considered. Requires upfront agreement on a hierarchy that's likely wrong; better to let `tags` carry the load and add hierarchy if needed.

- **Defer the question entirely (don't even RFC it):** considered. RFCing speculatively keeps the question visible; explicit "deferred" status communicates that we know it exists without committing time to it now.

## Trade-offs

- Speculative RFC is not full deliberation — when the problem becomes real, the proposed approach should be revisited with actual evidence.
- v1 chooses tags as the pragmatic discovery mechanism; tag quality becomes a vocabulary-contributor concern (sensible tags vs noisy ones).
- Strategies 2-4 each have implementation cost; deferring keeps the engine bounded.

## Open questions

- **What's the threshold scale where strategy 1 (tags) breaks down?** Likely 200-500 entries. Would benefit from real-world evidence from a long-running personal vocabulary.
- **Is semantic search worth the embeddings dependency?** If embeddings are computed by the photo agent (already configured), there's no new dependency. If we need a separate model, that's cost.
- **Could the agent self-learn discovery patterns?** "I notice you reach for `warm_*` entries 80% of the time when masking the subject." Long-term, vocabulary discovery and taste articulation converge. Defer.
- **Per-pack listing vs unified.** Should `list_vocabulary` be per-pack (less to scan) or unified (single namespace)? Proposed: unified by default, with an optional `pack` filter parameter.

## How this closes

This RFC stays open as a placeholder until either:
- v1 evidence shows discovery is genuinely a problem (then revisit, deliberate properly, close)
- v1 evidence shows it's not a problem (then close as "deferred indefinitely; tags suffice").

No closing ADR until then.

## Links

- TA/components/synthesizer
- TA/components/mcp-server
- ADR-001 (vocabulary approach)
- ADR-023 (vocabulary primitives)
- ADR-033 (MCP tool surface — `list_vocabulary`)
