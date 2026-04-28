# ADR-007 — BYOA: no bundled AI capabilities

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/byoa ·/components/ai-providers
> Related RFC · RFC-004 (default masking provider deliberation)

## Context

Chemigram needs AI capabilities — at minimum, subject masking. Future capabilities include Mode B evaluators and possibly specialist segmenters. The project must decide whether these capabilities ship bundled with the engine or are provided externally by photographer-configured providers.

Bundling AI in v1 would mean: PyTorch as a hard dependency, model weights distributed with releases (or downloaded on first run), GPU configuration in setup, model lifecycle management (updates, deprecation). Each of these is non-trivial.

## Decision

Chemigram bundles no AI capabilities. `chemigram_core` has no PyTorch dependency. No model weights distributed with the engine. AI capabilities are provided through MCP-configured providers — the photographer chooses maskers, evaluators, the photo agent itself.

The engine ships a coarse default masking provider that uses the photo agent's vision capability to produce bbox/gradient/color-region masks with no ML dependency. Production-quality masking is an opt-in sibling project (`chemigram-masker-sam`).

## Rationale

- **Engine stays substrate-shaped.** Without ML weights and GPU configuration, Chemigram is a small Python package with simple dependencies. Setup friction is dramatically lower.
- **Photographer agency.** Quality, speed, and cost trade-offs are explicit choices in `config.toml`, not engine-imposed defaults.
- **Pluggability is preserved.** New providers (hosted services, local models, photographer-trained specialists) integrate via MCP without engine changes.
- **The project's research thesis benefits.** Different photographers can use different AI configurations and still share the substrate; this maps directly onto the BYOA principle in PA/principles/byoa.

## Alternatives considered

- **Bundle SAM as a v1 default:** rejected — adds PyTorch + MPS configuration to setup, ties release cadence to model availability, makes "Chemigram for Apple Silicon" different from "Chemigram for Linux + CUDA." The friction is substantial for what's ultimately one optional capability.
- **Bundle a tiny model (MobileSAM):** considered as a middle ground; deferred. If the coarse default proves inadequate in real use, this could be added without changing the BYOA principle (it would just become one of several options).
- **No default at all (force users to install a provider before any masking works):** rejected — too steep an onboarding cliff. Coarse default lets users get started immediately.

## Consequences

Positive:
- `pip install chemigram` is fast and produces a working setup
- No GPU/MPS configuration in the engine
- No model versioning to manage
- New AI providers can be developed independently from engine releases

Negative:
- Production-quality subject masking requires an opt-in install of `chemigram-masker-sam` or similar
- The coarse default's quality ceiling is bounded by the photo agent's vision capability
- Integration documentation must clearly explain which MCP-configured services to set up, where, and how

## Implementation notes

`src/chemigram_core/masking/__init__.py` defines the `MaskingProvider` Protocol. `src/chemigram_core/masking/coarse_agent.py` is the bundled default. RFC-009 specifies the protocol shape; RFC-004 deliberates the v1 default choice.
