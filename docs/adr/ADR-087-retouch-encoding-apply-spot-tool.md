# ADR-087 — Retouch byte encoding + `apply_spot` MCP tool

> Status · Accepted
> Date · 2026-05-08
> TA anchor · /components/masking · /contracts/mcp-tools · /components/synthesizer
> Related RFC · RFC-025 (spot removal / heal architecture)

## Context

Lightroom's spot removal / heal / clone is the canonical retouch workflow — the largest remaining portrait gap per capability-survey § 10. darktable's `retouch` module (mv3) covers the same workflow at the engine level. Reading the source struct (verified against darktable 5.4.1 `src/iop/retouch.c`) reveals the byte format is form-array-based: each retouch form references a `mask_id` from `masks_history` — same wire as drawn masks (RFC-029 / ADR-084) and parametric masks (RFC-024 / ADR-085). Full deliberation in RFC-025; this ADR captures the closing decisions.

Per-form struct is 44 bytes; op_params total is 13260 bytes (300 × 44 form-array + 60-byte global tail). Most bytes are zero in real use (one or two active forms, the rest empty). The architectural question is the agent-facing surface, not the byte format — RFC-025 v0.1's deliberation closed on **a new MCP tool sister to `apply_primitive`** as the cleanest fit for spot correction's structurally different primitive class (replaces pixels rather than filtering through a primitive).

## Decision

Adopt a **new MCP tool `apply_spot`** + **byte encoders in `dt_serialize.py`** for retouch op_params and circle mask forms. v1.9.0 scope: **HEAL + CLONE algorithms, CIRCLE geometry, single-form per call.**

### 1. New MCP tool: `apply_spot`

```python
@tool
def apply_spot(
    image_id: str,
    *,
    kind: Literal["heal", "clone"],
    x: float,            # spot center, [0..1]
    y: float,            # spot center, [0..1]
    radius: float,       # spot radius, [0..1] (typically 0.01-0.10)
    source_x: float | None = None,  # required for clone; ignored for heal
    source_y: float | None = None,  # required for clone; ignored for heal
    opacity: float = 100.0,
) -> dict:
    """Apply a spot retouch (heal or clone) at the given coordinate and snapshot."""
```

Sister to `apply_primitive`. Justifies its own MCP tool because spot correction is structurally different from other primitives — it replaces pixels rather than filtering an effect, and its parameter shape (coordinates + algorithm choice + optional source coords) doesn't fit the magnitude-parameter convention of `apply_primitive`. ADR-033's narrow-surface principle is preserved with this single addition.

The flow:

1. Compute deterministic `mask_id` from hash of `(kind, x, y, radius, source_x?, source_y?)`.
2. Build a CIRCLE form: `encode_circle_mask_points(center_x=x, center_y=y, radius=radius, border=0.02)`.
3. Build `mask_src`: zeros for HEAL, `(source_x, source_y)` for CLONE.
4. Wrap in `DrawnMaskForm(mask_type=DT_MASKS_CIRCLE, mask_points=circle_bytes, mask_src=...)`.
5. Build retouch op_params: one form referencing mask_id with the chosen algorithm.
6. Build dtstyle with one retouch plugin (op_params + blendop_params, mask_id binding via blendop).
7. Synthesize new XMP from baseline + dtstyle, injecting masks_history.
8. Snapshot.

### 2. Byte encoders in `dt_serialize.py`

Verified against darktable 5.4.1's `dt_iop_retouch_params_t`:

```python
# Per-form: 44 bytes
def encode_retouch_form(
    *,
    formid: int,
    algorithm: int,         # DT_IOP_RETOUCH_HEAL=2, DT_IOP_RETOUCH_CLONE=1
    scale: int = 0,
    blur_type: int = 0,
    blur_radius: float = 0.0,
    fill_mode: int = 0,
    fill_color: tuple[float, float, float] = (0.0, 0.0, 0.0),
    fill_brightness: float = 0.0,
    distort_mode: int = 0,
) -> bytes: ...

# Op_params: 13260 bytes (300 forms × 44 + 60-byte tail)
def encode_retouch_op_params(forms: list[bytes]) -> bytes: ...

# Circle mask form: 16 bytes (cx, cy, radius, border as floats)
def encode_circle_mask_points(
    *, center_x: float, center_y: float, radius: float, border: float = 0.0
) -> bytes: ...

# Clone source: 8 bytes (source_x, source_y as floats)
def encode_clone_mask_src(*, source_x: float, source_y: float) -> bytes: ...
```

New constants:

```python
DT_IOP_RETOUCH_NONE  = 0
DT_IOP_RETOUCH_CLONE = 1
DT_IOP_RETOUCH_HEAL  = 2
DT_IOP_RETOUCH_BLUR  = 3   # not exposed in v1.9.0
DT_IOP_RETOUCH_FILL  = 4   # not exposed in v1.9.0

RETOUCH_NO_FORMS    = 300
RETOUCH_FORM_SIZE   = 44
RETOUCH_PARAMS_SIZE = 13260  # 300*44 + 60-byte tail

# DT_MASKS_CIRCLE already defined (= 1 << 0)
```

### 3. v1.9.0 scope boundaries

- **Algorithms**: HEAL + CLONE only. BLUR + FILL deferred.
- **Geometry**: CIRCLE only. Ellipse / path / brush deferred.
- **Form count**: single form per call. Multi-form per call deferred to RFC-030 (where AI auto-detection returns batched spot lists).
- **Module version**: retouch mv3 (current darktable 5.4.1).
- **Tier classification**: Tier 2 per ADR-081.

### 4. Test coverage

5-layer per ADR-080:

1. **Unit** — byte offsets, multi-form arrays, algorithm encoding, validation, preserved bytes.
2. **Integration** — `apply_spot` produces XMP that round-trips through parse/serialize.
3. **Lab-grade global** — synthetic fixture with constructed blemish; spot_heal removes the variance at the heal coordinate.
4. **Lab-grade masked** — N/A (retouch IS the mask path; no separate masked tier).
5. **Visual proof** — real-raw fixture (per #103 mechanism); synthetic charts have no content continuity for heal/clone to work meaningfully.

## Rationale

The decoder shape is a small extension of the existing dt_serialize codec — same architectural pattern as parametric mask encoding (ADR-085). Most retouch op_params bytes are zeros in real use; the encoder pattern (pack form 0 active, leave forms 1..299 empty) keeps the implementation simple.

A new MCP tool wins over vocabulary-entry-via-`apply_primitive` because:

1. **Different primitive class.** Spot correction replaces pixels via a darktable algorithm. `apply_primitive` modifies an effect through parameter values. The cognitive model "spot correction is its own kind of primitive" matches reality.
2. **Different parameter shape.** Coordinates (x, y) and algorithm choice (heal/clone) don't fit the magnitude-parameter convention of `apply_primitive`'s `value` argument.
3. **Cleaner extension surface.** The retouch patch logic needs to generate a mask form + masks_history XML + op_params + blendop binding — all four pieces. Forcing this through `apply_primitive`'s parameterize/patch path would couple `parameterize/` to `masking/`. A dedicated tool keeps the boundaries clean.
4. **ADR-033 cost is bounded.** Just one new tool. The narrow-surface principle is preserved; future primitive-class additions (e.g., perspective correction, advanced cropping) can each justify their own tool.

The v1.9.0 scope (HEAL + CLONE, CIRCLE, single-form) covers ~95% of real-world spot-removal workflows. The deferred items (BLUR / FILL algorithms, ellipse / path geometries, multi-form per call) all address edge cases that can layer on additively when evidence demands.

## Alternatives considered

- **Vocabulary entry `spot_heal` parameterized over `(x, y, radius)` via `apply_primitive`.** Rejected — couples parameterize/ to masking/, mixes magnitude and coordinate parameter classes, conflates pixel-replacement with effect-filtering primitives.
- **Multi-form per call in v1.9.0.** Rejected — single-form is a clean MVP; AI batching is RFC-030's territory.
- **All four retouch algorithms (HEAL / CLONE / BLUR / FILL) in v1.9.0.** Rejected — BLUR + FILL are rare moves; defer until evidence.
- **Ellipse / path / brush mask geometries.** Rejected — circles cover the dominant case (spots are radially symmetric); other geometries are exotic.
- **Stroke-based recording** (Lightroom's spot-remove brush stroke). Rejected — darktable's wire is form-shaped; strokes serialize to forms via the same coordinate mechanism.
- **Sibling-provider scaffolding for everything (no native decoder).** Rejected — re-creates ADR-076's dead-Protocol problem for the byte-tractable manual case. Provider arc is correct for AI auto-detection (RFC-030), overkill for "user clicks on this spot."

## Consequences

Positive:

- **Closes the largest remaining portrait gap.** Sensor dust, blemishes, distracting elements — all become one MCP call away.
- **Architecturally clean.** Spot correction has its own MCP surface; doesn't pollute `apply_primitive`'s magnitude-parameter convention.
- **Composes with existing wire.** Mask form + masks_history + blendop_params binding all reuse the RFC-029 / ADR-084 substrate.
- **Bounded byte exposure.** ~13KB op_params is large but mostly zeros; encoder is straightforward.
- **AI auto-detection path stays open.** RFC-030's deployed-provider scaffolding lands batched multi-spot detection on top of this RFC's wire.

Negative:

- **One more MCP tool** (ADR-033 cost). Justified by the structurally different primitive class.
- **Single-form per call adds latency for multi-spot workflows** (5 dust spots = 5 calls = 5 snapshots). Mitigated by per-call snapshot review value.
- **Visual proof requires real-raw fixture** (synthetic charts have no continuity for heal/clone to work). Same constraint as some other entries (HSL via colorequal); existing fixture mechanism (#103) handles it.
- **modversion-drift surface grows by one module.** ADR-082 backstop applies.
- **AI auto-detection deferred.** Manual spot-by-spot until RFC-030 ships; documented limitation.

## Implementation notes

### Files touched

- `src/chemigram/core/masking/dt_serialize.py` — new encoders (`encode_retouch_form`, `encode_retouch_op_params`, `encode_circle_mask_points`, `encode_clone_mask_src`) + new constants.
- `src/chemigram/core/helpers.py` — possibly a new `apply_spot_retouch()` helper (sister to `apply_with_drawn_mask`) that handles the retouch-specific synthesis.
- `src/chemigram/mcp/tools/` — new file `retouch.py` (or addition to `vocab_edit.py`) registering the `apply_spot` tool.
- `tests/unit/core/masking/test_dt_serialize.py` — unit tests for the encoders.
- `tests/integration/core/` — integration test for the apply path.
- `tests/e2e/test_apply_spot_retouch.py` — e2e test against darktable.
- `docs/guides/mask-applicable-controls.md` — note retouch as a separate primitive class.
- `docs/capability-survey.md` — mark RFC-025 closed.

### What this ADR explicitly does NOT settle

- **AI auto-spot detection** (RFC-030's territory).
- **Multi-form per call** (RFC-030's territory).
- **BLUR / FILL algorithms** (deferred until evidence).
- **Ellipse / path / brush retouch geometries** (deferred until evidence).
- **Pre-baked vocabulary entries** for common spot patterns (e.g., `spot_heal_default`). Could layer on later; `apply_spot` IS the v1.9.0 primitive surface.

When AI auto-detection becomes the bottleneck, RFC-030 unfreezes and lands the batching layer above this RFC's `apply_spot` wire.
