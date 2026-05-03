# ADR-071 — CLI, MCP, and core: thin-wrapper discipline (lint-enforced)

> Status · Accepted
> Date · 2026-05-03
> TA anchor ·/components/cli ·/components/mcp-server
> Related RFC · RFC-020 (closes here); related ADR-006

## Context

With the addition of the CLI (ADR-069), Chemigram has two external invocation surfaces — MCP and CLI — over the same engine. A naive implementation duplicates logic across both layers: error handling, validation, vocabulary resolution, XMP mutation. Either by copy-paste or by having each adapter call slightly different internal paths.

Duplication in this position has historically caused, across other projects:

- Bugs that manifest in one adapter but not the other
- Inconsistent error messages and exit behavior
- Test suites that cover one adapter but miss the other
- Drift over time as the two surfaces evolve independently

## Decision

**All domain logic lives in `chemigram.core`. The CLI and MCP layers contain only argument parsing, output formatting, error mapping, and entry-point glue.**

Specifically:

- **`chemigram.core`** — XMP parsing and synthesis, vocabulary resolution, snapshot management, taste validation, darktable-cli invocation, pipeline stages, all file I/O, all domain error types.
- **`chemigram.cli`** — Typer command definitions, output formatters (`HumanWriter`, `JsonWriter`), exit-code mapping from core exceptions, entry point.
- **`chemigram.mcp`** — MCP tool definitions, MCP result serialization, MCP server lifecycle.

**The rule, lint-enforced:** if you find yourself writing a conditional, a validation, or a file operation in `chemigram.cli` or `chemigram.mcp`, it belongs in `chemigram.core` instead.

### Forbidden imports in adapter layers

```
# FORBIDDEN in chemigram.cli/ and chemigram.mcp/:
import subprocess           # darktable-cli invocation belongs in core.pipeline
import xml.etree.ElementTree # XMP parsing belongs in core.xmp
import xml.*                # any xml module
```

Allowlisted callsites (auditable, justified):

- `chemigram.cli.commands.status` — calls `subprocess.run([darktable-cli, "--version"])`. Justified because reporting the binary's version is metadata about an external dependency, not domain logic. `chemigram status` is itself not an MCP tool wrapper.
- `tests/integration/cli/test_audit_imports.py` — uses `subprocess` to run the audit script as a test. Lives outside the adapter dirs, so allowlisted by directory scope.

### Enforcement

`scripts/audit-cli-imports.py` walks `src/chemigram/cli/` and `src/chemigram/mcp/`, AST-parses each `.py` file, and flags forbidden imports against the allowlist. Wired into `make ci` as step 7/10. Negative-case tests (`tests/integration/cli/test_audit_imports.py`) plant a forbidden import in a tmp tree to verify the audit catches violations.

## Rationale

- **Single source of truth for behavior.** When a core operation changes — vocabulary entry application, snapshot format, XMP key mapping — it changes in one place. Both adapters inherit the change automatically.
- **Adapter symmetry by construction.** If CLI and MCP both call the same core functions, their behavior is symmetric *by construction*, not by convention. Tests written against `chemigram.core` cover both adapters.
- **Adding a third adapter is bounded.** A future REST or gRPC adapter (if Chemigram needs one) costs only the thin layer, not a re-implementation of the domain.
- **Enforced at the dependency level.** `chemigram.cli` and `chemigram.mcp` both import from `chemigram.core`; `chemigram.core` imports from neither. This is enforceable by import linting (no circular imports, no cross-adapter imports).

## Consequences

**Positive:**

- No logic duplication between CLI and MCP. The 6 pragmatic shared helpers the CLI imports from `chemigram.mcp` (`_state.summarize_state`, `_state.current_xmp`, `server._resolve_prompts_root`, `tools._masks_apply.materialize_mask_for_dt`, `tools.rendering._stitch_side_by_side`, `tools.versioning.parse_xmp_at`, `tools.masks._serialize_entry`) are infrastructure helpers, not domain logic. They're documented as candidates to lift into `chemigram.core` in a future refactor.
- `chemigram.core` is independently importable and testable without any adapter layer. The Slice-1 unit and integration tests prove this.
- Audit-style integration tests catch drift early (verb-parity audit, error-code parity audit, audit-imports).

**Negative:**

- **Core API design matters more.** The core API must serve multiple callers, not just one. A function that works for MCP might need to return more structured data to serve CLI's output formatter. The cost is higher API quality, which is a positive side effect.
- **Temptation to break the rule under time pressure.** "Just put this validation in the CLI, it's only one line" is how duplication starts. The lint must be enforced in code review, not just in this ADR.
- **The 6 MCP-private helpers the CLI imports are debt.** Each is documented as such; the longer-term move is to lift them into `chemigram.core.helpers` (or similar) so neither adapter imports the other. Not blocking for v1.3.0; flagged for future cleanup.

## Verification

- The audit script itself is tested for both positive (current tree clean) and negative (planted violations caught) cases.
- The verb-parity audit asserts every MCP tool has either a CLI verb or a documented exclusion in `_KNOWN_PENDING_VERBS`.
- The error-code parity audit asserts every `ErrorCode` value maps to exactly one non-zero `ExitCode` value.
- Both adapters are exercised by the same integration tests (per-verb CliRunner tests on the CLI side; per-tool MCP harness tests on the MCP side).

## Alternatives considered

### Allow domain logic in adapters with case-by-case review

**Rejected.** Code review can't reliably catch this — duplication tends to start small (a single conditional) and accumulates. Lint enforcement is the only durable mechanism.

### Move MCP-private helpers into `chemigram.core` immediately

**Deferred.** The 6 helpers (`summarize_state`, `current_xmp`, etc.) are pragmatic infrastructure shared between adapters. Lifting them is a clean refactor but doesn't unblock v1.3.0 and risks churn. Tracked as a follow-up.
