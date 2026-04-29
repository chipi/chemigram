# ADR-058 — Default masking provider: CoarseAgentProvider

> Status · Accepted
> Date · 2026-04-29
> TA anchor · /components/masking
> Related RFC · RFC-004 (closes); ADR-057 (Protocol)

## Context

RFC-004 left open: which masker ships as the default with `chemigram`?
Three candidates were considered: a SAM/MobileSAM-bundled default, a
classical-CV heuristic provider, and a sampling-based provider that
delegates target localization to the calling agent.

ADR-007 (BYOA) forbids bundling AI capabilities with the engine. ADR-032
puts SAM in the sibling `chemigram-masker-sam` project. That eliminates
the SAM-bundled option and clarifies the shape of the choice: classical
CV vs sampling-based.

## Decision

The bundled default masker in v0.4.0 is `CoarseAgentProvider` — a
sampling-based implementation that asks the calling agent (via MCP
`sampling_callback`) for a region descriptor (`{bbox, polygon_hint?,
confidence}`) against the current rendered preview, then rasterizes the
descriptor to a grayscale PNG via Pillow.

`chemigram-masker-sam` (sibling project, Phase 4) remains the
**recommended production upgrade** per ADR-032 — installed via
`pip install chemigram-masker-sam` and configured in the photographer's
`config.toml`. Same Protocol (ADR-057), substituted at server startup
via `build_server(masker=...)`.

## Rationale

- **BYOA-aligned:** no PyTorch dependency; no model weights distributed
  with the engine. Stays inside ADR-007.
- **Agent vision is already there:** Mode A clients are MCP-capable
  agents (Claude with vision, etc.) that already have multimodal
  capability. Reusing it via sampling avoids a second model in the
  loop.
- **Quality is bounded by the agent, not the engine:** as the
  photographer's chosen agent improves at spatial reasoning, the
  bundled masker improves with no engine release. Conversely, the
  bundled default's quality won't beat the agent's vision — for that,
  install `chemigram-masker-sam`.
- **Implementation simplicity:** the descriptor-then-rasterize split
  produces ~150 LOC of pure-Python code (mostly Pillow polygon
  rasterization). Easy to test in isolation; easy to reason about.

### Quality bar for the default

RFC-004's soft target was ≥70% accept-on-first-generation for marine
animals against contrasting water. v0.4.0 documents this as a target,
not a gate-blocker. The mechanism works (proven by the gate test); the
quality is a function of the calling agent's vision and the test
material. Real-session evidence in Slice 6 calibrates whether the
default needs replacement or refinement before 1.0.

## Alternatives considered

- **Classical-CV heuristic provider (OpenCV GrabCut / k-means).**
  Rejected: adds an opencv-python-headless dep without delivering
  meaningfully better masks than the sampling-based provider for the
  marine-animal case the gate targets. We'd be carrying the binary dep
  for a corner case.
- **Bundle SAM/MobileSAM directly.** Rejected: violates ADR-007.
  Production users wanting SAM install `chemigram-masker-sam`.
- **No bundled default — Protocol-only ship.** Rejected: makes the
  `generate_mask` tool unusable out of the box, which would surface as
  a documentation/UX gap that every photographer hits on day one.
- **Bundle a stub provider that always returns a centered ellipse.**
  Rejected: produces useless masks without surfacing the BYOA
  conversation. Better to use the agent's actual vision and let
  photographers upgrade to SAM when they need pixel precision.

## Consequences

Positive:
- `pip install chemigram` produces a working masker out of the box for
  any MCP-capable agent that supports sampling.
- Quality scales with the agent's vision capability — no engine
  release needed to benefit from agent improvements.
- Clear upgrade path: install `chemigram-masker-sam` for pixel-precise
  masks.

Negative:
- Mask quality is bounded by the agent's spatial reasoning. For fine
  detail (eye edges, fur, water-surface boundaries) the bundled
  provider underperforms SAM-based providers. Documented in the agent
  prompt's masker-available branch ("for fine detail, mask quality may
  be limited").
- The provider's success depends on the calling client supporting MCP
  sampling. Clients that don't (e.g., a non-vision agent or a CLI
  tooling client) would see `MASKING_ERROR` from `generate_mask`. This
  is intentional — the photographer chose their agent; we surface the
  capability gap rather than papering over it.

## Implementation notes

- `chemigram.core.masking.coarse_agent.CoarseAgentProvider` — the
  implementation.
- `chemigram.mcp.server.build_server(masker=...)` — production callers
  wire `CoarseAgentProvider(ask_agent=…)` against the MCP session's
  sampling callback.
- The `ask_agent` callable signature is intentionally loose
  (`Callable[[AgentRequest], dict[str, Any]]`) so the production wiring
  can issue a real `mcp.types.CreateMessageRequest` while tests inject
  arbitrary fakes.
- Quality gate test runs in `tests/integration/mcp/test_full_session_with_masks.py`
  against a fake sampling callback (deterministic test). The "real
  agent ≥70% accept" target is recorded for Slice 6 manual evidence
  collection.
