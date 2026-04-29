# ADR-061 — End-of-session synthesis is agent-orchestrated

> Status · Accepted
> Date · 2026-04-29
> TA anchor · /components/context, /components/session
> Related RFC · RFC-014 (closes); ADR-029 (transcripts), ADR-031 (propose-and-confirm)

## Context

RFC-014 asked: when a Mode A session winds down, who orchestrates the
wrap-up? Two options were considered: an engine-side `end_session()`
convenience tool that triggers the agent's wrap-up sequence, or a
fully agent-orchestrated pattern where the agent uses existing tools
(`propose_*`, `log_vocabulary_gap`, `tag`, `snapshot`) without an
engine-side callback.

v0.5.0 ships the agent-orchestrated pattern; the engine has no
`end_session` tool. The Mode A v1 prompt's "End of session" section
documents the canonical wrap-up sequence; the transcript writer's
`close()` method is called by the MCP server when the stdio session
ends.

## Decision

**End-of-session is agent-orchestrated. No engine `end_session` tool.**

The canonical wrap-up sequence (per Mode A v1 prompt):

1. Suggest 0–2 taste-file additions noticed during the session — patterns
   across multiple moves, not single observations. Use
   `propose_taste_update` + `confirm_taste_update`.
2. Confirm any vocabulary gaps logged this session via
   `log_vocabulary_gap` (full RFC-013 shape; `satisfaction` honest).
3. Propose 1 `notes.md` update summarizing the session's decisions via
   `propose_notes_update` + `confirm_notes_update`.
4. Confirm pending exports if any (existing `export_final` tool).
5. Optionally `tag` the session's final snapshot for later reference.

Two propose-and-confirm cycles maximum. The agent doesn't drag out the
wrap-up; it orchestrates a small, predictable closing.

The transcript writer's `close()` is called by the MCP server (or by
test harnesses) when the session terminates — typically on stdio EOF.
The footer line records `entry_count` and `ended_at`.

## Rationale

- **Fits the agent-only-writer discipline (ADR-024).** The agent
  initiates every state change. An engine-side `end_session()` would
  either mutate state on its own (bad) or be a no-op wrapper (then
  why have it).
- **Same toolkit as the rest of the session.** Wrap-up uses the tools
  the agent already used during the session — propose, confirm, tag,
  snapshot, log_gap. Agents don't need a special end-of-session
  vocabulary; transcripts read uniformly throughout.
- **Prompt-driven, not engine-driven.** The Mode A prompt's wrap-up
  section is where the orchestration lives. New patterns (e.g., a
  cross-session summary tool in Phase 5) get added to the prompt;
  the engine tool surface stays narrow.
- **Test surface is unchanged.** No new tool means no new schema, no
  new error category, no new ADR-057-style contract to lock down.

## Alternatives considered

- **`end_session(image_id, session_id, summary?)` convenience tool.**
  Rejected: would either bundle a chain of confirmations (which
  violates propose-and-confirm) or be a thin wrapper over
  `transcript.close()` that doesn't earn its place.
- **Engine-side scheduler that fires "wrap up now" prompts.**
  Rejected: agent agency. The photographer signals the end; the agent
  responds via the prompt's instructions. No engine timer.
- **No documented wrap-up at all — let agents improvise.** Rejected:
  the prompt's "End of session" section earns its place by capping
  the cycles at two and naming the canonical sequence. Without it,
  agents drift toward over-orchestration ("would you like me to also
  re-tag, re-snapshot, summarize again?").

## Consequences

Positive:
- Session transcripts read uniformly: same `tool_call` /
  `tool_result` / `proposal` / `confirmation` entries throughout, no
  special markers for the wrap-up phase.
- The Mode A prompt is the single source of orchestration truth.
  Iterations (Mode A v2 in Slice 6) can refine the wrap-up without
  changing the engine.
- Implementing wrap-up logic against a different agent (Mode B in
  Phase 5) is just a new prompt; no engine work.

Negative:
- Photographers don't get a single tool button to "wrap this up." The
  agent has to know to do it. Mitigation: the Mode A v1 prompt's "End
  of session" section makes the sequence explicit.
- Cross-session reflection ("across the last 3 sessions you've reached
  for X") is harder to add later — it would either be a new tool or
  baked into `read_context`. Slice 6 evidence dictates which.

## Implementation notes

- No new tool in v0.5.0.
- The Mode A v1 prompt's "End of session" section (lines 121–134 of
  `src/chemigram/mcp/prompts/mode_a/system_v1.j2`) documents the
  canonical sequence. v2 in Slice 6 will refine based on real-session
  evidence.
- `chemigram.core.session.SessionTranscript.close()` writes the footer
  + closes the file handle. Idempotent.
- Test evidence: `tests/integration/mcp/test_full_session_with_context.py`
  exercises propose_taste + confirm_taste + log_gap + propose_notes +
  confirm_notes + transcript.close() in the wrap-up sequence; the
  transcript footer + entry counts are asserted.
