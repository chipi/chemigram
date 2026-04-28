# ADR-049 — Vocabulary-starter ships within chemigram (clarifies ADR-032)

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /stack
> Clarifies · ADR-032 (does not supersede; re-affirms the location decision and locks the PyPI boundary)

## Context

ADR-032 ("Distribution split") established that the chemigram public repo is a **monorepo** containing the engine source, the starter vocabulary at `vocabulary/starter/`, and community packs at `vocabulary/packs/`. Only `chemigram-masker-sam` was named as an "optional sibling project" — a separate repo with its own release cadence — because it brings PyTorch and SAM model weights into a dependency graph the engine deliberately keeps out of itself (per ADR-007 BYOA, ADR-014).

Subsequent ADRs (ADR-034 build system, ADR-041 versioning scheme, ADR-042 distribution) referred in passing to `chemigram-vocabulary-starter` as a "sibling project" alongside `chemigram-masker-sam`. That phrasing was drift — those ADRs were focused on other concerns (build backend, SemVer rules, PyPI mechanics) and treated the vocabulary as a hypothetically-separate distribution without ever explicitly making that decision. ADR-032's monorepo decision was never overturned.

This ADR clarifies: there is **one** repo, **one** PyPI distribution, and the starter vocabulary ships inside both. Only `chemigram-masker-sam` is a true sibling project.

## Decision

**The starter vocabulary lives at `vocabulary/starter/` in the chemigram repo and ships as part of the `chemigram` PyPI distribution.** It is not a separate distribution.

```
chemigram/                               # the OSS monorepo
├── src/chemigram/                       # engine + MCP server (per ADR-034)
├── vocabulary/
│   ├── starter/                         # the starter pack — ships in `chemigram` wheel
│   │   ├── manifest.json
│   │   ├── exposure/
│   │   │   ├── expo_-0.5.dtstyle
│   │   │   └── ...
│   │   ├── wb/
│   │   ├── colorcal/
│   │   └── ... (per docs/starter-vocabulary.md)
│   └── packs/                           # community packs (per ADR-032)
│       └── <pack_name>/
│           ├── manifest.json
│           ├── ATTRIBUTION.md
│           └── *.dtstyle
└── ...

# Sibling repos (separate distributions)
chemigram-masker-sam/                    # per ADR-032, ships PyTorch + SAM weights
```

**PyPI implications:**

- `chemigram` (the package): includes `vocabulary/starter/` as package data. `pip install chemigram` gets the engine + the starter pack out of the box.
- `chemigram-masker-sam` (separate distribution, separate repo): ships when Phase 4 lands (per ADR-032).
- **`chemigram-vocabulary-starter` is not a PyPI name we'll claim or use.** Earlier mentions of this name in ADR-034, ADR-041, ADR-042 were drift; those ADRs are not edited (append-only) but readers should treat their "sibling project" mentions of vocabulary-starter as obsolete.

**Engine API:**

- `chemigram.core.vocab.load_starter()` resolves to the bundled starter pack at runtime via package-data lookup. No environment configuration needed; no separate install step; no `pip install chemigram-vocabulary-starter`.

## Rationale

The case for the merge (and against treating vocabulary-starter as a separate distribution):

- **ADR-032 already said this.** The drift in ADR-034/041/042 was unintentional. We are re-affirming, not changing direction.
- **Community-pack ecosystem is aspirational.** The argument for separating vocabulary-starter ("it sets the pattern for community packs") only matters if community packs materialize. At v1, they don't exist. Splitting now prepares for a future that may never arrive at the cost of friction now.
- **Empty action space is not a desirable default.** A `pip install chemigram` that produces a working engine with no vocabulary surfaces gaps immediately. Bundling the starter means first-time users have something to do; the path to "what does this thing actually do?" is one step shorter.
- **Iteration cost.** Engine-and-starter cross-changes are common during Phase 1 (a new pipeline stage may require a new vocabulary entry to validate end-to-end). One-repo iteration is cheaper than coordinating two repos and two release cycles.
- **`chemigram-masker-sam` is unaffected.** It stays separate because PyTorch + model weights belong outside the engine's dependency graph. That argument is technical and immediate; the vocabulary-starter argument was aspirational and not.

## Alternatives considered

- **Keep vocabulary-starter as a separate sibling distribution** (the position implied by drift in ADR-034/041/042): rejected. Premature for v1; conflicts with ADR-032's explicit monorepo decision; adds release-coordination friction.
- **Vocabulary as user-supplied only, no starter ships**: considered briefly, rejected for the same reason ADR-032 rejected it — first-time users face an empty action space; the starter is the on-ramp.
- **Vocabulary-starter as a separate `extras_require` rather than separate package** (`pip install chemigram[starter]`): considered. Pointlessly clever — the starter is small (~50 KB of `.dtstyle` files), useful by default, and there's no dependency cost to pulling it in. Just include it.

## Consequences

Positive:

- One repo, one CI, one release process for the engine + starter
- `pip install chemigram` works out of the box
- Engine-and-starter cross-changes ship together (common during Phase 1)
- Re-affirms ADR-032's position cleanly; resolves drift in later ADRs
- Less infrastructure to maintain (no second repo, no second PyPI listing)

Negative:

- If the community-pack ecosystem ever materializes, the starter sitting inside chemigram becomes asymmetric vs community packs in their own repos. Mitigation: at that point, splitting is a small refactor; ship it then if needed, not now.
- The `chemigram-vocabulary-starter` PyPI name remains available for a squatter. Mitigation: optionally claim it as a placeholder (a 0.0.0 wheel pointing at `chemigram` itself) at first release. Cheap, defensive, no commitment.

## Implementation notes

- `pyproject.toml` is updated to include `vocabulary/starter/` in the wheel build (via hatchling's `[tool.hatch.build.targets.wheel]` `force-include` directive). Implementation lands in Slice 1 of Phase 1 alongside the rest of the bootstrap config.
- Slice 6 of Phase 1 captures the actual `.dtstyle` files into `vocabulary/starter/` per the spec at `docs/starter-vocabulary.md`. No sibling repo is created.
- `docs/IMPLEMENTATION.md` Slice 6 wording is updated: distribution happens via the main `chemigram` package, not via a separate `chemigram-vocabulary-starter` package.
- `docs/starter-vocabulary.md` is updated: references to "the OSS `chemigram-vocabulary-starter` package" become "the starter pack at `vocabulary/starter/`."
- `docs/CONTRIBUTING.md` already documents two contribution paths (code, vocabulary) within the same repo. No changes needed.
- ADR-034, ADR-041, ADR-042 are not edited. They were correct on their actual subjects; their references to vocabulary-starter as a sibling project were drift, and ADR-049 makes the correct position explicit.
- `chemigram-masker-sam` continues unchanged per ADR-032: separate repo, separate distribution, deferred to Phase 4.
