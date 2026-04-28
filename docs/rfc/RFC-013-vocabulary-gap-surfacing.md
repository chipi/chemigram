# RFC-013 — Vocabulary gap surfacing format

> Status · Draft v0.1
> TA anchor ·/components/mcp-server ·/contracts/per-image-repo
> Related · ADR-033, RFC-008
> Closes into · ADR (pending) — locks the format and tool contract
> Why this is an RFC · Vocabulary gaps are central to the project's research thesis (vocabulary grows with use, photographer-articulated). The agent surfaces gaps mid-session ("we don't have a good word for X — here's what I improvised"). The format these gaps are recorded in shapes how they're later reviewed and how they feed back into vocabulary expansion. Wrong format → unusable artifacts.

## The question

When the agent improvises around a vocabulary gap (couldn't find an entry that fits the photographer's intent; used a workaround), how is the gap recorded for later review?

Specifically: format of the JSONL record, what fields it captures, how the photographer reviews accumulated gaps, how the gap pool informs vocabulary expansion.

## Use cases

- Mid-session: photographer says "I want to lift just the highlight zones in the water." Agent doesn't have a good entry; combines two existing entries. Logs gap: "needed 'highlight-only luminance lift'; used parametric mask + tone_lifted_shadows as workaround."
- End of session: photographer reviews accumulated gaps for this image and across recent sessions.
- Periodically: photographer (or a contributor) reviews gaps across all images, decides which ones to author.
- Mode B (future): an autonomous evaluator reads vocabulary gaps and proposes new vocabulary entries.

## Goals

- Gaps are richly described (what was missing, what was used as workaround, what context)
- Gaps are easily reviewable (filter by image, by date, by operation type)
- Gap accumulation across sessions informs which new vocabulary entries to author
- Format is JSONL (consistent with logs/transcripts per ADR-029)

## Constraints

- TA/contracts/per-image-repo — `<image_id>/vocabulary_gaps.jsonl` exists
- ADR-029 — JSONL is the chosen log format
- ADR-033 — `log_vocabulary_gap` is the v1 tool

## Proposed approach

**Per-image gap log:** `<image_id>/vocabulary_gaps.jsonl` — append-only, one gap per line.

**Gap record shape:**

```json
{
  "timestamp": "2026-04-27T15:30:00Z",
  "session_id": "uuid",
  "snapshot_hash": "a3f2...",
  "intent": "lift just the highlight zones in the water",
  "intent_category": "tonal",
  "missing_capability": "highlight-only luminance lift",
  "operations_involved": ["toneequalizer", "highlights"],
  "workaround": "parametric mask + tone_lifted_shadows",
  "vocabulary_used": ["tone_lifted_shadows"],
  "satisfaction": "mediocre",
  "notes": "the parametric mask isolated the right zones but feathering felt off; needed something more precise"
}
```

Field rationale:
- `intent` — natural language; the photographer's actual phrasing or the agent's reframing
- `intent_category` — coarse classification (`tonal`, `color`, `structure`, `mask`, `composite`); helps filter
- `missing_capability` — what the agent thinks would have been the right primitive
- `operations_involved` — darktable modules the workaround touched
- `workaround` — what was actually done
- `vocabulary_used` — which existing primitives were involved
- `satisfaction` — `mediocre`, `acceptable`, `bad` — subjective; informs prioritization
- `notes` — free text; observations that don't fit elsewhere

**Cross-image aggregation:**

A `chemigram report-gaps` CLI command (or MCP tool) aggregates across all images:
- Counts by `intent_category`
- Counts by `missing_capability` (clusters similar missing capabilities)
- Surfaces the top 10 most-frequently-mentioned missing capabilities

This is the gap-prioritization mechanism: when the photographer (or a vocabulary contributor) wants to author new vocabulary, they look at this report.

**Tool contract for `log_vocabulary_gap`:**

```python
log_vocabulary_gap(
    image_id: str,
    intent: str,
    missing_capability: str,
    workaround: str,
    operations_involved: list[str],
    vocabulary_used: list[str] | None = None,
    intent_category: str | None = None,   # auto-classified if None
    satisfaction: str | None = None,
    notes: str | None = None,
) -> {"success": True, "gap_id": "..."}
```

The agent calls this when it improvises around a gap. Auto-classification of `intent_category` from `missing_capability` is best-effort (LLM-aware engine logic; can fall back to "uncategorized").

## Alternatives considered

- **Free-text gap entries:** rejected — review at scale becomes "read 200 free-text entries"; structured fields enable filtering and aggregation.
- **Schema-strict (no free-text fields):** rejected — `notes` is valuable; the agent's free-form observations sometimes capture what structured fields can't.
- **Global gap log (one file across all images):** considered. Per-image is more aligned with the per-image-repo principle (ADR-018) and supports image-specific gap analysis. Cross-image aggregation is done at report time.
- **Gap entries inside snapshot metadata:** rejected — couples gap tracking to snapshot lifecycle. Gaps are independent of snapshots (one session might surface 3 gaps but only 1 snapshot).

## Trade-offs

- Field-rich format requires the agent to populate them. The agent has good context (session conversation), so this is reasonable.
- Auto-classification of `intent_category` is best-effort; some entries may be "uncategorized." Acceptable: the report tool can re-classify on demand.
- Per-image gap logs mean cross-image analysis requires walking many files. Acceptable: this is offline work, not session-time.

## Open questions

- **Should `intent_category` be a fixed enum or open-ended?** Fixed enum makes filtering reliable; open-ended captures unforeseen categories. Proposed: a fixed-but-extendable enum (additions become new categories via a vocabulary-system update).
- **How does Mode B consume gap reports?** Future concern. The structured format makes machine consumption feasible.
- **Gap deduplication across sessions.** If the same gap is surfaced 5 times across 5 sessions, should the report cluster them? Proposed: yes — clustering by `missing_capability` (string-similarity-based) at report time.
- **Privacy of gaps.** Gap records contain photographer's intent ("lift the shadows on the iguana"). Are these shared in any way? No — same as all session data, local only (ADR-027).

## How this closes

This RFC closes into:
- **An ADR locking the gap record schema** as proposed.
- **An ADR or implementation note** for the cross-image aggregation tool.

## Links

- TA/components/mcp-server
- TA/contracts/per-image-repo
- ADR-029 (JSONL convention)
- ADR-033 (`log_vocabulary_gap` tool)
- RFC-008 (vocabulary discovery; gap reports are upstream of "what to author next")
