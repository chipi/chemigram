# Using your LLM's vision to design masks

> Companion to RFC-026 / ADR-086. The build-by-vision workflow: when the photographer says "lift the iguana's face," the LLM in the chat client looks at the photo and constructs a `mask_spec` from what it sees.
> Sister to `mask-shapes-from-words.md` (build-by-words, ADR-084) and `mask-applicable-controls.md` (which primitive can be applied through a mask).

## The workflow shape

1. Photographer says: *"lift the iguana's face by half a stop"*.
2. Agent calls `render_preview(image_id)` to surface a current-state JPEG of the photo.
3. Chat client renders the JPEG inline (Claude Code via `Read`; Claude Desktop / ChatGPT inline; agent tooling that supports MCP image blocks via image content).
4. The LLM in the conversation **looks at the photo**. It identifies the iguana's face, estimates a bounding region, decides whether ellipse / rectangle / polygon is the right shape.
5. LLM constructs `mask_spec` and calls `apply_primitive("exposure", 0.5, mask_spec={...})`.
6. Photographer reviews the result. If it's wrong, the LLM re-examines and adjusts.

The "AI provider" here is the chat-client LLM itself. No sibling project, no model deployment, no inference server. The vision capability is already in the conversation surface the photographer chose.

## When this works (~70% of content-derived masking)

| Workflow | LLM-vision can do this | Notes |
|-|-|-|
| Coarse subject region | ✓ | Bounding box / ellipse around the subject |
| Sky / foreground split | ✓ | Gradient at horizon + optional color_h refinement |
| Color-range estimation from the photo | ✓ | "What hue range covers the warm tones?" |
| Coarse polygon trace (8-15 vertices) | ✓ | Manta silhouette, building outline, etc. |
| Subject vs background routing | ✓ | Apply edit + apply complementary edit with `invert: true` |
| Iterative refinement | ✓ | LLM re-examines render, adjusts mask coordinates |
| Single-strand hair / fur edges | ✗ | Use drawn radial approximation; precision-tier RFC-030 will lift this ceiling |
| 200+ scattered small spots | ✗ | RFC-025 manual marking + future AI variant in RFC-030 |
| Per-pixel depth maps | ✗ | Needs MiDaS-class model — RFC-030 |

## Pattern library

Each pattern shows: **photographer's phrase → LLM's expected reasoning → resulting `mask_spec`**.

### Pattern 1: Subject region (rectangle or ellipse)

**Photographer:** *"Lift the iguana's face."*

**LLM reasoning** (after looking at the photo via `render_preview`):

> "The iguana's head is in the center-right of the frame, occupying roughly the middle horizontally and the upper third vertically. An ellipse centered around (0.6, 0.35) with radii (0.18, 0.22) and a soft border (0.06) covers the head with natural feathering."

**`mask_spec`:**

```json
{
  "dt_form": "ellipse",
  "dt_params": {
    "center_x": 0.6, "center_y": 0.35,
    "radius_x": 0.18, "radius_y": 0.22,
    "border": 0.06
  }
}
```

**Apply:**

```python
apply_primitive("exposure", 0.5, mask_spec=<spec_above>)
```

When to use rectangle instead of ellipse: subject is rectangular (a building, a sign, a structured object) or the photographer wants hard edges.

### Pattern 2: Polygon trace for irregular subjects

**Photographer:** *"Mask the manta."*

**LLM reasoning:**

> "The manta is in the lower half of the frame, diamond-shaped with wing tips extending. Tracing the rough silhouette as 10 vertices: top of head, right shoulder, right wing tip, right tail, bottom center, left tail, left wing tip, left shoulder, head center, back to top."

**`mask_spec`:**

```json
{
  "dt_form": "path",
  "dt_params": {
    "vertices": [
      [0.5, 0.3], [0.6, 0.4], [0.85, 0.55],
      [0.7, 0.7], [0.5, 0.75],
      [0.3, 0.7], [0.15, 0.55],
      [0.4, 0.4], [0.5, 0.32]
    ],
    "border": 0.04
  }
}
```

LLM polygon estimates degrade past ~15 vertices and on subjects with very irregular boundaries. For pixel-precise silhouettes (single-strand hair, fur edges), drop to RFC-030's deployed-provider arc when it ships.

### Pattern 3: Sky / foreground split (gradient + color_h)

**Photographer:** *"Deepen the sky's blue without affecting the foreground."*

**LLM reasoning:**

> "The horizon line sits at roughly y=0.45. Above is sky (cyan-blue, hue range ~0.55-0.7); below is foreground (warmer tones). Two ways to localize: (a) drawn gradient with anchor at horizon, light side up — affects everything in the upper region uniformly; (b) gradient + color_h range filter — affects only the blue pixels in the upper region. Option (b) is more precise."

**`mask_spec` (drawn gradient + parametric color refinement, intersection):**

```json
{
  "dt_form": "gradient",
  "dt_params": {
    "anchor_x": 0.5, "anchor_y": 0.45,
    "rotation": 0.0, "compression": 0.5, "state": 2
  },
  "range_filter": {
    "kind": "color_h",
    "min": 0.55, "max": 0.7,
    "feather": 0.05
  }
}
```

This is the canonical compositional case: spatial mask defines the *region* (upper half), parametric filter refines to *which pixels* (cyan-blue hues only).

### Pattern 4: Color-range estimation (parametric only)

**Photographer:** *"Mute the saturated reds in the photo."*

**LLM reasoning:**

> "The saturated reds in this photo cluster around hue 0.0-0.05 with high saturation (>0.6). I'll use a parametric `color_s` filter to target high-saturation pixels, no spatial mask needed since the photographer wants the effect everywhere reds appear."

**`mask_spec` (parametric only):**

```json
{
  "range_filter": {
    "kind": "color_s",
    "min": 0.6, "max": 1.0,
    "feather": 0.05
  }
}
```

For more precise hue-specific targeting, combine with a hue range:

```json
{
  "range_filter": {
    "kind": "color_h",
    "min": 0.95, "max": 0.05,
    "feather": 0.05
  }
}
```

(Note: hue wraps, so reds span 0.95-1.0 and 0.0-0.05. For wrap-around ranges, multiple apply calls or a future `compose` schema may be needed; for now, pick the side with more red pixels.)

### Pattern 5: Subject vs background routing

**Photographer:** *"Brighten the iguana, dim everything else."*

**LLM reasoning:**

> "Two complementary edits. First: lift exposure on the subject region (ellipse around the iguana). Second: dim exposure on everything else — same region, inverted via the `range_filter.invert` flag (or apply the complementary edit through a separate `mask_spec` if drawn-only). Or: use just the parametric inversion via a luminance band wider than the whole image, marking the inside as the iguana's region."

**Apply (two calls):**

```python
# First: brighten the subject
apply_primitive("exposure", 0.4, mask_spec={
    "dt_form": "ellipse",
    "dt_params": {"center_x": 0.6, "center_y": 0.35, "radius_x": 0.2, "radius_y": 0.25, "border": 0.08}
})

# Second: dim the background — same shape, but apply a NEGATIVE edit
# (the mask_spec is identical; deterministic-hash means same mask_id;
# darktable composes the two edits)
apply_primitive("exposure", -0.3, mask_spec={
    "dt_form": "ellipse",
    "dt_params": {"center_x": 0.6, "center_y": 0.35, "radius_x": 0.2, "radius_y": 0.25, "border": 0.08},
    "range_filter": {"kind": "luminance", "min": 0.0, "max": 1.0, "feather": 0.0, "invert": True}
})
```

(The `invert: true` on a full-luminance band effectively inverts the mask; apply order + edit polarity together produce the subject-vs-background contrast.)

### Pattern 6: Iterative refinement

**Photographer:** *"That mask is too small — extend it to include the iguana's tail."*

**LLM reasoning:**

> "The iguana's tail extends to the lower-right, around (0.85, 0.6). Current ellipse is at (0.6, 0.35) with radii (0.18, 0.22) — too small and not covering the tail. Switching to a path with vertices that include the tail: head ellipse-like vertices plus tail vertices."

**Apply (revised mask):**

```python
apply_primitive("exposure", 0.5, mask_spec={
    "dt_form": "path",
    "dt_params": {
        "vertices": [
            [0.45, 0.2], [0.75, 0.25], [0.85, 0.4],
            [0.95, 0.55], [0.85, 0.7],
            [0.7, 0.55], [0.45, 0.5], [0.4, 0.3]
        ],
        "border": 0.05
    }
})
```

Photographer sees the new render, gives feedback, LLM iterates. The conversation IS the refinement loop.

## How to ground the LLM in this workflow

When a photographer asks for a content-derived mask, the agent's reasoning chain should be:

1. **Surface the photo** — call `render_preview(image_id)` to get a current-state JPEG.
2. **Look at it** — the chat client renders the JPEG; the LLM's vision sees it.
3. **Identify what the photographer described** — subject, sky, color region, etc.
4. **Pick the right shape** — rectangle for hard regions, ellipse for circular subjects, path for irregular silhouettes, range_filter for tonal/color selection, both for spatial+content intersection.
5. **Estimate coordinates** — use the photo's spatial layout, not assumed positions.
6. **Construct `mask_spec`** — see `mask-shapes-from-words.md` for parameter conventions.
7. **Apply** — `apply_primitive(name, value, mask_spec=...)`.
8. **Verify** — render again, examine, adjust if needed.

## Image-surfacing in different chat clients

| Client | Mechanism |
|-|-|
| Claude Code (this is the primary path) | Agent calls `Read` on the JPEG path returned by `render_preview`; image content surfaces in the conversation |
| Claude Desktop | Drag-drop the rendered JPEG; LLM sees attached images directly |
| ChatGPT (Plus / Team) | Same — drag-drop the JPEG file |
| Anthropic Console / API users | Pass image bytes as MCP `image` content blocks (future enhancement; works via custom tooling today) |

## Limitations of LLM-vision (when to fall back)

LLM-vision is coarse. It is **not** the right tool for:

- **Pixel-perfect silhouettes.** Single-strand hair, fur edges, glasses frames against a complex background.
- **Dense spot enumeration.** "Find all 200+ small spots" — LLMs lose count and miss spots.
- **Per-pixel depth.** "Far mountains only" — no spatial-depth estimation in vision LLMs at usable quality.
- **Sub-pixel registration.** "Move the mask 3 pixels left" — LLMs estimate at percentage-of-image granularity, not pixel granularity.

For these, the photographer falls back to drawn approximations today, and to RFC-030's deployed providers when that lands.

## See also

- [**Mask shapes from words**](mask-shapes-from-words.md) — spatial-English-to-`mask_spec` mapping for build-by-words workflows (RFC-029 / ADR-084)
- [**Mask-applicable controls**](mask-applicable-controls.md) — which vocabulary primitive can be applied through a mask
- ADR-076 (drawn-mask only architecture)
- ADR-084 / RFC-029 (compositional masks at apply time — the wire LLM-vision uses)
- ADR-085 / RFC-024 (parametric range-filter — composes with LLM-vision for content+region intersection)
- ADR-086 / RFC-026 (this guide's closing ADR / RFC)
- RFC-030 (deferred precision-tier deployed-sibling-provider scaffolding)
- `src/chemigram/mcp/tools/rendering.py` — `render_preview` (image-surfacing tool)
