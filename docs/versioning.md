# Chemigram — Versioning

*Content-addressed DAG of edit snapshots. "Mini git for photos", baked into the engine.*

## Why this exists

darktable has a linear edit history with a single pointer (`<darktable:history_end>`). You can roll back the pointer to truncate-and-resume. That's it: no branches, no named states, no comparison across alternatives.

For the **collaborative journey** mode (Mode A, photographer + agent), this is mildly limiting — you mostly want linear undo and "go back to where I liked it." For the **autonomous mode** (Mode B, agent self-evaluating against criteria), it's structurally inadequate. Autonomous exploration is inherently branching: the agent tries variant A, variant B, variant C from the same starting point, picks the winner, discards the rest. Without versioning, that exploration is invisible — no record of what was tried, no way to revisit, no inspectability.

So we add a layer darktable doesn't have: **a content-addressed DAG of XMP snapshots**, with refs (branches, tags) and a HEAD pointer. Conceptually a stripped-down git, optimized for one-image-many-variants rather than one-repo-many-files.

This is core engine, not optional. It lands in v1.

## The repo: where data lives

User's photos live where the user wants them — Chemigram never assumes. Default location is `~/Pictures/Chemigram/` to match how darktable and LR think about photo libraries (content lives near other content; software state lives in `~/.chemigram/`). User configurable in `config.toml`:

```toml
[storage]
repos_root = "~/Pictures/Chemigram"      # default, override as needed
```

Each image is its own repo. Layout:

```
~/Pictures/Chemigram/
  <image_id>/                              # one image, one repo
    raw/
      DSCF1234.RAF                         # symlink to original raw, never modified
    objects/                               # content-addressed snapshot store
      a3/f291d2e8b....xmp                  # SHA-256 keyed, two-char prefix subdirs
      b7/1204a99c1....xmp
      c0/8815f3b22....xmp
    refs/
      heads/
        main                               # text file: c08815f3b22...
        explore_warm                       # text file: b71204a99c1...
      tags/
        v1_export                          # text file: a3f291d2e8b...
        instagram_crop                     # text file: c08815f3b22...
      HEAD                                 # text file: ref: refs/heads/main
    log.jsonl                              # append-only operation log
    previews/                              # ephemeral, regenerable
      a3f291.jpg                           # JPEG previews keyed by hash prefix
      b71204.jpg
    sessions/                              # session transcripts (Mode A and B)
      2026-04-27-mobula.jsonl
    metadata.json                          # EXIF cache, layer bindings, image-level state
```

Symlinks are deliberate: the original raw stays in the user's primary photo library. Chemigram references it without copying. If the original moves, we surface a clear error rather than silently breaking.

`objects/` mirrors git's loose-object store. Two-character prefix subdirs prevent flat-directory pathology when an image accumulates hundreds of snapshots (real possibility in Mode B). Identical edits produce identical SHA-256 hashes — free deduplication.

`previews/` is cache. Deletable at any time. Reconstructable by re-rendering from the corresponding object.

`sessions/` is orthogonal to versioning. A single Mode A session can produce many snapshots; a single snapshot can be referenced from many sessions. Sessions live alongside but don't entangle with the version history.

## Refs: branches, tags, HEAD

Cloned from git's design because the model is well-understood and the semantics map cleanly:

- **Branches** (`refs/heads/<name>`) are mutable refs. New snapshots committed while on a branch advance that branch.
- **Tags** (`refs/tags/<name>`) are immutable refs. They mark specific snapshots and don't move.
- **HEAD** points at either a branch (`ref: refs/heads/main`) or directly at a hash (detached HEAD, used when checked out to a specific historical snapshot for reference).

A ref file is a single line of text, exactly like git. Any tool — `cat`, `grep`, your editor — can inspect or repair the repo state. No binary metadata.

## Operations

Two layers: engine API (Python, called by Chemigram internals) and MCP surface (the agent's view).

### Engine API

```
snapshot(image, label?, parent=HEAD) → hash
  Hash the current XMP, store at objects/<prefix>/<rest>.xmp,
  advance HEAD if on a branch, optionally tag.

checkout(image, ref_or_hash) → state
  Move HEAD to a ref or hash. Update current.xmp on disk so
  darktable-cli sees the right state on next render.

branch(image, name, from=HEAD) → ref
  Create refs/heads/<name>. Doesn't switch.

switch(image, ref) → state
  checkout + update HEAD to follow the ref (vs. detached).

log(image, ref=HEAD, limit=20) → list of {hash, label, parent, ops_summary, timestamp}
  Walk parent chain backward, return commit-log-style summary.
  ops_summary is a human-readable list of vocabulary primitives applied
  since parent.

diff(image, hash_a, hash_b) → list of {primitive, change}
  Higher-level than XML diff: "expo_+0.5 replaced with expo_+0.7;
  warm_highlights added; tone_lifted_shadows removed."
  Operates on the vocabulary-primitive level, not the raw XMP.

merge_pick(image, source_hash, primitives) → new hash on current branch
  Cherry-pick: take specific primitives from source_hash, apply to
  current HEAD, snapshot. No three-way merge — doesn't make sense
  for photo edits.

tag(image, hash, name) → ref
  Static reference at a specific hash.

gc(image) → freed_bytes
  Garbage-collect snapshots not reachable from any ref or HEAD.
  Useful after Mode B leaves orphan branches.
```

### MCP surface (agent-visible subset)

```
snapshot(image, label?)
checkout(image, ref_or_hash)
branch(image, name)
log(image)                       # returns DAG with refs
diff(image, hash_a, hash_b)
tag(image, name)                 # for marking final / export-ready states
```

`gc` and `merge_pick` stay engine-internal in v1. Don't expose to the agent without a reason. Keeping the agent's surface narrow is a feature.

## How this integrates with the agent flow

### Mode A — collaborative journey

```
User: "Let's start"
  Agent: snapshot(label="baseline")           # initial state from L1+L2

User: "Punch the mobula"
  Agent: apply_primitive(subject_lift_midtones)
  Agent: render_preview()
  Agent: snapshot(label="lift_midtones")      # commit the move

User: "Too far"
  Agent: checkout(HEAD~1)                      # back one snapshot
  Agent: apply_primitive(subject_lift_midtones_subtle)
  Agent: render_preview()
  Agent: snapshot(label="lift_midtones_subtle")

User: "Yes — let's explore from here"
  Agent: tag(name="user_approved_baseline")
  Agent: branch(name="explore_from_subtle")

[continues exploring along explore_from_subtle...]

User: "Actually, let's try a completely different direction"
  Agent: switch(ref="user_approved_baseline")  # back to the tagged anchor
  Agent: branch(name="explore_warmth")
  Agent: apply_primitive(warm_highlights_subject)
  ...
```

Branching becomes natural in conversation. "Explore from here" is a branch. "Try a different direction" is another branch from the same parent. Multiple variants coexist. The user picks; the unwinning branches stay around in case they change their minds.

### Mode B — autonomous exploration

A Mode B run produces a tree, not a sequence:

```
main: [baseline] → [global moves] → [variant_A] → [refined_A] → [final_A]
                                  ↘ [variant_B] → [refined_B]
                                  ↘ [variant_C] → [refined_C] → [final_C] ← winner
```

The agent commits at each step, branches when exploring alternatives, evaluates each candidate against the eval function, presents the winner. The branches that didn't win remain in the repo. The session transcript explains *why* each branch was tried.

Without versioning, this exploration is opaque. With it, the user can review the agent's reasoning in full: "you tried variant A, B, and C; you picked C because the eval scored 0.83 vs. 0.71 and 0.69; here's exactly what's different between them."

This is what makes Mode B inspectable and therefore researchable.

## Integration with darktable's catalog

Worth being explicit: **Chemigram repos do not integrate with darktable's catalog.** Deliberately.

darktable's catalog (`library.db`) tracks images, tags, ratings, history, etc. for darktable's own use. Chemigram runs its embedded darktable subprocess against an *isolated configdir*, with a separate `library.db` it owns. Your everyday darktable library is untouched.

This means Chemigram is a side workflow, not a replacement DAM:

- Your real photo workflow stays in your DAM of choice (LR, darktable, Capture One, whatever).
- Copy a raw into a Chemigram repo when you want agent-driven editing.
- Work with the agent.
- Export the final via `export_final` to `<image_id>/exports/`.
- Decide whether to ingest the export back into your real catalog.

The honest cost: a raw "lives" in two places. Cheap with symlinks — we don't duplicate the bytes. The Chemigram repo references the original raw, doesn't copy it.

This is the right division. Building a real DAM is a multi-year project. Chemigram is a research instrument for one image at a time. Different tools, different jobs.

## Comparison to other version-control models

| Model | Granularity | Branching | Used for |
|-|-|-|-|
| darktable history | Single image, single linear stack | No | Linear undo within an image |
| LR catalog versions | Single image, multiple flat snapshots | No (just named copies) | "Save as virtual copy" |
| git | Repo, full DAG | Yes | Source code |
| **Chemigram repo** | Single image, full DAG | Yes | Agent-driven exploration of one image |

The closest analog is git, deliberately, because git's data model is the right shape for branching exploration — and because cloning git's mental model (refs, HEAD, commit hashes, branches, tags) gets us free understandability for technical users.

The granularity is per-image rather than per-repo. This is a deliberate departure: in git, a repo holds many files and a commit captures a snapshot of all of them; in Chemigram, a "repo" holds one image and a commit captures one XMP. We could have done a single repo holding all images, but that conflates per-image exploration with cross-image library management — and we already established that DAM is out of scope. One image, one repo, simple model.

## Implementation cost

Honest estimate:

- ~300 lines of Python: object store, refs, log, basic operations
- ~100 lines of MCP wiring: the six agent-visible tools
- One disk-format decision: clone git's loose-object format and ref file format. No invention required.
- Testing: snapshot/checkout/branch round-trip, ref consistency, hash determinism, GC correctness

Small enough to land in v1. Large enough to deserve its own doc — this one.

## What we're explicitly not building

Worth listing to set expectations:

- **No remote / push / pull.** Local repos only. Cloud sync is the user's problem (Dropbox, iCloud, rsync).
- **No three-way merge.** Photo edits don't merge in the source-code sense. Cherry-pick suffices.
- **No CRDT-style multi-user concurrent editing.** Single-user, single-process at a time.
- **No reflog.** If the user `gc`s, branches they didn't ref are gone. Document this.
- **No partial XMP staging / "git add -p" equivalent.** A snapshot commits the entire current XMP.
- **No protected branches / hooks / permissions.** Trust model is "single user owns the repo."

These are deliberate. Keeping the model minimal is what makes ~300 lines of Python sufficient.

## Open questions for Phase 1

- [ ] Confirm SHA-256 over canonical-XMP is stable enough — do whitespace or attribute-order changes produce different hashes when the semantic content is identical? (Probably yes; we need a canonical-serialization pass before hashing.)
- [ ] Decide on log.jsonl schema specifics: what's recorded per operation, what's derived later from objects.
- [ ] Decide on session transcript schema and how sessions reference snapshots (probably by hash, in transcript entries).
- [ ] Validate that `merge_pick` is genuinely useful or whether agents will only ever use snapshot/checkout/branch. If it's never used in practice, strip it.

## Where this lands in the doc set

- `chemigram.md` — mention versioning as part of the engine in the project's framing.
- `architecture.md` — versioning is a core engine subsystem; reference this doc.
- `modes.md` (when written) — Mode B's tree-shaped exploration depends on this doc; cross-reference.
- This doc is the reference spec.
