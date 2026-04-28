# ADR-044 — PromptStore API and MANIFEST.toml as active-version registry

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /components/prompts
> Related RFC · RFC-016
> Related ADR · ADR-043

## Context

Templates exist on the filesystem at versioned paths (per ADR-043). Runtime callers — the MCP server loading the Mode A system prompt at session start, the eval harness pinning a specific Mode B version — need a way to load a prompt by logical name (`"mode_a/system"`) without coupling to the directory layout. They also need a single source of truth for which version is "active" — i.e., which version ships in the current commit.

Without a registry, "which version is active" becomes implicit (latest file? convention? code constant somewhere?). All three options are bad. With a registry, a PR review sees "this PR bumps `mode_a/system` from v1 to v2" cleanly.

## Decision

**Active versions are declared in `src/chemigram/mcp/prompts/MANIFEST.toml`.** This file is the single source of truth. Templates are not loaded by directory scan or "latest version" inference — only by lookup against MANIFEST.

The runtime interface is a `PromptStore` class in `src/chemigram/mcp/prompts/store.py`:

```python
class PromptStore:
    def render(
        self,
        path: str,                          # e.g. "mode_a/system"
        context: dict[str, Any],
        version: str | None = None,         # default: active version per MANIFEST
        provider: str | None = None,        # default: no suffix (canonical)
    ) -> str:
        """Render a prompt template. Raises PromptContextError on missing required vars."""
        ...

    def active_version(self, path: str) -> str:
        """Return the currently-active version for a template path."""
        ...

    def context_schema(self, path: str) -> dict[str, list[str]]:
        """Return {'required': [...], 'optional': [...]} for a template."""
        ...

    def list_templates(self) -> list[str]:
        """Return all template paths declared in MANIFEST."""
        ...
```

`MANIFEST.toml` format:

```toml
[prompts."mode_a/system"]
active = "v1"
context_required = ["vocabulary_size", "image_id"]
context_optional = ["masker_available"]

[prompts."mode_b/plan"]
active = "v1"
context_required = ["brief_text", "taste_text", "candidate_count"]
context_optional = []
```

## Rationale

- **MANIFEST.toml as source of truth makes "what version ships" a one-line PR diff.** No scattered code constants, no implicit conventions. The reviewer sees `active = "v2"` change and knows exactly what shipped.
- **TOML (not JSON or YAML) for consistency** with chemigram's other config files (ADR-028).
- **Context schemas in MANIFEST give structure to context variables.** Without this, every render() is a guess about what context the template wants. With it, missing vars surface as explicit errors at render time, not as silently empty strings in the prompt.
- **PromptStore as a class (not free functions) supports test injection.** Tests construct a `PromptStore(root="tests/fixtures/prompts/")` to isolate from the real templates.
- **Explicit `version=` on render() supports eval harness pinning.** RFC-017's auto-research workflow pins prompt versions explicitly to make runs comparable. This ADR makes that supported, not retrofitted.
- **`provider=` deferred but designed in.** Provider-specific tuning (Claude vs GPT vs local) isn't shipped at v1; the API accommodates it without forcing it.

## Alternatives considered

- **Active versions in code (a Python constant `ACTIVE_VERSIONS = {...}`):** considered. Equally explicit; reviewers see the diff. Rejected because TOML keeps prompts as a coherent self-contained area (templates + changelogs + manifest all in `prompts/`); the constant in code splits the concern.
- **Active versions inferred from "latest filename":** silently changing prompts is the bug we're preventing. Rejected.
- **No active-version concept; callers pass version explicitly always:** brittle. Every caller has to know which version to use. Rejected; explicit version remains an option for eval, but day-to-day callers (the MCP server) just say `render("mode_a/system")` and get the current canonical.
- **YAML for MANIFEST:** YAML's whitespace-sensitivity is a footgun for a config that may grow. TOML matches existing project conventions (ADR-028).
- **Per-template MANIFEST files:** considered (one MANIFEST.toml per directory). Rejected because the global view is more useful for reviewing "what versions are active across the whole prompt set."

## Consequences

Positive:

- "What version ships" is grep-able in one file
- Context schemas catch missing-variable bugs at render time
- Explicit version selection supports eval pinning without coupling
- Test injection works cleanly via `PromptStore(root=...)`

Negative:

- A bit more ceremony than "just load the file" (justified by the version-clarity benefit)
- MANIFEST.toml and template filenames must stay in sync (validated by a CI check; mismatch fails build)

## Implementation notes

- `PromptStore` lives at `src/chemigram/mcp/prompts/store.py`. It loads MANIFEST.toml at construction; templates are loaded lazily on first `render()`. Templates are cached per-process.
- Errors are explicit: `PromptNotFoundError` (template path not in MANIFEST), `PromptVersionNotFoundError` (version requested but file missing), `PromptContextError` (required context variable missing).
- A CI check (`scripts/verify-prompts.sh`) validates that every `<task>_v<N>.j2` file has a corresponding MANIFEST entry, that every active version's template file exists, and that every template has a sibling `.changelog.md`.
- `chemigram.core` may import PromptStore for engine-side helpers (taste-consistency checks, gap framings). The slight layering compromise (`chemigram.mcp.prompts` is technically MCP-layer but used by core) is documented; refactor if the dependency direction becomes painful.
