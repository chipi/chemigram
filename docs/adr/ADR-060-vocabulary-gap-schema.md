# ADR-060 — Vocabulary gap JSONL schema

> Status · Accepted
> Date · 2026-04-29
> TA anchor · /contracts/vocabulary-gaps
> Related RFC · RFC-013 (closes)

## Context

RFC-013 specified the per-image `vocabulary_gaps.jsonl` format: when an
agent reaches for a primitive that doesn't exist, it logs the gap so
the vocabulary can grow from real evidence. v0.3.0 shipped a minimal
4-field placeholder (`timestamp`, `image_id`, `description`,
`workaround`). v0.5.0 (Slice 5) extends to the full RFC-013 shape.

This ADR closes RFC-013 with the schema as implemented and exercised
by `tests/integration/mcp/test_full_session_with_context.py`.

## Decision

### Record schema (RFC-013)

```json
{
  "timestamp": "<ISO-8601>",
  "image_id": "<string>",
  "session_id": "<string|null>",
  "snapshot_hash": "<sha256-hex|null>",
  "description": "<required, non-empty string>",
  "workaround": "<string>",
  "intent": "<string|null>",
  "intent_category": "<string; default 'uncategorized'>",
  "missing_capability": "<string|null>",
  "operations_involved": ["<darktable_module>", ...],
  "vocabulary_used": ["<vocab_entry_name>", ...],
  "satisfaction": -1 | 0 | 1 | null,
  "notes": "<string>"
}
```

`description` is required at the tool boundary; everything else is
optional with the defaults shown.

### Auto-population

- `session_id` is read from `ctx.transcript.session_id` when a session
  transcript is configured on the MCP server; otherwise `null`.
- `snapshot_hash` is read from `workspace.repo.resolve_ref("HEAD")`
  when a snapshot exists; otherwise `null`.

### `satisfaction` semantics

- `-1` — workaround was unsatisfactory; the photographer wanted what
  the missing capability would have produced.
- `0` — neutral; the workaround was acceptable.
- `1` — workaround was satisfying despite being a workaround.
- `null` — agent didn't capture a rating.

### `intent_category` values

The agent fills this in best-effort. Default: `"uncategorized"`. The
canonical set is informally `{"tone", "wb", "color", "detail", "local",
"composition", "uncategorized"}` — tests don't enforce this enum;
a future ADR may. LLM-aware auto-classification is Phase 2.

### Append semantics

JSONL append-only: the writer opens with `mode="a"` and writes one
JSON-encoded line per record. Records do not get rewritten; corrections
are new records that reference the prior `snapshot_hash` via `notes`.

### Backwards compatibility

`chemigram.core.context.RecentGaps.load` reads both v0.3.0 minimal
records (4 fields) and full RFC-013 records — missing fields take the
dataclass defaults. Pre-release; no migration path needed for shipped
data.

## Rationale

- **JSONL over a structured DB:** filesystem-as-state matches the rest
  of the project (per-image-repo, snapshots, masks). One record per
  line, append-only, no schema migrations.
- **`snapshot_hash` + `session_id` for reproducibility:** future
  cross-image aggregation tooling (`chemigram report-gaps`) clusters by
  `missing_capability` and references back to the exact state where the
  gap was hit.
- **`satisfaction` as a tri-state:** binary "good/bad" misses the
  middle case where the workaround was *acceptable* but not satisfying.
  Three levels gives the agent room to be honest.
- **`intent_category` open-vocabulary by default:** locking categories
  too early would force the agent to mis-bucket; the future ADR can
  formalize once we have enough records to see what naturally clusters.

## Alternatives considered

- **JSON file with one big array.** Rejected: rewriting the whole file
  on each append doesn't scale and risks data loss on crash.
- **SQLite database for gaps.** Rejected: adds a binary dep and a
  schema migration story for what's fundamentally append-only data.
- **No backwards-compat — require migration of v0.3.0 records.**
  Rejected: pre-release means there are no "real" records to migrate,
  but the cheap dual-shape reader keeps the option open if any
  development workspaces accumulated records.
- **Closed `intent_category` enum.** Rejected for v1: we don't have
  enough cross-image data to know what categories will surface.
  Defaulting to `"uncategorized"` lets the agent be honest about
  uncertainty.

## Consequences

Positive:
- Schema rich enough to support cross-image aggregation when that
  tooling lands (Phase 2+).
- Records carry their session + snapshot context, so `chemigram
  report-gaps --since 2026-01-01` can cluster gaps that hit the same
  combination of operations.
- Backwards compat preserved: v0.3.0 fixture records still parse.

Negative:
- 13 fields is a lot for the agent to fill. Most are optional; the
  required two (`image_id`, `description`) match v0.3.0. Agents that
  fill the optional fields get richer aggregation; agents that don't
  still produce valid records.
- `intent_category` is unconstrained, so the cluster-by-category
  tooling will need normalization once it ships.

## Implementation notes

- `chemigram.mcp.tools.ingest._log_vocabulary_gap` — writer.
- `chemigram.core.context.GapEntry` + `RecentGaps.load` — reader.
- `chemigram.core.context._gap_from_dict` — backwards-compat shim that
  reads both v0.3.0 minimal and full RFC-013 records.
- `chemigram.mcp.tools.ingest._read_head_hash` — auto-populates
  `snapshot_hash` from HEAD when resolvable.
- Test evidence: `tests/unit/mcp/tools/test_ingest.py` (writer +
  auto-populate + validation), `tests/unit/core/context/test_context.py`
  (reader handles both shapes), `tests/integration/mcp/tools/test_ingest_via_mcp.py`
  + `test_full_session_with_context.py` (end-to-end through MCP).
