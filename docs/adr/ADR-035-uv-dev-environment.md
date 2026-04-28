# ADR-035 — Dev environment with uv

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack
> Related RFC · None (engineering choice)

## Context

Contributors need a consistent way to install Chemigram for development, manage a virtual environment, install dependencies (including dev dependencies and pre-commit hooks), and run tests. The choice of dev tooling affects onboarding friction, lockfile reproducibility, and contributor experience.

## Decision

Use **`uv`** as the dev environment and dependency tool for Chemigram. Standard workflow:

```bash
uv venv                       # create .venv
uv sync --all-extras --dev    # install with dev extras
uv run pytest                 # run tests
uv run pre-commit install     # install hooks
```

The repo includes a `uv.lock` file for reproducible installs.

## Rationale

- **Speed** — uv is roughly 10x faster than pip for resolution and installation. Visible improvement on every dev cycle.
- **Single tool** — replaces pip + venv + pip-tools (or virtualenv + pip + pip-compile). One command to learn.
- **Lockfile support** — `uv.lock` gives reproducible installs across contributor machines and CI without the overhead of Poetry.
- **PEP 517/518/621 native** — works with `pyproject.toml` directly, no wrapper config.
- **Compatible with non-uv users** — anyone preferring plain `venv + pip` can still install with `pip install -e ".[dev]"`. uv is the recommended path, not the only path.

## Alternatives considered

- **Plain `venv + pip + pip-tools`:** bulletproof but slower; requires pip-compile for lockfiles. Acceptable but less ergonomic.
- **Poetry:** offers similar workflow but introduces its own ecosystem (poetry.lock, poetry-specific commands). The wrapper-around-standards approach is its own learning curve.
- **PDM:** similar to Poetry but less popular; smaller ecosystem.
- **Hatch's environment manager:** good but tied to `hatch` as a CLI tool; uv is more modular.

## Consequences

Positive:
- Fast installs (matters every contributor dev cycle and every CI run)
- Reproducible builds via `uv.lock`
- Single tool for venv + pip + lockfile workflows
- Compatible with plain pip+venv as fallback

Negative:
- uv is newer than pip+venv (released 2024); some contributors may be unfamiliar (mitigation: CONTRIBUTING.md documents the workflow)
- Requires installation as a separate tool (`pip install uv` or `brew install uv`) rather than coming with Python (mitigation: one-line install)

## Implementation notes

CONTRIBUTING.md walks new contributors through `brew install uv` (macOS) followed by the standard workflow. CI uses uv for installation. `uv.lock` is committed to the repo. The pyproject.toml `[project.optional-dependencies]` declares `dev` and other extras.
