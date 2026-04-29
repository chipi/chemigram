# mode_a/system — version log

## v2 — 2026-04-29 (Phase 1 Slice 6, v1.0.0)

Refinements based on v0.4.0 (masking real) and v0.5.0 (context real)
shipping. Mostly polish — the structure and apprentice frame are the
same; targeted edits where v1's prose was hedging or future-tense.

Specific changes vs v1:

1. **Drops the `{% if masker_available %}` conditional.** Masking is
   bundled (CoarseAgentProvider, ADR-058); every Mode A session has a
   masker. The "Local adjustments" section is now unconditional and
   names `generate_mask` / `regenerate_mask` directly. References
   `chemigram-masker-sam` as the production upgrade for pixel
   precision.
2. **`read_context` shape concretized.** v1 listed what gets loaded;
   v2 references the actual shape (`tastes.conflicts` field, recent
   gaps as part of context, notes summarization).
3. **`propose_taste_update` argument shape concretized.** v2 names the
   `category` enum (`"appearance" | "process" | "value"` per ADR-031)
   and the `file` default convention.
4. **New "Vocabulary gaps" section.** Documents the full RFC-013
   schema (intent, intent_category, missing_capability,
   operations_involved, vocabulary_used, satisfaction, notes). v1
   referenced `log_vocabulary_gap` as a 3-arg call; v2 reflects the
   richer shape and explains why it matters (cross-image aggregation
   later).
5. **End-of-session sequence updated.** v1 was order-only; v2 adds:
   "the engine has no end_session tool — you orchestrate via the
   existing tools" (per ADR-061). Adds `tag` as an optional step.
6. **Removes "future-tense" hedging.** Phrases like "if installed",
   "may be limited", "not yet implemented" trimmed where the v0.4/v0.5
   surface made them obsolete.

`masker_available` is kept in MANIFEST as an optional context key for
v1 backwards-compat; v2 ignores it.

## v1 — 2026-04 (Phase 1 Slice 3)

Initial Mode A system prompt. Migrated from `docs/agent-prompt.md` (v0.1
draft authored 2026-04 during Phase 0 / early Phase 1). Establishes:

- The apprentice frame (bearings / opinions / limits)
- The propose-and-confirm discipline for taste-file and `notes.md`
  updates
- The action space: vocabulary primitives, masks, versioning,
  rendering
- Voice rules (direct, honest, no throat-clearing)
- Conditional masking guidance via `masker_available` context flag

Future versions append below; this file never gets edited in place per
ADR-043.
