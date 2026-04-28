# ADR-003 — Three foundational disciplines

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/agent-only-writes ·/constraints/dt-orchestration-only ·/constraints/byoa
> Related RFC · None (foundational)

## Context

A research project working with vague AI capabilities and a complex substrate (darktable) needs hard scope discipline or it sprawls into "agent that does photo editing" — a project shape that doesn't fit on any reasonable schedule. The concept-package work identified three load-bearing principles that, together, make the project tractable.

## Decision

Three disciplines hold across all design and implementation decisions:

1. **Agent is the only writer.** The photographer reads previews and judges. The agent is the sole mutator of edit state. Photographer does not directly edit XMPs, configdir state, or vocabulary at runtime.

2. **darktable does the photography, Chemigram does the loop.** Every image-processing capability — color science, lens correction, denoise, tone, masks, etc. — comes from darktable. Chemigram contributes orchestration: vocabulary, composition, versioning, sessions. We do not implement image-processing logic.

3. **Bring Your Own AI (BYOA).** No AI capabilities bundled with the engine. No PyTorch dependency in `chemigram_core`. No model weights. AI is provided through MCP-configured providers — the photographer chooses maskers, evaluators, the photo agent itself.

## Rationale

Together these three drastically narrow the project's surface area:
- (1) eliminates a class of user-modifiable-state edge cases that would explode test coverage
- (2) eliminates an enormous amount of competence we don't need to build (and couldn't build well anyway)
- (3) eliminates a hard dependency tree (PyTorch, model weights, GPU configuration) that would otherwise dominate setup friction

The disciplines are also load-bearing for the project's research thesis: agent-as-apprentice (1), vocabulary-as-voice (2), photographer-controls-AI-choices (3).

## Alternatives considered

- **Allow direct photographer edits to state:** rejected — would require the synthesizer to handle arbitrary input, snapshot conflict resolution, and an undo model. Agent-only writes is dramatically simpler and matches the project's research thesis.
- **Build some image-processing capabilities (e.g., a custom denoiser):** rejected — reimplements what darktable does well. Chemigram cannot compete with darktable's color science.
- **Bundle a default AI stack (e.g., SAM):** rejected — adds heavy dependencies (PyTorch, GPU configuration), couples engine release cadence to model availability, and forces a quality/cost choice on every photographer. BYOA keeps the engine substrate-shaped.

## Consequences

Positive:
- Project scope is tractable on a hobbyist schedule
- Engine has no heavy dependencies, no GPU config, no model management
- Photographer agency is preserved — they choose AI capabilities, not us
- All three disciplines compound: they reinforce each other rather than competing

Negative:
- Some convenient features (e.g., "let me tweak this slider directly without going through the agent") are deliberately unavailable
- First-time setup requires the photographer to configure a masking provider for production-quality work (or accept the coarse default)
- We can't claim "best-in-class color science" — we're standing on darktable's

## Implementation notes

These disciplines surface throughout the codebase as constraints (TA/constraints) and shape per-component decisions in subsequent ADRs. Any feature proposal that violates one of these three is rejected by default; departures require an explicit superseding ADR with justification.
