# RFC-025 — Spot removal / heal architecture (retouch byte serialization)

> Status · Decided
> Date · 2026-05-08
> TA anchor · /components/synthesizer · /contracts/per-image-repo · /components/masking · /constraints/opaque-hex-blobs
> Related · ADR-076 (drawn-mask only architecture; this RFC formalizes the retouch extension), ADR-084 / RFC-029 (compositional masks at apply time; the wire), ADR-085 / RFC-024 (parametric range masks; the sibling architectural extension), ADR-007 (BYOA principle), ADR-086 / RFC-026 (LLM-vision-as-provider for AI masks; AI variants of spot detection route here), RFC-030 (deployed sibling-provider scaffolding; AI content-aware spot detection deferred there), capability-survey.md § 10 ("Truly novel-shape gaps" — retouch / spot healing named as the major portrait gap), #108
> Closes into · ADR-087 (retouch byte encoding + `apply_spot` MCP tool + heal/clone scope)
> Why this is an RFC · Lightroom's spot removal / heal / clone is the canonical workflow for blemish removal, dust spots, sensor cleanup, distracting-element removal, and portrait skin clean-up. Chemigram has no equivalent today. The drawn-mask path can *select* a region but no primitive *replaces* pixels; the photographer's mental model "remove this spot" has no vocabulary verb. Initial framing assumed pixel-level edits would need a sibling provider (the retouch algorithms run inside darktable but the user-action shape was unclear). Reading darktable's `retouch` source (mv3) reveals the struct is a 300-form fixed array where each form references a `mask_id` from `masks_history` — structurally identical to the drawn-form mask wire chemigram already serializes per ADR-076. That collapses the cost shape from "qualitatively different architectural arc" to "extension of the byte serializer we already have." The genuine open question argued — and decided below — is **the agent-facing surface shape** (new MCP tool vs vocabulary entry vs mask_spec extension) and the **scope of v1.9.0 ship** (single-form vs multi-form, heal/clone vs all four algorithms, circle vs all mask geometries). AI content-aware spot detection ("find all 200 spots on the manta") is correctly orthogonal — that arc routes to RFC-030's deployed-provider scaffolding.

---

## The question

Lightroom's spot removal / heal / clone is the canonical retouch workflow. darktable's `retouch` module (mv3) is the obvious target. Reading the struct (verified against darktable 5.4.1 `src/iop/retouch.c`):

```c
typedef struct dt_iop_retouch_form_data_t {
  dt_mask_id_t formid;       // int32 — mask_id reference
  int scale;
  dt_iop_retouch_algo_type_t algorithm;  // 0=NONE 1=CLONE 2=HEAL 3=BLUR 4=FILL
  dt_iop_retouch_blur_types_t blur_type;
  float blur_radius;
  dt_iop_retouch_fill_modes_t fill_mode;
  float fill_color[3];
  float fill_brightness;
  int distort_mode;
} dt_iop_retouch_form_data_t;  // 44 bytes per form

typedef struct dt_iop_retouch_params_t {
  dt_iop_retouch_form_data_t rt_forms[300];  // 13200 bytes
  // ...60 bytes of global tail (default algorithm, scales, fill mode, etc.)
} dt_iop_retouch_params_t;  // total: 13260 bytes
```

Each `rt_forms[i]` carries a `formid` referencing a mask form in `masks_history`. The mask form (a `DT_MASKS_CIRCLE` for spots) carries the spatial geometry (center, radius). The retouch op_params adds the algorithm choice and per-form parameters.

**Architectural shape**: structurally identical to drawn-mask + parametric mask composition. A spot is a circle mask + a retouch_form linking the mask_id to an algorithm. The wire (mask form bytes + masks_history XML + blendop_params binding) is what RFC-029 / ADR-084 already ships.

The genuine open questions argued — and decided below:

1. **Agent-facing surface shape.** New MCP tool sister to `apply_primitive`? Or vocabulary entry through `apply_primitive` with parameterized `(x, y, radius)`? Or `mask_spec` extension?
2. **v1.9.0 scope.** Single-form per call vs multi-form? HEAL + CLONE only vs all four algorithms (HEAL / CLONE / BLUR / FILL)? CIRCLE geometry only vs ellipse / path / brush?
3. **Source-region coordinates for CLONE.** Where does `(source_x, source_y)` live? On the mask form's `mask_src` field? In the retouch op_params? In the MCP tool args?

---

## Use cases

1. **Manual sensor-dust removal.** Photographer says "remove the dust spot at (0.4, 0.2) about 5% radius." `apply_spot(image_id, kind="heal", x=0.4, y=0.2, radius=0.05)`. Single form, HEAL algorithm. Pure path-1 (this RFC).

2. **Single blemish on a portrait.** Same mechanism — coordinate + radius + heal.

3. **Manual clone — mirror an eye.** Photographer says "clone from (0.4, 0.3) to (0.6, 0.3) about 4% radius." `apply_spot(image_id, kind="clone", x=0.6, y=0.3, radius=0.04, source_x=0.4, source_y=0.3)`. Single form, CLONE algorithm.

4. **Multiple spots in one workflow.** Photographer iterates: heal spot 1, then heal spot 2, then heal spot 3. Each is a separate `apply_spot` call; each produces a snapshot. The retouch plugin's form-array accumulates across calls (or each call appends a new retouch plugin instance — see implementation note below).

5. **AI auto-spot detection.** "Clean up the manta's belly across 200+ small white dots." LLM-vision can identify a few; precision-tier needs deployed spot detector. **Routes to RFC-030.** Once a provider returns a list of `(x, y, radius)` regions, the engine emits N `apply_spot` calls (or one batched call — Phase 2 decision in RFC-030).

---

## Goals

- **Pick the agent-facing surface** — a new MCP tool `apply_spot` is the clean answer (decision below).
- **Bound v1.9.0 scope** to HEAL + CLONE on CIRCLE geometry, single-form per call.
- **Honor ADR-076's structural lesson** — retouch forms reference masks_history elements via formid; same wire as drawn masks.
- **Stay byte-level-correct.** The 13260-byte op_params is verified against darktable 5.4.1's source struct.
- **Defer correctly.** AI content-aware multi-spot detection is RFC-030's territory; multi-form per call, BLUR / FILL algorithms, ellipse / path geometries are all post-v1.9.0 expansions when evidence demands.
- **Bound modversion-drift exposure.** retouch mv3 adds one more module; same backstop policy as ADR-082.

---

## Constraints

- **ADR-076** (drawn-mask only architecture): retouch forms reference masks_history via formid. The mask form (CIRCLE) lives in the same `<darktable:masks_history>` array we already serialize.
- **ADR-007** (BYOA): no AI dependencies in `chemigram.core`. AI auto-spot-detection providers live in RFC-030's territory.
- **ADR-008 (amended by ADR-081)**: `op_params` is opaque except where parameterization is registered. Adding retouch registers the form-array region as another tracked module.
- **ADR-033** (narrow MCP tool surface): adding `apply_spot` requires an ADR. ADR-087 justifies its presence — spot correction is structurally a different primitive class (replaces pixels rather than modifies them through a primitive).
- **ADR-084** (apply-time mask spec semantics): existing `mask_spec` integration shapes don't fit cleanly because spot correction *replaces* pixels rather than *filters* a primitive's effect.
- **ADR-085** (parametric mask encoding): same byte-level codec pattern; retouch uses a different op_params shape but same architectural approach.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (spot decisions via tool calls); darktable-does-the-photography (heal/clone math runs in darktable); BYOA (AI auto-detection in RFC-030 sibling projects).

---

## Decision

**A new MCP tool `apply_spot`. v1.9.0 scope: HEAL + CLONE on CIRCLE geometry, single-form per call.** AI auto-spot detection deferred to RFC-030.

### 1. New MCP tool: `apply_spot`

```python
@tool
def apply_spot(
    image_id: str,
    *,
    kind: Literal["heal", "clone"],
    x: float,           # spot center, [0..1]
    y: float,           # spot center, [0..1]
    radius: float,      # spot radius, [0..1] (typically 0.01-0.10)
    source_x: float | None = None,  # required for clone; ignored for heal
    source_y: float | None = None,  # required for clone; ignored for heal
    opacity: float = 100.0,
) -> dict:
    """Apply a spot retouch (heal or clone) at the given coordinate and snapshot.

    Heal: darktable picks the source automatically using its
    wavelet-decomposition heal algorithm. Best for blemishes, dust spots.
    Clone: caller specifies (source_x, source_y) for the source region.
    Best for mirroring features or copying texture from elsewhere.
    """
```

Sister to `apply_primitive` (narrow MCP surface preserved per ADR-033 — one new tool, justified by the structurally different primitive class). The tool synthesizes a retouch dtstyle on the fly, allocates a deterministic mask_id, writes the masks_history element, and snapshots.

### 2. v1.9.0 scope

**HEAL and CLONE only.** BLUR (apply Gaussian/bilateral blur to a region) and FILL (paint a solid color) are valid retouch algorithms but rare in real workflows; deferred until evidence.

**CIRCLE geometry only.** The retouch UI in darktable defaults to circles for spot removal. Ellipse / path geometries are valid for retouch but uncommon; deferred. (When AI content-aware detection lands in RFC-030, it returns `(x, y, radius)` tuples that map directly to circles.)

**Single form per call.** Each `apply_spot` invocation generates one retouch plugin in the dtstyle with one form populated (forms[0] active, forms[1..299] zeroed). Multi-form per call is an RFC-030 concern — when AI detection returns 200+ spots, the engine batches them. For v1.9.0, multiple spots = multiple `apply_spot` calls, each a separate snapshot.

### 3. Source coords for CLONE

The mask form's `mask_src` field (8 bytes — 2 floats: source_x, source_y in normalized coords) carries the clone source. For HEAL, mask_src stays zero (8 bytes of zeros) and darktable picks the source automatically.

This is what `empty_mask_src()` already exists for — we just stop returning zeros for clone forms and instead pack the source coords there.

### 4. Byte encoders

New encoders in `chemigram.core.masking.dt_serialize`:

```python
# 16 bytes: center_x, center_y, radius, border (all floats)
def encode_circle_mask_points(*, center_x, center_y, radius, border=0.0) -> bytes: ...

# 8 bytes: source_x, source_y (for clone forms; replaces empty_mask_src)
def encode_clone_mask_src(*, source_x, source_y) -> bytes: ...

# 44 bytes: dt_iop_retouch_form_data_t
def encode_retouch_form(*, formid, algorithm, scale=0, ...) -> bytes: ...

# 13260 bytes: dt_iop_retouch_params_t (300-form array + 60-byte tail)
def encode_retouch_op_params(forms: list[bytes]) -> bytes: ...
```

Constants:

```python
DT_IOP_RETOUCH_NONE = 0
DT_IOP_RETOUCH_CLONE = 1
DT_IOP_RETOUCH_HEAL = 2
DT_IOP_RETOUCH_BLUR = 3   # not exposed in v1.9.0 surface
DT_IOP_RETOUCH_FILL = 4   # not exposed in v1.9.0 surface

RETOUCH_NO_FORMS = 300
RETOUCH_FORM_SIZE = 44
RETOUCH_PARAMS_SIZE = 13260  # 300 * 44 + 60-byte tail

DT_MASKS_CIRCLE = 1 << 0  # already defined; circle mask form type
```

### 5. Apply path

The MCP tool's flow:

1. Compute deterministic `mask_id` from hash of `(kind, x, y, radius, source_x?, source_y?)`.
2. Build a CIRCLE form with `encode_circle_mask_points(center_x=x, center_y=y, radius=radius, border=0.02)`.
3. Build `mask_src`: zeros for HEAL, `(source_x, source_y)` for CLONE.
4. Build a `DrawnMaskForm` (mask_type=DT_MASKS_CIRCLE, points=circle_form_bytes, mask_src=...).
5. Build retouch op_params: one form referencing mask_id with the chosen algorithm (HEAL=2 or CLONE=1).
6. Build a dtstyle with one retouch plugin (op_params + standard blendop_params, mask_id binding via blendop).
7. Synthesize new XMP from baseline + dtstyle, injecting masks_history with the circle form.
8. Snapshot.

Same pattern as `apply_with_drawn_mask` (ADR-084), with the added byte-level work of generating the retouch op_params.

---

## Alternatives considered

### Alt 1: Vocabulary entry `spot_heal` with parameterized (x, y, radius), via `apply_primitive`

Considered. Would route through the existing `apply_primitive` MCP surface using RFC-021's parameterization mechanism. Rejected because:

- The patch logic for retouch is structurally bigger than current parameterize decoders. It needs to (a) generate a mask form from coordinates, (b) inject masks_history, (c) write retouch op_params with formid linking, (d) bind blendop_params. Current decoders only patch op_params bytes — extending the parameterize mechanism to handle mask form generation would couple parameterize/ to masking/.
- Spot correction is structurally a different operation from "modify a primitive's effect through parameter values." It REPLACES pixels rather than filtering an effect. The cognitive model "spot correction is a special primitive type with its own MCP tool" matches reality better than "spot correction is a vocabulary entry with parameters."
- Coordinate parameters (x, y) feel different from magnitude parameters (EV, hue°, sat). Splitting them into a dedicated tool keeps `apply_primitive` cohesive.

The decision: **new tool**. ADR-087 carries the ADR-033 cost; the gain is a clean primitive class boundary.

### Alt 2: Sibling-provider scaffolding for everything (no native retouch decoder)

Rejected (carry-over from RFC-025 v0.1). The user-driven spot-removal case is byte-level tractable. Routing it through a provider re-creates ADR-076's dead-infrastructure problem. Provider shape is correct for AI content-aware variants but overkill for "user clicks on this spot." Lands in RFC-030 for the AI variants.

### Alt 3: Defer all spot removal until a content-aware provider lands

Rejected. The user-driven case is the bulk of Lightroom spot-removal usage in real workflows. Deferring means shipping v1.9.0 without the most common version of the gap addressed.

### Alt 4: Stroke recording (record start/end + radius for each painted stroke)

Rejected. darktable's retouch isn't stroke-shaped at the byte level — it's form-shaped. A "stroke" in the user's mental model serializes to one or more form entries with mask_id references. The translation layer between "stroke" and "form" is just CLI/MCP parameter shape; the byte serializer operates on forms.

### Alt 5: Multi-form per call in v1.9.0

Considered. Allowing `apply_spot` to take a list of `(x, y, radius, kind)` tuples in one call would be useful for batched detection. Rejected for v1.9.0:

- The dominant manual workflow is "one spot at a time, snapshot, see result, decide on next."
- AI auto-detection is RFC-030's territory; that RFC will need a multi-form variant or a batching layer above `apply_spot`.
- Single-form is a clean MVP; multi-form can layer on additively.

### Alt 6: Expose all four algorithms (HEAL / CLONE / BLUR / FILL) in v1.9.0

Considered. Rejected for v1.9.0 because:

- HEAL covers ~90% of real spot-removal workflows.
- CLONE covers the other 10% (mirror eyes, copy texture).
- BLUR is rarely used; bilateral / gaussian blur on a region is an exotic move.
- FILL (solid color paint) is even rarer.

Adds two more enum values + scope creep without proportional value. Defer until evidence.

### Alt 7: Expose ellipse / path geometries in v1.9.0

Considered. Rejected — circles cover the dominant case (sensor dust, blemishes, small distractions are all radially symmetric). Ellipses / paths add geometry surface that v1.9.0 doesn't need.

---

## Trade-offs

- **13260-byte op_params is large compared to other modules.** Most retouch op_params bytes are zeros (the unused 299/300 form slots). The encoder is straightforward (pack one form into slot 0, leave the rest zero). modversion drift exposure is the same as smaller modules — ADR-082 backstop covers it.
- **Single-form per call adds latency for multi-spot workflows.** Photographer healing 5 dust spots makes 5 MCP calls = 5 snapshots. Mitigated: each is fast (~ms-level), gives intermediate review points, and matches the "iterate per spot" mental model. Multi-form per call is RFC-030 territory.
- **Coordinates depend on image dimensions.** Coordinates are normalized [0..1]; a 4:3 photo's spot at (0.5, 0.5) vs a 16:9 photo's spot at (0.5, 0.5) are at different absolute positions. Same constraint as the rest of the mask system; consistent with ADR-076.
- **Visual proof on synthetic charts is impossible.** Heal / clone require image content with continuity (skin, sky, etc.) for the algorithm to produce sensible output. Synthetic charts have no continuity. Mitigated: e2e tests use a constructed fixture (image with a known artifact pattern); visual proofs use a real-raw fixture (per #103 mechanism).
- **No undo of a single spot from a multi-spot workflow.** The retouch plugin's form-array carries all forms; there's no per-form unsnapshot. Mitigated: chemigram's snapshot history is per-apply, so reverting one snapshot reverts that spot's introduction. Standard snapshot UX.
- **AI auto-detection deferred.** Photographers wanting "clean up all the manta's spots" route to manual `apply_spot` calls (one per spot) until RFC-030 lands. Documented limitation.

---

## Open questions resolved during deliberation

1. ~~Agent-facing surface shape?~~ → **New MCP tool `apply_spot`** (sister to `apply_primitive`). Justified in ADR-087 against ADR-033's narrow-surface principle.
2. ~~Single-form vs multi-form scope?~~ → **Single-form for v1.9.0.** Multi-form deferred to RFC-030.
3. ~~Algorithm scope?~~ → **HEAL + CLONE for v1.9.0.** BLUR + FILL deferred.
4. ~~Geometry scope?~~ → **CIRCLE for v1.9.0.** Ellipse / path deferred.
5. ~~Source coords encoding for CLONE?~~ → **`mask_src` field on the circle form.** 8 bytes: source_x, source_y as floats. Heal stays at empty (zeros).
6. ~~Per-form vs global algorithm?~~ → **Per-form** (matches darktable's runtime; the global algorithm field is the UI default, the per-form algorithm is what's applied).
7. ~~Tier classification?~~ → **Tier 2** (per ADR-081). Bytes-level, bounded, same cost-shape as other parameterized modules.
8. ~~Vocabulary entries?~~ → **None for v1.9.0.** The tool IS the primitive surface. Vocabulary entries can layer on later if pre-baked spot recipes become valuable.

---

## How this closes

**ADR-087 — Retouch byte encoding + `apply_spot` MCP tool + v1.9.0 scope.** Settles:

- Byte encoders for circle mask form (16 bytes), clone mask_src (8 bytes), retouch form (44 bytes), retouch op_params (13260 bytes).
- The new MCP tool `apply_spot(image_id, *, kind, x, y, radius, source_x?, source_y?, opacity)` and its narrow-surface justification against ADR-033.
- v1.9.0 scope: HEAL + CLONE, CIRCLE geometry, single-form per call. BLUR / FILL / ellipse / path / multi-form deferred.
- Module modversion: retouch mv3.
- Tier classification: Tier 2.
- Test coverage per ADR-080's 5-layer policy, with synthetic fixture for unit/integration and real-raw fixture for visual proof.

AI content-aware variants ("find all the spots automatically") explicitly route to **RFC-030** when that unfreezes.

---

## Links

- TA/components/masking — `chemigram.core.masking.dt_serialize` extension target
- TA/components/synthesizer — apply path
- TA/contracts/per-image-repo — mask form storage
- TA/constraints/opaque-hex-blobs — ADR-008 amended boundary
- ADR-007 — BYOA principle
- ADR-076 — drawn-mask only architecture
- ADR-077..080 — parameterization architecture
- ADR-081 — Tier 2 cost-shape
- ADR-082 — modversion-drift handling
- ADR-084 / RFC-029 — compositional masks at apply time
- ADR-085 / RFC-024 — parametric mask encoding (sibling architectural extension)
- ADR-086 / RFC-026 — LLM-vision-as-provider for AI masks
- RFC-030 — deployed sibling-provider scaffolding (AI auto-spot-detection lands there)
- capability-survey.md § 10 — names retouch as the major portrait gap
- darktable 5.4.1 `src/iop/retouch.c` — `dt_iop_retouch_params_t` source struct
- Issue #108 — opened the question
