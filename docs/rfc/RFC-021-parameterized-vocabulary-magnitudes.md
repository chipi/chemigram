# RFC-021 — Parameterized vocabulary magnitudes (Path C as default for continuous-magnitude modules)

> Status · Decided (2026-05-05)
> Date · 2026-05-05
> TA anchor ·/components/synthesizer ·/contracts/vocabulary-manifest ·/contracts/mcp-tools ·/components/cli ·/constraints/opaque-hex-blobs
> Related · ADR-008 (opaque blob default), RFC-012 / ADR-073 (Path C as authoring technique), RFC-018 (vocabulary expansion), ADR-076 (drawn-mask architecture), capability-survey.md §11
> Closes into · ADR-077 (Path C as default for parameterized modules) · ADR-078 (manifest `parameters` schema, multi-parameter from day one) · ADR-079 (`apply_primitive` `value` / `param` argument shape; range validation) · ADR-080 (test-coverage policy for parameterized modules)
> Why this is an RFC · ADR-008 made `op_params` opacity the default and Path C the rare exception. RFC-012 / ADR-073 confirmed Path C is feasible and shipped it as an *authoring* technique (programmatically generate `.dtstyle` files at vocabulary-build time). The next step — letting the *applier* parameterize at apply time so a photographer can request `+0.7 EV` directly — is a real architectural shift that supersedes part of ADR-008's framing. The shift, the manifest schema, the user-facing surface, the test-coverage policy were the open questions. Resolved 2026-05-05; closes into ADR-077..080.

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

## Open questions — resolved 2026-05-05

1. **Manifest schema — single-parameter only, or multi-parameter?**
   **Resolved:** multi-parameter from day one (closes into ADR-078). Schema lists an array of parameters; entries with one param are just `parameters: [{...}]`. Avoids a forced schema migration when `temperature` (temp + tint multi-axis) joins the parameterized set.

2. **CLI flag shape — `--value V` or `--param NAME=V`?**
   **Resolved:** both (closes into ADR-079). `--value V` is shorthand for `--param <default>=V` when the entry has a single parameter. Multi-parameter entries require `--param NAME=V` flags (repeatable). MCP tool `value` argument follows the same shape: scalar shorthand for single-param, dict for multi.

3. **Range validation — soft clamp or hard reject?**
   **Resolved:** hard reject with `INVALID_INPUT` (closes into ADR-079). Predictable; no silent surprises. The manifest's `range` declares the supported domain — extending it is a manifest edit, not a runtime override.

4. **Deprecation timeline for migrated entries.**
   **Resolved:** no deprecation period; no overlap. The existing `expo_+0.5/+0.3/-0.5/-0.3`, `vignette_subtle/medium/heavy`, etc. magnitude-ladder entries get **deleted in the same PR** that introduces the parameterized form. The product has no users yet whose scripts depend on these names; backwards-compatibility burden buys nothing and adds complexity. New shape wins cleanly. Folded into ADR-078 implementation notes.

5. **Test-coverage policy enforcement — soft convention or hard CI gate?**
   **Resolved:** hard CI gate (closes into ADR-080). A parameterized-module manifest entry without corresponding lab-grade-global + lab-grade-masked test coverage fails CI. Implemented as a small linter test that reads the manifest, finds entries with a `parameters` field, and asserts each is referenced in both `tests/e2e/_lab_grade_deltas.py` (global) and `tests/e2e/test_lab_grade_masked_universality.py` (or successor file with masked coverage).

6. **Sanity-check second module — ship `exposure` alone, or `exposure` + one more?**
   **Resolved:** ship `exposure` + `vignette` together in v1.6.0. Both are single-axis, simple structs; the marginal cost of the second is small; catches architecture-tied-to-one-module problems immediately. Folded into Phase 1 of the implementation plan.

---

## How this closes

This RFC closes into four ADRs (resolved 2026-05-05):

1. **ADR-077 — Path C as default for parameterized modules.** Supersedes part of ADR-008's framing for the explicitly-declared-parameterizable case. ADR-008 stands for the rest of darktable's modules.
2. **ADR-078 — Vocabulary manifest `parameters` schema.** Multi-parameter from day one; per-parameter type + range + default + module field offset/encoding declaration. Existing magnitude-ladder entries are removed in the same PR (no deprecation overlap; no users to migrate).
3. **ADR-079 — `apply_primitive` `value` / `param` argument shape** (CLI `--value`/`--param` flags and MCP `value` argument). User-facing surface; precedence rules with `mask_spec` (independent axes); hard-reject range validation.
4. **ADR-080 — Test-coverage policy for parameterized modules.** Unit + integration + lab-grade global + lab-grade masked, all required, hard CI gate enforced via a linter that reads the manifest.

The migration question (originally proposed as a fifth ADR) collapsed when Q4 resolved to "no overlap" — folded into ADR-078 implementation notes.

`exposure` and `vignette` are the first two parameterized modules that ship under the new architecture (v1.6.0) and serve as the closing-evidence for ADRs 077–080.

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
