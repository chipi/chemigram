# CLI reference

> Auto-generated from `chemigram --help`. Do not edit by hand.
> Regenerate with `make docs-cli`. CI fails if this file drifts from
> the live `--help` output.

The chemigram CLI mirrors the MCP tool surface verb-for-verb (with
`_` → `-`). Output is human-readable by default and newline-delimited
JSON via `--json`. Exit codes are stable per RFC-020 §D / ADR-072.

For the user-value rationale and design discussion see
[PRD-005](../prd/PRD-005-command-line-interface.md) and
[RFC-020](../rfc/RFC-020-command-line-interface.md). When to reach for
the CLI vs the MCP server: see `docs/index.md` § Two planes of control.

## Global options

These apply to every verb. See `chemigram --help` for the canonical
listing; this section captures the same content.

| Flag | Env var | Description |
|-|-|-|
| `--json` | — | Emit NDJSON to stdout instead of human-readable text. |
| `--workspace <path>` | `CHEMIGRAM_WORKSPACE` | Workspace root (default `~/Pictures/Chemigram`). |
| `--configdir <path>` | `CHEMIGRAM_DT_CONFIGDIR` | darktable-cli configdir (must be pre-bootstrapped per ADR-005). |
| `--quiet`, `-q` | — | Suppress informational events; errors still surface. |
| `--verbose`, `-v` | — | Increase log verbosity (stackable: `-v`, `-vv`). |
| `--dry-run` | — | Describe what would happen without writing. (No-op for v1.3.0; verbs honor it incrementally.) |

## Exit codes

| Code | Name | Meaning |
|-|-|-|
| 0 | `SUCCESS` | OK |
| 1 | `INTERNAL_ERROR` | Unhandled exception (bug — please report) |
| 2 | `INVALID_INPUT` | Bad arguments or schema validation failure |
| 3 | `NOT_FOUND` | image_id, entry, ref, mask, or proposal not found |
| 4 | `STATE_ERROR` | Workspace in inconsistent state |
| 5 | `VERSIONING_ERROR` | Snapshot-graph integrity issue |
| 6 | `DARKTABLE_ERROR` | Render subprocess failure |
| 7 | `MASKING_ERROR` | Masking provider failure |
| 8 | `SYNTHESIZER_ERROR` | XMP synthesis failure |
| 9 | `PERMISSION_ERROR` | Filesystem permission denied |
| 10 | `NOT_IMPLEMENTED` | Tool stub or feature gate |

## Verbs

### `chemigram status`

```
Usage: chemigram status [OPTIONS]

 Print runtime diagnostics: chemigram + darktable-cli versions, configured
 packs, workspace root, prompt store version, output schema.

 --help          Show this message and exit.
```

### `chemigram ingest`

```
Usage: chemigram ingest [OPTIONS] RAW_PATH

 Bootstrap a per-image workspace from a raw file.

 *    raw_path      FILE  Path to the raw image file. Must exist. [required]
 --image-id          TEXT  Override the derived image_id (default: raw
                           filename stem, sanitized).
 --pack      -p      TEXT  Vocabulary pack(s) for L1 binding. Defaults to
                           ['starter'].
 --help                    Show this message and exit.
```

### `chemigram apply-primitive`

```
Usage: chemigram apply-primitive [OPTIONS] [IMAGE_ID]

 Apply a vocabulary entry; snapshot the result.

   image_id      [IMAGE_ID]  Image ID (or '-' with --stdin for batch).
 *  --entry              TEXT  Vocabulary entry name. [required]
    --pack       -p      TEXT  Vocabulary pack(s). Defaults to ['starter'].
    --mask-spec          TEXT  Optional JSON mask spec to apply this
                               primitive through a drawn mask region. Schema:
                               '{"dt_form":"gradient|ellipse|rectangle","dt_…
                               Overrides the entry's manifest mask_spec when
                               both are present. See
                               docs/guides/mask-applicable-controls.md for
                               parameter semantics and the per-module
                               compatibility matrix.
    --value              TEXT  Single-parameter shorthand for parameterized
                               entries (e.g. 'exposure --value 0.7'). For
                               multi-parameter entries, use --param NAME=V
                               instead. See docs/guides/recipes.md.
    --param              TEXT  Repeatable NAME=VALUE for multi-parameter
                               entries (e.g. '--param temp=+0.4 --param
                               tint=-0.1'). May be combined with --value if
                               values agree.
    --strength           FLOAT Scale a parameterized L2 look's authored
                               magnitudes by `strength ∈ [0.0, 1.0]`
                               (default 1.0 = authored). Each parameterized
                               field interpolates from identity:
                               `interpolated = identity + strength *
                               (authored - identity)`. Non-parameterized
                               fields preserve authored values. Modules
                               without a registered Path C decoder pass
                               through unchanged. Closes RFC-035 / ADR-088.
    --stdin                    Read image_ids from stdin (one per line); same
                               entry applied to each.
    --help                     Show this message and exit.
```

### `chemigram apply-per-region`

```
Usage: chemigram apply-per-region [OPTIONS] IMAGE_ID

 Apply one or more primitives to N mask-bound regions atomically.
 Single-op shape closes RFC-031; mixed-op shape closes RFC-036 / ADR-089.

 *    image_id     TEXT  Image ID. [required]
      --entry      TEXT  Vocabulary entry name (single-op shape per
                         RFC-031). Omit when using mixed-op shape — each
                         region then carries its own `ops` list.
 *    --regions    TEXT  JSON array of regions. [required]
                         Single-op shape: `{"mask_spec": {...},
                         "parameter_values": {...}}`.
                         Mixed-op shape (RFC-036): each region is
                         `{"mask_spec": {...}, "ops": [{"primitive_name":
                         "...", "parameter_values": {...}}, ...]}`.
                         Discriminator: presence of `ops` on any region
                         routes to mixed-op.
      --pack  -p   TEXT  Pack name (repeatable). Defaults to ['starter'].
      --label      TEXT  Optional snapshot label.
      --help             Show this message and exit.
```

The single-op canonical use case is dodge-and-burn: brighten cheekbones,
brighten nose bridge, deepen jaw shadow — one move from the photographer's
perspective, N region-specific applications underneath. Soft cap: 32 regions.

The mixed-op shape (RFC-036 / ADR-089) handles composite moves where regions
need different primitives — eye-region work (`+exposure` on iris, `+sharpen`
on lashes), face-sculpt-with-clarity, sky-and-foreground twin moves. Per-(op,
region) `multi_priority` allocation keeps stacked instances coexisting cleanly.
Cap: 64 (op × region) pairs.

Atomic semantics in both shapes — all (op × region) combinations validate
first; if any fails (out-of-range parameter, unresolved named-mask reference,
modversion mismatch), none apply.

### `chemigram propagate-state`

```
Usage: chemigram propagate-state [OPTIONS] SOURCE_IMAGE_ID

 Sync edit state from one anchor to N targets atomically (RFC-037 / ADR-090).
 Lightroom-Sync analog.

 *    source_image_id        TEXT  Anchor image (state propagates FROM).
                                   [required]
 *    --to                   TEXT  Target image_id (repeatable; state
                                   propagates TO). Cap: 200 targets per
                                   call. [required]
      --exclude-op           TEXT  Operation name to skip (repeatable).
                                   Default: inherit everything except the
                                   framing-bound auto-exclusion list.
      --include-per-image          Override framing-bound auto-exclusion
                                   (drawn masks, retouch, crop, lens). Use
                                   for tripod-fixed series where framing-
                                   bound moves are portable.
      --label                TEXT  Optional snapshot label per target.
      --help                       Show this message and exit.
```

Inheritance discipline: inherit everything by default; auto-exclude framing-
bound ops. Parametric range masks (color-range / luminance-range) DO propagate
— they're content-relative, not coordinate-bound. Atomic — every target
validates first; any modversion mismatch / missing target / empty-history
source aborts the entire batch. Each target gets a single snapshot capturing
the propagated state plus the supplied label.

Use cases: wedding lighting groups (anchor on the best frame, propagate to
the burst), product photography variants (anchor on the hero shot, propagate
to color-A vs color-B), portfolio series consistency.

### `chemigram remove-module`

```
Usage: chemigram remove-module [OPTIONS] IMAGE_ID

 Strip all history entries for an operation.

 *    image_id      TEXT  Image ID. [required]
 *  --operation        TEXT  darktable operation name to strip from history
                             (e.g. exposure, channelmixerrgb).
                             [required]
    --help                   Show this message and exit.
```

### `chemigram reset`

```
Usage: chemigram reset [OPTIONS] IMAGE_ID

 Rewind the current branch to baseline (ADR-062).

 *    image_id      TEXT  Image ID. [required]
 --help          Show this message and exit.
```

### `chemigram get-state`

```
Usage: chemigram get-state [OPTIONS] [IMAGE_ID]

 Print a summary of the workspace's current XMP.

   image_id      [IMAGE_ID]  Image ID (or '-' with --stdin for batch).
 --stdin          Read image_ids from stdin (one per line); aggregate exit
                  code.
 --help           Show this message and exit.
```

### `chemigram snapshot`

```
Usage: chemigram snapshot [OPTIONS] IMAGE_ID

 Snapshot the current XMP; return the new content hash.

 *    image_id      TEXT  Image ID. [required]
 --label        TEXT  Optional human-readable label for the log entry.
 --help               Show this message and exit.
```

### `chemigram branch`

```
Usage: chemigram branch [OPTIONS] IMAGE_ID

 Create a branch at HEAD (or --from <ref>).

 *    image_id      TEXT  Image ID. [required]
 *  --name        TEXT  Branch name (no slashes). [required]
    --from        TEXT  Ref or hash to branch from. Defaults to HEAD.
                        [default: HEAD]
    --help              Show this message and exit.
```

### `chemigram tag`

```
Usage: chemigram tag [OPTIONS] IMAGE_ID

 Create an immutable tag at HEAD (or --hash <h>).

 *    image_id      TEXT  Image ID. [required]
 *  --name        TEXT  Tag name (immutable; cannot retag). [required]
    --hash        TEXT  Snapshot hash to tag. Defaults to HEAD.
    --help              Show this message and exit.
```

### `chemigram checkout`

```
Usage: chemigram checkout [OPTIONS] IMAGE_ID REF_OR_HASH

 Move HEAD to a ref or hash.

 *    image_id         TEXT  Image ID. [required]
 *    ref_or_hash      TEXT  Branch name, tag name, or snapshot hash to check
                             out.
                             [required]
 --help          Show this message and exit.
```

### `chemigram log`

```
Usage: chemigram log [OPTIONS] IMAGE_ID

 Print the operation log (newest first).

 *    image_id      TEXT  Image ID. [required]
 --limit        INTEGER RANGE [1<=x<=200]  Max number of log entries to
                                           return.
                                           [default: 20]
 --help                                    Show this message and exit.
```

### `chemigram diff`

```
Usage: chemigram diff [OPTIONS] IMAGE_ID HASH_A HASH_B

 Diff two snapshots — added/removed/changed primitives.

 *    image_id      TEXT  Image ID. [required]
 *    hash_a        TEXT  First snapshot hash. [required]
 *    hash_b        TEXT  Second snapshot hash. [required]
 --help          Show this message and exit.
```

### `chemigram bind-layers`

```
Usage: chemigram bind-layers [OPTIONS] IMAGE_ID

 Apply L1/L2 vocabulary templates onto the current XMP.

 *    image_id      TEXT  Image ID. [required]
 --l1            TEXT  L1 vocabulary template name (camera/lens binding).
 --l2            TEXT  L2 vocabulary template name (look baseline).
 --pack  -p      TEXT  Vocabulary pack(s). Defaults to ['starter'].
 --help                Show this message and exit.
```

### `chemigram render-preview`

```
Usage: chemigram render-preview [OPTIONS] [IMAGE_ID]

 Render a snapshot to a JPEG preview.

   image_id      [IMAGE_ID]  Image ID (or '-' with --stdin for batch).
 --size         INTEGER RANGE [64<=x<=8192]  Max width/height in pixels.
                                             [default: 1024]
 --ref          TEXT                         Ref name or content hash to
                                             render (defaults to HEAD).
                                             [default: HEAD]
 --stdin                                     Read image_ids from stdin (one
                                             per line); render each.
 --help                                      Show this message and exit.
```

### `chemigram compare`

```
Usage: chemigram compare [OPTIONS] IMAGE_ID HASH_A HASH_B

 Render two snapshots and stitch them side-by-side.

 *    image_id      TEXT  Image ID. [required]
 *    hash_a        TEXT  First ref or hash. [required]
 *    hash_b        TEXT  Second ref or hash. [required]
 --size        INTEGER RANGE [64<=x<=8192]  Max width/height per side.
                                            [default: 1024]
 --help                                     Show this message and exit.
```

### `chemigram export-final`

```
Usage: chemigram export-final [OPTIONS] [IMAGE_ID]

 High-quality export to the workspace's exports/ dir.

   image_id      [IMAGE_ID]  Image ID (or '-' with --stdin for batch).
 --ref           TEXT                          Ref name or hash to export.
                                               Defaults to HEAD.
                                               [default: HEAD]
 --format        TEXT                          Output format: jpeg or png.
                                               [default: jpeg]
 --size          INTEGER RANGE [64<=x<=16384]  Max width/height in pixels.
                                               Omit for full resolution.
 --stdin                                       Read image_ids from stdin (one
                                               per line); export each.
 --help                                        Show this message and exit.
```

### `chemigram read-context`

```
Usage: chemigram read-context [OPTIONS] IMAGE_ID

 Print the agent's first-turn context (RFC-011).

 *    image_id      TEXT  Image ID (workspace name). [required]
 --help          Show this message and exit.
```

### `chemigram log-vocabulary-gap`

```
Usage: chemigram log-vocabulary-gap [OPTIONS] IMAGE_ID

 Append a gap record to vocabulary_gaps.jsonl.

 *    image_id      TEXT  Image ID. [required]
 *  --description               TEXT     What the agent reached for that
                                         didn't exist.
                                         [required]
    --workaround                TEXT     What was used instead, if anything.
    --intent                    TEXT     The intent the agent was after.
    --intent-category           TEXT     Tier of the missing primitive.
                                         [default: uncategorized]
    --missing-capability        TEXT     The specific capability that's
                                         absent.
    --operation                 TEXT     darktable operation(s) involved in
                                         the workaround (repeatable).
    --vocab-used                TEXT     Vocabulary entries used in the
                                         workaround (repeatable).
    --satisfaction              INTEGER  Photographer's read on the
                                         workaround: -1 (poor), 0 (ok), +1
                                         (good).
    --notes                     TEXT     Free-form.
    --help                               Show this message and exit.
```

### `chemigram apply-taste-update`

```
Usage: chemigram apply-taste-update [OPTIONS]

 Append directly to a taste file (CLI-only; MCP uses propose/confirm).

 *  --content         TEXT  Markdown to append (must be non-empty).
                            [required]
 *  --category        TEXT  Taste category: appearance | process | value (per
                            ADR-048).
                            [required]
    --file            TEXT  Target taste file (auto-suffixed with .md).
                            Defaults to _default.md.
                            [default: _default.md]
    --help                  Show this message and exit.
```

### `chemigram apply-notes-update`

```
Usage: chemigram apply-notes-update [OPTIONS] IMAGE_ID

 Append directly to per-image notes (CLI-only; MCP uses propose/confirm).

 *    image_id      TEXT  Image ID. [required]
 *  --content        TEXT  Markdown to append (must be non-empty). [required]
    --help                 Show this message and exit.
```

### `chemigram vocab list`

```
Usage: chemigram vocab list [OPTIONS]

 List vocabulary entries across the loaded packs.

 --pack   -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --layer          TEXT  Filter by layer (L1/L2/L3).
 --help                 Show this message and exit.
```

### `chemigram vocab show`

```
Usage: chemigram vocab show [OPTIONS] NAME

 Print one entry's manifest fields + .dtstyle path.

 *    name      TEXT  Vocabulary entry name (e.g. expo_+0.5). [required]
 --pack  -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --help                Show this message and exit.
```

### `chemigram vocab list-masks`

```
Usage: chemigram vocab list-masks [OPTIONS]

 List named masks (RFC-032) across the loaded packs.

 --pack   -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --tag            TEXT  Filter by tag (repeatable; OR — any matching tag
                        includes the maskdef).
 --help                 Show this message and exit.
```

Each entry's `spec` field is the apply-time `mask_spec`; reference a named
mask in any `apply_primitive` / `apply_per_region` / `--mask-spec` argument
as `{"kind": "named", "name": "<maskdef-name>"}`. Maskdefs that ship an
`llm_vision_prompt` field can be upgraded from the parametric fallback to a
constructed mask via render_preview + LLM-vision (per
`docs/guides/llm-vision-for-masks.md` Pattern 7).

### `chemigram vocab show-mask`

```
Usage: chemigram vocab show-mask [OPTIONS] NAME

 Print one maskdef's manifest fields + spec (RFC-032).

 *    name      TEXT  Maskdef name (e.g. mask_sky). [required]
 --pack  -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --help                Show this message and exit.
```

When the maskdef has an `llm_vision_prompt`, the output includes a
`llm_vision_hint` line pointing to Pattern 7 of
`docs/guides/llm-vision-for-masks.md` for the higher-precision construction
workflow.
