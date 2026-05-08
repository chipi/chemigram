# ADR-085 — Parametric mask encoding via blendif; range_filter mask_spec field

> Status · Accepted
> Date · 2026-05-08
> TA anchor · /components/masking · /contracts/per-image-repo
> Related RFC · RFC-024 (range masks)

## Context

ADR-076 settled the v1.5.0 mask architecture as drawn-only after the PNG-mask path was discovered to be a silent no-op. ADR-084 / RFC-029 closed the agent-facing build-by-words *spatial* workflow. The remaining Lightroom-parity gap is **content-derived masks** — "affect only the dark pixels," "affect only the blue hues" — which Lightroom calls range masks. RFC-024 deliberated four flavors (color, luminance, depth, subject) and concluded with a hybrid: parametric encoding for darktable-native color + luminance (this ADR); provider scaffolding for depth + subject (RFC-026). Full deliberation in RFC-024.

The byte layout was verified against darktable 5.4.1's `src/develop/blend.h`: parametric mask data lives inside `blendop_params` at known offsets, with default per-channel control points of `[0, 0, 1, 1]` (= "always pass") so we only modify channels we filter on.

## Decision

Adopt a **parametric mask encoder** in `chemigram.core.masking.dt_serialize`, with a `range_filter` field on `mask_spec` as the agent-facing surface, AND-composing with the existing `dt_form` / `dt_params` drawn-mask fields.

Three concrete pieces:

### 1. Byte offsets and channel IDs

Verified against `dt_develop_blend_params_t`:

```
offset  20: mask_combine          uint32   (composition: 0 = AND, hardcoded)
offset  28: blendif               uint32   (bitmask: which channels active + invert flags)
offset  68: blendif_parameters    float[64]  (4 control points × 16 channels)
offset 324: blendif_boost_factors float[16]  (per-channel boost; left at default)
```

Per-channel control points at `68 + channel_id * 16` are 4 floats `[low_min, low_max, high_min, high_max]` defining a trapezoid mask. Default `[0, 0, 1, 1]` = always pass.

Channel IDs (color-space-dependent in darktable, but we expose a `kind` string that the encoder maps internally):

| `kind` | Channel ID | blend_cst |
|-|-|-|
| `luminance` | 0 (GRAY_in/L_in; universal) | unchanged |
| `color_h` | 8 (H_in in HSL) | HSL |
| `color_s` | 9 (S_in in HSL) | HSL |
| `color_l` | 10 (l_in in HSL) | HSL |

Inversion is the `+16` bit in the `blendif` bitmask (darktable convention).

### 2. range_filter mask_spec schema

```python
mask_spec = {
    # Spatial (RFC-029 / ADR-084, optional)
    "dt_form": "gradient" | "ellipse" | "rectangle" | "path",
    "dt_params": {...},

    # Pixel-level refinement (this ADR, optional)
    "range_filter": {
        "kind": "luminance" | "color_h" | "color_s" | "color_l",
        "min": 0.0,            # band lower bound, [0..1]
        "max": 0.3,            # band upper bound, [0..1]
        "feather": 0.05,       # ramp width applied to both edges (default 0.05)
        "invert": false,       # default; true = OUTSIDE the range becomes the mask
    },
}
```

The encoder maps `{min, max, feather}` to 4 control points:

```
low_min  = max(0.0, min - feather)
low_max  = min
high_min = max
high_max = min(1.0, max + feather)
```

### 3. mask_mode wiring + mask_combine hardcode

Three valid combinations:

| dt_form | range_filter | mask_mode | mask_combine |
|-|-|-|-|
| present | absent | `1 \| 2 = 3` (drawn only) | unchanged |
| absent | present | `1 \| 4 = 5` (parametric only) | unchanged |
| present | present | `1 \| 2 \| 4 = 7` (AND) | `0` (intersect) |

`mask_combine` other than 0 (OR / SUBTRACT / INVERT) is out of scope. Hardcoded to 0 for v1.9.0; future RFC may revisit.

ADR-033's narrow MCP tool surface preserved — no new tools. The change is purely additive on `mask_spec`.

## Rationale

The byte-level extension is bounded: ~4 byte regions in `blendop_params`, all already documented in darktable's source. Adding parametric encoding matches Tier 2 cost-shape per ADR-081 — flat-scalar struct, byte-level operation, same machinery as parameterized vocabulary modules.

The `range_filter` schema as a sibling to `dt_form` rather than a `kind: "compose"` discriminator is deliberate: it keeps the schema flat, the three valid combinations enumerable, and the agent's mental model simple ("optionally add a pixel filter to your spatial mask"). A more general compose syntax (multi-mask AND/OR/SUBTRACT graphs) is genuinely a different RFC if photographer evidence ever demands it.

mask_combine hardcoded to AND (intersection) reflects the dominant Lightroom workflow; SUBTRACT/INVERT can be expressed via `range_filter.invert: true` (parametric mask flips, drawn-AND-not-parametric). The 3-4% of workflows that need explicit OR or full SUBTRACT can drive a future RFC.

## Alternatives considered

- **Native parametric for ALL four (color/luminance/depth/subject).** Rejected — depth and subject need ML at inference time; Tier 2 cost-shape would be misleading.
- **MCP-provider scaffolding for ALL four.** Rejected — re-creates ADR-076's dead-Protocol problem for the darktable-native cases.
- **`compose` discriminator with operand list (multi-mask graph).** Rejected as scope creep — the flat `dt_form` + `range_filter` shape covers the dominant workflow with less schema surface; a richer compose syntax can land in a future RFC if evidence demands.
- **Expose all four mask_combine modes (AND/OR/SUBTRACT/INVERT).** Rejected for v1.9.0 — `invert` on `range_filter` covers the common SUBTRACT case; OR is rare enough to defer.
- **Drawn-mask approximations forever (don't ship parametric).** Rejected — color and luminance ranges are fundamentally different operations from spatial regions; no drawn approximation captures "all the dark pixels in the photo."

## Consequences

Positive:

- **The user's mental model lands.** "Refine my drawn mask down to specific pixels" works directly: drawn ellipse + luminance shadows filter = "dark pixels in the subject region."
- **Color and luminance ranges become first-class.** Photographers can ship vocabulary entries that target "blue sky," "shadows only," "highlights only" without a per-image session.
- **Composes cleanly with RFC-029.** Same `mask_spec` struct, same apply path, same deterministic-hash reuse. The `range_filter` field is purely additive.
- **MCP surface stays narrow.** No new tools (ADR-033 preserved).
- **Subject + depth correctly deferred.** RFC-026's BYOA-shaped scaffolding is the right architectural arc for those; coupling them to RFC-024's bytes-only path would muddle both.

Negative:

- **mask_combine hardcoded to AND.** Workflows needing explicit OR can't be expressed in v1.9.0. Mitigated: rare in practice; `invert` covers SUBTRACT.
- **Color-range entries are camera/image-dependent.** Hue ranges tuned to one image's sky won't match another's. Mitigated: Phase 2 evidence drives parameterization (RFC-021 mechanism) if the issue surfaces.
- **modversion drift surface grows.** ~5 new byte regions exposed. Mitigated: ADR-082 backstop applies (warn at load, fail at apply).
- **`range_filter` adds cognitive overhead to the schema.** Agents now decide: drawn? parametric? both? Mitigated: docs guide spells out the three combinations with concrete examples.

## Implementation notes

### `dt_serialize.py` extensions

New constants:

```python
_OFFSET_MASK_COMBINE: Final = 20
_OFFSET_BLENDIF: Final = 28
_OFFSET_BLENDIF_PARAMETERS: Final = 68
_OFFSET_BLENDIF_BOOST_FACTORS: Final = 324
_OFFSET_BLEND_CST: Final = 4

# Channel IDs (subset relevant for v1.9.0)
DEVELOP_BLENDIF_GRAY_in: Final = 0   # luminance (universal)
DEVELOP_BLENDIF_H_in: Final = 8      # HSL hue
DEVELOP_BLENDIF_S_in: Final = 9      # HSL saturation
DEVELOP_BLENDIF_l_in: Final = 10     # HSL lightness

# Color-space constants (dt_iop_colorspace_type_t subset)
IOP_CS_HSL: Final = 5  # verified against darktable 5.4.1
```

New encoder:

```python
def encode_blendop_with_parametric_mask(
    *,
    range_kind: Literal["luminance", "color_h", "color_s", "color_l"],
    range_min: float,
    range_max: float,
    feather: float = 0.05,
    invert: bool = False,
    mask_id: int | None = None,  # None = parametric only; int = drawn AND parametric
    opacity: float = 100.0,
    base_blendop: bytes = _DEFAULT_BLENDOP_BYTES,
) -> bytes:
    ...
```

Logic:
1. Compute mask_mode based on `mask_id is None` (parametric only = 5) vs not (drawn + parametric = 7)
2. Patch `mask_mode`, `mask_combine` (=0), `mask_id` (if drawn), `opacity`
3. Set `blendif` bit for the channel; set `+16` bit if `invert`
4. Patch the 4 control points at offset `68 + channel_id * 16`
5. If `range_kind` starts with `"color_"`, patch `blend_cst` to `IOP_CS_HSL`

### `helpers.py` apply path

`apply_with_drawn_mask` generalizes (or sister function `apply_with_mask`) to handle the three valid combinations:

```python
def apply_entry(
    baseline: Xmp,
    entry: VocabEntry,
    *,
    parameter_values: dict[str, float] | None = None,
    mask_spec: dict | None = None,  # may have dt_form, range_filter, or both
    ...
) -> Xmp:
    ...
```

Dispatch logic in `apply_with_drawn_mask` (or generalized helper):

- Both `dt_form` and `range_filter` present → encode drawn form + parametric mask, mask_mode=7
- Only `dt_form` → existing path (mask_mode=3)
- Only `range_filter` → no `masks_history` element; just modified `blendop_params`, mask_mode=5

### MCP tool schema

`_MASK_SPEC_SCHEMA` in `vocab_edit.py` gains `range_filter` as an optional property:

```python
"range_filter": {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["luminance", "color_h", "color_s", "color_l"]},
        "min": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "max": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "feather": {"type": "number", "minimum": 0.0, "maximum": 0.5},
        "invert": {"type": "boolean"},
    },
    "required": ["kind", "min", "max"],
}
```

### Test coverage

Per ADR-080's 5-layer policy, with the lab-grade tier requiring a fixture with sufficient luminance variation:

1. **Unit (test_dt_serialize.py)** — byte offsets correct, blendif bitmask sets right channel, control points map correctly, default fields preserved
2. **Integration** — apply_with_drawn_mask or generalized helper produces XMP that round-trips through parse/serialize
3. **Lab-grade global** — luminance_range alone produces correct render on synthetic grayscale ramp (shadow band brightens, midtones don't)
4. **Lab-grade masked** — drawn gradient + luminance_range produces intersection (only dark pixels in gradient region brighten)
5. **Visual proof** — gallery render against grayscale ramp showing each kind's effect

Color-range coverage may use real-raw fixture (synthetic chart has no hue diversity); add to gallery script's skip-list mechanism if synthetic rendering is unstable.

The substrate (drawn mask wire from ADR-076 + path encoding from RFC-026 substrate) is in place. This ADR adds the parametric layer alongside.
