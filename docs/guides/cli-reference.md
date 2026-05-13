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
 *  --entry              TEXT   Vocabulary entry name. [required]
    --pack       -p      TEXT   Vocabulary pack(s). Defaults to ['starter'].
    --mask-spec          TEXT   Optional JSON mask spec to apply this
                                primitive through a drawn mask region.
                                Schema:
                                '{"dt_form":"gradient|ellipse|rectangle","dt…
                                Overrides the entry's manifest mask_spec when
                                both are present. See
                                docs/guides/mask-applicable-controls.md for
                                parameter semantics and the per-module
                                compatibility matrix.
    --value              TEXT   Single-parameter shorthand for parameterized
                                entries (e.g. 'exposure --value 0.7'). For
                                multi-parameter entries, use --param NAME=V
                                instead. See docs/guides/recipes.md.
    --param              TEXT   Repeatable NAME=VALUE for multi-parameter
                                entries (e.g. '--param temp=+0.4 --param
                                tint=-0.1'). May be combined with --value if
                                values agree.
    --strength           FLOAT  RFC-035 Path B — interpolate the entry's
                                authored parameterized fields toward identity
                                by this factor [0.0, 1.0]. 1.0 preserves
                                authored (default); 0.0 = identity / no-op;
                                0.5 = halfway. Useful for L2 looks:
                                '--strength 0.5' produces a softer variant.
    --stdin                     Read image_ids from stdin (one per line);
                                same entry applied to each.
    --help                      Show this message and exit.
```

### `chemigram apply-per-region`

```
Usage: chemigram apply-per-region [OPTIONS] IMAGE_ID

 Apply one primitive to N mask-bound regions atomically (RFC-031).

 *    image_id      TEXT  Image ID. [required]
    --entry            TEXT  Vocabulary entry name (single-op shape per
                             RFC-031). Omit to use mixed-op shape where each
                             region carries its own 'ops' list.
 *  --regions          TEXT  JSON array of regions. Single-op shape: each
                             region is {"mask_spec": {...},
                             "parameter_values": {...}}. Mixed-op shape
                             (RFC-036): each region is {"mask_spec": {...},
                             "ops": [{"primitive_name": "...",
                             "parameter_values": {...}}, ...]}. mask_spec
                             accepts drawn / parametric / named-mask shapes.
                             [required]
    --pack     -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
    --label            TEXT  Optional snapshot label.
    --help                   Show this message and exit.
```

### `chemigram apply-spot`

```
Usage: chemigram apply-spot [OPTIONS] IMAGE_ID

 Apply a spot retouch (heal/clone) at the given coordinate (RFC-025 / ADR-087).

 *    image_id      TEXT  Image ID. [required]
 *  --kind            TEXT   'heal' (auto-source via wavelet decomposition)
                             or 'clone' (caller-specified source).
                             [required]
 *  --x               FLOAT  Spot center x in normalized [0, 1] coords.
                             [required]
 *  --y               FLOAT  Spot center y in normalized [0, 1] coords.
                             [required]
 *  --radius          FLOAT  Spot radius in normalized [0, 1]. Typical:
                             0.01-0.10 for blemishes / dust spots.
                             [required]
    --source-x        FLOAT  Clone source x in normalized [0, 1] coords.
                             Required when --kind=clone.
    --source-y        FLOAT  Clone source y in normalized [0, 1] coords.
                             Required when --kind=clone.
    --opacity         FLOAT  Mask opacity 0..100 (default 100).
                             [default: 100.0]
    --border          FLOAT  Mask feather border 0..1 (default 0.02).
                             [default: 0.02]
    --label           TEXT   Optional snapshot label.
    --help                   Show this message and exit.
```

### `chemigram wb-from-gray-card`

```
Usage: chemigram wb-from-gray-card [OPTIONS] IMAGE_PATH

 Sample a gray-card region; return temperature coefficients (survey Gap #20).

 *    image_path      TEXT  Path to rendered image (e.g., from
                            render-preview).
                            [required]
 *  --x                    INTEGER  Pixel x coordinate of gray-card sample.
                                    [required]
 *  --y                    INTEGER  Pixel y coordinate of gray-card sample.
                                    [required]
    --sample-radius        INTEGER  Half-side of square sample region
                                    (default 5 → 11x11 pixels).
                                    [default: 5]
    --help                          Show this message and exit.
```

### `chemigram propagate-state`

```
Usage: chemigram propagate-state [OPTIONS] SOURCE_IMAGE_ID

 Sync edit state from one anchor to N targets atomically (RFC-037).

 *    source_image_id      TEXT  Anchor image (state propagates FROM).
                                 [required]
 *  --to                       TEXT  Target image_id (repeatable; state
                                     propagates TO).
                                     [required]
    --exclude-op               TEXT  Operation name to skip (repeatable).
                                     Default: inherit everything.
    --include-per-image              Override framing-bound auto-exclusion
                                     (drawn masks, retouch, crop, lens). Use
                                     for tripod-fixed series.
    --label                    TEXT  Optional snapshot label.
    --help                           Show this message and exit.
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

 --pack  -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --tag           TEXT  Filter by tag (repeatable; OR — any matching tag
                       includes the maskdef).
 --help                Show this message and exit.
```

### `chemigram vocab show-mask`

```
Usage: chemigram vocab show-mask [OPTIONS] NAME

 Print one maskdef's manifest fields + spec (RFC-032).

 *    name      TEXT  Maskdef name (e.g. mask_sky). [required]
 --pack  -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --help                Show this message and exit.
```

### `chemigram vocab validate`

```
Usage: chemigram vocab validate [OPTIONS] NAME

 Run consistency checks on a vocabulary entry.

 Validates: manifest schema, dtstyle file exists + parses, blendop_params
 bytes decode at the expected size, modversion drift between manifest
 and dtstyle, parameters block declarations valid (ranges + offsets).
 Useful mid-authoring to catch drift before commit.

 Per ADR-072: text + --json output modes. Returns NOT_FOUND if entry
 missing; INVALID_INPUT if any check fails; SUCCESS if all pass.

 *    name      TEXT  Vocabulary entry name to validate. [required]
 --pack  -p      TEXT  Pack name (repeatable). Defaults to ['starter'].
 --help                Show this message and exit.
```

### `chemigram gap-log list`

```
Usage: chemigram gap-log list [OPTIONS]

 List vocabulary-gap entries across the workspace, filterable.

 Each row is one ``vocabulary_entry``-equivalent event. The result
 summary reports the total count + the filter scope.

 --since         TEXT  Only show gaps logged after this point. ISO 8601
                       (2026-05-01) or relative (7d / 2w / 24h / 30m).
 --image         TEXT  Filter to one image_id. Omit to scan all images in the
                       workspace.
 --module        TEXT  Filter to gaps mentioning a darktable module name
                       (matches missing_capability, operations_involved, or
                       description).
 --help                Show this message and exit.
```

### `chemigram gap-log rank`

```
Usage: chemigram gap-log rank [OPTIONS]

 Rank vocabulary gaps by frequency.

 Aggregation key: ``(description, missing_capability)``. Each unique
 key is one row; ``count`` is the occurrence frequency; ``examples``
 surfaces a sample image_id + timestamp for the row.

 --since        TEXT                  Only count gaps logged after this
                                      point. ISO 8601 or relative.
 --image        TEXT                  Filter to one image_id. Omit to scan
                                      all images.
 --top          INTEGER RANGE [x>=0]  Show the top N most frequent gaps
                                      (default 20). 0 = no limit.
                                      [default: 20]
 --help                               Show this message and exit.
```

### `chemigram gap-log show`

```
Usage: chemigram gap-log show [OPTIONS] IMAGE_ID

 Show all gap entries for one image, chronological (oldest first).

 *    image_id      TEXT  Image identifier. [required]
 --help          Show this message and exit.
```

### `chemigram gap-log clear`

```
Usage: chemigram gap-log clear [OPTIONS] IMAGE_ID

 Delete the vocabulary_gaps.jsonl for one image (opt-in cleanup).

 Intended for use after the photographer / maintainer has reviewed
 the image's gaps and either authored missing primitives or decided
 they don't need addressing. The file is deleted, not truncated, so
 a fresh empty file is created when the agent next logs a gap.

 *    image_id      TEXT  Image identifier. [required]
 --yes   -y        Skip the confirmation prompt. Use after you've reviewed
                   and addressed the gaps for this image.
 --help            Show this message and exit.
```

### `chemigram session-log list`

```
Usage: chemigram session-log list [OPTIONS]

 List session transcripts across the workspace, newest-first.

 --since        TEXT  Only show sessions started after this point. ISO 8601
                      or relative (7d / 2w / 24h / 30m).
 --image        TEXT  Filter to one image_id. Omit to scan all images.
 --help               Show this message and exit.
```

### `chemigram session-log show`

```
Usage: chemigram session-log show [OPTIONS] SESSION_ID

 Show all entries from one session, chronological.

 *    session_id      TEXT  Session identifier (matches the JSONL filename or
                            header's session_id).
                            [required]
 --help          Show this message and exit.
```

### `chemigram session-log find`

```
Usage: chemigram session-log find [OPTIONS]

 Find entries across all session transcripts matching the query.

 --primitive        TEXT  Match tool_call entries where args.name == this
                          primitive (e.g. 'exposure').
 --module           TEXT  Match anywhere in the entry's serialized JSON
                          (covers tool args, error messages, notes).
 --tool             TEXT  Match tool_call / tool_result entries with this
                          tool name (e.g. 'apply_primitive').
 --image            TEXT  Restrict to one image_id.
 --help                   Show this message and exit.
```

### `chemigram session-log replay`

```
Usage: chemigram session-log replay [OPTIONS] SESSION_ID

 Re-emit a session's tool calls as CLI invocation hints.

 Best-effort rendering: each tool_call becomes a line you could
 re-run from the shell. Tool-specific argument shapes are mapped for
 the common cases (apply_primitive, versioning verbs); others fall
 through as a comment.

 *    session_id      TEXT  Session identifier. [required]
 --help          Show this message and exit.
```

### `chemigram cache list`

```
Usage: chemigram cache list [OPTIONS]

 List cached preview JPEGs newest-first across the workspace.

 Each row reports image_id, filename, size (bytes + human-friendly),
 and modified time. Matches the gap-log / session-log row pattern.

 --image        TEXT  Restrict to one image_id.
 --since        TEXT  Only show previews modified within this window (e.g.
                      7d, 24h, 30m).
 --help               Show this message and exit.
```

### `chemigram cache size`

```
Usage: chemigram cache size [OPTIONS]

 Aggregate cache size: total bytes + per-image breakdown.

 --image        TEXT  Restrict to one image_id.
 --help               Show this message and exit.
```

### `chemigram cache clear`

```
Usage: chemigram cache clear [OPTIONS]

 Remove cached preview JPEGs.

 Previews are regenerable from snapshots, so this is a safe cleanup
 operation. Requires ``--yes`` to skip the interactive confirmation
 prompt; without ``--yes``, prints what would be removed and exits
 without modifying anything (matches the gap-log clear UX).

 Removes only ``previews/*.jpg`` files. The directory itself is
 preserved (other tools assume it exists).

 --image          TEXT  Restrict to one image_id.
 --yes    -y            Skip confirmation; required for non-interactive use.
 --help                 Show this message and exit.
```
