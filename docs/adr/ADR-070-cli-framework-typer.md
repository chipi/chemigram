# ADR-070 — CLI framework: Typer

> Status · Accepted; partially superseded by ADR-076 (2026-05-03) — the `masks` sub-command group (list/generate/regenerate/tag/invalidate) was removed in v1.5.0; the CLI now has 1 sub-command group (`vocab`), not 2. Typer remains the framework choice and the rest of this ADR's reasoning stands.
> Date · 2026-05-03
> TA anchor ·/components/cli
> Related RFC · RFC-020 (closes here)

## Context

Implementing the CLI (per ADR-069) requires choosing a framework. The candidates were:

- `argparse` — Python standard library, zero dependency
- `click` — widely used, decorator-based
- `typer` — built on Click, annotation-driven
- Custom — hand-rolled argument parsing

The command surface is moderate: 22 verbs, 2 sub-command groups (`vocab`, `masks`), ~3 options per command on average, 5 global options shared across all verbs. This is well beyond where argparse is pleasant and well within Click/Typer territory.

## Decision

**Use Typer.** Pinned to `typer>=0.12` in `pyproject.toml`; uv.lock pins the exact version for CI reproducibility.

## Rationale

### Against argparse

argparse requires explicit `add_argument` calls for every parameter. For a 22-verb surface with shared global options and grouped subcommands, that's roughly 100 lines of repetitive setup code that type annotations plus Typer generate automatically. argparse's error messages and help formatting are also weaker.

The zero-dependency argument is real but not decisive: Typer brings Click + Rich transitively, both stable and widely used, and adding them does not meaningfully increase supply-chain risk for a project with darktable as a hard dependency.

### Click vs Typer

Click is the foundation; Typer adds:

1. **Type annotations drive the CLI.** Parameters are declared as Python function arguments with type hints. No separate `add_argument` calls. For a 22-verb surface this reduces boilerplate by roughly 60%.
2. **Auto-generated `--help`** from docstrings. No separate help strings to maintain.
3. **`typer.testing.CliRunner`** (from Click) for synchronous, deterministic testing — no subprocess required for integration tests.
4. **Escape hatch to raw Click.** Typer exposes the underlying Click command/group objects when needed. If Typer's abstractions become a constraint, the migration to raw Click is mechanical.

### Against hand-rolled

Not seriously considered for a 22-verb surface. The maintenance cost of a custom parser grows with the number of commands.

## Consequences

**Positive:**

- Annotation-driven CLI definition is concise and maintainable.
- `CliRunner` made the test suite straightforward — 80+ integration tests written without subprocess overhead.
- Click's error handling is robust and covers edge cases (missing args, wrong types, ambiguous abbreviations) without us writing them.
- Auto-generated `chemigram --help` and `chemigram <verb> --help` are accurate and complete.

**Negative:**

- **Typer dependency.** Adds Typer + Click + Rich to the dependency tree. Acceptable: these are stable, widely used, and their combined footprint is small.
- **`typer.Option(...)` as default argument value triggers ruff B008** — the canonical Typer idiom. Suppressed via per-file ignore in `pyproject.toml` for `chemigram.cli.main` and `chemigram.cli.commands.*`.
- **Mypy untyped-decorator warning** on `@app.command` — Typer's decorators don't type-narrow the wrapped function. Suppressed via per-module mypy override `disallow_untyped_decorators = false` for `chemigram.cli.*`.
- **CliRunner API has shifted across Click versions.** Click 8.2 removed `mix_stderr` from `CliRunner.__init__`; integration tests use the newer API (default-separated stderr). uv.lock is the version-pinning source of truth.

## Alternatives considered

See "Rationale" above for argparse and hand-rolled rejections. Click directly was considered as a fallback if Typer's abstractions became a problem; not needed.
