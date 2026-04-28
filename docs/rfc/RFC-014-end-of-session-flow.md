# RFC-014 — End-of-session synthesis flow

> Status · Draft v0.1
> TA anchor ·/components/mcp-server
> Related · ADR-029, ADR-030, ADR-031
> Closes into · ADR (pending) — locks the end-of-session sequence
> Why this is an RFC · A session ends. What happens? Snapshot? Auto-tag final state? Propose taste updates? Write notes? The end-of-session flow is one of the highest-leverage moments for the project's compounding-context promise. Doing it well makes the next session feel like the agent has been there for months. Doing it poorly leaves valuable observations unrecorded.

## The question

When a session ends (the photographer signals "I'm done"), what's the orchestrated sequence of operations?

Naive answer: "the session just ends." Loses the chance to consolidate observations.

Better answer: "the agent reflects on the session and proposes updates to taste/notes/gaps; the photographer confirms; final state is snapshotted and tagged."

This RFC specifies the sequence and the agent's role.

## Use cases

- Photographer says "OK I'm done" → agent should consolidate the session into lasting context.
- Session ends abruptly (timeout, error) → minimal recovery (snapshot at last good state); no proposals lost in volatile memory.
- Session is long (30 turns) — many observations to consolidate. Agent's reflection should be bounded, not exhaustive.
- Session is short (5 turns) — sometimes nothing meaningful to consolidate. Don't waste the photographer's time with empty proposals.

## Goals

- Each session leaves taste, notes, gaps, and snapshot trail in good shape
- The agent's end-of-session reflection is structured and bounded
- The photographer can opt out (skip the consolidation when they don't want it)
- Crashes don't lose meaningful state (snapshots are written eagerly during the session)

## Constraints

- TA/components/mcp-server — flow happens through tool calls
- ADR-031 — propose-and-confirm for context updates
- ADR-029 — session transcripts as JSONL

## Proposed approach

**The end-of-session sequence (orchestrated by the agent, not the engine):**

1. **Photographer signals end** (natural language, "we're done," "let's wrap up").

2. **Agent enters reflection mode.** Reads the session transcript (or the agent's own conversation memory). Forms observations.

3. **Agent proposes consolidation:**
   - **Taste updates** — observations applicable across images. "I noticed you reach for `tone_lifted_shadows_subject` more than typical for this image type. Should that be in your taste?"
   - **Notes updates** — observations specific to this image. "The WB feels too cool here despite the brief saying neutral. Adding to notes?"
   - **Vocabulary gaps** — already logged during the session; agent recaps for confirmation.
   - **Tag suggestion** — final state tag. "Tag this state as v1_export?"

4. **Photographer confirms or declines** each proposal individually, or batch-confirms.

5. **Agent writes**:
   - Confirmed taste updates → `~/.chemigram/taste.md` (via `confirm_taste_update`)
   - Confirmed notes updates → `<image_id>/notes.md` (via `confirm_notes_update`)
   - Confirmed tag → `refs/tags/<n>` (via `tag`)
   - Declined proposals are recorded in the session transcript (audit trail) but not written to lasting context

6. **Final snapshot** (if state changed since last snapshot).

7. **Session transcript closure.** Engine writes `session_end` event to the JSONL with summary stats.

8. **Optional: brief summary message** to the photographer ("session done; tagged as v1_export; 2 taste updates accepted, 1 declined").

**Engine support:**

The engine doesn't orchestrate this; the agent does. But the engine provides:
- `read_session_transcript(image_id, session_id)` — for the agent to re-read events if needed
- `propose_taste_update`, `confirm_taste_update`
- `propose_notes_update`, `confirm_notes_update`
- `snapshot`, `tag` (already in v1 surface)
- `log_vocabulary_gap` (already)

The MCP server provides one **convenience tool** for end-of-session: `end_session(image_id, session_id, summary?)`. This finalizes the JSONL transcript and clears any pending proposals.

## Alternatives considered

- **Engine drives the flow (e.g., calls back to agent via callback):** rejected — MCP is request-response; the engine doesn't push to the agent. The flow is naturally agent-driven.
- **Auto-confirm everything (no propose-and-confirm at end):** rejected — violates ADR-031.
- **Force a structured end-of-session prompt (agent must use specific phrasing):** rejected — the agent's natural language proposal feels less robotic. Structure comes from the underlying tool calls (`propose_*`), not the conversation form.
- **Defer all consolidation to a separate "review" mode (not at session end):** considered. Loses the freshness of the session's observations. Better at session end.
- **Skip the end-of-session reflection if session was short:** proposed but optional. Heuristic: if fewer than 3 tool calls in the session, agent skips reflection unless something noteworthy happened.

## Trade-offs

- The flow asks the photographer for confirmation at session end — a small friction. Mitigated: it's natural conversation; the photographer is already reflecting on the session anyway.
- Long-running images accumulate increasingly long `notes.md` files. Mitigated: see RFC-011 (long-notes summarization).
- The agent's reflection quality varies. Mitigated: starts working with rough proposals; improves as photographer accepts/declines patterns.

## Open questions

- **What if the photographer's "I'm done" is ambiguous?** "OK that's enough for tonight" might mean "stop everything" or "wrap up properly." Agent should recognize ambiguity and ask. Proposed: agent's prompt template guides this.
- **How long after end-of-session can the photographer reopen the session?** Current model: not at all — sessions are events. A new session on the same image is a new session. Proposed: keep this; if the photographer wants to add more, that's a new session.
- **Cross-session reflection.** "Across the last 3 sessions on this image, you've consistently reached for X — should that be in taste?" Proposed: defer to a future tool. v1 reflects per-session.
- **Reflection on an empty session (photographer brief but agent didn't apply anything).** Probably nothing to consolidate; just close cleanly.

## How this closes

This RFC closes into:
- **An ADR locking the end-of-session sequence** (the steps the agent's prompt template should orchestrate).
- **An ADR for the `end_session` convenience tool.**
- **An update to 02/9** (agent prompt template) reflecting the end-of-session protocol.

## Links

- TA/components/mcp-server
- ADR-029 (session transcripts)
- ADR-030 (three-tier context)
- ADR-031 (propose-and-confirm)
- ADR-033 (MCP tools)
- 02/9 (agent prompt template)
