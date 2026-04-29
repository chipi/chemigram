# RFC-003 — Mask storage in versioning

> Status · Decided (closed by ADR-055 at the v0.2.0 milestone, 2026-04-29)
> TA anchor ·/components/versioning ·/components/ai-providers
> Related · ADR-018, ADR-021, ADR-022
> Closed by · ADR-055 (raster masks share the per-image objects/ store; masks/registry.json maps symbolic names to hashes plus provenance). PNG validation is byte-magic only in v0.2.0; full format validation lands when a masking provider needing Pillow ships.
> Why this is an RFC · ADR-022 commits to the mask registry pattern, but doesn't specify how masks integrate with snapshot-based versioning. Two viable storage strategies exist with different trade-offs around storage efficiency, simplicity, and cross-snapshot mask sharing. The choice affects how `checkout`, `snapshot`, `gc`, and `compare` interact with masks.

## The question

When the agent applies vocabulary entries that reference an AI-generated raster mask, the synthesized XMP contains a path to the mask PNG. Snapshots capture the XMP. But what about the mask itself? Does it live alongside snapshots in the content-addressed object store (Option A), or in a per-snapshot directory (Option B), or somewhere else?

The choice affects: storage efficiency (do identical masks share storage?), `gc` correctness (when can a mask be garbage-collected?), `checkout` semantics (do we restore mask files when checking out an old snapshot?), and `compare` (does comparing two snapshots regenerate or reuse masks?).

## Use cases

- The agent generates `current_subject_mask` once. Three vocabulary entries reference it across the session.
- The photographer branches at snapshot A, applies different vocabulary on each branch — both branches reference the same mask.
- The photographer comes back next session, runs `compare(hash_A, hash_B)` — masks must still resolve.
- After many sessions, the photographer runs `gc` to clean up unreferenced snapshots and masks.

## Goals

- Snapshots are reproducible — the XMP plus its referenced masks must restore correctly
- Identical masks across snapshots share storage
- `gc` can identify unreferenced masks safely
- `checkout` doesn't break mid-session if the registry has moved on (e.g., mask was regenerated)

## Constraints

- TA/components/versioning — content-addressed by SHA-256
- TA/contracts/per-image-repo — masks live under `<image_id>/masks/`
- ADR-022 — symbolic references in vocabulary entries; resolved at synthesis time

## Proposed approach

**Option A — Content-addressed mask storage (recommended).**

Masks are stored content-addressed, alongside the XMP snapshot store but in a separate object directory (or with a tag prefix). Sharded the same way (`masks/objects/AB/CDEF.png`).

When the synthesizer composes an XMP that references a mask, it computes the mask's SHA-256, stores the mask under that hash, and writes the hash-form path into the synthesized XMP's `blendop_params` mask reference (if achievable) or via a Chemigram-side metadata note that maps the symbolic ref → mask hash at the time of snapshot.

The per-image registry tracks: symbolic name → current mask hash (`current_subject_mask` → `a3f2...`). When the mask is regenerated, the registry's pointer updates; the old hash stays in storage as long as some snapshot references it (via the side-metadata).

Snapshot record (in `log.jsonl` or an extended snapshot manifest) includes: `xmp_hash`, plus a list of mask hashes referenced by this XMP. The mask GC walks all snapshot records and marks reachable mask hashes; unreachable ones are deleted.

`checkout(image_id, snapshot_hash)`:
1. Resolves the snapshot's XMP from `objects/`.
2. Reads its referenced mask hashes from the snapshot's metadata.
3. Restores `masks/current_*_mask.png` symlinks (or copies) to point at the snapshot-time mask hashes.
4. Updates the registry to reflect this.

`compare(image_id, hash_a, hash_b)`:
1. Resolves both snapshots' XMPs and mask hashes.
2. Renders both — masks resolve via their snapshot-time hashes.
3. Returns the comparison.

## Alternatives considered

- **Option B — Per-snapshot mask directories.**
  Each snapshot has its own `masks/` subdirectory; masks are duplicated when snapshots reference the same mask data. Simple, no GC question. Rejected: storage explodes when an image has many snapshots referencing the same subject mask. After 30 sessions on one image, identical subject masks duplicate 30+ times.

- **Option C — Masks stay live under `masks/<name>.png`; snapshots only reference by symbolic name.**
  Snapshot fully captures XMP including symbolic references; resolution always uses current registry. Rejected: breaks `compare` and `checkout` of historical snapshots — you can't render an old snapshot if its referenced mask was regenerated. Loses reproducibility.

- **Option D — No mask versioning at all (always regenerate).**
  Rejected: regeneration is expensive, non-deterministic (different masking provider runs produce different masks), and breaks reproducibility entirely.

## Trade-offs

- Option A's GC requires walking snapshot records — a real cost at scale (thousands of snapshots), though still cheap in absolute terms.
- The registry's "current pointer" model adds a layer of indirection (symbolic name → current hash → storage path).
- Implementation complexity vs Option B is meaningfully higher (custom mask GC logic, snapshot metadata extension).

## Open questions

- **How does the snapshot record reference its masks?** A separate `masks` field in the snapshot's metadata file, or embedded in the XMP itself, or in the per-image `log.jsonl`? Proposed: a `masks` field in the snapshot metadata, since XMP doesn't have a clean place to put non-darktable metadata.
- **Does `compare` need mask-rendering symmetry?** If snapshots A and B reference different mask versions, the comparison reflects both XMP changes AND mask changes. Should we surface this distinction? Proposed: yes — `compare` returns metadata indicating which masks differ between A and B.
- **Cross-image mask sharing.** Could the same mask hash be shared across multiple images? In principle yes; in practice unlikely. Defer until evidence shows it matters.
- **Mask provenance preservation.** When a mask is GC'd, its registry entry (provider, prompt, generated_from_render_hash) is also lost. Proposed: keep registry entries even after the mask itself is deleted, marked as "purged" — the audit trail value is preserved.

## How this closes

This RFC closes into:
- **An amendment to ADR-022** specifying Option A: content-addressed mask storage with snapshot-side metadata.
- **A new ADR for mask GC semantics** (or merge into the amendment) — what's reachable, when GC runs, manual vs automatic.

## Links

- TA/components/versioning
- TA/components/ai-providers
- ADR-018, ADR-021, ADR-022
