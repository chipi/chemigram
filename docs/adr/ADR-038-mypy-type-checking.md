# ADR-038 — Type checking with mypy strict for core

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack, /constraints
> Related RFC · None (engineering choice)

## Context

Chemigram's core has several places where types matter for correctness: opaque hex/base64 blobs that must not be confused with decoded data, the (operation, multi_priority) collision key in the synthesizer, content-addressed hashes vs ref names in versioning, and the `MaskingProvider` Protocol shape. Type errors in these areas tend to be subtle and discovered late. Static type checking catches them early.

The cost of strict typing is friction during exploratory code — sometimes type errors are noise during a refactor. Keeping the strict zone bounded preserves the benefit without forcing discipline where it adds friction.

## Decision

Use **`mypy`** for static type checking with **strict mode for `chemigram_core`** and **less strict mode for `chemigram_mcp` and tests**. Configure in `pyproject.toml` under `[tool.mypy]` with per-module overrides.

## Rationale

- **mypy is the established standard.** Most type-aware Python tooling (IDEs, linters) interoperates with mypy semantics.
- **Strict mode catches real bugs.** `disallow_untyped_defs`, `disallow_any_generics`, `no_implicit_optional`, `warn_return_any` together reject the common "I'll add types later" patterns that compound debt.
- **Strict zone bounded to `chemigram_core`** because:
  - The synthesizer's API shapes are load-bearing and consumed by the MCP layer
  - The versioning DAG operations touch hashes, refs, and snapshots that are easy to mix up
  - Protocols (MaskingProvider, PipelineStage) only work as intended with full type information
- **`chemigram_mcp` is loosely typed** because MCP framework types may not always have perfect stubs; pragmatism wins there.
- **Tests are loosely typed** because pytest fixtures and parametrization fight strict typing in ways that don't catch real bugs.

## Alternatives considered

- **Pyright/Pylance:** faster than mypy, better IDE integration, but mypy is more conventional and its strict mode is well-understood. Either would work; mypy chosen for ecosystem familiarity.
- **No type checking:** loses real bug-catching value, especially for opaque-blob handling and protocol-based pluggability.
- **Strict everywhere (including tests):** generates noise without catching real bugs in test code.
- **Permissive everywhere (lenient mypy):** catches almost no real bugs; not worth the overhead.

## Consequences

Positive:
- Bugs in `chemigram_core` caught before runtime
- Public API shapes documented via type hints
- Protocol-based pluggability works as designed (mask providers, pipeline stages)

Negative:
- Strict mode adds friction during exploratory refactoring (mitigation: types can be loosened temporarily during refactor, tightened before merge)
- mypy's incremental performance can degrade on large changes (mitigation: not yet a concern at v1 size)

## Implementation notes

`pyproject.toml` configures mypy:

```toml
[tool.mypy]
python_version = "3.11"
strict = false                          # default off; per-module override on for core

[[tool.mypy.overrides]]
module = "chemigram.core.*"
strict = true

[[tool.mypy.overrides]]
module = ["chemigram.mcp.*", "tests.*"]
strict = false
warn_return_any = false
```

CI runs `mypy src/chemigram` as a separate step. Pre-commit runs mypy on staged files.
