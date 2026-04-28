# ADR-013 — Python 3.11+

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/stack
> Related RFC · None (engineering choice)

## Context

Chemigram's engine is implemented in Python (chosen for its strong fit with MCP server work, XML/JSON handling, subprocess management, and the agent ecosystem). The minimum Python version affects available language features, library compatibility, and platform support.

## Decision

Chemigram requires Python 3.11 or newer.

## Rationale

- **Modern type hints** — `Self` type, `LiteralString`, structural typing improvements. The synthesizer and protocol-based interfaces (e.g., `MaskingProvider`, `PipelineStage`) benefit from precise type hints; older Python versions force less expressive workarounds.
- **Performance** — Python 3.11's interpreter improvements are meaningful for an engine that does subprocess management, XML parsing, and file I/O in tight loops.
- **`tomllib` in stdlib** — `config.toml` parsing without an external dependency.
- **`typing.Protocol` is mature** — protocol-based pluggability (RFC-009 for `MaskingProvider`, RFC-005 for `PipelineStage`) works cleanly.
- **Platform availability** — Python 3.11 is widely available on Apple Silicon (Homebrew, official installer), Linux distros, and Windows. Setting the floor at 3.11 doesn't exclude reasonable platforms.

## Alternatives considered

- **Python 3.10:** would require backporting some type hints (e.g., `Self`) and adding a TOML dependency. Marginal compatibility benefit not worth the cost.
- **Python 3.12:** considered as the floor, but 3.11 is widely available and 3.12's specific improvements aren't load-bearing for Chemigram's code.
- **Python 3.13:** too new at v1's launch — Apple Silicon Homebrew lag, library compatibility uncertain.

## Consequences

Positive:
- Modern type hints throughout the codebase
- `tomllib` for config parsing without dependency
- Strong performance baseline

Negative:
- Excludes Python 3.10 users (mitigation: 3.11 is straightforwardly installable everywhere we care about)
- New libraries occasionally don't yet support 3.11 (rare in 2026; not expected to bite)

## Implementation notes

`pyproject.toml` declares `requires-python = ">=3.11"`. CI runs against 3.11 and 3.12 to catch forward-compat issues.
