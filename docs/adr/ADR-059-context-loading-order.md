# ADR-059 — Agent context loading order and format

> Status · Accepted
> Date · 2026-04-29
> TA anchor · /components/context, /contracts/context-loading
> Related RFC · RFC-011 (closes); ADR-031 (propose-and-confirm); ADR-048 (multi-scope tastes)

## Context

RFC-011 left open: when the agent's first turn calls `read_context(image_id)`,
what does it get back, and in what order? v0.5.0 (Slice 5) ships
`chemigram.core.context` (loaders) plus the real `read_context` MCP tool,
exercised end-to-end by `tests/integration/mcp/test_full_session_with_context.py`.

This ADR closes RFC-011 with the concrete shape.

## Decision

### Loading order

The agent's first turn always reads in this order — each piece informs
the next:

1. **Tastes** — multi-scope per ADR-048. `_default.md` always loads;
   genre files declared in `brief.md`'s `Tastes:` line layer on top.
   Conflicts (same line in two genre files) are surfaced in
   `tastes.conflicts` for the agent to mediate; the engine doesn't
   auto-resolve.
2. **Brief** — per-image `<workspace>/brief.md`. Parsed for `Tastes:`
   declarations + `intent` (everything else).
3. **Notes** — per-image `<workspace>/notes.md`. Long files truncated
   to first 10 lines + last 30 lines + ellision marker (see
   "summarization" below). `truncated: bool` flag tells the agent
   whether to call `read_full_notes` (deferred to Slice 6+).
4. **Recent log** — last 10 entries from `<workspace>/log.jsonl`,
   newest first.
5. **Recent gaps** — last 10 vocabulary-gap records from
   `<workspace>/vocabulary_gaps.jsonl`, newest first.

### Response shape

`read_context(image_id)` returns:

```json
{
  "tastes": {
    "default": "<text>",
    "genres": {"underwater": "<text>", ...},
    "conflicts": [{"point": "<line>", "files": ["a", "b"]}, ...]
  },
  "brief": {
    "raw": "<full markdown>",
    "intent": "<everything except Tastes: line>",
    "tastes": ["underwater", ...]
  },
  "notes": {
    "summary": "<first10 + ellision + last30 OR raw if short>",
    "truncated": false
  },
  "recent_log": [{"timestamp": "...", "op": "...", "details": {}}, ...],
  "recent_gaps": [
    {
      "timestamp": "...", "image_id": "...", "description": "...",
      "session_id": null, "snapshot_hash": null, "intent": null,
      "intent_category": "uncategorized", "missing_capability": null,
      "operations_involved": [], "vocabulary_used": [],
      "satisfaction": null, "notes": ""
    },
    ...
  ]
}
```

Structured top, prose body. Agent reads tastes/brief/notes as markdown;
recent_log and recent_gaps are structured for branching.

### Long-notes summarization

Threshold: `NOTES_HEAD_LINES + NOTES_TAIL_LINES = 40` lines. Files at or
below the threshold return raw, `truncated: false`. Files above:
first 10 lines, then `\n\n... [N lines elided] ...\n\n`, then last 30
lines. `truncated: true`.

Rationale: line-count is a coarse proxy for "context-window cost"; LLM-
aware summarization is deferred to Phase 2 (RFC-011 Open Question #5).

### Tolerance for missing files

Every loader returns an empty struct on missing/unreadable files. The
agent's first turn must work on a fresh workspace with no prior context.

### Conflict surfacing convention

When a non-comment, non-empty line appears in ≥2 genre files,
`tastes.conflicts` gets a `{point, files}` entry. The engine doesn't
suggest a resolution — the agent talks to the photographer per the
"Bearings/opinions/limits" frame in the Mode A prompt.

## Rationale

- **Structured top + prose body:** keeps the agent fluent in the
  markdown of taste/brief/notes (which a human reads/writes) while
  giving structured fields the agent can branch on (`brief.tastes`,
  `recent_log[i].op`).
- **Loading order matches importance:** tastes first because they're
  cross-image; brief next because it picks the genre subset; notes
  third because they're per-image session memory; log + gaps last
  because they're meta-evidence.
- **Line-truncation summarization, not LLM-based:** deterministic, fast,
  tested, doesn't add a model dep. Fine for v1 — Phase 2 evidence will
  show whether we need smarter.
- **Tolerance for missing files:** the v1 use case includes brand-new
  workspaces. Hard-failing on any missing file would prevent the
  "first turn ever" experience from working.

## Alternatives considered

- **JSON-only response (no prose markdown).** Rejected: tastes/brief/
  notes are author-edited markdown by humans; round-tripping to JSON
  would either lose formatting or require a markdown→JSON layer the
  agent doesn't need.
- **Single big text blob.** Rejected: agents can't branch on `op`,
  `intent_category`, etc. Loses the value of the structured `recent_log`
  and `recent_gaps`.
- **Reverse loading order (gaps first).** Rejected: the agent should
  see foundational context before meta-evidence. Gaps last because
  they're "things to consider while doing the work," not "what to do."
- **Eager full notes (no truncation).** Rejected: long notes consume
  the context window without proportional value. Truncation makes the
  short-context path the default with an explicit `read_full_notes`
  follow-up tool (Slice 6+) for the long-context path.
- **LLM-aware summarization for notes.** Rejected for v1: adds a model
  dep, non-deterministic, harder to test. Phase 2 if line truncation
  proves inadequate.

## Consequences

Positive:
- Agent's first turn is one tool call.
- Test coverage is straightforward (every shape has a fixed schema).
- Photographers' markdown stays human-edited; no engine layer to
  marshal taste files into another format.

Negative:
- `read_context` size is bounded by notes-truncation + gap/log limit.
  An agent that wants more depth needs follow-up tools (read_full_notes
  in Slice 6+).
- Conflict surfacing is line-equality based; doesn't catch semantic
  conflicts ("warm tones" vs "cool palette"). Phase 2.

## Implementation notes

- `chemigram.core.context.{Tastes, Brief, Notes, RecentLog, RecentGaps}` —
  loaders.
- `chemigram.core.context.NOTES_HEAD_LINES = 10`, `NOTES_TAIL_LINES = 30`,
  `NOTES_TRUNCATION_THRESHOLD = 40`.
- `chemigram.core.workspace.tastes_dir()` — global tastes resolver,
  honors `CHEMIGRAM_TASTES_DIR` env var for tests.
- `chemigram.mcp.tools.context._read_context` — wires the loaders into
  the MCP tool.
- Test evidence: `tests/integration/mcp/test_full_session_with_context.py`
  exercises the full read_context shape on a fresh + populated
  workspace.
