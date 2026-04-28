# ADR-043 — Jinja2 + filename-versioned templates as prompt format

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /components/prompts
> Related RFC · RFC-016

## Context

The agent's behavior depends on the system prompt loaded at session start. As prompts evolve, we need a format that supports clean diffs, append-only versioning, and a templating layer for the small amount of dynamic context (image_id, vocabulary_size, etc.) interpolated into otherwise-static prose. The reference pattern is `chipi/podcast_scraper`'s prompt store (its RFC-017): Jinja2 templates organized by `<provider>/<task>/<version>.j2`.

Prompts in chemigram are mostly system prompts (loaded once per session), not per-call templates, but the same versioning + templating discipline applies — a prompt change is a behavior change, and behavior changes need explicit versions in the source tree.

## Decision

Prompt templates use **Jinja2** as the templating engine. Each template lives at a versioned filename of the form `<task>_v<N>.j2`. Each version ships with a sibling `<task>_v<N>.changelog.md` documenting what changed and why. Once a version is shipped, that file is **append-only** — never edited.

Layout:

```
src/chemigram/mcp/prompts/
├── mode_a/
│   ├── system_v1.j2
│   ├── system_v1.changelog.md
│   └── (later: system_v2.j2 + sibling changelog)
├── mode_b/
│   ├── system_v1.j2
│   ├── plan_v1.j2
│   └── *.changelog.md
└── helpers/
    └── *.j2
```

## Rationale

- **Jinja2's `{{ var }}` syntax safely coexists with literal `{` / `}` in prompts.** F-strings break on JSON examples, XML tags, and any prompt that needs to show literal braces. Jinja2 doesn't.
- **Already in Marko's other projects** (`podcast_scraper`). Cross-project consistency, no new mental model.
- **Templating power earned, not paid for.** Most prompts will use only variable interpolation. Jinja2's loops/conditionals are available if a prompt ever needs to vary structure (e.g., conditional inclusion of a vocabulary reference). Doesn't cost anything to have.
- **Filename-level versioning is grep-able.** `ls prompts/mode_a/` shows the version history at a glance. Code review of "which version ships" is one-line clear.
- **Append-only files match ADR-style discipline.** Old versions stay in the source tree as the historical record. New iterations ship as new files. No silent in-place edits that obscure what changed.
- **Sibling changelog files keep history human-readable.** A `.changelog.md` next to `system_v2.j2` answers "why v2?" without requiring git archaeology.

## Alternatives considered

- **Plain Markdown with f-string substitution:** breaks on `{` literals, no real templating. Rejected.
- **Multi-line string constants in Python source:** entangles prompt diffs with code diffs, no clean per-version history, painful to review. The standard pattern for early projects but doesn't scale.
- **JSON config with prompt-as-string:** JSON-encoded multiline prose is a maintenance disaster (escaping, no syntax highlighting). Rejected.
- **A custom templating engine:** doesn't earn its complexity. Jinja2 is the well-understood standard.
- **Path-style versioning (`prompts/mode_a/system/v1.j2`):** considered but adds a directory level for no real benefit; filename versioning is flatter and clearer.
- **SemVer per template (`system_v1.2.3.j2`):** unnecessary granularity. Integer versions are enough; if a "minor" change ships, just bump to the next integer.

## Consequences

Positive:

- Append-only history visible directly in the source tree
- Safe templating that handles arbitrary prompt content
- Cross-project consistency with other Marko projects
- Clean PR diffs (new file, new changelog) when shipping a new version

Negative:

- Adds a `Jinja2` runtime dependency (small; ~150KB; mature)
- Two files per version (template + changelog) — slight overhead, mitigated by changelog being one short paragraph
- Old versions stay in the tree forever (small repo-size cost; acceptable)

## Implementation notes

`pyproject.toml` adds `Jinja2>=3.1` to runtime dependencies. Templates use Jinja2's standard syntax. Each template includes a top-of-file Jinja2 comment block declaring expected context variables (the canonical declaration lives in `MANIFEST.toml`; the comment is a quick reference for template authors). Changelog format is a 1–3 paragraph markdown file; no rigid schema.
