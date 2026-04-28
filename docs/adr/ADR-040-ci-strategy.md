# ADR-040 — CI on GitHub Actions, macOS-only for v1

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack
> Related RFC · None (engineering choice)

## Context

The repo is hosted on GitHub. Continuous integration validates that pushed code passes the same quality bar as local pre-commit, plus tests that don't run pre-commit (integration tier). The matrix dimensions to consider are: Python version, operating system, optional dependencies. Each dimension multiplies CI time and cost; choices need justification.

Chemigram's primary platform is macOS Apple Silicon (ADR-013, Phase 0 work was on this). darktable's behavior on Linux is its own validation surface — a build that passes Linux CI doesn't necessarily mean Linux is supported. E2E tests (which actually invoke `darktable-cli`) require a darktable installation, which GitHub Actions runners don't have by default and which is non-trivial to install reliably.

## Decision

Use **GitHub Actions** for CI. Matrix:

- **Python:** 3.11, 3.12, 3.13
- **OS:** macOS-latest only for v1 (Linux deferred to Phase 2)
- **Optional deps:** none in matrix; dev extras installed as part of every job

CI steps per job:

1. Checkout
2. Install uv
3. `uv sync --all-extras --dev`
4. `ruff check --no-fix` + `ruff format --check`
5. `mypy src/chemigram`
6. `uv run pytest tests/unit tests/integration` (no E2E)

E2E tests run **locally before releases**, not in CI.

## Rationale

- **GitHub Actions is the obvious choice** for a GitHub-hosted repo. Free tier covers public-repo CI generously.
- **Python 3.11/3.12/3.13 matrix** validates the stated minimum (3.11 per ADR-013) and forward compatibility through current stable releases.
- **macOS-only for v1** because:
  - darktable's macOS Apple Silicon behavior is the primary supported configuration
  - Linux darktable behavior is a separate validation surface; passing Linux CI doesn't prove Linux works
  - GitHub Actions macOS runners are slower and more expensive than Linux runners, but the matrix is small (3 Python versions × 1 OS)
- **No E2E in CI** because installing and configuring darktable in a CI runner is fragile and slow; the cost outweighs the benefit at v1 size. Pre-release validation runs locally with a known-good darktable.
- **Integration tier in CI** is the right level — exercises the engine with real `.dtstyle` files but doesn't require the darktable binary.

## Alternatives considered

- **Linux CI alongside macOS:** considered but Linux darktable behavior is separately validated; CI passing on Linux doesn't establish Linux support, so the additional CI cost isn't justified for v1.
- **Cross-OS matrix (macOS + Linux + Windows):** Windows is not a target for v1; Linux deferred per above.
- **E2E in CI via Docker with darktable:** technically possible but the Docker image maintenance burden, the headless display setup, and the OS-divergence in darktable behavior all add friction. Defer.
- **CircleCI / GitLab CI:** no advantage over GitHub Actions for a GitHub-hosted repo.
- **Single Python version (3.11 only):** too restrictive; forward-compat issues are real.

## Consequences

Positive:
- CI reflects the actual supported platform (macOS Apple Silicon)
- Fast feedback (small matrix, no slow E2E)
- Matches Phase 1 scope precisely

Negative:
- Linux support is technically theoretical (mitigation: clearly documented in README; Phase 2 expands CI as Linux gets validated)
- E2E regressions can land if pre-release isn't run (mitigation: pre-release script in `scripts/` makes this hard to skip)

## Implementation notes

`.github/workflows/ci.yml` with the matrix and steps above. Cache `uv` downloads via `actions/cache` keyed on `uv.lock`. Pre-release script `scripts/pre-release-check.sh` runs the full suite including E2E; documented in CONTRIBUTING.md and referenced from the release process.
