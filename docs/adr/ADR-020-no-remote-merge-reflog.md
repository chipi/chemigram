# ADR-020 — No remote, no three-way merge, no reflog

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/versioning
> Related RFC · None (scope discipline)

## Context

ADR-018 commits to a per-image DAG with branches and tags. Git supports more: remotes (push/pull), three-way merge, reflog, partial staging, hooks, signed commits. Each adds complexity. For Chemigram's actual use case (single photographer, local research, no collaboration on per-image state), most of these are not needed.

## Decision

Chemigram's versioning explicitly does **not** implement:

- **No remote / push / pull / fetch.** Per-image repos are local only.
- **No three-way merge.** Photo edits don't compose like source code; "merge these two branches" is not a meaningful operation on XMP histories.
- **No reflog.** If the user runs `gc` and a branch they didn't keep is gone, it's gone.
- **No partial XMP staging.** A snapshot captures the entire XMP, not selective parts.
- **No hooks, no signing, no submodules.**

What we *do* implement: snapshot, checkout, branch, log, diff, tag, and a `merge_pick` operation that's actually a cherry-pick (apply selected primitives from another snapshot to the current one).

## Rationale

- **Scope discipline.** Each excluded feature is engineering work that v1 doesn't need.
- **Per-image scope is naturally bounded.** No collaboration story to support.
- **Photo edits don't three-way merge sensibly.** The conceptual model breaks: how do you "merge" a warmer-WB branch with a stronger-clarity branch? Not by superimposing the diffs. The right operation is "pick this primitive from there, apply it here," which is `merge_pick` and is fundamentally cherry-picking.
- **Reflog adds storage and complexity for an undo case that's already covered by snapshots.** Every meaningful state is already snapshotted (per the agent's discipline); recovery is finding the right snapshot, not reflog-walking.

## Alternatives considered

- **Implement remote support for cross-machine sync:** rejected for v1 — no clear use case, adds significant complexity. Could be revisited if/when photographers want to work on the same image across machines.
- **Implement three-way merge for cherry-picking semantics:** unnecessary — `merge_pick` does the actual operation people want without claiming "merge."
- **Implement reflog as a safety net:** rejected — operating cost (storage, traversal) outweighs the rare recovery benefit; snapshot discipline (ADR-029, agent disciplines in the project concept doc, section 6.4) already covers the common case.

## Consequences

Positive:
- Versioning implementation stays bounded (~300-400 lines)
- No collaboration concerns to design for
- `merge_pick` is the right primitive for photo workflows (not "merge")

Negative:
- Photographers who want cross-machine sync must use external tooling (rsync, git-of-the-image-repo, cloud filesystem) — not impossible, but not first-class
- Recovery from accidental `gc` of an unreferenced branch is impossible (mitigation: don't `gc` unless you mean it)
- If three-way merge ever became valuable (e.g., for collaborative vocabulary work, which lives in a separate repo anyway), it would require a future ADR

## Implementation notes

`gc` removes objects unreachable from any ref. The implementation is a straight reachability sweep — no reflog to consider. `merge_pick` is implemented in versioning.py as cherry-picking primitives, not as merge.
