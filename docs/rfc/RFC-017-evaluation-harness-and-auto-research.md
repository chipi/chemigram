# RFC-017 — Evaluation harness and auto-research workflow

> Status · Accepted (design); built Phase 5
> Date · 2026-04-28
> TA anchor · /components/eval
> Related ADRs · ADR-046, ADR-047
> Related RFCs · RFC-016 (prompt system), RFC-002 (Mode B)
> Related PRDs · PRD-002 (Mode B)

## Why this is an RFC

Mode B's value proposition (PRD-002) is that the agent can run autonomously against a brief and produce candidate edits worth reviewing. That value is asserted, not proven — and the only way to prove it is to systematically run Mode B across representative scenarios and measure whether outputs hold up. Without that infrastructure, Mode B will either ship un-validated (we hope it works) or get blocked indefinitely on "it might not work in the real cases." Building the eval harness solves the validation problem and unlocks something more interesting: **auto-research**, the iterative workflow of varying prompts/configs/models against fixed scenarios and learning what improves outputs.

Auto-research is not regression testing. Regression testing asks "did the existing behavior break?" Auto-research asks "what behavior is best, given this scenario set?" Both matter; the harness supports both, but the design priority is auto-research because that's what unlocks Mode B's iteration loop.

The reference architecture is `chipi/podcast_scraper`'s ADR-026 (golden dataset versioning) + ADR-031 (heuristic-based quality gates) + Issue #379 (run manifests for reproducibility), adapted for chemigram's interactive-but-scriptable pipeline.

## Background

Phase 1 ships Mode A (interactive, photographer-in-the-loop). Mode A's "evaluation" is implicit — the photographer evaluates each move in real time. Auto-evaluation of Mode A is partially possible (mechanical correctness checks: did the agent read context first? did taste updates go through propose-and-confirm?) but limited (you can't auto-evaluate "did the agent suggest a sensible move" without a synthetic photographer, which is its own can of worms).

Mode B is different. The agent runs autonomously: take a brief, take a taste, propose 3 candidates with reasoning. There's no photographer in the loop until candidates are presented. That makes Mode B genuinely scriptable — same input, deterministic-modulo-LLM-temperature output, comparable across runs.

The opportunity:

1. **Capture canonical scenarios.** A handful of (brief, taste, raw) tuples that represent the kinds of work the system is supposed to support.
2. **Run Mode B against them.** Headlessly, with a fixed config, producing 3 candidates per scenario.
3. **Measure outputs.** Mechanical metrics (tool sequence sanity, vocabulary purity) plus rubric-scored metrics (brief alignment, taste alignment, candidate diversity).
4. **Compare runs.** Did prompt v3 outperform v2? Did Claude beat GPT-N at this scenario set? Did widening the candidate count improve diversity without sacrificing brief alignment?

That's the auto-research loop.

## Problem

What we need from an eval harness:

- **A scriptable Mode B runner** that takes (scenario, prompt versions, model config) and produces output.
- **A versioned golden dataset** of canonical scenarios. Once shipped, a golden version is frozen forever — improvements ship as the next version. This is what makes "did v3 beat v2?" answerable.
- **Mechanical and rubric metrics**, computed automatically, with structure that supports adding new metrics without rewriting old ones.
- **Run manifests** capturing system state per run, so any output is reproducible (or at least re-explainable) months later.
- **A reporting layer** that surfaces metric trends across runs.
- **CI integration** (eventually) — prompt PRs run eval against golden_v1 (or whichever version is current); regressions surface in PR reviews.

What we want to avoid:

- Eval as "we'll figure it out when Mode B exists." The cost of designing eval is high; the cost of not having it after Mode B ships is higher.
- Mutable golden datasets ("we improved scenario 3"). Mutating golden data destroys the comparability that makes auto-research work.
- LLM-judge metrics as the primary scoring mechanism. They're useful as supplements but introduce stochasticity that defeats the cross-run comparison goal.
- Synthetic photographers for Mode A eval. The interactive nature of Mode A makes auto-eval misleading; humans are the right evaluators there.
- Building the harness right now. Mode B doesn't exist; Phase 1 is about Mode A. The DESIGN matters now; the BUILD waits.

## Proposal

### Directory layout

```
data/eval/
├── golden_v1/                          # frozen forever once shipped
│   ├── manifest.json                   # which scenarios + which metric weights
│   ├── scenarios/
│   │   ├── 001_iguana_warm/
│   │   │   ├── scenario.toml           # brief, taste fragments, expected vocab usage
│   │   │   ├── raw.NEF                 # the test image (or a content-hash pointer)
│   │   │   └── reference.md            # human-curated reference outcome notes
│   │   ├── 002_manta_blue/
│   │   ├── 003_evening_pelagic/
│   │   ├── 004_high_iso_subject/
│   │   ├── 005_mixed_light_portrait/
│   │   └── ...                         # 5–10 scenarios in v1
│   └── README.md
└── golden_v2/                          # next golden set; v1 is frozen forever

src/chemigram/eval/
├── __init__.py
├── runner.py                           # run agent against scenarios in headless mode
├── scenarios.py                        # scenario loading and validation
├── metrics/
│   ├── __init__.py
│   ├── mechanical.py                   # tool-call sequencing, context-load order, protocol adherence
│   └── semantic.py                     # brief alignment, taste alignment, vocab-gap rate
├── reports.py                          # render eval reports
└── manifest.py                         # run manifests (per ADR-047)

metrics/                                # CI-tracked time-series of eval metric history
└── eval_history.jsonl                  # one JSON line per eval run, append-only
```

### Scenario format

Each scenario is a self-contained directory:

```toml
# data/eval/golden_v1/scenarios/001_iguana_warm/scenario.toml

[metadata]
id = "001_iguana_warm"
title = "Marine iguana, warm-light variant"
created = "2026-04-28"
tags = ["wildlife", "underwater", "warm-cast"]

[brief]
subject = "Adult marine iguana, half-submerged near volcanic rock"
intent = "Quiet, weighty image. Slate-blue water target, not cyan-pop."
constraints = [
  "Preserve skin texture (no aggressive denoise)",
  "Don't lose rock shapes in background",
]

[taste_fragments]
# A subset of taste.md entries relevant to this scenario
entries = [
  "Slate-blue water for cold-pelagic shots; cyan-pop reads tropical and is wrong.",
  "Lift shadows on subjects, almost always.",
  "Avoid `tone_compress_highlights` on bright water surfaces.",
]

[image]
# Either a file path or a content hash pointer
path = "raw.NEF"
sha256 = "a3f291..."   # optional verification

[expected]
# Loose expectations; not strict equality. Used by metrics.
likely_primitives = [
  "tone_lift_shadows",
  "wb_cooler_subtle",
  "structure_subtle",
]
forbidden_primitives = [
  "tone_compress_highlights",   # contradicts taste
]
expected_mask_targets = ["subject"]
expected_branch_count = "1-2"
```

### The eval runner

```python
from chemigram.eval import EvalRunner
from chemigram.mcp.prompts import PromptStore

runner = EvalRunner(
    golden_version="v1",
    prompt_versions={"mode_b/system": "v1", "mode_b/plan": "v3"},
    model_config={
        "provider": "anthropic",
        "model": "claude-opus-4-7",
        "temperature": 0.7,
    },
)

# Run all scenarios, or a single one
result = runner.run_all()                          # → EvalRunResult
# OR
result = runner.run_scenario("001_iguana_warm")    # → EvalScenarioResult

# Persist with run manifest
result.save("metrics/run_2026-04-28T14:30Z.json")

# Append to running history
result.append_history("metrics/eval_history.jsonl")
```

The runner:

1. Loads each scenario.
2. Spins up the engine in a headless mode (no MCP server; programmatic policy speaks the same protocol the agent would).
3. Invokes the configured LLM via the provider's API (real LLM call, not mocked) — passing the rendered prompts from PromptStore at the pinned versions.
4. Captures the resulting tool-call sequence + final state per scenario per candidate.
5. Computes metrics.
6. Writes a run manifest.

### Metrics — mechanical (cheap, deterministic)

Computed from the tool-call sequence and final state. No LLM judge required.

| Metric | Computation |
|-|-|
| `read_context_first` | Did `read_context()` appear before any edit call? Binary per scenario. |
| `propose_confirm_taste` | Did taste.md updates always go through propose+confirm? Binary. |
| `vocab_purity` | Fraction of edit calls that used existing vocabulary primitives (vs. attempted ad-hoc). |
| `vocab_gap_logged` | Did `log_vocabulary_gap()` get called when the agent reached for something missing? Rate. |
| `forbidden_primitives_used` | Did the agent use any primitives the scenario marks forbidden? Count. |
| `expected_primitives_used` | Of the scenario's `likely_primitives`, how many appeared? Coverage rate. |
| `mask_targets_match` | Did mask generation target the expected regions? Rate. |
| `candidate_count` | Did the agent produce the requested number of candidates? Binary. |
| `tool_call_count` | Total tool calls made (efficiency proxy; monitored only). |

These run in seconds. No LLM judge needed.

### Metrics — semantic (expensive, sampled or LLM-assisted)

Subjective metrics that resist purely mechanical scoring. Run optionally per ADR-031's pattern (heuristics first, LLM-judge as supplement when heuristics aren't enough).

| Metric | Approach |
|-|-|
| `brief_alignment` | Rubric-scored. Either human-rated on a sample of runs, or LLM-judge (Claude as judge) with an explicit rubric. |
| `taste_alignment` | Same. Did the candidates respect stated preferences in taste_fragments? |
| `candidate_diversity` | Pairwise comparison of the N candidates: how different are their tool-call sequences and final states? Computable mechanically (edit distance on call sequences) OR semantically (LLM-judge). |
| `reasoning_quality` | If the agent provided rationale alongside candidates, is the rationale coherent? LLM-judge. |

For v1, mechanical metrics are the gate; semantic metrics are advisory and run on a sample (10–20% of scenarios) to keep costs sane.

### Run manifests (per ADR-047)

Every run writes a JSON manifest:

```json
{
  "run_id": "2026-04-28T14:30Z",
  "git_sha": "abc123...",
  "golden_version": "v1",
  "prompt_versions": {
    "mode_b/system": "v1",
    "mode_b/plan": "v3",
    "mode_b/evaluate": "v1"
  },
  "model_config": {
    "provider": "anthropic",
    "model": "claude-opus-4-7",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "system": {
    "python_version": "3.12.3",
    "darktable_version": "5.4.1",
    "os": "Darwin 24.0.0",
    "config_hash": "..."
  },
  "scenarios_run": ["001_iguana_warm", "002_manta_blue", ...],
  "metrics": {
    "001_iguana_warm": {
      "read_context_first": true,
      "vocab_purity": 1.0,
      "expected_primitives_used": 0.67,
      "forbidden_primitives_used": 0,
      ...
    },
    ...
  },
  "metric_summary": {
    "vocab_purity_mean": 0.92,
    "expected_primitives_used_mean": 0.71,
    ...
  },
  "duration_seconds": 287.3,
  "total_tool_calls": 142,
  "errors": []
}
```

This is the unit that gets compared across runs.

### The auto-research workflow

With the harness in place, the iteration loop is:

1. **Hypothesize.** "I think `mode_b/plan_v3` will produce more diverse candidates than v2 because of the new diversity instruction."
2. **Snapshot.** Pin everything except the variable being tested. `golden_v1`, model_config, all other prompt versions.
3. **Run twice.** Once with v2, once with v3. Same scenarios.
4. **Compare manifests.** Did `candidate_diversity` go up? Did `vocab_purity` stay constant? Did `expected_primitives_used` change?
5. **Decide.** Ship v3, revert to v2, or try v4 with a different angle.

Auto-research is *systematic*: every change goes through a measured run before merging. It's *cheap* on the mechanical metrics (run time is bounded by LLM API latency, which is the dominant cost). And it's *honest*: the manifest captures everything that varied, so months later we can answer "why did we ship v3?"

### CI integration (Phase 5+)

Once the harness exists, CI on PRs that touch `src/chemigram/mcp/prompts/` triggers:

1. Run eval against golden_vN where N is the current version, using the PR's prompt versions.
2. Diff metrics against `metrics/eval_history.jsonl`'s baseline (latest main-branch run).
3. Surface any regression beyond a threshold (TBD; probably ~5% on key metrics).

Doesn't block merges automatically — surfaces them for review.

## Alternatives considered

### Live in production observability instead of a harness

Watch real Mode B sessions, log tool call sequences, compute metrics from production data.

**Why rejected.** Production data is non-comparable across time (different briefs, different photographers, different images). Auto-research requires fixed inputs. Production observability is complementary (RFC-014 covers session transcripts) but doesn't replace eval against golden data.

### Synthetic photographer for Mode A eval

Build a "photographer simulator" that responds to Mode A's prompts in plausible ways, run the loop, score outcomes.

**Why rejected.** The simulator IS the prompt. You'd be evaluating prompt-against-prompt, not prompt-against-real-use. And building a simulator that captures real photographer judgment is an entire research project of its own. Mode A eval stays mechanical; semantic Mode A eval stays human-rated on session transcripts.

### LLM-judge as the primary metric

Skip mechanical metrics, use Claude/GPT to score outputs end-to-end against rubrics.

**Why rejected.** Stochastic judges introduce run-to-run variance that defeats cross-run comparison. They're useful as supplements but can't be the gate. Heuristics-first matches `podcast_scraper`'s ADR-031 for the same reason.

### Per-PR eval running on PR opens

CI runs eval automatically on every prompt PR.

**Why rejected for v1.** API costs are real (the harness invokes the LLM, not a mock). For v1, eval runs locally and the developer commits the manifest output to the PR. CI eval can be added when prompt change frequency justifies the cost.

### Mutable golden datasets

Improve scenarios in-place ("scenario 3 had a bad brief; let me rewrite it").

**Why rejected.** Mutating destroys comparability. Improvements ship as `golden_v2`. ADR-046 locks this.

## Open questions

1. **Which scenarios go in golden_v1?** This is curation work. 5–10 scenarios spanning Marko's actual work (underwater wildlife, cold pelagic, warm pelagic, high-ISO night, mixed light) — but the specific list needs Marko's input. Defer until Phase 5; capture in a follow-up RFC or as part of the curation work itself.
2. **How are LLM-judge prompts versioned?** They're prompts too. They live in `src/chemigram/mcp/prompts/eval/` (a new sibling to `mode_a/`, `mode_b/`, `helpers/`) and follow the same conventions. RFC-016 + ADR-043/044/045 cover them.
3. **Should the harness support multiple LLM providers in one run?** Phase 5 question. If the goal is to compare Claude vs GPT, yes; if the goal is to ship Mode B with one provider, no.
4. **Do golden raws get committed to the repo?** Probably content-hashed pointers + photographer-supplied actual files (per the test fixtures convention in CONTRIBUTING.md). Defer to Phase 5 implementation.
5. **What's the time budget per eval run?** A 10-scenario, 3-candidates-each Mode B eval could be 30 LLM calls × ~30 seconds each = ~15 minutes wall-clock. Acceptable for occasional runs; too slow for per-commit. Plan accordingly.

## Decision summary

If accepted, the following ADRs lock the structural pieces:

- **ADR-046** — Golden dataset versioning (immutable, append-only)
- **ADR-047** — Run manifests for eval reproducibility

Build phasing:

- **Now (Phase 1):** Design only. Directory shape proposed, metrics enumerated, manifest format locked. No code.
- **Phase 5 (when Mode B lands):** Build `chemigram.eval`, curate `golden_v1`, run first auto-research iterations. CI integration deferred unless prompt change frequency demands it.

---

*RFC-017 · Accepted (design) 2026-04-28*
