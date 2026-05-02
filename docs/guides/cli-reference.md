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
Usage: chemigram apply-primitive [OPTIONS] IMAGE_ID

 Apply a vocabulary entry; snapshot the result.

 *    image_id      TEXT  Image ID. [required]
 *  --entry                  TEXT  Vocabulary entry name. [required]
    --mask-override          TEXT  Raster-mask-bound primitives: registered
                                   mask name to use instead of
                                   entry.mask_ref.
    --pack           -p      TEXT  Vocabulary pack(s). Defaults to
                                   ['starter'].
    --help                         Show this message and exit.
```

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
Usage: chemigram get-state [OPTIONS] IMAGE_ID

 Print a summary of the workspace's current XMP.

 *    image_id      TEXT  Image ID. [required]
 --help          Show this message and exit.
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
Usage: chemigram render-preview [OPTIONS] IMAGE_ID

 Render a snapshot to a JPEG preview.

 *    image_id      TEXT  Image ID. [required]
 --size        INTEGER RANGE [64<=x<=8192]  Max width/height in pixels.
                                            [default: 1024]
 --ref         TEXT                         Ref name or content hash to
                                            render (defaults to HEAD).
                                            [default: HEAD]
 --help                                     Show this message and exit.
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
Usage: chemigram export-final [OPTIONS] IMAGE_ID

 High-quality export to the workspace's exports/ dir.

 *    image_id      TEXT  Image ID. [required]
 --ref           TEXT                          Ref name or hash to export.
                                               Defaults to HEAD.
                                               [default: HEAD]
 --format        TEXT                          Output format: jpeg or png.
                                               [default: jpeg]
 --size          INTEGER RANGE [64<=x<=16384]  Max width/height in pixels.
                                               Omit for full resolution.
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

### `chemigram masks list`

```
Usage: chemigram masks list [OPTIONS] IMAGE_ID

 List registered masks (newest first).

 *    image_id      TEXT  Image ID. [required]
 --help          Show this message and exit.
```

### `chemigram masks generate`

```
Usage: chemigram masks generate [OPTIONS] IMAGE_ID

 Generate a raster mask via the configured provider.

 The CLI has no provider wiring today (see module docstring). Both
 generate and regenerate exit ``MASKING_ERROR`` (7) with a clear hint.

 *    image_id      TEXT  Image ID. [required]
 *  --target        TEXT  Subject for the masker (e.g. 'manta'). [required]
    --prompt        TEXT  Free-form refinement prompt for the provider.
    --name          TEXT  Mask registry name (defaults to
                          current_<target>_mask).
    --help                Show this message and exit.
```

### `chemigram masks regenerate`

```
Usage: chemigram masks regenerate [OPTIONS] IMAGE_ID

 Refine an existing mask via the configured provider. (Same MASKING_ERROR
 constraint as ``generate`` — see module docstring.)

 *    image_id      TEXT  Image ID. [required]
 *  --name          TEXT  Existing mask name to refine. [required]
    --target        TEXT  Override the target (defaults to inferred from
                          name).
    --prompt        TEXT  Refinement prompt.
    --help                Show this message and exit.
```

### `chemigram masks tag`

```
Usage: chemigram masks tag [OPTIONS] IMAGE_ID

 Copy a mask registry entry under a new name (snapshot-before-regenerate
 pattern).

 *    image_id      TEXT  Image ID. [required]
 *  --source          TEXT  Existing mask name. [required]
 *  --new-name        TEXT  New name (must be non-empty). [required]
    --help                  Show this message and exit.
```

### `chemigram masks invalidate`

```
Usage: chemigram masks invalidate [OPTIONS] IMAGE_ID

 Drop a mask from the registry (PNG bytes remain content-addressed).

 *    image_id      TEXT  Image ID. [required]
 *  --name        TEXT  Mask registry name to drop. [required]
    --help              Show this message and exit.
```
