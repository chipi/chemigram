# ADR-057 — MaskingProvider Protocol shape

> Status · Superseded by ADR-076 (2026-05-03)
> Date · 2026-04-29
> TA anchor · /components/masking, /contracts/masking-provider
> Related RFC · RFC-009 (closes)

## Context

RFC-009 left open: what's the contract every mask provider implements?
Sync vs async, single-call vs streaming, what does the result carry,
how do failures surface? v0.4.0 (Slice 4) ships
`chemigram.core.masking.MaskingProvider` (Protocol) plus the bundled
`CoarseAgentProvider` (sampling-based) and exercises the surface end-to-
end through `tests/integration/mcp/test_full_session_with_masks.py`.

This ADR closes RFC-009 with the concrete shape.

## Decision

### Protocol

```python
class MaskingProvider(Protocol):
    def generate(self, *, target: str, render_path: Path,
                 prompt: str | None = None) -> MaskResult: ...
    def regenerate(self, *, target: str, render_path: Path,
                   prior_mask: bytes,
                   prompt: str | None = None) -> MaskResult: ...
```

Keyword-only. Sync. Both methods return `MaskResult`. Failures raise
`MaskGenerationError` (subclass of `MaskingError`); the MCP boundary
maps these to `MASKING_ERROR` (recoverable).

### Result shape

```python
@dataclass(frozen=True)
class MaskResult:
    png_bytes: bytes        # 8-bit grayscale PNG, target=255 / outside=0 (ADR-021)
    generator: str          # "coarse_agent" | "sam_provider" | ...
    prompt: str | None      # refinement prompt used; None on first generation
    target: str             # the descriptor that produced this mask
```

Caller registers via
`chemigram.core.versioning.masks.register_mask`; PNG bytes are
content-addressed in the per-image objects/ store.

### Error categories

| Exception | When | MCP code |
|-|-|-|
| `MaskGenerationError` | Sampling declined; descriptor invalid; provider can't produce a mask | `MASKING_ERROR` (recoverable) |
| `MaskFormatError` | Produced bytes aren't a valid PNG | `MASKING_ERROR` (typically not recoverable) |

### Sampling-based pattern

`CoarseAgentProvider` is the canonical bundled implementation. It splits
two concerns: an injected `ask_agent` callable that produces a region
descriptor (`{bbox, polygon_hint?, confidence}`), and a pure-Pillow
rasterizer that converts the descriptor to a grayscale PNG matching the
render's dimensions. The split keeps `chemigram.core.masking` free of
any `mcp` SDK import — the production wiring of the sampling round-trip
lives in the MCP layer (#18).

### Async path

Reserved for a follow-up RFC. v0.4.0 sync is sufficient because the
agent-orchestrated mask generation already overlaps with previous-turn
inference latency.

## Rationale

- **Sync over async:** the provider sits behind one MCP tool call; the
  cost of awaiting completion is bounded by the agent's own response
  latency. Adding async surface area without evidence of a bottleneck is
  YAGNI.
- **Keyword-only args:** prevents argument-position breakage when
  third-party providers (e.g., `chemigram-masker-sam`) implement the
  Protocol.
- **PNG bytes in `MaskResult`, not a path:** the registry is content-
  addressed; making bytes the contract avoids each provider needing
  filesystem semantics.
- **`generator` string, not class identity:** registry records carry
  it for provenance; serializable; cross-process portable.

## Alternatives considered

- **Async-only Protocol** — rejected: forces every caller into the
  async transport even for trivial in-process providers. Sync + run-in-
  thread for slow providers is cleaner for v1.
- **Stream of partial masks** — rejected: agent-orchestrated mask
  generation is one-shot per turn. Streaming would only help if a
  provider could yield progressively-refined masks during sampling, and
  no current provider does.
- **Single `mask` method with `prior_mask: bytes | None = None`** —
  rejected: separates first-gen vs refinement paths so providers that
  treat them differently (e.g., SAM with prompt expansion) don't have
  to branch internally on `prior_mask is None`.
- **Return only PNG bytes** — rejected: registry needs `generator` and
  `prompt` for provenance; `target` is useful when an agent passes a
  registered mask name and we recover the descriptor.

## Consequences

Positive:
- Provider implementations are simple to write and to test in
  isolation; the rasterizer + descriptor split keeps the bundled default
  close to the BYOA frontier (no PyTorch).
- Sibling project `chemigram-masker-sam` (Phase 4) implements the same
  Protocol — substituting providers is a one-line `build_server(masker=...)`
  change.

Negative:
- Sync API blocks the MCP server's event loop during generation. v0.4.0
  uses MCP sampling which is itself async-driven; the bundled provider
  marshals via `anyio.run` internally where needed.
- `MaskResult` doesn't carry a confidence score. Agents can ask for it
  via the descriptor schema; if confidence becomes a registry-level
  concern, a follow-up ADR adds the field.

## Implementation notes

- `chemigram.core.masking.__init__` — Protocol + `MaskResult` +
  exception hierarchy.
- `chemigram.core.masking.coarse_agent` — `CoarseAgentProvider`,
  `AgentRequest`, `AskAgent` + the `_rasterize` helper.
- `chemigram.mcp.tools.masks._generate_mask` / `_regenerate_mask` —
  consumes a `MaskingProvider` via `ToolContext.masker`.
- `chemigram.mcp.server.build_server(masker=...)` — production wiring
  point.
- `chemigram.mcp._test_harness` — accepts a fake masker for tests.
- Test evidence: `tests/integration/mcp/test_full_session_with_masks.py`
  exercises generate → list → apply(mask_override) → regenerate end-to-
  end through MCP with a fake sampling-based masker.
