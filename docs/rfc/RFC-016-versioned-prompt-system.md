# RFC-016 — Versioned prompt system

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /components/prompts
> Related ADRs · ADR-043, ADR-044, ADR-045
> Related PRDs · PRD-001 (Mode A), PRD-002 (Mode B)

## Why this is an RFC

The agent's behavior in both Mode A and Mode B depends critically on the system prompt it loads. As the project evolves, that prompt will change: the apprentice framing will tighten, propose-and-confirm protocols will get refined, mode B's planning prompt will be tuned against real outputs. Without a versioning discipline, prompt edits will silently change agent behavior between commits, making session quality and bug investigation impossible to track. The decision is structural — where prompts live, how they're versioned, how they're loaded — and it touches every future prompt-shipping PR. That's RFC-shaped, not "decide as we go."

The reference architecture is `chipi/podcast_scraper`'s RFC-017 (the `PromptStore` pattern), adapted for chemigram's interactive-session model rather than one-shot LLM calls.

## Background

The agent prompt currently exists as a v0.1 draft in `docs/agent-prompt.md` (no formal versioning, no loading mechanism, no separation between authoring artifact and runtime artifact). The prompt is referenced throughout the project's design docs but has no canonical home in the source tree. Slice 3 of Phase 1 ships the MCP server, at which point the prompt becomes load-bearing and informal handling stops being acceptable.

Two related problems sit alongside the prompt system:

1. **Mode B's autonomy** depends on multiple coordinated prompts (plan, evaluate, refine), not one. The system needs to handle prompt families, not just single templates.
2. **Provider-specific tuning** may eventually be needed (Claude vs GPT vs local models behave differently). The system should accommodate that without forcing it now.

## Problem

What we need from a prompt system:

- **Append-only versioning** — once a prompt ships, that version is frozen. New iterations go to new files. No silent changes.
- **A single source of truth** for which version is currently active. Reviewers see "this PR bumps `mode_a/system` from v1 to v2" cleanly.
- **Templates with explicit context** — variables interpolated into the prompt should be declared, not implicit.
- **Multiple modes and tasks** — Mode A system prompt, Mode B's plan/evaluate/refine prompts, helper prompts (taste-consistency checks, vocabulary-gap framings).
- **A loading mechanism** that decouples runtime callers from filesystem layout.
- **Future-readiness for provider forks** without committing to per-provider prompts on day one.
- **Reasonable interop with eval** — a scriptable way to point the eval harness at a specific prompt version (RFC-017).

What we want to avoid:

- Prompts as multi-line string constants in code (review burden, no diff history per version, mixing concerns).
- A "latest version" abstraction that lets prompts silently change between commits.
- Templating power we don't need (a full DSL when simple variable substitution works).
- Provider-specific prompt forks before there's evidence one is needed.

## Proposal

### Directory layout

Prompts live at `src/chemigram/mcp/prompts/` — colocated with the MCP server because that's where they're loaded. Subdirectories partition by mode and concern:

```
src/chemigram/mcp/prompts/
├── store.py                            # PromptStore class
├── MANIFEST.toml                       # active versions + context schemas
├── mode_a/
│   ├── system_v1.j2                    # Mode A system prompt v1
│   ├── system_v1.changelog.md
│   └── (later: system_v2.j2 + changelog when v2 ships)
├── mode_b/
│   ├── system_v1.j2                    # Mode B system prompt
│   ├── plan_v1.j2                      # candidate generation
│   ├── evaluate_v1.j2                  # self-evaluation against criteria
│   ├── refine_v1.j2                    # iteration after evaluation
│   └── *.changelog.md
└── helpers/
    ├── taste_proposal_v1.j2            # framing for "should this become a taste.md entry?"
    ├── gap_framing_v1.j2               # framing for vocabulary-gap descriptions
    └── *.changelog.md
```

Per-version conventions:

- **Filename carries the version.** `system_v1.j2`, `system_v2.j2`. Append-only; never edit a shipped version.
- **Each version has a sibling changelog** — `system_v1.changelog.md` documents what changed and why, in 1–3 short paragraphs. Lives next to the template.
- **Templates use Jinja2** (per ADR-043). Why Jinja2: matches Marko's existing pattern in `podcast_scraper`, full enough for any reasonable prompt complexity, lightweight dependency.

### MANIFEST.toml — the active-version registry

A single TOML file at `src/chemigram/mcp/prompts/MANIFEST.toml` declares which version of each template is currently active and what context variables each template accepts:

```toml
# MANIFEST.toml — active prompt versions and their context schemas
# Bumping a version here is the unit of "shipping a new prompt."
# This file is THE source of truth; templates are not loaded by directory scan.

[prompts."mode_a/system"]
active = "v1"
context_required = ["vocabulary_size", "image_id"]
context_optional = ["masker_available"]

[prompts."mode_b/system"]
active = "v1"
context_required = ["vocabulary_size"]
context_optional = []

[prompts."mode_b/plan"]
active = "v1"
context_required = ["brief_text", "taste_text", "candidate_count"]
context_optional = []

[prompts."mode_b/evaluate"]
active = "v1"
context_required = ["brief_text", "taste_text", "candidate"]
context_optional = []

[prompts."helpers/taste_proposal"]
active = "v1"
context_required = ["proposed_text", "session_context"]
context_optional = []
```

Reviewers reading a PR see a clean diff like "`mode_a/system` bumped from v1 to v2" alongside the new template file. There's no ambiguity about what version ships in any given commit.

### PromptStore API

The runtime interface is intentionally small:

```python
from chemigram.mcp.prompts import PromptStore

store = PromptStore()

# Load active version of mode_a/system; render with required context
prompt = store.render(
    "mode_a/system",
    context={"vocabulary_size": 31, "image_id": "iguana_galapagos_2024_03_14"},
)

# Explicit version override (for eval harness — pinning a version)
prompt = store.render(
    "mode_a/system",
    version="v2",
    context={...},
)

# Inspect: which version is currently active?
store.active_version("mode_a/system")  # → "v1"

# Inspect: what context does this template expect?
store.context_schema("mode_a/system")
# → {"required": ["vocabulary_size", "image_id"], "optional": ["masker_available"]}
```

Behavior:

- `render()` without `version=` uses the active version per MANIFEST.
- Missing required context → explicit `PromptContextError` at render time.
- Unknown extra context → ignored (loose; logged at debug level).
- Unknown template path → `PromptNotFoundError`.

This is locked in ADR-044.

### Versioning is independent of package SemVer

Prompt versions (v1, v2, …) are independent integers. Bumping `mode_a/system` from v1 to v2 does **not** bump the chemigram package version. The package's CHANGELOG.md notes prompt-version changes when they ship in a release. Rationale lives in ADR-045.

### Provider-specific tuning (deferred)

The system supports provider forks via filename suffix when needed:

```
mode_a/
├── system_v2.j2                # default (canonical)
├── system_v2_claude.j2         # Claude-tuned variant
└── system_v2_gpt.j2            # GPT-tuned variant
```

PromptStore.render() optionally takes a `provider=` argument that selects the suffix. The default (no suffix) is canonical.

**Forks are NOT introduced in v1.** Until evidence shows a real divergence in prompt effectiveness between providers, all prompts ship as the unsuffixed default. Forks earn their cost when there's evidence; speculation about which provider needs what doesn't.

### How this connects to eval (RFC-017)

The eval harness uses PromptStore's explicit-version mode (`store.render("mode_b/plan", version="v3", ...)`) to run autonomous Mode B against pinned prompt versions. Eval run manifests record which version was used (per ADR-047), enabling comparisons like "did prompt v3 beat v2 on golden_v1 dataset?"

This decoupling — versions as first-class identities, not "whatever's in the file right now" — is what makes auto-research possible in the first place.

## Alternatives considered

### Prompts as Python multi-line constants

```python
MODE_A_SYSTEM_PROMPT = """You are an apprentice photo editor..."""
```

**Why rejected.** No versioning at the file level — diffs entangle prompt changes with code changes. Reviewing "this PR changed the prompt" requires reading multi-line string diffs in the middle of a code file. No clean home for changelog entries. Provider forks become if/else branches in code. Standard pattern for early projects, but doesn't scale past one prompt.

### Markdown templates with f-string substitution

```python
prompt = open("prompts/mode_a/system_v1.md").read().format(image_id=...)
```

**Why rejected.** F-strings break on `{` literally appearing in the prompt (which happens — JSON examples, XML tag names). Jinja2's `{{ var }}` syntax is safer. Plus Jinja2 gives loops/conditionals if a prompt ever needs them.

### JSON config with prompt-as-string fields

```json
{ "mode_a_system": { "version": "v1", "text": "You are an apprentice..." } }
```

**Why rejected.** JSON-encoded multiline prose is a maintenance disaster — escaping, no syntax highlighting, painful diffs. Templates as files in their natural format wins.

### Latest-version magic (no MANIFEST.toml)

PromptStore scans the directory and picks the highest-numbered file.

**Why rejected.** Silently active versions are exactly the bug we're preventing. Adding `system_v3.j2` shouldn't ship v3 to production until the MANIFEST is updated.

### A non-Jinja2 templating engine (string.Template, custom)

**Why rejected.** Jinja2 is the existing convention in Marko's other projects. Bringing a different engine for a small win is friction. Jinja2's dependency footprint is small.

## Open questions

1. **Should provider forks be allowed at v1, or strictly deferred?** Proposal says deferred; the ADR locks it. Is that too rigid? *Answer for now:* deferred. Reopen if Phase 1 evidence demands.
2. **Where do per-tool MCP-level descriptions live?** MCP tool descriptions are part of the schema sent to agents but aren't really "prompts." They live in code (decorators on tool implementations), not in this prompt directory. Worth being explicit so confusion doesn't arise.
3. **Do helpers/ prompts live here or somewhere else?** They're used by `chemigram.core` (e.g., taste-consistency checks called by the engine), not just by the MCP server. Keeping them under `chemigram.mcp.prompts` is conceptually wrong. Defer to ADR-044's "PromptStore is in `chemigram.mcp.prompts`, but `chemigram.core` may also depend on it" — slight layering compromise we accept for v1.
4. **Migration path for the existing `docs/agent-prompt.md` v0.1 draft.** It moves to `src/chemigram/mcp/prompts/mode_a/system_v1.j2` when Slice 3 starts. The doc gets a stub redirect note; the canonical home becomes the source tree.

## Decision summary

If accepted, the following ADRs lock the structural pieces:

- **ADR-043** — Jinja2 templates, filename-versioned (`<task>_v<N>.j2`), changelog sibling files
- **ADR-044** — `PromptStore` API and `MANIFEST.toml` as active-version registry
- **ADR-045** — Prompt versioning is independent of package SemVer

The eval harness that consumes this system is RFC-017.

---

*RFC-016 · Accepted 2026-04-28*
