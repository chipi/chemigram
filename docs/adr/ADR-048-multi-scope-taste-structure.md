# ADR-048 — Multi-scope taste structure

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /components/context
> Related ADR · ADR-030 (three-tier context)
> Related RFC · RFC-011 (agent context loading) — pending; will incorporate this

## Context

ADR-030 established the three-tier context model (taste / brief / notes). The implicit assumption was that tier 1 (taste) is a single file. In practice, photographers' preferences are not monolithic — preferences for portrait work (skin tones, eye sharpening, soft light handling) diverge meaningfully from preferences for landscape (vivid skies, deep contrast, broad clarity) or underwater work (slate-blue water, recover red subtly, lift shadows on subjects). A single `taste.md` either stays small and shallow (gaps surface immediately) or grows into a contradictory grab-bag where "I want quiet, restrained looks" and "I want vivid pop" coexist in different sections without context.

The first proposed example (the year-of-use `taste.md` draft in `examples/templates/`) demonstrated the problem at ~25 entries: water-color preferences mixed with cross-genre workflow notes mixed with marine-animal masking patterns. At 100 entries across multiple genres, the file is unworkable.

## Decision

**Tastes are multi-file, scoped by genre, with explicit per-image declaration.** The single `taste.md` is replaced by a `tastes/` directory:

```
~/.chemigram/tastes/                   # location settled in RFC-011
├── _default.md                        # universal — always loads
├── portrait.md                        # genre-specific
├── landscape.md
├── underwater.md
├── wildlife.md
└── street.md
```

Loading rules:

1. **`_default.md` always loads** at session start. Holds universal preferences (workflow notes, communication style, cross-genre aversions, settings that apply regardless of subject).
2. **Genre files load only when `brief.md` declares them.** The brief includes a `Tastes` field listing which genre files apply to the current image, e.g. `**Tastes:** underwater, wildlife`. Files not declared do not load.
3. **No automatic inference.** The agent does not guess which tastes apply based on subject metadata. The photographer declares; the agent loads what was declared. This v1 default may be revisited if evidence accumulates that explicit declaration is friction.
4. **Loading order is `_default.md` first, then genre files in the declaration order.** When a brief declares `["underwater", "wildlife"]`, the agent loads `_default.md`, then `underwater.md`, then `wildlife.md`.

Conflict resolution:

- **Genre overrides default** for direct contradictions (most-specific-wins).
- **Multiple genres are additive** until they contradict each other; if they do, the agent surfaces the conflict to the photographer rather than silently picking. ("Your `underwater.md` says X but your `wildlife.md` says not-X — which applies for this image?")
- **Within a single file**, newer dated entries override older entries when they conflict (already established convention).

Tool surface implications:

- `propose_taste_update` and `confirm_taste_update` (per ADR-031) take a `file` argument. The agent declares which taste file the proposed entry belongs to. Defaults to the most-relevant currently-loaded genre file; falls back to `_default.md` for cross-genre observations.

## Rationale

- **Aligns with how photographers actually think.** Portrait vs landscape vs underwater are distinct mental modes with mostly-independent preferences. Splitting the file matches the cognitive boundaries.
- **Prevents internal contradictions.** A photographer can hold both "I want vivid color in landscapes" and "I want quiet desaturated water" without those entries fighting in the same file.
- **Scales to long use.** 100 taste entries split across 5 files (averaging 20 each) is manageable; 100 in one file isn't.
- **Explicit declaration prevents silent misapplication.** The "wrong taste applied silently" failure mode (where the agent picked landscape preferences for an underwater shot) is much worse than the friction cost of one declaration line per brief.
- **Preserves ADR-030's three-tier model.** ADR-030's locked decision was the *tiers* (cross-image, per-image, session-log), not files-per-tier. Multi-file tastes are still a single tier — they all populate tier 1.
- **Growable organically.** A photographer who works only underwater starts with `_default.md` + `underwater.md`. They add `wildlife.md` when they start shooting birds. The structure accommodates growth without enforcing it.

## Alternatives considered

- **Single `taste.md`** (status quo before this ADR): doesn't scale, mixes contradictions, doesn't match how photographers think. Rejected.
- **Tags within a single file** (e.g., `[underwater]` prefix on each entry, agent filters): authoring is harder (need to remember the tag); reading is harder (mixed-genre file remains busy); doesn't really solve the "100 entries" problem. Rejected.
- **Auto-inference from brief metadata** (e.g., subject = "marine iguana" → load `underwater.md` + `wildlife.md`): fragile, silent failure mode is the worst kind. Defer until evidence shows explicit declaration is real friction. Rejected for v1.
- **Hierarchical taste tree** (`tastes/wildlife/birds.md`, `tastes/underwater/pelagic.md`): premature. Flat structure is enough until evidence for hierarchy. Rejected for v1.
- **Per-image override files** (a `taste-override.md` next to brief.md for one-off preferences): conflates per-image notes (`notes.md`) with cross-image preferences. Rejected.

## Consequences

Positive:

- Tastes scale with use without becoming unmanageable
- Internal contradictions become impossible by structure (different preferences live in different files)
- Photographers can declare scope explicitly per image
- Conflict surfacing makes contradictions visible rather than silent

Negative:

- Per-brief declaration adds one small line of friction (mitigated: usually a 2-3-word list, e.g., `underwater, wildlife`)
- Maintaining multiple files takes slightly more discipline (mitigated: each file stays small and focused, easier to maintain than one giant file)
- The `read_context` tool now opens N+1 files (1 default + N declared genres) instead of 1 (small overhead; tastes are small markdown files)
- Tool surface changes: `propose_taste_update` takes a `file` argument (a small change, in scope)

## Implementation notes

- Filesystem layout for `tastes/` is locked here; the parent location (`~/.chemigram/tastes/` vs `~/Pictures/Chemigram/_global/tastes/` vs other) is settled by RFC-011 when written.
- File naming convention: `{genre}.md`. The `_default.md` name uses a leading underscore to signal "special / always applies" and to sort first in `ls`.
- Missing files: if `brief.md` declares a genre that doesn't exist as a file, the agent logs a warning and continues with what it has. Doesn't error.
- The `examples/templates/tastes/` directory ships a worked example: `_default.md` + `underwater.md` + `wildlife.md`, threaded through the iguana brief.
- ADR-030 is not superseded; it remains the source of truth for the three-tier model. ADR-048 extends it by clarifying tier 1's structure.
