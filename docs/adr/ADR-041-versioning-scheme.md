# ADR-041 — SemVer with 0.x for Phase 1 development

> Status · Accepted
> Date · 2026-04-27
> TA anchor · /stack
> Related RFC · None (engineering choice)

## Context

Chemigram is a research project that will publish to PyPI for local install. Users of the package — including AI agents reading documentation, MCP-host configurations referencing the entry point, and sibling projects (`chemigram-vocabulary-starter`, `chemigram-masker-sam`) declaring compatibility — need a versioning scheme that communicates compatibility clearly.

The project is also early-stage. Breaking changes to the synthesizer API or MCP tool surface are likely during Phase 1. A versioning scheme that signals "this is unstable" until Phase 1 is genuinely done is honest with consumers.

## Decision

Use **Semantic Versioning** (SemVer) per `https://semver.org`. Specifically:

- **`0.1.0`** at the first publishable slice (Slice 1 of Phase 1)
- **`0.x.y`** through Phase 1 development. Breaking changes bump the minor (0.1.0 → 0.2.0); non-breaking changes bump the patch (0.1.0 → 0.1.1)
- **`1.0.0`** when Phase 1's definition of done is met (real Mode A session works end-to-end on a real raw with the starter vocabulary)
- **Major bumps thereafter** (1.0.0 → 2.0.0) for breaking API changes only

The "API" includes: `chemigram_core` public functions, the MCP tool surface (tool names + parameter shapes + error contracts), the per-image repo layout, the manifest format, and the configuration file format.

## Rationale

- **SemVer is the dominant convention** for Python packages. Tooling (pip, uv, dependabot) assumes it.
- **`0.x` signals "not yet stable"** clearly. Sibling projects can pin `chemigram>=0.3.0,<0.4` and expect potential breakage at minor bumps. Once `1.0.0` ships, semver guarantees apply normally.
- **Phase 1 done = `1.0.0`** is a meaningful milestone. The first post-`1.0` consumer can rely on stability.
- **Minor bumps for breaking changes during 0.x** matches the convention of many early-stage Python projects (e.g., httpx, Pydantic during 0.x).

## Alternatives considered

- **CalVer** (e.g., 2026.04.0): clear about release date, less clear about compatibility. Worse fit for libraries where consumers care about API stability.
- **0.0.x for everything until 1.0:** too coarse — consumers can't tell which 0.0.x versions are compatible.
- **1.0.0 from the first release:** signals stability we don't have. Misleading for consumers.
- **Marketing version + build version:** unnecessary complexity for v1.

## Consequences

Positive:
- Consumers (sibling projects, dependabot, AI agents reading versions) get accurate compatibility signals
- Standard convention; no learning curve
- `1.0.0` becomes a meaningful milestone tied to Phase 1 completion

Negative:
- Risk of `0.x` lingering past Phase 1 if "definition of done" slips (mitigation: tied explicitly to IMPLEMENTATION.md's Phase 1 gate)
- Sibling projects pinning `<1.0` may need to update once 1.0 ships (mitigation: changelog calls this out at 1.0)

## Implementation notes

Version is declared in `pyproject.toml` under `[project] version`. Updated by hand for each release (no setuptools-scm or git-tag-based versioning for v1; release ceremony is small enough that manual is fine). Releases are tagged in git (`v0.1.0`, `v0.2.0`, etc.). CHANGELOG.md tracks changes per release with explicit "Breaking" / "Added" / "Fixed" sections.
