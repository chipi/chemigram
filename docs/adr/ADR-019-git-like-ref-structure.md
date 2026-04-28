# ADR-019 — Git-like ref structure

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/versioning ·/contracts/per-image-repo
> Related RFC · None (follows from ADR-018)

## Context

ADR-018 commits to a content-addressed DAG of snapshots. Within that, we need a structure for refs (branches, tags) and HEAD. Several conventions are possible; consistency matters more than the choice.

## Decision

Refs follow git's filesystem layout:

```
<image_id>/
  refs/
    heads/<branch_name>     plain text file containing snapshot hash
    tags/<tag_name>         plain text file containing snapshot hash
  HEAD                      plain text file:
                              either "ref: refs/heads/main"
                              or a literal hash (detached state)
```

Branch and tag names follow the same rules as git: no spaces, no `..`, no leading dot, etc. Hash format is full SHA-256 (64 hex characters).

## Rationale

- **Familiar.** Anyone who's used git can read these files directly.
- **Inspectable.** `cat refs/heads/main` shows the hash; no parsing.
- **Atomic updates.** Updating a ref is a single file write; no transaction boundaries to manage.
- **Compatibility with future tooling.** If we ever want to expose a Chemigram repo through a git-like CLI, the structure is ready.

## Alternatives considered

- **JSON manifest with all refs:** rejected — atomic-update story is worse (need to read-modify-write a single file), and the inspection ergonomics are worse (`cat refs.json | jq '.heads.main'` instead of `cat refs/heads/main`).
- **Database (SQLite) for refs:** rejected — same reasons as ADR-018 rejected SQLite for snapshots.
- **Custom ref format:** considered, no benefit over copying git's conventions. Reinventing this wheel is pointless.

## Consequences

Positive:
- Inspection and debugging via standard Unix tools
- Atomic ref updates
- Familiar mental model
- Easy to back up (rsync the directory)

Negative:
- Subdirectories for `refs/heads` and `refs/tags` are slightly more setup than a single flat refs file (one-time cost; not a real problem)

## Implementation notes

Branch creation: write `refs/heads/<name>` with the hash; update HEAD if checking out. Tag creation: write `refs/tags/<name>`. HEAD detached state (e.g., after `checkout <hash>`) is stored as the literal hash string in HEAD.
