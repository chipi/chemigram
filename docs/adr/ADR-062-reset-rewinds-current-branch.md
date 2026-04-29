# ADR-062 — Reset rewinds the current branch to baseline

> Status · Accepted
> Date · 2026-04-29
> TA anchor ·/components/versioning ·/contracts/mcp-tools
> Related RFC · None (clarifies ADR-015 + ADR-019 implementation)

## Context

ADR-015 specifies that `reset()` returns the workspace to `baseline_end` — discarding the agent's L3 work, leaving L1 + L2 intact, ready to continue applying primitives. The MCP `reset` tool currently implements this as `checkout(repo, "baseline")` where `baseline` is the tag created at ingest. Per ADR-019, checkout-to-tag detaches HEAD; per `versioning.ops.snapshot`, snapshot from a detached HEAD raises `VersioningError`. Result: any `apply_primitive` after `reset` fails with "cannot snapshot from a detached HEAD". The implementation contradicts the spec — reset was advertised as "ready to keep going" but actually leaves the workspace in a state where the next move blows up. Surfaced by the e2e MCP-level test that drives reset between two applies.

## Decision

`reset` rewinds the *current branch* to the baseline hash and ensures HEAD is symbolic on that branch. Concretely: resolve `workspace.baseline_ref` (the `baseline` tag) to a hash; if HEAD is symbolic, force-move that branch's ref to the hash; if HEAD is detached, attach it to the workspace's primary branch (`main` per `ImageRepo.init`, force-moving main to the hash). After reset, HEAD is always symbolic on a branch whose tip is the baseline hash. Subsequent `apply_primitive` works without further intervention. This matches `git reset --hard baseline` semantics.

A new engine-level op, `reset_to(repo, ref_or_hash) -> Xmp`, encapsulates the logic so the MCP tool stays a thin wrapper. The op appends a `reset` entry to `log.jsonl` recording the previous and new tip hashes — giving the agent (and humans inspecting later) an audit trail of what was discarded.

## Rationale

- **Matches the spec.** ADR-015 already named the target. This ADR fixes the implementation to honor it.
- **Git-shaped.** Photographers and agents already know "reset to a point" as a destructive rewind. The mental model carries over.
- **Cheap audit.** Force-moving a ref discards no objects (they live in `objects/`); only the branch pointer changes. The log entry preserves the prior tip hash, so anything reachable before reset can be located via `log` inspection.
- **Reset is already semantically destructive.** ADR-015 makes reset's purpose explicit: discard the agent's L3. The branch-move just makes the implementation honest about that.

## Alternatives considered

- **Auto-create a branch in `apply_primitive` when HEAD is detached.** Rejected — masks the problem; the failure mode silently mutates the ref topology in the apply path, making behavior depend on prior history. Reset is the right place to ensure HEAD is attached.
- **Create a fresh branch on every reset (e.g., `reset-N`).** Rejected — branch sprawl with no benefit; nobody asked to preserve the discarded line.
- **Refuse reset when not on the workspace's primary branch.** Rejected — blocks the obvious workflow ("explore on `experiment-1`, reset to baseline, keep exploring on `experiment-1`"). Resetting the current branch is the correct generalization.
- **Make `baseline` a branch instead of a tag.** Rejected — baseline is conceptually immutable (the state the photographer handed off); tags express that. Branches mutate. The fix lives in reset, not in the baseline ref's category.

## Consequences

Positive:
- The `reset → apply_primitive` workflow works as the spec promised.
- HEAD is never silently detached after a reset.
- Audit trail of what was reset away (log entry with prior tip).
- No new public concept introduced — just a semantic fix to an existing tool.

Negative:
- Reset is destructive on the current branch ref. A user who genuinely wanted to keep the prior tip must `tag` or `branch` *before* calling reset. Documented in the tool's MCP description.
- One additional engine op (`reset_to`) — small surface increase.

## Implementation notes

- `src/chemigram/core/versioning/ops.py`: add `reset_to(repo, ref_or_hash) -> Xmp`. Resolves the input to a hash (must reject "HEAD" as ambiguous in this context), reads/parses the object, force-writes the current branch's ref (or `refs/heads/main` if detached), writes HEAD symbolically, appends a `reset` log entry with `prior_hash` and `new_hash`. Raises `VersioningError` on unresolvable input.
- `src/chemigram/mcp/tools/vocab_edit.py`: `_reset` calls `reset_to(workspace.repo, workspace.baseline_ref)` instead of `checkout`. Tool description updated to note destructive-on-current-branch semantics.
- Unit tests cover detached → re-attached, on-branch → ref force-moved, log entry shape, unresolvable input.
- The detached-HEAD `VersioningError` from `snapshot` stays — it's the right error for callers other than reset that try to snapshot from a detached state.
