# ADR-036 — Testing strategy: pytest with three tiers

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /components
> Related RFC · None (engineering choice)

## Context

Chemigram has heterogeneous testability concerns. The XMP synthesizer is pure logic — fast, deterministic, easy to unit test. The render pipeline invokes a `darktable-cli` subprocess against real raws — slow, environment-dependent, hard to run in CI. The MCP server adapts the engine — naturally tested via integration tests with real `.dtstyle` files. A naive single-tier test approach either runs slowly (full E2E in every iteration) or has poor coverage (only fast tests).

## Decision

Use **`pytest`** as the test framework with a **three-tier structure**:

```
tests/
├── unit/                    # pure logic, no I/O, no subprocess
├── integration/             # exercise XMP synthesis with real .dtstyle files, temp filesystem
└── e2e/                     # invoke darktable-cli, validate rendered output
```

Test selection via pytest markers: `pytest tests/unit` (fast iteration), `pytest tests/integration` (CI), `pytest tests/e2e` (local pre-release, not in CI for v1).

## Rationale

- **pytest is the de-facto standard** for Python testing. Better fixtures, better assertions, better plugins than unittest.
- **Three tiers separate concerns by speed and dependency:**
  - **Unit tests** stay under 1 second total. Run on every save during development. Cover synthesizer logic, dtstyle parser, versioning DAG operations, mask registry, manifest validation.
  - **Integration tests** run in CI (no darktable required). Cover XMP synthesis with real `.dtstyle` files in temp directories, full `chemigram_core` API exercised against real fixtures.
  - **E2E tests** require a darktable installation. Cover the actual render pipeline producing JPEGs from raws. Run locally before releases; not in CI for v1.
- **Coverage targets are pragmatic, not strict.** High coverage on the synthesizer (pure logic, easy). Lower coverage acceptable on subprocess-handling code (focus on integration tests for those). No "must hit 90%" gate.

## Alternatives considered

- **`unittest`:** stdlib and bulletproof but verbose; pytest's fixtures and assertion rewriting genuinely improve test ergonomics.
- **Single-tier (all tests run together):** simpler structure but forces every test run to be slow; loses the "fast iteration" workflow.
- **Two-tier (unit + integration only):** considered but the E2E tier is genuinely different (requires darktable), worth separating.
- **Snapshot testing of rendered JPEGs:** considered for E2E but too brittle (Apple Silicon vs Linux render differences, darktable version drift); spot-check assertions on rendered JPEGs (file exists, expected dimensions, color near expected) are more durable.

## Consequences

Positive:
- Fast unit feedback loop during development
- CI runs cover the engine without darktable as a CI dependency
- E2E tier validates the full pipeline before releases
- Clear conventions about where each test type lives

Negative:
- Three test directories adds a small amount of structure to learn (mitigation: documented in CONTRIBUTING.md)
- E2E tests not in CI means a darktable upgrade can break things invisibly until pre-release validation (mitigation: pre-release E2E run is part of the release checklist)

## Implementation notes

`pyproject.toml` configures pytest under `[tool.pytest.ini_options]` with markers, addopts, and testpaths. Fixtures shared across tiers go in `tests/conftest.py`; tier-specific fixtures in `tests/<tier>/conftest.py`. Pre-release script (`scripts/pre-release-check.sh`) runs all three tiers including E2E.
