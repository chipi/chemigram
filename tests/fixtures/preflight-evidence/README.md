# Pre-flight evidence — Path B in darktable 5.4.1

## What we wanted to know

RFC-001 / ADR-051 / RFC-018 v0.1 inherited the assumption that Path B
(new-instance addition in `synthesize_xmp`) requires a per-entry
`iop_order` value. RFC-001 framed it as: *"darktable silently drops
new-instance entries that don't carry iop_order."* Phase 0 evidence
underpinned that finding.

That assumption shaped large parts of RFC-018: a probe-iop-order
workflow, manifest schema fields (`iop_order`, `iop_order_source`,
`iop_order_darktable_version`), validator rules requiring those fields
on Path B entries, an ADR (-063) committing to "Strategy X" (probe at
authoring time, store in manifest), authoring-discipline overhead.

We wanted to verify the assumption empirically before building all that.

## What we tested

Five Path B scenarios against the Phase 0 raw, all with `iop_order`
**absent** from per-`<rdf:li>` entries (only the description-level
`darktable:iop_order_version="4"` set):

| Scenario | Module | Form | Outcome |
|-|-|-|-|
| 1 | `vignette` | new operation (not in baseline) | rendered output differs from baseline → entry applied ✓ |
| 2 | `grain` | new operation | rendered output differs → entry applied ✓ |
| 3 | `exposure` | new instance at `multi_priority=1` | rendered output differs → entry applied ✓ |
| 4 | `temperature` | new instance at `multi_priority=1` | rendered output differs → entry applied ✓ |
| 5 | `channelmixerrgb` | new instance at `multi_priority=1` | rendered output differs → entry applied ✓ |

Both forms — *new operation* (module not in baseline) and *new instance*
(module in baseline, but at a previously-unused `multi_priority`) — work.

## What we conclude

**In darktable 5.4.1, per-entry `iop_order` is not required for Path B.**
darktable resolves pipeline order from the description-level
`iop_order_version` + its internal iop_list, regardless of whether the
per-entry attribute is present.

This overturns the assumption RFC-001 / ADR-051 carried forward from
Phase 0. The Phase 0 finding may have been about a different darktable
version, a specific module class we didn't test, or a misdiagnosed
symptom. Either way, dt 5.4.1's behavior is permissive.

## What it means for RFC-018

The probe-iop-order infrastructure is unnecessary in 5.4.1:

- ❌ Probe script (Strategy X) — drop
- ❌ Manifest `iop_order` / `iop_order_source` / `iop_order_darktable_version` — drop
- ❌ ADR-063 "iop_order strategy" — collapses to "leave None; darktable resolves"
- ✅ Path B synthesizer — still needed, but trivial: append `HistoryEntry`
  with `iop_order=None`, increment `history_end` and `num`, done.

The **multi-pack `VocabularyIndex`** work (already shipped under #41)
stays valuable for the `expressive-baseline` pack. The
**`HistoryEntry.iop_order: float | None`** type fix (#42) stays correct
because rendered sidecars *do* carry iop_order as a float when present
— the parser must handle that shape regardless of whether vocabulary
authoring needs it.

## Future-version risk

If darktable bumps its `iop_order_version` and reorders modules in the
internal iop_list, vocabulary entries authored against 5.4.1 may render
at a different pipeline position. RFC-007 (modversion drift) handles
the detection + warning path. But the simplification stands for 5.4.1
and likely for 5.x — darktable's pipeline order has been stable across
the 5.x series.

If a future dt version regresses to "drops entries without iop_order,"
RFC-018 can be reopened to add Strategy X back. The infrastructure
isn't burned — it's just not needed yet.

## How we tested

`test_path_b_without_iop_order.sh` in this directory is the runnable
script. It depends on the Phase 0 raw + configdir convention
(`CHEMIGRAM_TEST_RAW`, `CHEMIGRAM_DT_CONFIGDIR`, or default paths under
`~/chemigram-phase0/`). Renders are byte-compared to a baseline; MD5
differences confirm the Path B entries actually applied (a silent drop
would produce identical output).
