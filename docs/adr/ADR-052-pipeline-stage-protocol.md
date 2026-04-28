# ADR-052 — PipelineStage Protocol with single v1 stage (DarktableCliStage)

> Status · Accepted
> Date · 2026-04-28
> TA anchor ·/components/render-pipeline
> Related RFC · RFC-005 (closes here)
> Related ADR · ADR-004 (`darktable-cli` invocation form), ADR-005 (subprocess serialization), ADR-006 (single Python process), ADR-013 (Python 3.11+)

## Context

RFC-005 framed the open question: ship a `PipelineStage` Protocol now or treat it as YAGNI? v1 has exactly one stage (invoke `darktable-cli`); a Protocol would only earn its keep if it makes testing easier or accommodates a real second stage in the foreseeable future.

Slice 1 Issue #4 implemented and tested both `Pipeline` + `PipelineStage` Protocol + `DarktableCliStage`. The Protocol cost ~50 lines, made unit tests trivial (a fake stage replaces the real subprocess invocation), and its existence didn't add complexity to the synthesizer or anything upstream. Multi-stage chaining is genuinely YAGNI — nothing in v1 needs it — but the seam itself was cheap to keep.

## Decision

`chemigram.core.pipeline` exposes a small public surface:

- `class PipelineStage(Protocol)` — single method `run(context: StageContext) -> StageResult`
- `class Pipeline` — orchestrator over `list[PipelineStage]`. Constructor raises `ValueError` on empty list. `run` iterates stages sequentially; short-circuits on the first `success=False` result.
- `class StageContext` — frozen dataclass: `raw_path`, `xmp_path`, `output_path`, `configdir` (required), `width=1024`, `height=1024`, `high_quality=False`
- `class StageResult` — frozen dataclass: `success`, `output_path`, `duration_seconds`, `stderr`, `error_message: str | None = None`
- `def render(...) -> StageResult` — convenience entry point that builds a single-stage `Pipeline([DarktableCliStage()])` and runs it. If `configdir is None`, a process-local tempdir is created lazily.

`chemigram.core.stages.darktable_cli` provides the v1 stage:

- `class DarktableCliStage` implementing the Protocol
- Binary path resolution: explicit constructor argument > `$DARKTABLE_CLI` env var > `"darktable-cli"` on PATH
- Per-configdir `threading.Lock` enforces ADR-005 single-cli-per-configdir within a process; cross-process coordination is out of scope
- Default 60-second timeout; surfaces failures cleanly (`success=False` with `error_message`)
- Invocation form is locked to CLAUDE.md's canonical shape (verified by `test_invocation_form_locked` in unit tests)

**Multi-stage chaining is deferred.** `Pipeline.run` today does sequential stage invocation but doesn't thread N's output into N+1's input — there's no second stage that needs that semantic. If a real second stage materializes (e.g., a GenAI post-processor or format converter), `Pipeline.run` gains that wiring then; the Protocol contract doesn't change.

## Rationale

- **The Protocol seam is cheap (~50 lines) and pays for itself in testing.** Unit tests for the synthesizer (Issue #3) had to use real fixtures because there was no testable abstraction over rendering. The Protocol means future MCP-server tests, agent-flow tests, and synthesizer-vs-render integration tests all use a fake stage trivially.
- **`StageContext` and `StageResult` are frozen dataclasses** — match the rest of `chemigram.core` (PluginEntry, DtstyleEntry, HistoryEntry, Xmp). Hashable, immutable, easy to compare in tests.
- **Per-configdir locking lives in `DarktableCliStage`, not `Pipeline`.** It's an implementation detail of the darktable subprocess, not the orchestration model. Future stages may have their own concurrency rules.
- **`render()` convenience function defaults configdir to a tempdir.** Real renders need a pre-bootstrapped darktable configdir (a fresh empty directory makes darktable-cli fail with "can't init develop system"). The default is documented as test-friendly; production callers are expected to pass an explicit configdir. Slice 5's context layer will add the canonical `~/.chemigram/dt-configdir/` plumbing.
- **`$DARKTABLE_CLI` env var override** addresses the macOS .app-bundle case (discovered in Slice 1 prep): a naive symlink of `/Applications/darktable.app/Contents/MacOS/darktable-cli` onto PATH fails because macOS resolves bundle resources from the binary's invocation path. Either install a thin exec wrapper or set the env var.

## Alternatives considered

- **Skip the Protocol — call `darktable-cli` directly from a function.** Rejected. Refactoring later would cost ~30 lines while paying ongoing testing friction now. The seam is genuinely cheap.
- **Abstract base class instead of Protocol.** Rejected. Protocol is more Pythonic for v1's "small structural contract" and matches the ad-hoc-typing style of the rest of the codebase (no inheritance hierarchies).
- **Multi-stage Pipeline.run with output-threading from day one.** Rejected. Pure YAGNI — there's no second stage. Adding threading logic would need test cases that exercise it; we'd be writing tests for a contract we haven't established. Defer to first real second-stage need.
- **Async/concurrent rendering.** Rejected per ADR-005 — single subprocess per configdir, sequential. Future async wrapper could sit above `Pipeline` if needed; out of scope here.
- **Live progress reporting (callbacks during render).** Rejected. Render times of 1–3s on Apple Silicon don't justify the complexity. Revisit if 4K+ HQ renders become routine.

## Consequences

Positive:
- Unit tests use fake stages, no subprocess; test suite stays fast
- Clear extension path for future stages (GenAI, format converters, etc.)
- Failure modes (timeout, non-zero exit, missing output) all surface as structured `StageResult` rather than exceptions, simplifying caller error handling
- Per-configdir lock guarantees ADR-005 within a single process
- `$DARKTABLE_CLI` override unblocks the macOS bundle case without modifying PATH

Negative:
- One layer of indirection (`Pipeline → stage`) for a one-stage configuration. Acceptable.
- Cross-process configdir contention is undefended — multiple chemigram processes sharing a configdir can corrupt darktable's library.db. Documented; not common in practice; vocabulary CI and dev workflows use isolated configdirs.
- Default tempdir-as-configdir in `render()` is a footgun for production users (won't work without bootstrap). Documented in the docstring; Slice 5 adds the proper `~/.chemigram/dt-configdir/` plumbing.

## Implementation notes

- `src/chemigram/core/pipeline.py` — `StageContext`, `StageResult`, `PipelineStage` Protocol, `Pipeline`, `render()`
- `src/chemigram/core/stages/__init__.py` — re-exports `DarktableCliStage`
- `src/chemigram/core/stages/darktable_cli.py` — the v1 stage with subprocess invocation, per-configdir locking, timeout handling, env-var binary resolution
- Tests:
  - `tests/unit/core/test_pipeline.py` — 13 unit cases (pipeline orchestration, short-circuit, env-var binary, lock identity, invocation form, default tempdir)
  - `tests/integration/core/test_darktable_cli.py` — 4 integration cases (real render of v3 reference, failure stderr capture, timeout handling, concurrent-render serialization)
- RFC-005 status moves to `Decided`; remains as historical record
- Multi-stage chaining and live progress are explicitly deferred to future ADRs if/when real needs surface
