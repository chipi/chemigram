# Mode A system_v3 — changelog

## v3 — 2026-05-02 (Phase 1.2 / v1.2.0 prep)

- **New context key: `vocabulary_packs`** (`list[str]`). The agent now
  knows which packs are loaded — `["starter"]` for the minimal default,
  `["starter", "expressive-baseline"]` for the v1.2.0 default. Lets the
  prompt explain pack composition + role of each pack to the agent.
- **New section: "Navigating the vocabulary."** Explicit guidance on
  `list_vocabulary` filter use (`layer`, `tags`) for vocabularies of
  ~40 entries. The v2 prompt didn't address scaling beyond ~5 entries;
  v3 tells the agent to filter-first, then read descriptions.
- **No structural changes to other sections.** The propose/confirm
  flow, masking, vocabulary gaps, and end-of-session orchestration
  carry forward verbatim from v2.

Backwards-compat: callers that pass only `vocabulary_size` + `image_id`
(v2's required keys) get a Jinja `UndefinedError` for
`vocabulary_packs`. Required-context-keys updates per ADR-044 in
`MANIFEST.toml`.

## v2 — 2026-04-29 (Phase 1 Slice 6, v1.0.0)

(See system_v2.changelog.md.)

## v1 — pre-v1.0.0

(See system_v1.j2 for the original Mode A prompt — pre-context-layer.)
