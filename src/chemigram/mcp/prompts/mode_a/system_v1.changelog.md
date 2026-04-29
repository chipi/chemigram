# mode_a/system — version log

## v1 — 2026-04 (Phase 1 Slice 3)

Initial Mode A system prompt. Migrated from `docs/agent-prompt.md` (v0.1
draft). Establishes:

- The apprentice frame (bearings / opinions / limits)
- The propose-and-confirm discipline for taste-file and `notes.md` updates
- The action space: vocabulary primitives, masks, versioning, rendering
- Voice rules (direct, honest, no throat-clearing)
- Conditional masking guidance via `masker_available` context flag

Changes from `docs/agent-prompt.md`:

- `image_id` is now interpolated into the opening sentence
- Vocabulary count rendered as `{{ vocabulary_size }}` (was implicit)
- "Local adjustments" section is conditional on `masker_available` (Slice 4
  switches the flag on once a real masker provider lands)

Future versions append below; this file never gets edited in place per
ADR-043.
