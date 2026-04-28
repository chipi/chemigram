# ADR-031 — Propose-and-confirm for context updates

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/mcp-server
> Related RFC · None (concept-package decision)

## Context

The agent forms observations during sessions: "you reach for `tone_lifted_shadows_subject` more often than typical for this kind of image — should that be in your taste?" or "this image's notes should record that the WB feels too cool despite the brief." For these to compound (the central promise — PA/promises/compounding-context), they must accumulate in the right files.

But the agent silently mutating `taste.md` would violate the agent-only-writer-but-photographer-controls principle: the photographer must always know what's accumulating in their lasting context, not discover later that the agent edited their craft summary.

## Decision

Updates to `taste.md` and per-image `notes.md` follow a propose-and-confirm pattern:

**Propose:** the agent calls `propose_taste_update(content, category)` or `propose_notes_update(image_id, content)`. The system creates a pending proposal with a `proposal_id` and surfaces it to the photographer (in the conversation or via a tool the photographer queries).

**Confirm:** the photographer confirms via `confirm_taste_update(proposal_id)` or `confirm_notes_update(proposal_id)`. The system writes the content to the file and clears the proposal.

Pending proposals live until confirmed, declined, or session ends. Declined or session-end proposals are discarded (logged in the session transcript for audit, but not written to lasting context).

## Rationale

- **Photographer agency.** The photographer always knows what's accumulating; nothing is silently added to their craft summary.
- **Audit trail.** The session transcript records every proposal (accepted or declined) — the research artifact captures the agent's observations even when not adopted.
- **Friction is intentional.** A small UX cost (one extra confirmation step) preserves trust; trust is what makes `taste.md` valuable. PA/principles/compounding-over-throughput.
- **Simple mental model.** Everywhere the agent might silently update, there's a propose call. No "sometimes silent, sometimes not."

## Alternatives considered

- **Silent agent updates with retroactive review:** rejected — introduces "did I just write that?" doubt about everything in `taste.md`. Trust collapses.
- **Photographer manually edits, agent never proposes:** rejected — loses the research thesis (agent observations contributing to articulated taste). The agent's observations are valuable; the propose step makes them actionable without making them silent.
- **Diff-based review (agent writes; photographer sees a diff before commit):** equivalent to propose-and-confirm with extra UI cost. The current design is the same idea, simpler.

## Consequences

Positive:
- Photographer always knows what's in `taste.md` and `notes.md`
- Trust in the artifacts is preserved
- Session transcripts capture both adopted and declined proposals (research-valuable)

Negative:
- One extra step in the flow (mitigated: it's a single confirmation, often combined with the photographer's natural session-end reflection)
- Pending proposals must be tracked (mitigated: in-memory or in a small JSON file in the session directory; cleaned up at session end)

## Implementation notes

`src/chemigram_core/context.py` implements the proposal lifecycle. Pending proposals live in-memory during a session, persisted only if the session is interrupted (so they can be resumed). On session end, all unconfirmed proposals are discarded with a log entry. The MCP server exposes the propose/confirm pair as tools.
