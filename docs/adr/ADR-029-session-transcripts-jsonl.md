# ADR-029 — Session transcripts as JSONL with header metadata

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/contracts/per-image-repo
> Related RFC · None (concept-package decision)

## Context

A session is an editing conversation between the photographer and the agent — typically 10-30 turns over 5-20 minutes per image. Capturing these transcripts is core to the project's research thesis (taste transmission via accumulated context). The transcript needs to record: agent reasoning, tool calls, photographer responses, snapshots produced, masks generated, gaps surfaced.

The format must support: append-only writing during the session, robust recovery from crashes (truncated last line should be detectable), easy programmatic analysis afterward, and inspection by humans.

## Decision

Session transcripts are stored as JSONL files with a header object as the first line, followed by one event object per subsequent line.

Path: `<image_id>/sessions/YYYY-MM-DDTHH-MM-SS_session_NNN.jsonl`

Header (line 1):

```json
{
  "type": "session_start",
  "session_id": "uuid",
  "image_id": "...",
  "started_at": "2026-04-27T14:30:00Z",
  "agent_provider": "claude-sonnet-4-7",
  "agent_temperature": 1.0,
  "context_loaded": ["taste.md", "brief.md", "notes.md"],
  "starting_snapshot_hash": "..."
}
```

Subsequent lines: events in chronological order. Event types:
- `agent_thinking` — agent's reasoning (if exposed by provider)
- `agent_tool_call` — tool name + parameters
- `tool_result` — return value
- `photographer_message` — text from the photographer
- `snapshot_created` — hash + label
- `mask_generated` — name + provider + target
- `vocabulary_gap_logged` — description + workaround
- `taste_proposal` — pending update
- `taste_confirmation` — confirmed update
- `session_end` — final entry with summary stats

Each event has a `type` field, a `timestamp` field, and event-specific payload.

## Rationale

- **Append-only writing.** JSONL files are appended one line at a time; no need to rewrite the file. Robust against crashes — at worst, the last line is truncated and detectable.
- **Stream-processable.** Tools can read the file line-by-line without loading it all into memory.
- **Human-inspectable.** `cat session.jsonl | jq` works directly.
- **Header pattern.** Putting session metadata as the first line keeps the JSONL convention while still surfacing global session info.
- **Aligned with operation log.** `log.jsonl` follows the same pattern (ADR-018's per-image repo); consistency.

## Alternatives considered

- **Single JSON file (one object containing the whole session):** rejected — requires rewriting the file on every event, fragile during crashes.
- **YAML transcripts:** rejected — YAML's parsing complexity outweighs any readability advantage; JSONL with `jq` is just as readable in practice.
- **Plain-text logs (human-friendly format):** rejected — programmatic analysis (a key research use case) is much harder; we'd end up writing a parser. JSONL is both human-readable and program-readable.

## Consequences

Positive:
- Crash-safe writing (append-only)
- Easy programmatic analysis (line-stream-read)
- Easy human inspection (`jq`, `grep`)
- Consistent with `log.jsonl` and `vocabulary_gaps.jsonl`

Negative:
- Slightly verbose format (every event is a self-contained JSON object) — acceptable; transcripts are not a hot path
- The first-line-header pattern is a convention contributors must learn — documented in ADR-018 (the per-image repo description)

## Implementation notes

`src/chemigram_core/session.py` (or wherever session orchestration lives) writes the transcript via append. Header is written on session start; events are appended throughout; session_end is written on close. The MCP server is responsible for emitting events as it dispatches tool calls.
