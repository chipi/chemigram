# RFC-036 — Mixed-op `apply_per_region` (un-defer of RFC-031)

> Status · Decided (impl shipped 2026-05-10; ADR-089 stays Draft until darkroom validation)
> TA anchor · /contracts/mcp-tools · /components/synthesizer
> Related · RFC-031 (apply_per_region single-primitive — closes into pending ADR), RFC-032 (named-mask vocabulary), RFC-035 (parametric L2 strength)
> Closes into · ADR-089 (closes; flips to Accepted on darkroom-session sign-off)
> Closes into · ADR-NNN (pending)
> Why this is an RFC · RFC-031 explicitly deferred mixed-op batching: "the agent emits one apply_per_region per primitive instead. That's 3 calls instead of 6 for an eye-detail move — a real win — but doesn't pretend to solve mixed-op-mixed-region batching." After shipping RFC-031 and the 14 L2 looks, the eye-detail and skin-spot patterns recur prominently in the proposed-L2-portrait set. The deferral feels weaker now. **Question: can we lift the single-primitive restriction without exploding the API surface or the snapshot semantics?**

## The question

RFC-031 ships `apply_per_region(image_id, primitive_name, regions, ...)` — atomic batched apply of *one* primitive to N mask-bound regions. The use case it cleanly solves: dodge-and-burn (one primitive, varied across regions). The use case it punts on:

- **Eye-region detail lift** — `+exposure` on each iris + `+sharpening` on lashes + `+saturation` on iris color. Three primitives × 2 regions = 6 apply calls, or with current `apply_per_region`: 3 calls (one per primitive, each with 2 regions).
- **Skin-spot harmonization** — per-spot color shift via colorequal; mostly single-op, but if a spot needs both a hue shift and a saturation pull, that's 2 primitives.
- **Composed skin pass** — apply `skin_uniformity` (colorequal) + `skin_smooth_painterly` (bilat clarity) to the same masked skin region. Today: 2 separate `apply_primitive` calls or 2 separate `apply_per_region` calls. Naturally one move from the photographer's POV.

The RFC-031 deferral was conservative. Lifting it requires designing how a mixed-op batch's payload shape, atomicity, and op-log structure work — none of which are obvious.

## Use cases (post-RFC-031 evidence)

After shipping RFC-031 and the 14 L2 looks, three patterns recur where mixed-op batching would be a real win:

1. **Composed skin retouch** — `skin_uniformity` + `skin_smooth_painterly` bound to `mask_skin_region`. One agent move, same mask. Two primitives.
2. **Eye-detail lift** — exposure + sharpening + saturation on the eye region. Same mask (or per-eye masks), three primitives.
3. **Tonal-and-color region grading** — exposure shift + color shift on a graduated region (foreground in landscape work). Same mask, two primitives.

Each is *one move* from the photographer's perspective. Today each requires N separate apply calls (where N = number of primitives), which:

- Generates N snapshots (the conceptual-unit-loss problem from RFC-031, recurring)
- Costs N MCP turns (the cost overhead from RFC-031, recurring)
- Loses the atomic "all-or-nothing" semantic if any one primitive fails

## Goals

1. **One agent move = one tool call** for these mixed-op patterns.
2. **Atomic semantics** — same as RFC-031: all primitives × all regions validate first; any failure aborts the whole batch.
3. **One snapshot** — captures the photographer's conceptual unit, not the implementation's per-(primitive × region) granularity.
4. **Schema evolution, not parallel surface** — extend the existing `apply_per_region` payload, don't ship a sibling verb. The narrow-MCP-surface discipline (ADR-033) holds.
5. **Backwards compatible** — existing single-primitive `apply_per_region` calls continue to work without change.

## Constraints

- **TA/contracts/mcp-tools** — adding a verb requires affirmative justification. Better to extend the existing `apply_per_region` shape.
- **TA/constraints/single-process** — atomic semantics within one MCP turn.
- **Multi-instance stacking via `multi_priority`** — mixed-op batches require the synthesizer to allocate `multi_priority` per (primitive, region) pair, not just per region. More state to track.
- **Op-log schema** — RFC-031 ships a structured payload `{op, primitive, n_regions, regions: [...]}`. Mixed-op needs a richer shape.

## Proposed approach (sketch)

**Extend `apply_per_region` to accept either the existing single-primitive shape OR a new mixed-op shape:**

### Existing shape (RFC-031 — preserved)

```json
{
  "primitive_name": "exposure",
  "regions": [
    {"mask_spec": {...}, "parameter_values": {"ev": 0.3}},
    {"mask_spec": {...}, "parameter_values": {"ev": -0.4}}
  ]
}
```

### New mixed-op shape (RFC-036)

```json
{
  "regions": [
    {
      "mask_spec": {"kind": "named", "name": "mask_skin_region"},
      "ops": [
        {"primitive_name": "skin_uniformity", "parameter_values": {"sat_orange": -0.4}},
        {"primitive_name": "skin_smooth_painterly", "parameter_values": {"clarity_strength": -0.5}}
      ]
    }
  ]
}
```

Each region carries an `ops` array (list of `{primitive_name, parameter_values?}` pairs) instead of a single `primitive_name` at the top level. The synthesizer applies each op in order (within a region) and across regions (each (primitive, region) gets a unique multi_priority).

**Discriminator:** the presence of `primitive_name` at the top level (single-op) vs. `ops` per region (mixed-op) determines routing. Both can't appear together (validation rejects).

**Atomic semantics:** ALL (op × region) combinations validate first; if any fail (parameter range, mask resolution, op→primitive lookup), the entire batch aborts. Same discipline as RFC-031.

**Op-log structured payload:** mirrors the request shape — `{op: "apply_per_region_mixed", n_regions: ..., regions: [{mask_summary, ops: [{primitive, parameter_values}, ...]}]}`.

## Alternatives considered

**Ship a new verb `apply_per_region_mixed`.** Rejected — explodes the surface for a small payload-shape difference. Same discriminator pattern (single-op vs. mixed-op) belongs on one verb.

**Make every region carry `ops` (no single-op shorthand).** Rejected — the dodge-and-burn case (RFC-031's dominant pattern, 7/12 cross-genre recurrence) is overwhelmingly single-op. Forcing every caller to wrap a single op in an array is gratuitous noise.

**Allow `ops: [...]` at the top level (one ops list applies to all regions).** Tempting for the "skin retouch on N spots" case where the same N primitives apply to every region. Considered, deferred — the dominant mixed-op cases (eye-detail, foreground grading) have *different* op composition per region. Top-level `ops` is a minor convenience that doesn't justify the schema split.

**Defer indefinitely (RFC-031's original posture).** Rejected because post-RFC-031 evidence shows the patterns recurring — the cheap composed-skin-retouch and eye-detail moves now have shipped primitives that compose, but the composition costs N snapshots.

## Trade-offs

- **+1 schema shape on `apply_per_region`.** Validation has to discriminate cleanly. Tests cover both shapes.
- **Op-log entries diverge** — single-op entries record `op: "apply_per_region"`, mixed-op entries record `op: "apply_per_region_mixed"`. `log` and `diff` consumers handle both. Small surface; localized.
- **multi_priority allocation gets richer** — for mixed-op, each (primitive, region) needs a unique multi_priority *per primitive* (so multiple `exposure` regions stack, but `exposure` and `sigmoid` regions don't collide because they're different ops). The synthesizer's existing same-op detector handles this naturally; just need to thread per-op multi_priority bumps through.
- **Failure-mode surface grows** — more ways for a batch to fail (cross-op parameter validation, per-op mask resolution). Each failure path needs a clear error. Test coverage burden is real but bounded.

## Open questions

1. **Within a single region, can the same op appear twice?** E.g., `mask_skin_region` with two `colorequal` ops at different parameters. Probably yes (each op gets its own multi_priority). Worth confirming.
2. **What's the upper bound on (op count × region count)?** RFC-031 caps regions at 32. Mixed-op could legitimately produce 32 regions × 5 ops = 160 plugin instances in one XMP. Need a sanity bound; propose 64 total (op, region) pairs.
3. **Cross-op ordering within a region** — `ops` is a list; order matters (parameter overrides + dtstyle composition). Document explicitly.
4. **Parameter validation across ops** — same op declared twice in one region with conflicting parameter values: hard error or last-wins? Propose hard error (mirrors RFC-031's atomic discipline).

## How this closes

One ADR:

- **ADR-NNN — Mixed-op `apply_per_region` schema extension** — formalizes the new payload shape, the validation rules, the op-log structured payload, the multi_priority allocation strategy, and the (op × region) cap.

**Decision-checkpoint dependency:** stays Draft until the darkroom-session findings on RFC-031's dodge-and-burn workflow (per `darkroom-session-debt.md` item 5) confirm whether single-op-per-batch is genuinely insufficient. If single-op suffices in practice, this RFC stays deferred; if mixed-op recurs across genres in subsequent surveys (Wedding/Event, B&W, Nature/Wildlife, Food/Product), it ships.

## Links

- TA/contracts/mcp-tools (extends apply_per_region payload shape)
- TA/components/synthesizer (multi_priority allocation per (op, region))
- Related: RFC-031 (single-op apply_per_region — the substrate this extends), RFC-032 (named-mask resolution composes per-region), RFC-035 (parametric L2 strength composes per-region)
- Source: post-RFC-031 retro item #3 — the deferral felt weaker after the 14 L2 looks shipped and composed-skin / eye-detail patterns surfaced as load-bearing
- Blocker: `docs/guides/darkroom-session-debt.md` item 5 — RFC-031 single-op validation pass informs whether this is a real need
