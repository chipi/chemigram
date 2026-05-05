# RFC-021 — Parameterized vocabulary magnitudes (Path C as default for continuous-magnitude modules)

> Status · Draft v0.1
> Date · 2026-05-05
> TA anchor ·/components/synthesizer ·/contracts/vocabulary-manifest ·/contracts/mcp-tools ·/components/cli ·/constraints/opaque-hex-blobs
> Related · ADR-008 (opaque blob default), RFC-012 / ADR-073 (Path C as authoring technique), RFC-018 (vocabulary expansion), ADR-076 (drawn-mask architecture), capability-survey.md §11
> Closes into · ADR (pending) — parameterized apply path; ADR (pending) — manifest schema extension for `parameter`; ADR (pending) — CLI/MCP `value` arg shape; ADR (pending) — test-coverage policy for parameterized modules; ADR (pending) — migration of existing magnitude-ladder entries
> Why this is an RFC · ADR-008 made `op_params` opacity the default and Path C the rare exception. RFC-012 / ADR-073 confirmed Path C is feasible and shipped it as an *authoring* technique (programmatically generate `.dtstyle` files at vocabulary-build time). The next step — letting the *applier* parameterize at apply time so a photographer can request `+0.7 EV` directly — is a real architectural shift that supersedes part of ADR-008's framing. The shift, the manifest schema, the user-facing surface, the test-coverage policy, and the migration strategy are not all settled, so this is an RFC, not a direct ADR.

---

## The question

The vocabulary today ships **discrete entries with hardcoded magnitudes**: `expo_+0.5`, `expo_+0.3`, `expo_-0.5`, `expo_-0.3`. To request `+0.7 EV` you cannot — you can only stack `+0.5` and `+0.3` (which works for exposure because it's linear, but won't work for non-linear modules). The same shape repeats for `vignette_subtle/medium/heavy`, `wb_warm_subtle` (no medium/heavy), `sat_boost_strong/moderate`, `grain_fine/medium/heavy`, and so on.

Combinatorially enumerating every plausible magnitude (every 0.1 EV from -3 to +3 = 60 exposure entries, similar explosions for every other continuous-magnitude module) is infeasible. The current 4 exposure entries is therefore not a temporary thinness — it's a structural consequence of the discrete-vocabulary framing being asked to do work it wasn't designed for.

The genuinely open question: **for modules whose photographic axis is continuous magnitude, should the vocabulary entry be a *parameterized primitive* (one entry, value supplied at apply time) instead of an enumeration of discrete strengths?** And if so, how does that integrate with the existing discrete-vocabulary entries that *are* about photographic intent rather than magnitude (clarity painterly vs strong, grade shadows warm vs grade highlights warm, the four mask-bound entries)?

---

## Use cases

1. **Photographer requests `+0.7 EV`.** Today: nothing. Tomorrow: `chemigram apply-primitive iguana --entry exposure --value +0.7`.
2. **Photographer requests `wb_warm` at intermediate strength.** Today: only `wb_warm_subtle`. Tomorrow: `chemigram apply-primitive iguana --entry wb_warmth --value +0.4`.
3. **Agent reasons about magnitude continuously.** Today: agent picks from a 4-entry exposure menu, often picking the wrong one and stacking. Tomorrow: agent emits `apply_primitive(primitive_name="exposure", value=0.7)` directly.
4. **Photographer wants ad-hoc masked exposure at non-shipped magnitude.** Today: the 4 shipped masked exposure entries are fixed at -0.5/+0.4/+0.6/-0.3 EV. Tomorrow: any value through any drawn mask via `--value` + `--mask-spec` together.
5. **Vocabulary cleanup.** The 4 hardcoded `expo_*` entries collapse to 1 parameterized `exposure` entry. The 3 vignette intensities collapse to 1. The 2 WB entries collapse to 1 (with sign in the value). Net: ~30 of today's 39 entries collapse into ~10 parameterized entries, freeing manifest weight for genuinely new photographic moves.

---

## Goals

- **Continuous magnitude is a first-class parameter** at apply time for any module whose photographic axis is genuinely continuous.
- **Discrete entries remain the right shape** for moves with semantic intent that doesn't reduce to a magnitude (clarity painterly vs strong; the four mask-bound geometries; per-zone grade direction).
- **No combinatorial vocabulary explosion.** One `exposure` entry replaces four discrete ones, with value spanning the full meaningful range.
- **Strong test coverage** for the parameterized primitives. Specifically: any parameterized module that ships must have lab-grade tests covering both *global* application (whole image at value `v`) **and** *masked* application (the same value applied through a drawn-form mask, asserting localization). For `exposure` specifically — the first parameterized module — this is non-negotiable.
- **Migration without breakage.** Existing `expo_+0.5` etc. continue to work during the transition period; agent and user can adopt the parameterized shape gradually.
- **Bounded engineering cost.** Path C decoders are per-module; the manifest + apply-path machinery is one-time engineering. Adding a new parameterized module after the architecture lands should be roughly half-a-day of work (the decoder + tests + manifest entry).

---

## Constraints

- **ADR-008 (opaque-blob default)**: this RFC supersedes part of ADR-008's "Path C is the rare exception" framing. The new shape: Path C is the default for explicitly-declared parameterizable modules; ADR-008's opacity remains the default for everything else. The closing ADR will document the shift cleanly.
- **ADR-073 (Path C authoring)** already established the pattern at vocabulary-build time. This RFC extends it to apply time.
- **ADR-076 (drawn-mask architecture)**: parameterized apply must compose cleanly with mask binding. The user-facing shape: `--value V --mask-spec '<json>'` together produce one snapshot.
- **TA/contracts/vocabulary-manifest**: the manifest schema gains an optional `parameter` field. Backwards-compatible: entries without `parameter` continue to work as discrete primitives.
- **TA/contracts/mcp-tools** (ADR-033): `apply_primitive` MCP tool gains an optional `value` argument. CLI mirrors with `--value`.
- **No new dependency on darktable internals beyond what RFC-012 already accepted**. Path C decoders are byte-level edits to known struct layouts; no Python bindings to dt internals.

---

## Proposed approach

### Phase 1 — Architecture, narrowly scoped to `exposure` only

Implement the parameterization architecture end-to-end on a single module (`exposure`) before expanding. This proves the shape works, ships user-visible value immediately, and avoids a multi-week rabbit hole.

**Manifest schema extension**:

```json
{
  "name": "exposure",
  "layer": "L3",
  "subtype": "exposure",
  "path": "layers/L3/exposure/exposure.dtstyle",
  "touches": ["exposure"],
  "tags": ["exposure", "tone", "fundamental"],
  "description": "Global exposure compensation. Value in EV.",
  "modversions": {"exposure": 7},
  "darktable_version": "5.4",
  "source": "expressive-baseline",
  "license": "MIT",
  "parameter": {
    "name": "ev",
    "type": "float",
    "range": [-3.0, 3.0],
    "default": 0.0,
    "field": {
      "module": "exposure",
      "modversion": 7,
      "offset": 4,
      "encoding": "le_f32"
    }
  }
}
```

The `parameter` block declares: parameter name, type, range, default, and the *exact byte location* in the module's `op_params` blob. The synthesizer at apply time decodes the blob, edits the named field, re-encodes.

**Apply-time decoder** (per parameterized module):

`chemigram.core.parameterize.exposure` — a small module with one function:

```python
def patch_exposure_op_params(op_params: str, *, ev: float) -> str:
    """Decode the exposure module's op_params hex, set the ev field,
    re-encode. Modversion-pinned (exposure mv7); raises ValueError on
    mismatch."""
```

**CLI**: `chemigram apply-primitive <image_id> --entry exposure --value 0.7`

**MCP**: `apply_primitive` tool gains optional `value` arg. Same precedence rules already established for `mask_spec`: caller value → manifest default. Combines with `mask_spec` cleanly (independent axes).

### Phase 2 — Test coverage policy (load-bearing)

Every parameterized-module ship must include all of:

1. **Unit tests** — round-trip the encoder/decoder. For exposure: `encode(decode(blob)) == blob` for the shipped reference XMP; `decode(encode(decode(blob), ev=v)).ev == v` for v across the declared range.
2. **Integration tests** — apply path completes for every value across the declared range. For exposure: at minimum {-3, -1, -0.5, 0, +0.5, +1, +3}.
3. **Lab-grade global tests** — render through real darktable against the synthetic reference targets, assert direction-of-change matches the requested value. For exposure: `+1 EV` on the grayscale ramp doubles linear-RGB on midtone patches; `-1 EV` halves them.
4. **Lab-grade masked tests** — same value applied through a centered ellipse mask, assert spatial localization (zone delta exceeds complement delta). For exposure: `+1 EV` through a center mask brightens center patches but leaves corner patches at baseline. This is the *non-negotiable* requirement; without masked-coverage tests, parameterization is half-shipped.
5. **Visual proof regeneration** — `scripts/generate-visual-proofs.py` adds a parameter-sweep section showing the same primitive at multiple values in a row.

The test infrastructure for items 3 and 4 already exists (`tests/e2e/_lab_grade_deltas.py`, `tests/e2e/test_lab_grade_primitives.py`, `tests/e2e/test_lab_grade_masked_universality.py`); parameterization just adds new entries to those harnesses.

### Phase 3 — Migration of existing magnitude-ladder entries

Once Phase 1 ships and Phase 2 coverage is met for `exposure`, the four `expo_+0.3/+0.5/-0.3/-0.5` entries are:

1. Kept in place as deprecated aliases for one minor version (back-compat: `apply-primitive --entry expo_+0.5` keeps working but logs a deprecation event).
2. Documentation updated in `vocabulary/packs/expressive-baseline/README.md` to point at the parameterized form.
3. After one minor version, removed.

The same pattern repeats for: `vignette_subtle/medium/heavy`, `wb_warm_subtle/wb_cool_subtle`, `grain_fine/medium/heavy`, `sat_boost_strong/moderate`, `chroma_boost_*`, `clarity_strong` (the *strength* axis only — `clarity_painterly` stays a separate entry because painterly vs sharp is a different *kind*, not a different strength).

### Phase 4 — Expansion to additional modules

Once `exposure` is parameterized end-to-end with full test coverage, the same pattern applies (in priority order):

1. `vignette` — single-field magnitude (`brightness`, mv4)
2. `temperature` — three fields (temp + tint + WB strength) but parameterizable per-axis
3. `colorbalancergb` saturation — single field
4. `sigmoid` contrast — single field
5. `bilat` clarity strength — single field
6. `grain` strength — single field
7. `highlights` clip threshold — single field

Each is a self-contained ship: decoder + tests + manifest entry + visual proof. Roughly half a day per module after the architecture is in place.

---

## Alternatives considered

### Alternative A — Keep discrete vocabulary, just author more strengths

**Why rejected.** Combinatorially infeasible. To cover ±3 EV at 0.1 EV granularity needs 60 entries for *just exposure*. Repeated across all continuous-magnitude modules: hundreds of entries. The vocabulary becomes unsearchable; the manifest becomes unmanageable. This is the path the project has been on; the result is that 39 entries don't even cover the basics.

### Alternative B — Parameterize at session/client level (agent passes value as part of the prompt, vocabulary stays discrete)

**Why rejected.** Pushes the parameterization burden onto every agent integration and every CLI script. Doesn't solve the underlying problem (the engine still can't synthesize an `expo_+0.7` XMP). Agents end up emitting the same "stack `+0.5` and `+0.2`" workaround that humans currently emit. Doesn't compose with masking — agent has to coordinate value + mask geometry across multiple tool calls.

### Alternative C — Parameterize at darktable-rendering level (use `darktable-cli --style` with style overrides)

**Why rejected.** ADR-011 explicitly rejects `--style` for vocabulary application (it only takes one style; we need composition). Even if it took multiple styles, darktable's CLI doesn't expose per-module parameter overrides; the override has to live in the XMP. Path C — editing the XMP before passing to darktable — is the only path that composes with the existing synthesizer.

### Alternative D — Parameterize via two-step "load template, edit, write" GUI workflow

**Why rejected.** Requires the photographer (or agent) to launch darktable's GUI to author each variant. That's exactly the workflow Phase 2 vocabulary-authoring already uses for *new vocabulary entries*. Using it for "I want +0.7 EV" defeats the purpose of having a vocabulary system.

### Alternative E — Build a continuous parameter space *into the vocabulary entry name* via convention (`expo_+0.7` is parsed at lookup time)

**Why rejected.** Brittle (every primitive needs its own naming convention parser); ambiguous (does `expo_+0_7` mean +0.07 or +0.7?); doesn't compose with other parameters (how do you encode "exposure +0.7 with opacity 80%"?); pushes parameterization into the lookup layer instead of the apply layer. The clean shape is: name + value as separate fields.

---

## Trade-offs

### What Path C as default costs

- **Per-module engineering investment.** Each parameterized module needs reverse-engineering of its `op_params` struct layout. RFC-012 / ADR-073 already paid this cost for several modules during programmatic vocabulary generation; the same decoders are reusable. New modules cost ~half a day each.
- **Modversion drift exposure.** When darktable bumps a module's modversion, the decoder must be updated. ADR-008 explicitly avoided this; this RFC accepts it for parameterized modules. The mitigation: each decoder is modversion-pinned and refuses to operate on mismatched blobs (clear error rather than silent corruption).
- **Manifest complexity.** The `parameter` schema is more complex than today's flat fields. Mitigation: optional; backwards-compatible; the discrete entries that don't need parameterization stay flat.
- **Test surface grows.** Each parameterized module brings a unit + integration + lab-grade-global + lab-grade-masked test cluster. This is the *point* — test coverage is load-bearing — but it's still cost.

### What discrete vocabulary cost (the cost we're escaping)

- Hard coverage gaps for fundamentals (the section 1, 2, 4, 6 thinness in capability-survey.md)
- Vocabulary growth requires authoring entries one strength at a time
- Agent reasoning over magnitude as a discrete choice produces stacking workarounds
- Photographers want continuous control; vocabulary forces them to pick from a tiny menu

### What stays the same

- ADR-008 opacity remains the default for non-parameterized modules
- Path C is still per-module engineering — no automatic decoding for arbitrary modules
- Discrete entries with semantic intent (painterly clarity, the 4 mask-bound geometries, grade direction per zone) stay discrete
- The vocabulary as an abstraction — named photographic moves — stays the abstraction; magnitude becomes a *parameter of the move*, not part of the move's name

---

## Open questions

1. **Manifest schema — single-parameter only, or multi-parameter?** Some modules have natural multi-axis (`temperature` has temp + tint + WB strength). Should the first ship support only single-parameter (simpler) and add multi-parameter later, or design the schema for multi-parameter from day one?
   - Lean toward: single-parameter first, schema extensible to multi later.

2. **CLI flag shape — `--value V` or `--value name=V`?** With single-parameter modules, `--value 0.7` is unambiguous. With multi-parameter, you'd need `--value temp=+0.4 --value tint=-0.1`. Should the CLI commit to the multi-parameter shape from the start to avoid breaking change later?
   - Lean toward: `--value V` for single-parameter (clean), `--param NAME=V` for multi (when we get there).

3. **Range validation — soft (warn) or hard (reject)?** Should `--value 5.0` on `exposure` (declared range [-3, 3]) be a hard error, or apply with a clamp + warning?
   - Lean toward: hard reject. Cleaner semantics; the user can always extend the manifest's declared range if they need it.

4. **Deprecation timeline for migrated entries.** One minor version of overlap is the proposal — is that long enough? Some users may have scripts hardcoded to `expo_+0.5`.
   - Lean toward: one minor version with deprecation log, then removal. The CLI flag is forward-compatible from day one.

5. **Test-coverage policy enforcement.** Should the test policy be a soft convention (documented in CONTRIBUTING.md) or a hard CI gate (a parameterized-module manifest entry without corresponding lab-grade tests fails CI)?
   - Lean toward: hard CI gate. The "parameterized without test coverage" failure mode is exactly the trap that gets us a v1.6.0 with broken parameterization.

6. **`exposure` is the canonical first module — does *any* other module want to ship at the same time as a sanity check?** Picking exposure alone risks designing the architecture around exposure's quirks.
   - Lean toward: ship exposure alone in v1.6.0. Add `vignette` (also single-axis, simpler) as the second ship in v1.6.1 — that's the architectural-soundness check.

---

## How this closes

This RFC closes into multiple ADRs:

1. **ADR — Path C as default for parameterized modules.** Supersedes part of ADR-008's framing for the explicitly-declared-parameterizable case. ADR-008 stands for the rest of darktable's modules.
2. **ADR — Vocabulary manifest `parameter` schema.** The optional field; type system; modversion-pinning; field offset / encoding declaration.
3. **ADR — `apply_primitive` `value` argument** (CLI `--value` flag and MCP `value` arg). User-facing surface; precedence rules with `mask_spec`; range-validation policy.
4. **ADR — Test-coverage policy for parameterized modules.** Unit + integration + lab-grade global + lab-grade masked, all required, gated in CI.
5. **ADR — Migration policy for existing magnitude-ladder entries.** Deprecation period; alias behavior; doc-update obligations.

`exposure` is the first parameterized module that ships under the new architecture and serves as the closing-evidence for ADRs 1–4.

---

## Links

- TA/components/synthesizer
- TA/contracts/vocabulary-manifest
- TA/contracts/mcp-tools
- TA/components/cli
- TA/constraints/opaque-hex-blobs
- ADR-008 — XMP and `.dtstyle` as opaque-blob carriers (partially superseded for parameterized modules)
- ADR-076 — Drawn-mask-only mask architecture (composes with parameterization)
- RFC-012 / ADR-073 — Programmatic vocabulary generation (Path C); this RFC extends Path C from authoring-time to apply-time
- RFC-018 — Vocabulary expansion for expressive taste articulation
- `docs/capability-survey.md` §11 — the user-facing framing of the gap this RFC closes
