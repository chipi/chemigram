# RFC-031 — Batched per-region adjustment

> Status · Draft v0.1
> TA anchor · /contracts/mcp-tools · /components/mcp-server · /components/synthesizer
> Related · RFC-029 (compositional masks at apply time / ADR-084), RFC-024 (range masks / ADR-085), RFC-025 (spot removal / ADR-087), RFC-026 (LLM-vision masking / ADR-086), `docs/photographer-workflows-survey.md`
> Closes into · ADR-NNN (pending)
> Why this is an RFC · The capability is already composable from existing primitives (drawn / parametric / range masks plus `apply_primitive`). The genuinely open question is *workflow ergonomics*: should chemigram surface a single batched meta-tool, multiple pattern-specific verbs, transactional brackets, or none of those — letting the agent loop produce N separate calls? Each option costs something different in tool surface, snapshot semantics, and how the agent reasons about a move.

## The question

Across the photographer-workflows survey (12 working photographers, 6 portrait + 6 landscape), the single highest-recurrence gap was **batched per-region adjustment** — 7/12 photographers reach for it as a load-bearing technique. Variants:

- **Dodge and burn on a face** — Aaron Nace, Sean Tucker, Lindsay Adler — typically 5-15 small mask-bound exposure adjustments per portrait, articulated by photographers as one move ("I'm sculpting the face"), not 12.
- **Dodge and burn on a landscape** — Nick Page, Marc Adamus, Serge Ramelli, Mike O'Leary — same shape: brighten the foreground rocks, deepen the cloud shadows, lift the catchlight on water, all as one cohesive sculpting pass.
- **Eye-region contrast lift** (portrait) — separate +exposure on each iris + selective sharpening on lashes + slight saturation lift on iris color — articulated as "fix the eyes," produced as 3-5 calls.
- **Skin spot harmonization** — small per-region color shifts on a half-dozen patches, articulated as "even out the skin," produced as 5-10 calls.

Today each region is a separate `apply_primitive(image_id, primitive_name, mask_spec=...)` call. For a typical portrait dodge-and-burn pass, the agent emits 5-15 such calls back-to-back. This works, but it produces:

1. **Snapshot churn** — 5-15 snapshots in the per-image content-addressed object store for what photographers conceive of as one move. `log` becomes unreadable; `diff` between two coherent edit states crosses 12 hops of intermediate gibberish.
2. **Agent reasoning noise** — the agent has to reason about each region as an independent decision and re-establish the "this is a coherent dodge/burn pass" framing each turn. The framing is lost.
3. **Cost overhead** — N MCP turns instead of 1; N prompt-context refreshes; N tool-result formatting passes.
4. **Verbosity in `vocabulary-patterns.md`** — every pattern doc that uses dodge/burn has to describe the N-call manual workflow.

The wire is right; the ergonomics aren't. **What's the right surface for "this is one move with internal structure"?**

## Use cases

Concretely, the agent should be able to express each of these as a single coherent move:

- **Portrait dodge-and-burn** (Nace 6-step workflow, Step 5): brighten cheekbones, brighten nose-bridge highlight, brighten brow ridge, deepen jaw, deepen temple shadow, deepen under-eye recess. 6 regions, all `exposure` op, mixed signs.
- **Landscape dodge-and-burn** (Page luminosity-mask workflow): lift foreground rocks (+0.3 EV), lift water highlights (+0.2 EV), deepen cloud shadows (-0.4 EV), deepen frame edges (-0.2 EV). 4 regions, `exposure` op, mixed signs.
- **Eye-region detail lift** (Adler 3-step retouch): +exposure on each iris; +sharpening on each lash region; +saturation on each iris color. 3 ops × 2 regions = 6 calls collapsed into 1 batched move.
- **Skin spot harmonization** (Woloszynowicz Skin Tone uniformity workaround): selective hue/sat shifts on 5-8 small mask-bound regions in the orange-skin band. Same op, varying parameters.

Each is conceived by the photographer as one move and should be expressible by the agent as one tool call.

## Goals

1. **One agent move = one tool call** for the canonical batched patterns above.
2. **One snapshot per move** — the snapshot object store reflects the photographer's conceptual unit, not the implementation's per-region granularity.
3. **Single op-log entry** with structured `regions` payload — `log` and `diff` remain readable.
4. **No expansion of the MCP verb count** beyond what's necessary — the narrow surface is a feature (TA/components/mcp-server). Prefer one batched verb over N pattern-specific ones.
5. **Composable from existing mask primitives** — drawn / parametric / range masks per RFC-029/024/026 → ADR-084/085/086. No new mask machinery.
6. **Compatible with parameterized vocabulary** — values per region must work with the parameterized `apply_primitive` arg shape (RFC-021 / ADR-079).

## Constraints

- **TA/constraints/single-process** — no IPC, no daemon. Batching happens within one MCP turn.
- **TA/constraints/serial-renders** — no concurrent darktable invocations. (Not directly relevant here since synthesis is the bottleneck, not render — but worth naming.)
- **TA/constraints/agent-only-writes** — every state change is an explicit tool call; no background mutations. A batched move is one explicit tool call, satisfying this.
- **ADR-018 / content-addressed storage** — snapshot semantics must remain deterministic. Batched moves produce one canonical synthesized XMP, hashed once.
- **Narrow MCP tool surface** (ADR-033) — adding a verb requires affirmative justification.

## Proposed approach

**Add one new MCP verb: `apply_per_region(image_id, primitive_name, regions, *, label?) → state_after, snapshot_hash`.**

Where `regions` is a list of `{mask_spec: <RFC-029 mask spec>, parameter_values?: <RFC-021 params>}` entries. The verb:

1. Resolves `primitive_name` to a vocabulary entry (per RFC-021 — supports parameterized entries).
2. For each region: synthesizes the entry's dtstyle with the given `parameter_values`, bound to the region's `mask_spec`. Uses the existing `apply_with_mask` core helper (TA/components/synthesizer) under the hood.
3. **Composes all regions into a single synthesized XMP** — N module instances of the same op-name in the per-image XMP, each with its own mask spec, in order. The collision behavior follows ADR-051 (same-module-collision = stack semantics for masked instances).
4. Snapshots **once** — the hash reflects the post-batch XMP state.
5. Writes **one** op-log entry with structured payload `{op: "apply_per_region", primitive: "exposure", n_regions: 6, regions: [{mask_summary, parameter_values}, ...]}`.

**The vocabulary stays untouched.** No new dtstyles. No new mask types. No new layer. This is a workflow-shape primitive, not a vocabulary primitive — it operates on existing entries with existing masks, just batched.

**Restriction (deliberate, narrow scope):** the batched verb takes **exactly one `primitive_name`** for all regions. Mixed-op batches (e.g. eye-detail-lift = +exposure + +sharpening + +saturation across regions) **are not batched in this RFC**. The agent emits one `apply_per_region` per primitive: one for the exposure pass, one for the sharpening pass, one for the saturation pass. That's 3 calls instead of 6 for an eye-detail move — a real win — but doesn't pretend to solve mixed-op-mixed-region batching, which is a substantially larger surface and a different question.

The single-primitive restriction matches how dodge-and-burn (the dominant case, 7/12 recurrence) actually works: it's *always* one op (`exposure`) varied across regions. It's the eye-detail and skin-spot patterns where this restriction bites. We accept the tradeoff explicitly.

## Alternatives considered

**Agent-loop convention only — no new tool, document the pattern in `vocabulary-patterns.md`.** Rejected because the snapshot-churn problem is real (5-15 snapshots in the object store per dodge/burn move) and the conceptual-unit-loss problem is real (the agent reasons about each region independently and re-establishes "this is a dodge/burn pass" each turn). Documenting the pattern doesn't fix either. The MCP turn-cost is also non-trivial at 5-15× per move; in agent-economic terms, this is the most expensive part of the loop.

**Pattern-specific verbs — `apply_dodge_burn`, `apply_eye_lift`, `apply_skin_uniformity`.** Rejected because it expands the tool surface combinatorially. Each new pattern surfaced by future research adds another verb. The narrow MCP surface is a feature (ADR-033) — N verbs that are special-cases of one batched verb violate that. The first verb you add ("dodge/burn") is fine; the third you add reveals the pattern.

**Transactional brackets — `begin_batch(image_id) / apply_primitive ... / end_batch()`.** Rejected because: (a) it introduces transactional semantics that don't otherwise exist in the MCP surface — every other tool is one-call-one-effect; (b) the agent has to reason about an open transaction, which is a new failure mode (what if the agent forgets to close, what if a render call lands mid-batch, what does `get_state` return mid-batch); (c) snapshot atomicity becomes a question (one snapshot per batch? one per call inside a batch?). Genuinely simpler to make the batched call atomic-by-construction.

**Mixed-op batched verb — same shape but each region carries its own `primitive_name`.** Rejected for v1.10 (deferred). The single-primitive restriction above covers the 7/12 dominant case (dodge/burn) cleanly. Mixed-op batching opens questions about cross-op ordering inside a batch, parameter-shape uniformity (different ops have different parameters), and how `log`/`diff` summarize a heterogeneous batch. Worth a follow-up RFC after we have v1.10 evidence on whether mixed-op batches actually recur in practice or whether agents just emit two single-op batched calls in sequence.

**Make `apply_primitive` itself accept an optional `regions` parameter.** Rejected because it overloads a tool that's currently one-region-or-no-mask, and it makes the simple case visually noisier (every existing call site has to confront whether to batch). Cleaner to ship the batched form as a sibling verb (the `apply_spot` precedent — RFC-025/ADR-087 added a sibling verb rather than overloading `apply_primitive`).

## Trade-offs

- **+1 MCP verb** — but the alternatives are worse (N pattern-specific verbs, or transactional state). The narrow-surface discipline takes the +1 hit because it prevents the +N hit later.
- **Single-primitive restriction** — the eye-detail and skin-spot patterns still take 2-3 batched calls instead of 1. Acceptable tradeoff for v1.10; revisitable if mixed-op patterns recur strongly in subsequent genre research.
- **Snapshot semantics — N regions in one snapshot mean rolling back a single bad region requires either a manual edit or a full revert.** This is the same discipline that already applies to a single `apply_primitive` call with a complex mask: if you don't like the mask, revert and reapply. Photographers conceive these as atomic moves, so atomic rollback is correct.
- **Op-log payload schema change** — the structured `regions` payload is a new shape. Tooling that parses op-log entries (currently: `log` MCP tool, `diff`) needs to handle it. Surface area is small; localized to two tools.

## Open questions

1. **Parameter validation across regions** — the parameterized vocabulary contract (ADR-079) hard-rejects out-of-range parameter values. Do we hard-reject the *whole batch* if any region is out of range, or partially apply the valid ones? Proposal: hard-reject the whole batch (atomic semantics) — but worth confirming.
2. **Mask-spec normalization** — drawn masks per ADR-084 have content-addressed mask hashes; if the same mask shape appears in two regions of one batch, do we deduplicate the stored mask bytes? Proposal: yes (existing mask deduplication already handles this; should fall out for free).
3. **Empty-batch handling** — `apply_per_region(image_id, primitive_name, regions=[])` — error or no-op? Proposal: hard error. There's no semantically meaningful empty batch; an agent emitting it has a bug.
4. **Maximum regions per batch** — soft limit? Real photographers max out at ~15-20 regions per dodge/burn pass; an agent emitting 200 regions in one batch is almost certainly broken. Proposal: soft cap at 32 with an error message rather than silent truncation; revisit if real workflows hit it.

## How this closes

One ADR closes this RFC:

- **ADR-NNN — `apply_per_region` MCP verb + op-log payload shape** — formalizes the verb signature, the single-primitive restriction, the atomic-batch semantics, the op-log structured payload, the empty-batch / out-of-range / soft-cap behaviors. Amends `TA/contracts/mcp-tools` to add the verb.

## Links

- TA/contracts/mcp-tools (this is the modification surface)
- TA/components/synthesizer (uses existing `apply_with_mask` helper)
- TA/components/mcp-server (adds the verb)
- Related: RFC-029 / ADR-084 (mask spec shape), RFC-024 / ADR-085 (parametric range masks), RFC-025 / ADR-087 (sibling-verb precedent — `apply_spot`), RFC-021 / ADR-079 (`parameter_values` arg shape)
- Source survey: `docs/photographer-workflows-survey.md` (gap rank #1, 7/12 cross-genre recurrence)
