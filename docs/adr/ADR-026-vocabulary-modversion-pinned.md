# ADR-026 — Vocabulary modversion-pinned to darktable version

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/modversion-pinning
> Related RFC · RFC-007

## Context

darktable's modules have versioned binary parameter formats (`modversion`). When a module's modversion changes (e.g., adding a new parameter, restructuring the C struct), `op_params` from the old version are not interchangeable with the new version. Old `.dtstyle` files become invalid for that module after the upgrade.

The starter vocabulary and community packs are calibrated to a specific darktable release. Without pinning, a vocabulary that worked in 5.4 might silently break or misrender after a 5.6 upgrade.

## Decision

Every vocabulary pack declares its calibrated darktable version in `manifest.json`:

```json
{
  "name": "starter-pack",
  "version": "1.0",
  "darktable_version": "5.4",
  "modversions": {
    "exposure": 7,
    "channelmixerrgb": 3,
    "sigmoid": 3,
    "highlights": 4,
    "...": "..."
  },
  "entries": [
    { "name": "expo_+0.5", "..." }
  ]
}
```

Each entry can also declare its own `modversions` for the modules it touches; pack-level declares the default.

CI runs vocabulary tests against the declared darktable version. If darktable bumps a `modversion` and the pack's declared version doesn't match the engine's runtime darktable version, the engine logs a warning at vocabulary load time. Vocabulary that targets a known-broken modversion mismatch can be flagged and excluded.

## Rationale

- **Predictability.** A vocabulary pack states which darktable it works with; mismatches are detectable.
- **Safety.** Silent renders with mismatched modversions could produce wrong results without surfacing the issue. Explicit pinning makes the failure mode loud.
- **Distribution.** Vocabulary packs can be tagged for darktable versions; users running darktable 5.6 know which packs are tested against it.
- **Maintenance.** When darktable bumps a modversion, the affected vocabulary entries can be re-authored, the pack's version bumped, and old entries marked deprecated.

## Alternatives considered

- **No pinning (assume vocabulary "just works"):** rejected — silent miscalculation is the worst failure mode.
- **Per-entry pinning only (no pack-level default):** considered. Per-entry pinning is more accurate but more verbose; pack-level default with per-entry override is the right balance.
- **Auto-detect modversion at load time and warn:** complementary, not a replacement. The pack's declared version is the contract; auto-detection at runtime is a sanity check.

## Consequences

Positive:
- Vocabulary packs are tagged and auditable per darktable version
- Photographers know which packs work with their darktable
- Mismatch failures are loud (warnings/blocked load), not silent miscalculations

Negative:
- Vocabulary maintenance work: when darktable bumps a modversion, affected entries must be re-authored (this is unavoidable; the pinning just surfaces it instead of hiding it)
- Pack metadata must be updated on each darktable release; this is contributor work but it's bounded

## Implementation notes

`src/chemigram_core/vocab.py.load_pack()` reads `manifest.json`, checks declared `darktable_version` against the runtime darktable version (queried via `darktable-cli --version`), logs warnings on mismatch. Entries with mismatched modversions are loaded but flagged in their internal record; the agent can choose whether to use them. RFC-007 deliberates the full handling strategy for modversion drift.
