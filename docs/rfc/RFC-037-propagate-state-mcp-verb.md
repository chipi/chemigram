# RFC-037 — `propagate_state` MCP verb (anchor-and-sync workflow)

> Status · Draft v0.1
> TA anchor · /contracts/mcp-tools · /components/synthesizer · /components/versioning
> Related · RFC-031 (apply_per_region — single-image batched), RFC-032 (named-mask vocabulary), photographer-workflows survey Gap #4
> Closes into · ADR-NNN (pending)
> Why this is an RFC · Surfaced cleanly by R2 (Wedding/Event) and reinforced by R3 — 4/6 wedding photographers ship anchor-and-sync as a load-bearing technique. chemigram's `apply_primitive --stdin` propagates the same primitive call across N image_ids but does *not* propagate edit STATE (the resulting XMP / vocabulary entries) from a source image to N targets. Wedding-defining gap. Multiple legitimate API shapes; the right answer needs deliberation: should propagation copy raw vocabulary entries, copy resolved XMP plugins, or replay the op-log? Each costs differently in semantics, atomicity, and downstream state-tracking. Genuinely-open question.

## The question

Across the 6-genre photographer-workflows survey, the wedding/event genre surfaced **anchor-and-sync** as a load-bearing technique (4/6 photographers; defining for the genre). The pattern:

1. Photographer ingests ~3000 frames from a wedding.
2. Culls to ~300 deliverables.
3. **Edits one anchor image per lighting situation** (~5-15 lighting groups: prep / ceremony / reception / portraits / dance).
4. **Syncs the anchor's edit state to all N images in that lighting group** (~30-100 images per group).
5. Per-image fine-tuning on outliers.

Step 4 — propagating edit state from one image to N others — is the architectural primitive missing from chemigram. Today's options:

- **`apply_primitive --stdin`** — propagates the *same primitive call* across N images. Works for "apply skin_uniformity to these 50 images at strength -0.3" but not for "this image's full edit state (5 primitives + 2 named masks + 1 dodge/burn batch) should appear identically on these 50 images." The state-propagation isn't expressible.
- **Manually re-apply each step on each image** — defeats the purpose; this IS what anchor-and-sync exists to avoid.
- **Author an L2 look from the anchor** — works conceptually (the photographer's edit becomes a "personal preset"), but L2 looks ship as fixed-value composites and authoring one requires manual op_params extraction. Not a workflow tool.

The question: **what's the right MCP-verb shape for "propagate this image's edit state to N target images"?**

## Use cases (post-survey)

The dominant cases from R2:

- **Wedding lighting groups** (4/6 photographers) — Hunter & Sarah ship 30+ presets per (lens × lighting); Stripling/Flemming/Ronald propagate via Sync+Clipboard; Davidson via anchor + Sync. All want "edit one image, propagate to N similar-light images."
- **Per-camera batch** (Flemming) — sync color baseline per camera body; multiple-photographer wedding teams need this when bodies differ.
- **Per-ISO batch** (SLR Lounge) — sync noise reduction per ISO bucket; especially relevant to wildlife (R3) where high-ISO batches recur.
- **Time-bucketed batch** — every reception sequence shot in 5-minute windows shares lighting; sync within window.

Cross-genre echoes:
- **Landscape (R1)** — repeat trips to the same location may yield similar-light batches; apply the same look across a series.
- **Wildlife (R3)** — bird-photography burst sequences within seconds share exposure / WB / NR settings; anchor-and-sync would let the photographer edit one frame from a 20-frame burst and propagate.
- **Food/Product (R3)** — multi-shot product sets often share lighting and need identical color processing.

Wedding is the genre where this is *defining*; the others are where it's *helpful*.

## Goals

1. **One agent move = one tool call.** "Propagate this image's edit state to these 50 images" is one tool call, not 50.
2. **Atomic semantics.** Either all targets receive the propagated state, or none do (either-or; partial application is a UX failure mode).
3. **Inherit-everything-by-default.** The reference image's edit IS the contract. Whatever the photographer did to nail it — WB, exposure, sigmoid, color grade, masked moves — that's what propagates. **No scope-preset menu.** Same mental model as Lightroom's Sync function: "sync this edit to these targets" without first picking categories. Predefined scope presets force a "what counts as WB?" taxonomy debate; the photographer's choices ARE the answer.
4. **Auto-exclude framing-bound ops** (the LR-parity discipline). Settings that depend on per-image content / coordinates don't propagate by default: drawn masks (eye ellipse, retouch ellipse), compositional crop, spot retouch (heal/clone), L1 EXIF-bound camera baselines. Opt-in via `include_per_image: true` for the rare tripod-fixed series case.
5. **Optional fine-grained opt-out** via `exclude_ops: list[str]` for the rare "everything except <X>" case (e.g., "inherit everything but keep each target's individual exposure"). Default empty.
6. **Composable with named masks (RFC-032).** Named-mask references propagate cleanly because they're abstract (e.g., `mask_skin_region` resolves per-image at apply time). Drawn masks are caught by goal 4.
7. **Composable with `apply_per_region` (RFC-031).** Batched per-region calls in the anchor's history propagate as batched per-region calls on each target.
8. **One snapshot per target image.** Each target's snapshot history shows a clean "propagated from <source_image>" entry.
9. **Versioning-friendly.** The propagation respects the per-image content-addressed snapshot store (ADR-018).

## Constraints

- **TA/contracts/mcp-tools** — adding a verb requires affirmative justification. The narrow MCP surface is a feature.
- **TA/components/synthesizer** — propagating state means re-applying the source's vocabulary entries against each target's baseline. The synthesizer already does this for single-image apply; multi-image apply just orchestrates N calls.
- **TA/components/versioning** — each target gets one new snapshot per propagation. The op-log entry references the source image's hash for traceability.
- **ADR-002 (SET-replace semantics)** — propagating state replaces conflicting modules in each target. Existing target state for non-overlapping ops is preserved.
- **ADR-051 (same-module collision)** — `multi_priority` allocation per propagated module follows the same rules as `apply_per_region` (Path B in synthesize_xmp).

## Proposed approach

**Add a single MCP verb: `propagate_state(source_image_id, target_image_ids, *, exclude_ops?, include_per_image?, label?) → results`.**

Where:
- `source_image_id` — the anchor image.
- `target_image_ids` — list of image_ids; soft cap at 200 (enough for typical wedding lighting group; well above bird-burst range).
- `exclude_ops` — optional list of operation names to skip (default `[]`, i.e., inherit everything). For the rare "everything except <X>" case.
- `include_per_image` — optional boolean (default `false`) to override the framing-bound auto-exclusion (drawn masks, spot retouch, crop, L1 baselines). Use for tripod-fixed series.
- `label` — optional snapshot label per target.
- Returns: `{results: [{image_id, snapshot_hash, applied_ops}], n_succeeded, n_failed}`.

### Resolution algorithm

1. **Read source state.** Load the source image's current XMP via `current_xmp(source_workspace)`.
2. **Filter ops** — by default keep everything; auto-exclude the framing-bound op set (drawn-mask-bound entries, retouch, crop, L1) unless `include_per_image=True`. Drop any op explicitly listed in `exclude_ops`.
3. **For each target image:**
   a. Load the target's current XMP as baseline.
   b. Apply the filtered ops in source's order. Same module + same multi_priority replaces (per ADR-002 SET semantics); different multi_priority appends (Path B).
   c. **Atomic check** — if any op fails (modversion mismatch, parameter validation), abort the entire batch (no targets receive partial state).
   d. Snapshot per target with the supplied or default label `"propagated from <source_image_id> [<n_ops> ops]"`.
4. **Return aggregate result** with per-target snapshot hashes.

### Atomicity discipline

The validation phase walks ALL targets first; only after all validations pass does any apply happen. Failures hard-reject:

- Source image has no current XMP (no anchor to propagate from).
- Source XMP's history is empty (nothing to propagate).
- Any target image not found.
- Any target's modversion conflicts with the source's (rare; surfaces stale-pack drift).
- Filter (auto-exclusions + caller-supplied `exclude_ops`) produces empty op set.
- N targets exceeds soft cap (200).

### Default framing-bound exclusions (the LR-parity discipline)

Same discipline as Lightroom's Sync — settings that depend on per-image content / coordinates don't propagate. By default, propagation excludes:

- **Drawn-form mask history entries** (`dt_form` masks have coordinate-specific geometry — not portable).
- **Spot retouch entries** (heal/clone per RFC-025 / ADR-087; location-specific).
- **Compositional crop** (per-image framing).
- **L1 EXIF-bound camera baselines** (per-camera; usually consistent in batch but propagating across mixed-camera sets produces wrong color science).

Override: `include_per_image=True` for the rare case where the photographer explicitly wants to propagate framing-bound moves across a fixed-camera-tripod sequence (architectural still life, brackets, time-lapse).

## Alternatives considered

**Author an L2 look on the fly from the anchor and apply it.** The "anchor becomes a personal preset" framing. Rejected as the *primary* path because:
1. L2 looks today are fixed-value `.dtstyle` files + manifest entries; authoring one programmatically from a live edit state is a substantial engineering hit.
2. It produces a permanent vocabulary artifact for what's often an ephemeral session decision (the photographer doesn't want every wedding lighting group becoming a permanent L2 look in their pack).
3. The scope-control story is awkward — L2 looks are all-or-nothing; can't `wb_only`-apply an L2 look without splitting it.

A *future* enhancement could combine: photographer applies propagated state, then optionally promotes the propagated state to a personal-pack L2 look. That's separable and worth a follow-up RFC if Phase 2 evidence warrants.

**Extend `apply_primitive --stdin` to accept N primitives.** Already exists for stdin batches of *one* primitive across N images. Extending to N primitives means deriving the primitive list from somewhere — the natural place is the source image's XMP, which is exactly what `propagate_state` proposes. Rejected as a CLI extension because the semantic surface needs more than `--stdin` exposes (scope, atomicity, op-log).

**Use chemigram's existing branch / merge model (ADR-018).** The per-image snapshot store has branches; could each target image have a "propagated" branch tracking the source? Rejected because branches are per-image, not cross-image. Cross-image state-replication isn't what branches are for.

**Background-job model — propagate asynchronously, return job ID, photographer polls for completion.** Tempting for large batches (200 images × 5-second-each propagation = 17 minutes). Rejected for v1 because chemigram is single-process (TA/constraints/single-process); async job tracking is a substantial scope expansion. Atomic-synchronous is fine for v1; revisit if photographer feedback shows real wait pain.

**Per-target customization at propagation time (e.g., apply with N% strength scaling per image).** Tempting but conflates RFC-035 (parametric L2 strength) with this RFC. Defer to RFC-035 + per-target parameter overrides as a follow-up.

## Trade-offs

- **+1 MCP verb.** Acceptable; closes the highest-recurrence cross-genre workflow gap not yet addressed.
- **Soft cap at 200 targets.** Wedding lighting groups typically max out at ~80-100 images per group; bird bursts at ~30. 200 is generous-but-finite; revisitable if real workflows hit it.
- **Drawn-mask exclusion is opinionated.** Some photographers might want them propagated. The default favors the right-thing-by-default; the opt-in flag preserves flexibility.
- **Multi-modversion targets.** If source uses colorequal mv4 and target's XMP references mv3, propagation surfaces a real drift. Hard-reject is the right discipline (per RFC-007 / ADR-082); offers the photographer clear feedback rather than silent-bad-render.

## Open questions

1. **Scope preset definitions.** What ops fall into `"wb_only"` (just temperature?) vs `"color_only"` (temperature + colorequal + colorbalancergb?) vs `"tone_only"` (sigmoid + tone_eq + exposure?)? Propose: documented in `vocabulary-patterns.md`; `"all"` is the default.
2. **Op-log entry shape.** How does each target's op-log record the propagation? Propose: `{op: "propagate_state", source_image: "...", source_hash: "...", n_ops: N, scope: "..."}`. The source's hash anchors the propagation for traceability; a future "re-propagate from source's HEAD" recipe becomes possible.
3. **What happens when targets have unrelated edits already?** The default is SET-replace (per ADR-002) — propagated ops replace any matching ops on the target; non-matching ops on the target persist. Worth confirming this is the right discipline for wedding workflow specifically.
4. **CLI surface shape.** `chemigram propagate-state <source> --to <id1> <id2> ... --scope <...>`? Or via stdin: `chemigram propagate-state <source> --stdin --scope all`? Propose: support both — explicit list for small batches, stdin for typical wedding scale.
5. **Render-validation feedback.** Should `propagate_state` render-preview a few targets after propagation to surface obvious failures? Propose: no for v1 (would slow large batches; the existing render-preview tool is photographer-driven). Document the rendering recommendation in `vocabulary-patterns.md`.

## How this closes

One ADR:

- **ADR-NNN — `propagate_state` MCP verb + scope semantics + atomic discipline** — formalizes the verb signature, the scope preset definitions, the drawn-mask exclusion discipline, the op-log structured payload, the soft cap, and the multi-modversion-targets policy.

**Implementation effort estimate:** 3-5 days. Single core function (synth-from-source), single MCP verb, one CLI command, ~15-20 unit tests + integration tests for multi-image scenarios. Visual-review checkpoint validates wedding-scale scenarios (50-100 image lighting group propagation).

## Links

- TA/contracts/mcp-tools (this is the modification surface)
- TA/components/synthesizer (re-uses existing synth path per target)
- TA/components/versioning (snapshot per target; op-log entry references source hash)
- Related: RFC-031 (apply_per_region — single-image batched; this RFC is multi-image batched), RFC-032 (named masks propagate cleanly), RFC-035 (per-target strength scaling — future extension)
- Source: `docs/photographer-workflows-survey.md` Gap #4 — wedding-defining (4/6); cross-genre echoes in landscape series, wildlife bursts, multi-shot product sets
- Validation gate: `docs/guides/darkroom-session-debt.md` will get a new item once this RFC's implementation lands — wedding-scale propagation visual review
