# ADR-018 — Per-image content-addressed DAG

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/versioning ·/contracts/per-image-repo
> Related RFC · RFC-002

## Context

darktable's native edit history is linear with `<darktable:history_end>` as the pointer. No branches, no named states, no comparison across alternatives. For Mode A (collaborative), this is mildly limiting — you mostly want linear undo. For Mode B (autonomous fine-tuning, future), it's structurally inadequate — autonomous exploration produces a tree of variants, not a sequence.

Chemigram needs versioning that supports branching, tagging, comparison, and replay across sessions on the same image.

## Decision

Each image is its own repository — a content-addressed DAG of XMP snapshots, with refs (branches, tags) and a HEAD pointer. SHA-256 over the canonical XMP serialization is the snapshot identifier.

Repository structure (per image):

```
<image_id>/
  objects/
    NN/HHHHH...xmp        snapshot stored at sharded path
  refs/
    heads/<branch>        text file containing snapshot hash
    tags/<tag>            text file containing snapshot hash
  HEAD                    text file: "ref: refs/heads/main" or hash
  log.jsonl               append-only operation log
```

Mental model: small git, per image, locally only.

## Rationale

- **Branches make Mode B viable.** Mode B's exploration tree maps directly onto branches; no separate data structure needed.
- **Tags name keepable states.** "v1_export," "instagram_crop," "archive" — tags let the photographer mark final states without modifying history.
- **Content-addressing.** Identical snapshots have identical hashes; renames and moves are free; no per-snapshot metadata to maintain.
- **Inspectable.** `cat`, `grep`, and `ls` work directly. No proprietary database to query.
- **Familiar mental model.** Anyone who's used git understands the structure immediately.

## Alternatives considered

- **Linear undo stack (no branches):** rejected — Mode B becomes non-trivial; "I want to compare three variants" requires data-structure gymnastics.
- **SQLite database for snapshots:** rejected — opaque to inspection, requires schema migrations, conflicts with the filesystem-as-state principle (ADR-006).
- **Use real git internally:** considered — would inherit excellent tooling, but adds a hard dependency (git CLI) and forces snapshot operations through git's interface. The custom implementation is small enough (~300 lines) that the dependency cost outweighs the tooling benefit.
- **Three-way merge of snapshots:** rejected (see ADR-020) — photo edits don't merge in the source-code sense.

## Consequences

Positive:
- Branches and tags are first-class
- Snapshots are content-addressed; identical states share storage
- Filesystem inspection works; no database
- Mental model is familiar (git-shaped)

Negative:
- Custom implementation (~300 lines) rather than reusing git
- Identical-XMP detection requires canonical serialization (RFC-002) — this is a real open question about whitespace normalization, attribute ordering, etc.
- No remote/push/pull (intentional; local-only by ADR-027)

## Implementation notes

`src/chemigram_core/versioning.py` implements the operations: `snapshot`, `checkout`, `branch`, `log`, `diff`, `tag`. Storage uses the sharded path scheme (`objects/AB/CDEF...`) for filesystem performance with thousands of snapshots. RFC-002 deliberates the canonical XMP serialization for stable hashing. ADR-019 specifies the ref structure. ADR-020 lists what we explicitly don't build.
