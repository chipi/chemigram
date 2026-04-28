# ADR-045 — Prompt versioning is independent of package SemVer

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /constraints
> Related RFC · RFC-016
> Related ADR · ADR-041 (package SemVer), ADR-043, ADR-044

## Context

Prompts (per ADR-043, ADR-044) carry their own version numbers (`v1`, `v2`, …). The package as a whole carries SemVer (per ADR-041). The natural question: do these have to coordinate? If `mode_a/system` bumps from v1 to v2, does the package version bump too?

Two approaches:

1. **Couple them.** Prompt changes drive package version bumps. Bumping `mode_a/system` to v2 means the package version goes up.
2. **Decouple them.** Prompt versions and package versions move independently. The package's CHANGELOG.md notes prompt-version changes when they ship in a release.

The pattern in `chipi/podcast_scraper` is decoupled: prompt versions in `prompts/<provider>/<task>/v1.j2` evolve independently of package releases.

## Decision

**Prompt versions are independent of the package's SemVer.** Bumping `mode_a/system` from v1 to v2 does NOT bump the package version. The chemigram package's CHANGELOG.md (per ADR-042) notes prompt-version changes when they ship in a release, but the package version bump follows ADR-041's rules (breaking API → bump in 0.x; non-breaking → patch).

A prompt change IS noted in CHANGELOG.md under the appropriate section (typically "Changed" — a behavior change without API breakage):

```
## [0.3.0] - YYYY-MM-DD

### Changed
- Bumped `mode_a/system` from v1 to v2 (added explicit end-of-session protocol)
- Bumped `mode_b/plan` from v2 to v3 (revised diversity instructions)

### Added
- ...
```

## Rationale

- **Prompts evolve faster than the API.** The system prompt for Mode A might iterate 5 times in a Phase 1 sprint while the engine's public API stays stable. Tying them would force minor version bumps for every prompt tweak — noise that diminishes the SemVer signal.
- **SemVer's promise is about API contract.** A consumer pinning `chemigram>=0.3,<0.4` cares whether the API stays compatible, not which prompt version ships. Decoupling preserves that meaning.
- **Auto-research (RFC-017) needs prompt versions as first-class identities.** "Did v3 beat v2 on golden_v1?" is meaningful only if prompt versions are stable identifiers. Coupling them to package versions would make `mode_a/system_v0.3.0` vs `mode_a/system_v0.4.0` — meaningful only if you know the package release history. Decoupling keeps prompt versions clean.
- **Prompts are a behavior change, not an API change.** Existing API consumers don't break when a prompt ships; the agent just behaves slightly differently. That's not what SemVer is for.
- **Matches the reference architecture** (`chipi/podcast_scraper`'s prompt-versioning approach). Cross-project consistency.

## Alternatives considered

- **Couple them (prompt change → minor bump):** floods minor versions, dilutes SemVer signal, noisy for consumers who don't care which prompt ships.
- **Couple them via patch versions:** still adds noise. Patch bumps imply bug fixes, and a prompt iteration isn't a bug fix.
- **No prompt versioning at all (just edit-in-place):** silent behavior changes, defeats the purpose of ADR-043's append-only discipline.
- **Date-based prompt versions** (`mode_a/system_2026-04-28.j2`): considered. Less ambiguous than "v2" if multiple branches develop in parallel, but day-to-day reading is harder ("which is older, v3 or 2026-04-28?"). Integer versions win for simplicity.

## Consequences

Positive:

- Package SemVer keeps its API-contract meaning
- Prompts can iterate freely without semantic-version noise
- Eval comparisons (RFC-017) get clean prompt-version identifiers
- CHANGELOG.md still surfaces prompt changes for release readers

Negative:

- Two version numbers to track per release (package and per-prompt). Mitigation: CHANGELOG.md explicit; release notes can summarize.
- Consumers wanting to pin a specific prompt version must inspect MANIFEST.toml or the release notes; the package version doesn't carry the info. Acceptable: most consumers care about the package, not the specific prompt.

## Implementation notes

- `scripts/release.sh` (per ADR-042) is updated to surface "prompt versions in this release" by reading MANIFEST.toml and including the active versions in the GitHub release description.
- A release that ships only prompt changes (no API changes, no bug fixes) typically goes out as a patch version (0.X.Y → 0.X.(Y+1)) under "Changed" — this is the lightest-weight signal that something behavior-affecting shipped.
- During 0.x development (per ADR-041), breaking prompt format changes (e.g., a new required context variable that breaks existing template rendering) MAY justify a minor bump if they break runtime callers. Author judgment.
