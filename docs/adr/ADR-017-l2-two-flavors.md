# ADR-017 — L2 has two flavors (neutralizing, look-committed)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer
> Related RFC · None (concept-package decision)

## Context

L2 establishes the photographer's baseline before the agent starts working. But "baseline" means different things in different photographic contexts:

- An underwater photographer might want L2 to *recover* — neutralize the blue cast, restore the missing red, get to a "sane working state" so the agent's L3 work isn't fighting raw murk. L3 holds most of the look.
- A Fuji shooter who chose Acros at capture might want L2 to *commit* — apply Fuji Acros film simulation as the look. L3 refines within that committed direction.

Forcing one flavor would break the other use case.

## Decision

L2 supports two flavors of templates, both treated as "pre-agent baseline" by the engine:

- **Neutralizing L2** — recovers raw murk to a sane working state. Examples: `underwater_pelagic_blue`, `topside_neutral`. Most of the look is L3.
- **Look-committed L2** — already commits to a look. Examples: Fuji film simulations (`fuji_acros`, `fuji_classic_chrome`), Nikon picture-control emulations. L3 work refines within it.

Both are L2 because both are pre-agent, photographer-set baselines. They differ only in how much taste they pre-commit. The engine treats them identically; the distinction is content-level (in the vocabulary itself), not architectural.

## Rationale

- **Captures real photographer workflows.** Both flavors are common; collapsing to one excludes legitimate use cases.
- **Same engine treatment.** Neither flavor needs special-case logic in the synthesizer; both are sequences of `<plugin>` entries that bake into the baseline.
- **Documents in vocabulary metadata, not engine.** A vocabulary entry's manifest can declare it look-committed or neutralizing; the agent reads this to know how much L2 has pre-committed.

## Alternatives considered

- **Force all L2 entries to be neutralizing (looks live in L3):** rejected — Fuji shooters can't apply a film sim as a baseline, only as a layered move; this misrepresents what they did at capture.
- **Force all L2 entries to be look-committed (no neutralizing path):** rejected — underwater and other "raw is broken, fix to sane" workflows have no good home.
- **Add a fourth layer for "look commitment" between L2 and L3:** rejected — over-models. Two flavors of L2 capture the distinction at lower cost.

## Consequences

Positive:
- Both common workflows fit cleanly
- Vocabulary contributors choose flavor based on the entry's character
- The agent can read the L2 entry's metadata and adjust L3 strategy (don't fight a committed look)

Negative:
- The L2/L3 boundary is sometimes ambiguous (is `fuji_acros_red_filter` an L2 look or an L3 taste move?). Authors decide; conventions evolve in vocabulary docs.
- Photographers must understand the distinction when configuring L2 bindings; not difficult, but a concept to learn.

## Implementation notes

The vocabulary manifest can include `subtype: "neutralizing"` or `subtype: "look"` on L2 entries. The engine doesn't enforce; the agent uses the metadata for reasoning. Calibration caveats (e.g., "Fuji Acros applied to Sony A1 produces spirit-of-Acros, not pixel-identical") live in the entry's `description` field.
