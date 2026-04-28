# ADR-034 — Build system and package layout

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack, /components
> Related RFC · None (engineering choice)

## Context

Chemigram is a Python package distributed for local install. The choice of build backend, source layout, and distribution boundary affects how contributors set up the project, how releases are made, how sibling projects (`chemigram-vocabulary-starter`, `chemigram-masker-sam`) integrate, and the long-term maintenance cost of the build infrastructure.

The components that need packaging are `chemigram_core` (engine, no AI dependencies) and `chemigram_mcp` (MCP server adapter). The relationship is tight — the MCP server is the only interface a typical user invokes, but `chemigram_core` is also usable standalone (as a library) for testing, scripting, or alternative agent integrations.

## Decision

Use a single PyPI distribution `chemigram` built with **`hatchling`** as the PEP 517 build backend, declared entirely in `pyproject.toml`. Source layout is **src/-style** with two top-level modules:

```
chemigram/
├── pyproject.toml
├── src/
│   └── chemigram/
│       ├── core/             # engine, no AI deps
│       └── mcp/              # MCP server adapter
└── tests/
```

The package imports as `chemigram.core` and `chemigram.mcp`. Sibling projects (`chemigram-vocabulary-starter`, `chemigram-masker-sam`) are separate distributions in separate repos.

## Rationale

- **`pyproject.toml` is the modern standard** (PEP 517/518/621). All metadata, build config, and tool config in one file.
- **Hatchling is the lightest-weight modern build backend** — no `setup.py`, minimal config, written by the same author as `hatch`. Avoids setuptools' verbosity and Poetry's wrapper-on-top-of-standards approach.
- **`src/`-layout prevents accidental imports** of the project's own code during testing — the package must be properly installed (typically as `-e` for development) for tests to find it. This catches packaging bugs early.
- **Single distribution for `core` + `mcp`** matches v1 reality. The two components are tightly coupled — there's no serious use case for `chemigram_core` without `chemigram_mcp` in v1. Splitting them into separate distributions adds release-coordination cost without benefit.
- **Sibling projects in separate distributions** keeps optional capabilities (e.g., SAM masking) out of the engine's dependency tree, supporting BYOA (ADR-007).

## Alternatives considered

- **Setuptools backend:** mature and bulletproof but more verbose configuration; `hatchling` is simpler for a project of this size.
- **Poetry:** decent UX but introduces its own ecosystem (poetry.lock, poetry-specific commands) on top of standards. The wrapper isn't worth it for a single-package project.
- **Flit:** simpler than hatchling but less flexible for future build customization.
- **Two distributions (`chemigram-core` + `chemigram-mcp`):** considered but rejected for v1 — coordination cost, no use case driving the split.
- **Flat layout (no `src/`):** simpler at a glance but allows accidentally importing the in-repo source instead of the installed package; src/-layout is the modern best practice.
- **Namespace packages:** considered for sibling-project integration but adds complexity; flat package boundaries are simpler.

## Consequences

Positive:
- Single source of truth for build config (`pyproject.toml`)
- Lean build setup; minimal maintenance
- Clean separation between engine and MCP layer at the module level
- Sibling projects can integrate as separate distributions cleanly

Negative:
- `chemigram_core` and `chemigram_mcp` versions move in lockstep (acceptable trade-off; they don't release independently)
- `src/`-layout requires `pip install -e .` for development, slightly less convenient than flat layout (mitigation: documented in CONTRIBUTING.md)

## Implementation notes

`pyproject.toml` declares `[build-system] requires = ["hatchling"]; build-backend = "hatchling.build"`. The `[tool.hatch.build]` section names `src/chemigram` as the source root. Console scripts (e.g., `chemigram-mcp` for the MCP entry point) are declared under `[project.scripts]`.
