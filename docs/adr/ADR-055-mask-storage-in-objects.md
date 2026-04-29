# ADR-055 — Raster masks share the per-image objects/ store; registry maps symbolic names to hashes

> Status · Accepted
> Date · 2026-04-29
> TA anchor ·/components/versioning ·/contracts/per-image-repo
> Related RFC · RFC-003 (closes here)
> Related ADR · ADR-018 (per-image content-addressed DAG), ADR-019 (git-like ref structure), ADR-021 (three-layer mask pattern), ADR-022 (mask registry per image with symbolic refs)

## Context

Per-image repos store XMP edit-state snapshots in `objects/` content-addressed by SHA-256 (ADR-018, ADR-019). Raster masks (PNGs from AI-driven masking providers per ADR-021) also need somewhere to live. **RFC-003** framed the question: *do masks live in the same `objects/` store as XMPs, or in their own?*

This ADR closes the question.

## Decision

**Raster mask PNGs live in the same `objects/` store as XMP snapshots.** A separate `masks/registry.json` per image maps symbolic names (`current_subject_mask`, `subject_mask_v1_export`, ...) to object hashes plus provenance metadata.

Per-image layout (extends `contracts/per-image-repo`):

```
<root>/
  objects/                shared store: XMP snapshots AND mask PNGs
    NN/HHHHH...           SHA-256 sharded
  refs/
    heads/<branch>
    tags/<tag>
    HEAD
  masks/
    registry.json         {symbolic_name: {hash, generator, prompt, timestamp}}
  log.jsonl
```

`masks/registry.json` shape:

```json
{
  "current_subject_mask": {
    "hash": "abc123...",
    "generator": "coarse_agent",
    "prompt": "the manta",
    "timestamp": "2026-04-29T14:32:11+00:00"
  }
}
```

`json.dumps(..., sort_keys=True, indent=2)` for stable git diffs.

**Public API** (`chemigram.core.versioning.masks`):

- `register_mask(repo, name, png_bytes, *, generator, prompt=None) -> MaskEntry` — overwrites same name; bytes deduplicate via the object store
- `get_mask(repo, name) -> tuple[MaskEntry, bytes]`
- `list_masks(repo) -> list[MaskEntry]` (newest first by timestamp)
- `invalidate_mask(repo, name)` — drops registry entry; PNG bytes remain in `objects/`
- `tag_mask(repo, source_name, new_name)` — immutable alias under a new name; same hash, new timestamp

**PNG validation in v0.2.0 is byte-magic only** (verify the input starts with `\x89PNG\r\n\x1a\n`). Per ADR-021 we expect 8-bit grayscale, but full format validation needs Pillow which is out of scope here. When a masking provider that requires it lands, we add Pillow and tighten validation.

## Rationale

- **Single content-addressed store is simpler.** One `write_object`/`read_object` API serves both kinds of payload. `ImageRepo`'s primitives don't need to grow a per-type variant.
- **Dedup is automatic and beneficial.** If two symbolic names point at the same PNG bytes (which happens with `tag_mask`), they share storage. Same is true for any future case where mask bytes recur.
- **Type ambiguity in `objects/` is not a real problem.** Each consumer (XMP loader, mask loader) knows what bytes it's expecting; the file type is the consumer's concern, not the store's. Bytes are bytes.
- **`masks/registry.json` is one file per image.** Fits the per-image-repo philosophy: everything an image needs lives under its own root. Cross-image mask sharing isn't supported by design (TA's `contracts/per-image-repo` is explicit).
- **`tag_mask` gives mutable names + immutable history.** `current_subject_mask` is overwritten as the masker re-runs; `subject_mask_v1_export` captures a specific moment. This matches the pattern XMP versioning uses (branches mutate, tags don't).

## Alternatives considered

- **Separate `masks/objects/` store** (per-type isolation): rejected. Adds code, splits primitives, no benefit.
- **Inline PNG bytes in `registry.json`** (base64-encoded): rejected. Registry becomes huge; defeats content-addressing dedup; awful git diffs.
- **No registry, derive symbolic names from PNG filenames** (`masks/current_subject_mask.png`): rejected. Loses provenance metadata (generator, prompt, timestamp); doesn't dedup; symlinks would be fragile.
- **Use a SQLite registry instead of JSON**: rejected. Single-file JSON is human-readable, git-diff-friendly, and the registry stays small (typically <10 entries per image).
- **Add Pillow dep for full PNG validation in v0.2.0**: rejected. Byte-magic is enough for the typical contributor-error case (uploading a JPEG by mistake). Pillow lands when the masking provider system needs it.

## Consequences

Positive:
- Same primitives serve XMPs and masks; less code to maintain
- Automatic dedup of identical mask bytes across symbolic names
- Pure-Python PNG validation; no new deps for v0.2.0
- `tag_mask`'s "snapshot a mask before regen" semantics matches XMP `tag` ergonomics
- `registry.json` is human-readable and git-diff-friendly (sorted, indented)

Negative:
- `objects/` mixes binary types (XMP text, PNG binary). Documented; consumers know what they're looking for.
- `invalidate_mask` doesn't garbage-collect the PNG bytes — they stay in `objects/` until a future GC pass. v0.2.0 doesn't ship GC; tracked in TODO if storage grows surprisingly.
- PNG validation is shallow; a malformed-but-magic-correct PNG will fail later when a masker tries to read it. Acceptable since contributor packs are reviewed.

## Implementation notes

- `src/chemigram/core/versioning/masks.py` — `MaskEntry`, `register_mask`, `get_mask`, `list_masks`, `invalidate_mask`, `tag_mask`, plus `MaskError` / `MaskNotFoundError` / `InvalidMaskError`
- 17 unit tests in `tests/unit/core/versioning/test_masks.py` cover registration, retrieval, dedup, listing order, invalidation, tagging (incl. immutability), registry persistence across reopen, sorted JSON output, PNG-magic validation
- Inline test fixture: `make_test_png` produces an 8-bit grayscale PNG via stdlib `zlib`+`struct` (~80 bytes); avoids Pillow + keeps tests fast
- `chemigram.core.versioning.__init__` re-exports the public mask API
- RFC-003 status moves to `Decided`; remains as historical record
