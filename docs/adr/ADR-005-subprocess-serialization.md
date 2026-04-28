# ADR-005 — Subprocess serialization per configdir

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/render-pipeline ·/constraints/serial-renders
> Related RFC · None (forced by darktable behavior)

## Context

darktable's `library.db` (per configdir) is locked exclusively by any running darktable or `darktable-cli` process. A second process attempting to use the same configdir fails with "database is locked" until the first exits. Phase 0 confirmed this — when the GUI was left running, `darktable-cli` invocations against the same configdir failed.

## Decision

The render pipeline serializes all `darktable-cli` subprocess calls against a single isolated configdir. At most one render runs at a time.

## Rationale

- darktable enforces the lock; we have no choice about respecting it.
- Phase 0 wall-clock was 1.7-2.3s per render — fast enough that serialization is not a UX problem for the conversational Mode A loop.
- Mode B (autonomous fine-tuning, future) will explore variants in series; the serialization constraint is consistent with its workflow shape.

## Alternatives considered

- **Multiple isolated configdirs (parallel renders):** rejected for v1 — adds significant complexity (separate libraries, separate vocabulary imports if `--style` were used, configdir lifecycle management). The performance benefit isn't needed at v1's expected throughput. Could be revisited if Mode B becomes throughput-bound.
- **Background daemon holding the configdir open:** rejected — conflicts with ADR-006 (single-process, no daemon). Also doesn't help because darktable-cli would still fail to acquire the lock against a daemon-held library.

## Consequences

Positive:
- Implementation is simple — a process pool of size 1, or just sequential subprocess calls
- No race conditions between concurrent renders
- Lock-related debugging is unnecessary

Negative:
- A second render request waits for the first to finish (acceptable at ~2s/render in Mode A)
- Future parallelism in Mode B would require revisiting this ADR with multiple-configdir architecture

## Implementation notes

`src/chemigram_core/pipeline.py` — the runner serializes calls via a simple lock or async semaphore. The synchronous-then-await pattern is sufficient for v1.
