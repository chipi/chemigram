# Recipes — common "how do I" patterns

> Cross-cutting tasks organized by user intent rather than by verb. For verb reference, see [`cli-reference.md`](cli-reference.md). For vocabulary patterns (combining primitives), see [`vocabulary-patterns.md`](vocabulary-patterns.md).

Each recipe is a small command sequence (CLI) plus a one-line MCP-tool equivalent where relevant. Both work; pick the surface that fits your context.

---

## Workspace lifecycle

### Reset an image to its baseline

You went down an exploration that didn't work; you want HEAD back at the original ingested state.

```bash
# CLI
chemigram reset <image_id>

# MCP
# tool: reset(image_id)
```

`reset` rewinds the current branch's HEAD to the `baseline` ref (created at ingest, immutable). All snapshots between baseline and HEAD remain in `objects/` — they're recoverable via `checkout <hash>`. You haven't lost anything; you've just moved the working pointer.

### See all snapshots for an image

```bash
chemigram log <image_id>
chemigram log <image_id> --json | jq -r '.[] | "\(.hash[0:8]) \(.label)"'
```

### Check out an earlier snapshot to inspect

```bash
chemigram checkout <image_id> <hash-or-ref>
chemigram render-preview <image_id>
chemigram checkout <image_id> main    # back to your latest
```

`checkout` moves HEAD to a ref or hash. The working state on disk reflects that snapshot. Re-checkout to the head of `main` (or whichever branch you were on) when done inspecting.

### Compare two snapshots side-by-side

```bash
chemigram compare <image_id> <hash-a> <hash-b> --size 1024
# Outputs a stitched JPEG; opens in Preview / xdg-open
```

The two snapshots can be branches (`main`, `experimental`) or hashes. The stitched output goes to `<workspace>/previews/_compare_<a>_<b>.jpg`.

### Branch to explore a variant

```bash
chemigram branch <image_id> --name aggressive
chemigram apply-primitive <image_id> --entry contrast_high
chemigram apply-primitive <image_id> --entry blacks_crushed
chemigram render-preview <image_id>
# decide: yes or no
chemigram checkout <image_id> main    # back to original
# (the experimental branch is still in refs/heads/aggressive — abandon or tag)
```

---

## Vocabulary discovery

### List every entry across all loaded packs

```bash
chemigram vocab list
chemigram vocab list --json | jq -r '.[] | .name'
```

### List by tag

```bash
chemigram vocab list --tag wb
chemigram vocab list --tag mask --tag gradient    # OR-filter; either tag matches
```

### List by layer

```bash
chemigram vocab list --layer L3
```

### Show full details for one entry

```bash
chemigram vocab show <entry-name>
chemigram vocab show gradient_top_dampen_highlights --json | jq
```

Shows the entry's manifest fields (subtype, touches, tags, description, modversions, optional `mask_spec`).

### Find entries that touch a specific darktable module

```bash
chemigram vocab list --json | jq -r '.[] | select(.touches[] == "exposure") | .name'
```

(There's no built-in `--touches` flag yet; this is a `jq` post-filter.)

---

## Render and export

### Quick preview at default size

```bash
chemigram render-preview <image_id>
```

### Larger preview

```bash
chemigram render-preview <image_id> --size 2048
```

### Export at full resolution as JPEG

```bash
chemigram export-final <image_id> --format jpeg
# output: <workspace>/<image_id>/exports/<image_id>_<hash[:8]>.jpeg
```

### Export multiple sizes (for web + print)

```bash
chemigram export-final <image_id> --format jpeg --size 1920    # web
chemigram export-final <image_id> --format jpeg                 # full-res, print
```

The CLI doesn't yet support a single-call multi-size export; loop in shell.

### Export every snapshot in a branch

```bash
chemigram log <image_id> --branch main --json | jq -r '.[].hash' | while read hash; do
  chemigram checkout <image_id> "$hash"
  chemigram export-final <image_id> --format jpeg --size 1920
done
chemigram checkout <image_id> main    # restore HEAD
```

For batch export, see [`examples/cli-batch-watch.sh`](../../examples/cli-batch-watch.sh) for the watch-folder pattern.

---

## Tagging and versioning

### Tag the current snapshot

```bash
chemigram tag <image_id> --name v1-export
chemigram tag <image_id> --name v1-export --hash <specific-hash>   # tag a specific past snapshot
```

Tags are immutable — re-tagging an existing name is a `VERSIONING_ERROR`. To "rename" a tag, create a new one and the old one stays as historical record.

### See all tags for an image

```bash
chemigram log <image_id> --json | jq -r '.[] | select(.refs | contains("v")) | "\(.hash[0:8]) \(.refs)"'
```

(Tags ride alongside branches in the `refs` field of log entries.)

### Diff two snapshots (which primitives differ)

```bash
chemigram diff <image_id> baseline v1-export
# → list of added / removed / changed vocabulary primitives
```

---

## Context and tastes

### See your current taste files

```bash
ls ~/.chemigram/tastes/
```

### Add a taste line directly (CLI-only)

```bash
chemigram apply-taste-update --content "Lift shadows on subjects almost always." --category appearance
chemigram apply-taste-update --content "Specifically reach for radial_subject_lift on portraits." --category process --file portrait.md
```

The CLI's `apply-taste-update` writes directly. The MCP equivalent is `propose_taste_update` → `confirm_taste_update`, which is a two-step conversational dance.

### Add a per-image note

```bash
chemigram apply-notes-update <image_id> --content "Manta belly was the focal point; mid-tone lift carried the shot."
```

### Read what the agent will see at session start

```bash
chemigram --json read-context <image_id> | jq
```

This dumps the full first-turn context: tastes (default + genre), brief, notes, recent log, recent vocabulary gaps. Useful for understanding why the agent is suggesting what it suggests.

---

## Vocabulary growth

### Read your vocabulary gaps across images

```bash
cat ~/Pictures/Chemigram/*/vocabulary_gaps.jsonl | jq -r '.description'
```

### Filter to recent gaps

```bash
find ~/Pictures/Chemigram -name vocabulary_gaps.jsonl -mtime -30 -exec cat {} \; | jq
```

### Author a new vocabulary entry

See [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) for the full GUI walkthrough.

---

## Sessions and replay

### Find your session transcripts for an image

```bash
ls ~/Pictures/Chemigram/<image_id>/sessions/
```

Each `.jsonl` file is one session. The first line is the header; subsequent lines are tool calls, proposals, and confirmations; the last line is the closing footer.

### Read a session as prose

```bash
cat ~/Pictures/Chemigram/<image_id>/sessions/<session_id>.jsonl | \
  jq -r 'select(.event=="tool_call") | "\(.tool): \(.args)"'
```

### Replay a session as a sequence of CLI calls

There's no built-in replay verb. The session transcript captures every tool call; manual replay = walk the transcript and re-issue equivalent CLI calls. For deterministic re-runs, prefer working from snapshots (the workspace `objects/` store is the source of truth; transcripts are audit logs).

---

## Failure / recovery

### "My workspace is corrupted; how do I start over for this image?"

```bash
rm -rf ~/Pictures/Chemigram/<image_id>
chemigram ingest /path/to/raw.NEF
```

Workspaces are independent per image; deleting one doesn't affect others. The original raw is symlinked, not copied — deletion is safe.

### "I applied something I didn't mean to; how do I undo?"

There's no undo verb. Either:

- `chemigram reset <image_id>` rewinds to baseline (loses all snapshots-as-state but they remain in objects/)
- `chemigram checkout <image_id> <earlier-hash>` rewinds HEAD to a specific earlier snapshot
- `chemigram log` to find the hash you want to return to

### "The MCP server isn't picking up my new vocabulary entry."

The agent loads vocabulary at session start. Restart your MCP session (Claude Code, Cursor, etc.) and the new entry will be in the action space. Or verify it loads correctly via CLI: `chemigram vocab show <name>`.

### "Render is taking forever."

First render against a fresh `CHEMIGRAM_DT_CONFIGDIR` is always slow (darktable caches initialize). Subsequent renders should be 1–3 seconds at preview sizes. If renders consistently exceed 10s on Apple Silicon, profile darktable directly: `darktable-cli --quiet <raw> <xmp> <out>`. The slowness is darktable, not Chemigram.

---

## See also

- [`cli-reference.md`](cli-reference.md) — every verb / flag / global option
- [`cli-output-schema.md`](cli-output-schema.md) — NDJSON event shapes for scripting
- [`cli-env-vars.md`](cli-env-vars.md) — env var reference
- [`vocabulary-patterns.md`](vocabulary-patterns.md) — vocabulary composition recipes
- [`tastes-quickstart.md`](tastes-quickstart.md) — first taste file in 5 minutes
- [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) — author your own primitives
- [`docs/getting-started.md`](../getting-started.md) — full install + first-session walkthrough
