# ADR-046 — Golden dataset versioning (immutable, append-only)

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /components/eval
> Related RFC · RFC-017
> Inspired by · ADR-026 in chipi/podcast_scraper

## Context

The eval harness (per RFC-017) runs the autonomous Mode B agent against a curated set of canonical scenarios — the "golden dataset." Each scenario is a (brief, taste fragments, raw, expected outcome) tuple. The harness produces metrics per run; comparing metrics across runs is what makes auto-research possible.

Cross-run comparison is meaningful only if the inputs stay constant. If scenario 3's brief gets edited between run A and run B, "did the new prompt produce better metrics on scenario 3?" becomes unanswerable — better than what? The brief changed. The same applies to taste fragments, expected primitives, the raw file itself.

The pattern in `chipi/podcast_scraper`'s ADR-026 (explicit golden dataset versioning) addresses this: golden datasets are versioned, and once shipped, a version is frozen forever. Improvements ship as the next version.

## Decision

**Golden datasets are versioned (`golden_v1`, `golden_v2`, …) and immutable once shipped.**

Layout:

```
data/eval/
├── golden_v1/                 # frozen forever once shipped
│   ├── manifest.json          # which scenarios + metric weights for this version
│   ├── scenarios/
│   │   ├── 001_iguana_warm/
│   │   ├── 002_manta_blue/
│   │   └── ...
│   └── README.md              # what's in this version + curation notes
├── golden_v2/                 # next version when v1's coverage proves insufficient
└── ...
```

Once `golden_v1/` is shipped (a tagged release of the dataset, declared in `manifest.json`), no file under `golden_v1/` may be edited. Improvements — better scenarios, corrected briefs, tighter expected-primitives lists, additional scenarios — go into `golden_v2/`.

Eval runs declare which golden version they ran against (per ADR-047's run manifests). Comparisons are valid only across runs against the same golden version.

## Rationale

- **Immutability is what makes auto-research work.** "Did prompt v3 beat v2?" requires the same inputs. Mutable scenarios destroy the comparison.
- **Append-only matches ADR-style discipline already used elsewhere in the project.** Same mental model as ADRs themselves (once accepted, frozen) and prompt versions (per ADR-043).
- **Versioning by directory (not by git tag) keeps the comparison-relevant identifier visible.** A scenario can be referenced by `golden_v1/scenarios/003_evening_pelagic` clearly; a git-tag-based version would require checking out historical state to inspect.
- **Multiple golden versions can coexist.** New ML iterations might benefit from older scenarios (regression tests) AND newer ones (broader coverage). Both are accessible.
- **Curation effort is real and shouldn't be lost.** Scenarios represent careful work — selecting representative cases, capturing photographer intent, recording expected primitives. Versioning preserves that work even when the dataset evolves.

## Alternatives considered

- **Mutable golden dataset, git tag the release points:** comparable runs require checking out historical state. Awkward; a manifest in the run output should be self-contained.
- **Single golden dataset, never updated:** loses coverage as the project grows. Doesn't scale.
- **No golden dataset (per-run scenarios):** no comparability between runs. Defeats RFC-017's auto-research goal.
- **Versioning per scenario (each scenario carries its own version):** per-scenario versioning makes sense if scenarios evolve independently, but in practice the dataset evolves as a unit (a new release adds 3 scenarios and tightens 2 existing ones — that's one version bump). Simpler to version the set.

## Consequences

Positive:

- Cross-run metric comparison is sound
- Curation effort is preserved across iterations
- Multiple golden versions coexist for different testing needs (regression vs new coverage)
- Reproducibility is honest — a months-old run manifest references a specific golden version that still exists in the tree

Negative:

- Repository size grows with each golden version (mitigation: raws may live elsewhere via content-hash pointers; the markdown/TOML scenarios are tiny)
- "Which version should I run against?" becomes a small choice for the eval harness user (mitigation: default to the latest, allow override)
- Authoring overhead — improving a scenario means creating a new version, not editing in place (the discipline is the point)

## Implementation notes

- `data/eval/golden_v1/manifest.json` declares the version's scope:

```json
{
  "version": "v1",
  "shipped_at": "2026-09-15",
  "shipped_at_git_sha": "...",
  "scenarios": ["001_iguana_warm", "002_manta_blue", ...],
  "metric_weights": {
    "vocab_purity": 1.0,
    "expected_primitives_used": 0.8,
    "brief_alignment": 0.6
  },
  "notes": "Phase 5 launch dataset. 8 scenarios spanning underwater wildlife, cold pelagic, mixed light."
}
```

- A CI check (`scripts/verify-golden-immutable.sh`) compares each `golden_vN/` directory against its shipped state (via the git tag matching the version) and fails if any file under a shipped version has changed.
- Raw files (`.NEF`, `.ARW`, …) are too large to commit. Each scenario's `scenario.toml` records a SHA-256 of the raw; the actual file lives at `data/eval/golden_v1/scenarios/<id>/raw.NEF` for users who have a local copy, OR at a configurable `CHEMIGRAM_GOLDEN_RAWS_DIR` for users with raws stored elsewhere. If neither is present, scenarios skip gracefully with an explicit warning.
- The convention is: `golden_v1` is shipped at the close of Phase 5's first auto-research milestone. Phase 1 ships the eval harness design only (RFC-017, this ADR, and ADR-047), no scenarios.
