# ADR-074 — Built-in geometric mask providers

> Status · Superseded by ADR-076 (2026-05-03)
> Date · 2026-05-02
> TA anchor · /components/masking, /contracts/masking-provider
> Related ADRs · ADR-007 (BYOA), ADR-021 (mask format), ADR-057 (provider Protocol), ADR-058 (default agent provider)

## Context

ADR-057 established `MaskingProvider` as a Protocol; ADR-058 shipped
`CoarseAgentProvider` as the only bundled implementation. That provider
needs an MCP-sampling-capable agent in the loop, which is fine for
Mode A photographer sessions but blocks two adjacent use cases:

1. The CLI (`chemigram masks generate ...`) is subprocess-per-invocation
   with no persistent agent context. Today its `generate`/`regenerate`
   verbs return `MASKING_ERROR` with a "no masker configured" hint,
   per `src/chemigram/cli/commands/masks.py`.
2. Vocabulary entries that compose with masks today depend on a
   pre-existing registered mask. There's no way to author an entry that
   says "apply gradient ND to this image" without an agent or a
   separately-authored mask.

Many mask intents are pure geometry — a top-down gradient for a sky,
a radial vignette to bias attention to the subject, a rectangle around
a focal area. These don't need AI; they need parameters and a
rasterizer.

## Decision

Ship three built-in geometric providers in
`chemigram.core.masking.geometric`, each implementing the existing
`MaskingProvider` Protocol unchanged:

- **`GradientMaskProvider`** — angled linear gradient. Parameters:
  `angle_degrees` (0=right, 90=top, 180=left, 270=bottom),
  `start_offset` / `end_offset` (axis fractions where the ramp begins
  and reaches peak), `peak` (intensity cap, 0–1).
- **`RadialMaskProvider`** — circular / elliptical area mask.
  Parameters: `cx`, `cy` (normalized center), `inner_radius`,
  `outer_radius` (full / zero intensity, normalized to half-diagonal),
  `ellipse_ratio` (>1 widens horizontally), `peak`.
- **`RectangleMaskProvider`** — feathered bounding-box mask.
  Parameters: `x0`, `y0`, `x1`, `y1` (normalized corners), `feather`
  (falloff distance, normalized to half the smaller image side),
  `peak`.

All implement `MaskingProvider.generate` and `regenerate`; output is
8-bit grayscale PNG sized to the rendered preview (per ADR-021),
matching what the agent provider produces. `regenerate` delegates to
`generate` — geometric providers are deterministic and have no notion
of "refining" a prior mask. The `target` and `prompt` parameters are
captured into `MaskResult` for provenance but don't drive the output
shape; the shape is fully determined by the provider's construction
parameters.

`numpy` joins as a runtime dependency (alongside `Pillow`) for
per-pixel field math.

## Rationale

- **Complement, not replace, the agent provider.** Per ADR-007 (BYOA),
  the agent provider stays first-class for content-aware masking.
  Geometric providers cover the shape-known cases. Both can be wired
  via `build_server(masker=...)` or assembled together (a future
  `CompositeMaskProvider` ADR could route by descriptor).
- **Protocol unchanged.** Keeping `MaskingProvider` shape-stable means
  every consumer (MCP `_generate_mask`, CLI integration in v1.4.0 C2,
  sibling `chemigram-masker-sam`) gets the new providers for free.
- **Construction-time parameterization, not prompt-parsing.** Agent
  providers parse free-form prompts. Geometric providers are
  deterministic primitives — their parameters belong in code or in
  vocabulary entries, not in opaque strings. A vocabulary entry can
  bake in the parameters and expose only `target` to the agent.
- **NumPy over Pillow gymnastics.** Per-pixel field computations
  (`X*cos(θ) + Y*sin(θ)`, distance fields, distance-to-edge) are the
  natural domain of array math. Doing them in raw Pillow with
  `Image.point` requires position-aware tricks that obscure intent.
  NumPy is universally available as a wheel, has no AI semantics, and
  sits in the same tier as Pillow — pure infrastructure for image-
  array math, not a BYOA violation.

## Alternatives considered

- **Extend `MaskingProvider` with a separate `GeometricProvider`
  Protocol** — rejected: forks the surface unnecessarily. The contract
  ("produce a PNG sized to the render") is identical; what differs is
  *how* the PNG is computed, which is a private concern.
- **One configurable provider with a "kind" enum** — rejected: each
  provider has a meaningfully different parameter set; folding them
  collapses the type system's ability to reject invalid combinations
  at construction (e.g., passing `angle_degrees` to a radial
  provider).
- **Pure-Pillow implementation (no numpy)** — rejected after sketching:
  the gradient + ellipse + feather composition is doable but error-
  prone, mixing `Image.linear_gradient` rotations and resizes,
  `ImageFilter.GaussianBlur`, and `Image.point` lambdas. NumPy is the
  right tool for the job, and one extra wheel is a small price.
- **Dynamic descriptor parsing from `prompt`** — rejected for v1.4.0:
  that's the agent provider's role. If a "geometric provider that
  parses prompts" turns out to be necessary, it's a follow-up that
  composes on top of these primitives, not a replacement for them.

## Consequences

Positive:
- The CLI can now do mask generation via configured geometric
  providers (Workstream C2). The "no masker configured" hint goes
  away for the geometric paths.
- Vocabulary entries can compose with masks deterministically — a
  starter `vignette_radial` style can bake in its own
  `RadialMaskProvider` configuration (Workstream C3).
- The Protocol stays sync, sized-to-preview, and PNG-bytes-out, so
  third-party providers (e.g., `chemigram-masker-sam`) don't have
  to adapt.

Negative:
- NumPy enters the runtime dep set. It's well-trodden infrastructure
  but is the heaviest wheel chemigram now installs.
- `MaskResult.target` and `prompt` no longer have a uniform meaning
  across providers — for the agent provider they drive the mask;
  for geometric providers they're provenance only. Consumers
  generally treat `MaskResult.png_bytes` as the contract, so this is
  more of a documentation matter than a behavioral one.

## Implementation notes

- `src/chemigram/core/masking/geometric.py` — three providers + their
  rasterizers + parameter validation.
- `tests/unit/core/masking/test_geometric.py` — 21 tests covering
  default behavior, parameter validation, peak intensity capping,
  feathering, off-center geometry, and registry round-trip.
- `pyproject.toml` — adds `numpy>=1.26` to `[project.dependencies]`
  with a docstring justifying the addition.
- The CLI integration (`chemigram masks generate --provider gradient
  --angle 270 --target sky`) lands in v1.4.0 Workstream C2.
- Starter vocabulary entries (`vignette_radial`, `nd_top_grad`, …)
  using these providers land in v1.4.0 Workstream C3.
