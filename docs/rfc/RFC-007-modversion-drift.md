# RFC-007 — modversion drift handling

> Status · Draft v0.1
> TA anchor ·/constraints/modversion-pinning ·/components/synthesizer
> Related · ADR-026
> Closes into · ADR (pending) — specifies handling rules
> Why this is an RFC · ADR-026 commits to vocabulary modversion-pinning per pack. But the run-time question — what does the engine do when a vocabulary entry's modversion doesn't match the running darktable's modversion — is genuinely open. Several strategies are possible (block, warn, transparent migration, opportunistic re-export). The choice affects user experience in version-mismatch situations and the maintenance burden on vocabulary contributors.

## The question

When a vocabulary entry's declared modversion doesn't match the running darktable's reported modversion for that operation, what happens?

Several response strategies:

1. **Strict — refuse to apply mismatched entries.** Loud failure; user must update vocabulary or downgrade darktable.
2. **Warn-only — apply anyway, warn loudly.** Tries the operation; render may be wrong but at least proceeds.
3. **Best-effort migration — try to translate old op_params to new format.** Per-module migration logic. High maintenance.
4. **Transparent re-author — call darktable to translate.** darktable's library opens old XMPs and reads them; might be able to produce a re-encoded op_params.

Each has different costs and risks. The right answer probably mixes: strict for some operations, warn-only for others, with documented per-module guidance.

## Use cases

- darktable 5.4 → 5.6 minor update; 1-2 modules bump modversion. Most vocabulary still works; some entries need re-authoring.
- Major release with widespread modversion bumps (rare). Most vocabulary is invalidated; pack maintainers re-author.
- A photographer running an older darktable than vocabulary targets (they pinned 5.4; vocabulary is calibrated for 5.6). Reverse-direction mismatch.

## Goals

- Photographers know when their vocabulary is at risk of misrendering
- Maintenance burden on vocabulary contributors is bounded
- Failure modes are loud, not silent

## Constraints

- TA/constraints/opaque-hex-blobs — engine doesn't decode op_params
- TA/constraints/modversion-pinning — vocabulary declares modversions
- ADR-008 — opaque blob copying is the synthesizer's only operation on op_params

## Proposed approach

**Strategy: warn-loud, configurable to block.**

Default behavior on modversion mismatch:
1. **Engine logs a warning** at vocabulary load time, naming the affected entries and the modversion mismatch.
2. **The agent surfaces the mismatch** in the session output ("warning: 3 vocabulary entries are calibrated for darktable 5.4; you're running 5.6 — these may render unexpectedly: `expo_+0.5`, `wb_warm_subtle`, `tone_lifted_shadows_subject`").
3. **The mismatched entries are still loaded**, allowing the photographer to evaluate the actual visual difference rather than blocking workflow.
4. **The render result** is what the photographer judges. If it looks fine, the modversion bump didn't change the binary format meaningfully (this happens). If it looks wrong, the photographer re-authors.

Configuration override:
- `~/.chemigram/config.toml` can set `[vocabulary] strict_modversion = true` to block mismatched entries instead of warning. Default false.

Vocabulary maintenance:
- When a darktable version bumps a modversion, the affected vocabulary pack publishes a new pack version with re-authored entries.
- Pack-level CI can be configured to test against multiple darktable versions (e.g., 5.4, 5.6, 5.8) and report which entries pass/fail per version.
- Old pack versions remain available for users on older darktable.

## Alternatives considered

- **Strict by default (block mismatched entries):** rejected — too aggressive. Modversion bumps often don't change binary format meaningfully (e.g., adding a new optional field at the end of the struct). Blocking would cause unnecessary friction.

- **Best-effort migration (translate op_params):** rejected — requires per-module struct knowledge, contradicting ADR-008 (opaque-blob principle). Would also need maintenance for every modversion bump on every module.

- **Transparent re-author via darktable:** considered. Opening the dtstyle in darktable, exporting to XMP, may produce a re-encoded op_params. Worth exploring as a tooling option later, but as a runtime strategy it adds latency and a darktable round-trip per mismatch. Not v1.

- **Silent fallback to last-known-working modversion:** rejected — silent is the worst failure mode.

## Trade-offs

- Warn-only by default means some misrenders may slip through without the photographer noticing immediately. Mitigated: the warning is visible; render previews are inspected by the photographer naturally.
- Vocabulary maintenance burden grows with darktable releases. Mitigated: per-pack CI catches issues; community shares burden.
- The `strict_modversion = true` configuration adds complexity. Mitigated: it's a single toggle; default false.

## Open questions

- **What's "loud enough" warning?** Is logging to stderr sufficient? Should the agent inject the warning into the session output? Should the user have to acknowledge it once per session? Proposed: the agent surfaces it in the session output; photographer sees it; no acknowledgement gate.
- **Reverse-direction mismatch (vocab targets newer darktable than installed).** Proposed: same warning; same default-allow behavior. Render may be wrong because newer struct fields are missing in old darktable; visual inspection is the truth.
- **Pack version compatibility ranges.** Should packs declare ranges of compatible darktable versions, not just a single? Proposed: yes — `darktable_version` can be a single version (`"5.4"`) or a range (`"5.4-5.6"`). Engine checks runtime against range.
- **CI that tests vocabulary against multiple darktable versions.** Implementation-level concern; specify in pack-level CI documentation, not engine.

## How this closes

This RFC closes into:
- **An ADR specifying the warn-loud-with-strict-config approach.**
- **An ADR or amendment to ADR-026** documenting the version-range syntax (`"5.4-5.6"`) for pack manifests.

## Links

- TA/constraints/modversion-pinning
- ADR-008 (opaque-blob carriers)
- ADR-026 (vocabulary modversion-pinned)
