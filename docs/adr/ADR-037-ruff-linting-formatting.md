# ADR-037 — Linting and formatting with ruff

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack
> Related RFC · None (engineering choice)

## Context

The codebase needs a consistent style and a baseline of code-quality checks. The traditional approach combines black (formatting), isort (import sorting), flake8 (style/lint), pylint (broader lint), pyupgrade (modernization), and autoflake (dead-code removal). Each is its own tool with its own config and its own pre-commit step. Configuration drift between contributors is real; the cumulative latency of running 5+ tools in pre-commit is noticeable.

## Decision

Use **`ruff`** as the single linter and formatter for Chemigram. Configure via `[tool.ruff]` in `pyproject.toml`. Enable both `ruff check` (linting) and `ruff format` (formatting, black-compatible).

## Rationale

- **One tool replacing six.** ruff covers black, isort, flake8, pylint, pyupgrade, and autoflake in a single command. Single config, single pre-commit step.
- **Speed.** Written in Rust, ruff runs roughly 10-100x faster than the older toolchain. Pre-commit feedback is sub-second.
- **Auto-fix support.** `ruff check --fix` and `ruff format` correct violations automatically where safe. Reduces friction.
- **Black-compatible formatting.** `ruff format` produces output identical to black; switching is invisible to anyone used to black.
- **Active development and adoption.** ruff is increasingly the modern consensus answer; major projects (pandas, FastAPI, Pydantic) have migrated.
- **Built-in rule sets.** ruff includes the equivalent of bandit's most useful security rules (`S` prefix), pep8-naming, pyflakes, and many others. One config to enable them.

## Alternatives considered

- **black + isort + flake8:** the historical standard. Works fine but slower, multiple tools, multiple configs. ruff is genuinely better; no reason to keep the old stack for a new project.
- **Just black + flake8:** minimal but loses isort and modernization checks. Tighter than ruff's defaults.
- **pyright/Pylance for linting:** Pyright is a type checker; it doesn't replace style and import linting. Complementary at best.
- **No formatter, just a linter:** reasonable for some projects but consistent formatting is genuinely useful for Chemigram's contributor model.

## Consequences

Positive:
- Single tool, single config
- Sub-second linting on every save
- Auto-fix reduces manual cleanup
- Modern consensus answer (less learning curve for contributors familiar with current Python)

Negative:
- ruff's rule set evolves; occasional upgrades may surface new warnings (mitigation: pin a version range in pyproject.toml)
- ruff format has occasional style differences from raw black on edge cases (mitigation: black-compatible by design; differences are rare and accepted)

## Implementation notes

`pyproject.toml` configures ruff under `[tool.ruff]`. Rule sets enabled (initial set): `E`, `W`, `F`, `I`, `N`, `UP`, `B`, `S`, `C90`, `RUF`. Line length 100 (slightly wider than black's 88 default — Chemigram has long XMP-related strings). Format on save in editor configs (documented in CONTRIBUTING.md). CI runs `ruff check --no-fix` and `ruff format --check` as separate steps.
