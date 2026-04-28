# ADR-039 — Pre-commit hooks for local quality gates

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack
> Related RFC · None (engineering choice)

## Context

Catching style, lint, type, and test failures locally — before they hit CI — saves wall-clock time and reduces broken commits in the history. Without local enforcement, contributors discover issues only at CI, which slows iteration. With heavy local enforcement (full test suite on every commit), the friction discourages frequent commits.

## Decision

Use the **`pre-commit`** framework with hooks for **ruff (lint + format)**, **mypy (on staged files)**, and **fast unit tests**. Hooks are **opt-in** (each contributor runs `pre-commit install` once after cloning) but **strongly recommended** in CONTRIBUTING.md.

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: <pinned>
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: <pinned>
    hooks:
      - id: mypy
        files: ^src/chemigram/
  - repo: local
    hooks:
      - id: pytest-unit
        name: Fast unit tests
        entry: uv run pytest tests/unit -q
        language: system
        pass_filenames: false
        stages: [pre-push]
```

Pre-commit runs ruff and mypy on every commit; unit tests on `git push` (not commit) to keep commits fast.

## Rationale

- **Pre-commit framework is standard.** Cross-language, declarative, version-pinned hook definitions. Reproducible across contributors.
- **Ruff + mypy in pre-commit catches style and type issues sub-second.** Aligns with the speed of the underlying tools (ADR-037, ADR-038).
- **Unit tests on push, not commit.** Tests run fast (target <1s for unit tier) but still adding them to every commit creates friction; pushing is the right boundary.
- **Opt-in rather than enforced.** Forcing pre-commit on every contributor adds friction for occasional contributors and AI-assisted edits. Documented as recommended; CI enforces the same checks.

## Alternatives considered

- **No pre-commit:** broken commits land in the repo; CI catches them but the cycle time is longer.
- **Husky/lefthook:** non-Python alternatives. `pre-commit` is the Python ecosystem's standard; chosen for familiarity.
- **Run all tests in pre-commit:** too slow; integration and E2E tiers belong in CI or pre-release scripts.
- **Enforce pre-commit (CI checks for `.git/hooks/pre-commit`):** considered hostile to occasional contributors. CI catches everything anyway.

## Consequences

Positive:
- Most contributor commits are clean before they hit CI
- Sub-second pre-commit latency
- Same checks locally and in CI (consistency)

Negative:
- Opt-in means some contributors won't use it (mitigation: CI catches what pre-commit would have)
- Pre-commit version drift across contributors possible (mitigation: pinned hook versions; updates via PRs)

## Implementation notes

`.pre-commit-config.yaml` at repo root with pinned hook versions. CONTRIBUTING.md documents the one-time setup: `uv run pre-commit install` (and `uv run pre-commit install --hook-type pre-push` for the test hook). Hook versions are bumped via Renovate or Dependabot config.
