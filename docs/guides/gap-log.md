# Reading the vocabulary gap-log

> The agent records missing-primitive observations to per-image `vocabulary_gaps.jsonl` files. This guide covers the read-side tooling — how to surface patterns across sessions, rank gaps by photographic frequency, and clean up after addressing them.

## Background

When the photo agent (Mode A loop) reaches for a primitive that doesn't exist in the loaded vocabulary, it calls `log_vocabulary_gap` (MCP) or `chemigram log-vocabulary-gap` (CLI) to record what it wanted, what was missing, and how it worked around it. Each call appends one JSON record to `<workspace>/<image_id>/vocabulary_gaps.jsonl`.

Per CLAUDE.md, this is **the load-bearing feedback mechanism for Phase 2** (vocabulary maturation). The vocabulary grows because real sessions surface real gaps; the photographer (or maintainer) reads the log periodically and authors missing primitives.

Per ADR-081, this surface also feeds the eventual Tier 3 → Tier 2 promotion threshold (deferred to the multi-photographer review phase).

## Commands

```sh
chemigram gap-log list   [--since 7d] [--image <id>] [--module <name>]
chemigram gap-log rank   [--since 7d] [--image <id>] [--top 20]
chemigram gap-log show   <image_id>
chemigram gap-log clear  <image_id> [--yes]
```

All commands accept the global `--workspace` flag (defaults to `~/Pictures/Chemigram`) and `--json` for streaming-friendly machine-readable output.

### `gap-log list` — flat enumeration

Walks the workspace, opens each per-image gap log, returns the union of all gaps newest-first. Useful as a starting point.

```sh
# Everything across all images
chemigram gap-log list

# Last week's gaps only
chemigram gap-log list --since 7d

# All gaps that mention the lens module (matches missing_capability,
# operations_involved, or description)
chemigram gap-log list --module lens

# Combine
chemigram gap-log list --since 30d --module hazeremoval
```

`--since` accepts ISO 8601 (`2026-05-01`, `2026-05-01T12:00:00Z`) or relative (`7d`, `2w`, `24h`, `30m`).

### `gap-log rank` — frequency-ranked patterns

The pattern-finding view. Aggregates gaps by `(description, missing_capability)` and sorts by count descending. Use this to decide which Tier 3 module to promote next, or which primitive to author next.

```sh
# Top 20 most frequent gaps across all images, ever
chemigram gap-log rank

# Top 5 gaps from the last 30 days
chemigram gap-log rank --since 30d --top 5

# Drop the limit
chemigram gap-log rank --top 0
```

Output is one `gap_rank` event per row, plus a result summary with `unique_patterns`, `total_gaps`, and `images_scanned`.

### `gap-log show` — full view of one image

Dump all gaps for one image, chronological (oldest first). Useful when reviewing a single session's gap output.

```sh
chemigram gap-log show DSCF1234
```

### `gap-log clear` — opt-in cleanup

After reviewing gaps for an image and either authoring missing primitives or deciding they don't need addressing, delete the gap log to keep future `list` / `rank` queries focused.

```sh
# Confirms before deleting
chemigram gap-log clear DSCF1234

# Skip the confirmation
chemigram gap-log clear DSCF1234 --yes
```

The file is deleted, not truncated — a fresh empty file is created on the next `log_vocabulary_gap` call.

## Workflow recipes

### "What's the next primitive I should author?"

```sh
chemigram gap-log rank --since 30d --top 10
```

The top rows tell you which gaps are surfacing most frequently. Cross-reference against the capability survey § 12 module catalog to see which darktable module to author against.

### "Has this image's session pulled cleanly?"

```sh
chemigram gap-log show <image_id>
```

If you see no gaps, the agent didn't reach for anything missing — vocabulary served the session. If you see gaps, those are candidates for authoring or for compositional looks.

### "Am I done with this image's gaps?"

```sh
chemigram gap-log clear <image_id>
```

Clean slate; subsequent sessions on the image start fresh.

### Aggregating across images for a Tier 3 → Tier 2 case

```sh
chemigram --json gap-log rank --since 90d --top 0 | jq 'select(.event == "gap_rank") | {count, capability: .missing_capability}' | sort
```

Per ADR-081, the formal threshold for Tier 3 → Tier 2 promotion (multi-photographer + multi-session evidence) is deferred. Until then, any session-driven gap-log signal is suggestive but not load-bearing for promotion decisions; the gating is "the project decides it's worth the decoder + tests + manifest entry" per the ADR.

## See also

- ADR-060 — vocabulary-gap surfacing format
- RFC-013 — vocabulary-gap surfacing (closed by ADR-060)
- ADR-081 — parameterization tiering policy
- CLAUDE.md — Phase 2 framing
