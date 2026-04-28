# ADR-047 — Run manifests for eval reproducibility

> Status · Accepted
> Date · 2026-04-28
> TA anchor · /components/eval
> Related RFC · RFC-017
> Inspired by · Issue #379 in chipi/podcast_scraper

## Context

The eval harness (per RFC-017) produces metrics per run. Without capturing the full system context that produced those metrics, comparing runs across time becomes guesswork — "did prompt v3 win because the prompt was better, or because we upgraded the model that day, or because darktable shipped a new release?" The auto-research workflow is honest only if every run carries enough context to be re-explained later.

The reference pattern is `chipi/podcast_scraper`'s Issue #379 work: every run writes a manifest capturing system state (Python version, OS, GPU info, model versions, git commit SHA, config hash) plus per-stage timings and metrics. Comparison across runs is then a matter of inspecting manifests, not reconstructing missing context.

## Decision

**Every eval run writes a JSON manifest** capturing the full set of identifiers, configurations, and outputs that produced the metrics. The manifest is the unit of comparison — running one manifest against another (e.g., "v2 run vs v3 run") is what auto-research is.

Manifest schema:

```json
{
  "run_id": "2026-09-20T14:30:00Z",
  "timestamp": "2026-09-20T14:30:00Z",
  "git_sha": "abc123def456...",
  "git_dirty": false,
  "golden_version": "v1",
  "prompt_versions": {
    "mode_b/system": "v1",
    "mode_b/plan": "v3",
    "mode_b/evaluate": "v1",
    "mode_b/refine": "v1"
  },
  "model_config": {
    "provider": "anthropic",
    "model": "claude-opus-4-7",
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "system": {
    "python_version": "3.12.3",
    "platform": "Darwin 24.0.0 arm64",
    "darktable_version": "5.4.1",
    "chemigram_version": "0.5.0",
    "config_hash": "sha256:..."
  },
  "scenarios_run": [
    "001_iguana_warm",
    "002_manta_blue",
    "003_evening_pelagic"
  ],
  "metrics": {
    "001_iguana_warm": {
      "read_context_first": true,
      "vocab_purity": 1.0,
      "expected_primitives_used": 0.67,
      "forbidden_primitives_used": 0,
      "candidate_count": 3,
      "tool_call_count": 18,
      "duration_seconds": 47.2
    },
    "002_manta_blue": { ... },
    "003_evening_pelagic": { ... }
  },
  "metric_summary": {
    "vocab_purity_mean": 0.92,
    "expected_primitives_used_mean": 0.71,
    "forbidden_primitives_used_total": 0,
    "tool_call_count_mean": 19.3
  },
  "duration_seconds": 287.3,
  "total_tool_calls": 142,
  "errors": []
}
```

Manifests are written to `metrics/runs/<run_id>.json` and appended (one line each) to `metrics/eval_history.jsonl` for time-series analysis.

## Rationale

- **The manifest IS the run.** Without it, a metrics number is a number with no provenance. With it, six months later we can answer "was that 0.92 vocab_purity from prompt v2 or v3?"
- **Captures everything that varied.** Git SHA, prompt versions, model config, system info, golden version. If one of these changed between runs, the manifest shows it.
- **`config_hash` covers what the explicit fields don't.** A run with a custom config (different vocabulary scope, different masker, different threshold) hashes the config; comparison runs can verify they used the same config without comparing every field by hand.
- **Per-scenario metrics + summary.** Per-scenario lets you see "scenario 4 regressed badly even though the mean is fine"; summary gives the headline number.
- **Append-only `eval_history.jsonl` enables trends.** A scatter-plot of `vocab_purity_mean` over time, colored by `prompt_versions["mode_b/plan"]`, tells the story of the prompt's evolution.
- **Errors as a top-level field.** Failed scenarios stay visible in the manifest rather than disappearing as silent gaps.

## Alternatives considered

- **No manifest (just metrics):** loses the ability to explain runs after the fact. The metrics-without-context problem.
- **Manifest as YAML or TOML:** JSON is the standard for machine-read structured data; toolchain (`jq`, etc.) is rich. JSON wins.
- **Manifest in a database:** considered (sqlite for the history). Overkill for v1; flat files are fine until query patterns demand otherwise. JSONL gives append-friendly + grep-friendly + jq-friendly.
- **Embedded in the metrics file (no separate manifest):** considered. Splitting "what produced this" from "what was measured" is cleaner; per-scenario metrics nest naturally under the run-level manifest.
- **Less detail (just prompt versions and metrics):** loses the ability to debug "did the model change?" Auto-research depends on knowing all the inputs, not just the named ones.

## Consequences

Positive:

- Auto-research is honest: comparisons reference real manifests, not vague memory
- Time-series analysis of metric evolution is possible (eval_history.jsonl)
- Months-old metrics are still explainable
- Failed runs stay visible, not silent
- Standard tooling (`jq`, etc.) works directly

Negative:

- Per-run disk overhead (small — a manifest is ~5–20 KB)
- Discipline required: developers must run eval through the harness, not ad-hoc, to get a manifest. Mitigation: the harness IS the canonical interface; ad-hoc running shouldn't happen in the auto-research loop.

## Implementation notes

- Manifest writing happens in `chemigram.eval.manifest`. The eval runner (per RFC-017) calls this at the end of every run.
- `metrics/runs/` and `metrics/eval_history.jsonl` are gitignored by default — they're outputs, not source. Specific runs that establish baselines or document major decisions can be committed explicitly (e.g., `metrics/baselines/golden_v1_first_run.json`).
- Config hashing uses SHA-256 of the canonicalized config (sorted keys, no whitespace). Implementation lives alongside `chemigram.core` config loading.
- The `system` section is captured at run start using stdlib (`platform`, `sys`) plus a `darktable-cli --version` subprocess call.
- Run IDs are ISO 8601 UTC timestamps with seconds precision (`2026-09-20T14:30:00Z`). Collision is unlikely; if it happens, the second run gets a `_2` suffix.
- Eval comparison utilities (`chemigram.eval.reports`) load two manifests and produce a diff report — what changed, what stayed the same, which metrics moved.
