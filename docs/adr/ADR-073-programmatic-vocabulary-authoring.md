# ADR-073 — Programmatic vocabulary authoring via reverse-engineered iop structs

> Status · Accepted
> Date · 2026-05-02
> TA anchor · /components/synthesizer · /constraints/opaque-hex-blobs
> Related RFC · RFC-012 (closes), RFC-018 (informs)
> Related ADRs · ADR-001 (Path A/B/C original framing), ADR-008 (opaque blobs), ADR-051 (synthesizer SET-replace), ADR-064 (vocabulary authoring workflow)

## Context

ADR-008 commits to treating `op_params` and `blendop_params` as opaque
hex blobs the engine moves around but never decodes. ADR-001 enumerated
three architectures: Path A (hex param manipulation), Path B (style
composition without decoding), Path C (programmatic generation from
known module struct layouts). v1 chose Path B; Path C was reserved
for a "rare exception" path documented in `docs/TODO.md`.

The v1.4.0 expressive-baseline work (in support of RFC-018) hit a
practical limit: 35 attribute entries needed to ship, but only 4 had
been hand-authored via darktable sessions before the user offered to
defer the rest. To unblock progress, the team reverse-engineered the
C struct layouts of 9 darktable iop modules from
`src/iop/<module>.c` in the upstream darktable source, then encoded
the structs in Python via `struct.pack`. 31 entries authored this
way; 22 e2e direction-of-change tests passing against real
darktable 5.4.1.

This is exactly Path C. The technique works. RFC-012 had marked it
"deferred until v1 evidence accumulates" — that evidence is now in.
This ADR closes the RFC by formalizing the technique, scoping its
applicability, and documenting the audit trail for future authors.

## Decision

Programmatic authoring via reverse-engineered iop struct layouts is
an **accepted complement to hand-authoring**, not a replacement. The
constraints:

1. **In-tree audit guide is mandatory.** Each module's struct mapping
   lives in `docs/guides/expressive-baseline-authoring.md` with a
   citation to the upstream `src/iop/<module>.c` source, the
   `DT_MODULE_INTROSPECTION` version, and the per-field `struct.pack`
   format string used. New modules require an audit-guide entry
   before any vocabulary entry can ship.
2. **One Python file per module's encoder.** Encoders live in
   `scripts/author-dtstyle.py` (or its module equivalents). Each
   encoder is a pure function: parameters → bytes. Tests assert each
   encoder's output round-trips through darktable-cli.
3. **e2e validation is required.** Every programmatically-authored
   entry needs a corresponding e2e test in `tests/e2e/expressive/`
   that asserts the rendered pixel statistic moves in the expected
   direction (or, where direction-of-change is ambiguous, a
   "measurable change" assertion per the `blacks_crushed` precedent).
4. **Hand-authoring stays first-class** for any module whose struct
   layout includes gz-compressed blobs, raster mask binding via
   `blendop_params`, or anything else where reverse-engineering would
   be more brittle than a darktable session.
5. **Per-module DT_MODULE_INTROSPECTION versioning is tracked.** When
   darktable bumps a module's introspection version, the audit guide
   and encoders need updating; manifest entries' `modversions` field
   already records the version a given dtstyle was authored against.

## Rationale

- **The evidence is in:** 31 entries across 9 modules,
  22 direction-of-change e2e tests passing. Pretending the technique
  doesn't work because of an old "rare exception" marker is dishonest.
- **Hand-authoring doesn't scale to 35 entries** without a
  domain-expert photographer with darktable open for a day. The
  vocabulary needs to grow faster than that to make the broader
  Mode A use case work.
- **Audit guide as the gate.** The risk with Path C is silent
  drift between our struct understanding and darktable's actual
  layout. Forcing every module mapping through the audit guide makes
  the assumption explicit and reviewable.
- **Encoders, not generators.** The encoders are pure
  `params → bytes` functions, not "generators" that output multiple
  variants. The vocabulary entries are still hand-curated taste
  decisions; encoders just remove the friction of opening darktable
  to materialize them.

## Alternatives considered

- **Stay Path B-only forever:** rejected by the v1.4.0 evidence —
  Path B alone leaves a 90% gap between "what we want to ship" and
  "what we can ship without a darktable session per entry."
- **Generate vocabulary from a high-level DSL:** rejected as
  premature abstraction. Each module's struct is different enough
  that one DSL for all would be either too thin to matter or too
  thick to maintain. Per-module encoders are honest.
- **Auto-discover struct layouts from darktable's introspection
  metadata:** considered. Darktable does ship some introspection
  data, but parsing it reliably across versions is its own project;
  reverse-engineering the C source once per module bump is simpler.
- **Defer Path C indefinitely:** would have blocked the
  expressive-baseline work entirely or pushed the user into a
  multi-day darktable session. Neither was the right trade.

## Consequences

Positive:
- The vocabulary grows at programmer-pace, not photographer-pace,
  for any module whose struct is straightforward.
- Future contributors have a documented path to add new modules:
  read C source, write encoder, write audit-guide entry, write e2e.
- Hand-authoring gets to focus on the cases where it adds value
  (raster masks, complex blends, taste calibration that needs
  visual feedback).

Negative:
- Reverse-engineered structs go stale when darktable bumps
  introspection versions. Mitigation: `modversions` field in
  manifests + the audit-guide makes the upgrade work mechanical.
- Two authoring workflows (hand vs programmatic) is more surface
  area than one. Mitigation: the audit guide makes the choice
  explicit per module, not per entry.
- Some modules (e.g. `channelmixerrgb` for B&W, with 160-byte
  structs and gz-compressed sub-blobs) are too complex for
  reverse-engineering at acceptable risk. Those stay
  hand-authored — and that's deliberately fine.

## Implementation notes

- `scripts/author-dtstyle.py` — Python encoders for each module.
  One module per `_encode_<module>` function; pure
  `params → bytes`.
- `docs/guides/expressive-baseline-authoring.md` — per-module
  struct mapping, source citation, `DT_MODULE_INTROSPECTION`
  version, validation method.
- `tests/e2e/expressive/` — direction-of-change tests. The
  `blacks_crushed` test (#64) sets the precedent for the
  "measurable change" pattern when direction-of-change is ambiguous
  on Phase 0 fixtures.
- 9 modules currently programmatically-authored: exposure,
  temperature, sigmoid, localcontrast, colorbalancergb, grain,
  vignette, highlights, channelmixerrgb (deferred to user
  darktable seed per module-complexity gate).
- Vocabulary count at v1.4.0 ship: 4 starter (hand-authored) + 31
  expressive-baseline (programmatic) + 4 pending user darktable
  seeds (#62 + #63).
