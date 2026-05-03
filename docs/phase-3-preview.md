# Phase 3 Preview — Expanding the masked vocabulary

> A guide to thinking about Phase 3 while you're in Phase 2. Heads up: Phase 3 may dissolve into Phase 2 entirely — you might just author masked entries from day one of Phase 2 and never have a separate "Phase 3" transition. This page is for understanding the move, not waiting for permission.
>
> **v1.5.0 update:** the original Phase 3 framing positioned parametric masks against a "Phase 1 raster mask" path that has since been retired (ADR-076 — darktable doesn't read external PNGs for raster masks). The substance survives: vocabulary entries can carry their own masks. The mask flavors are now drawn-form (gradient/ellipse/rectangle, shipping today) and parametric (range-based, blendop-encoded).

## What Phase 3 is

Vocabulary entries carry their own masks. Not AI-generated per-image masks (those don't exist in v1.5.0; they arrive in Phase 4 as a sibling project producing darktable drawn-form geometry). The mask is *baked into the vocabulary entry at authoring time* and applied universally across every image.

Two flavors are usable today:

- **Drawn-form** — gradient, ellipse, or rectangle geometry declared in the entry's `mask_spec`. The engine encodes it into the XMP's `masks_history` at apply time. v1.5.0 ships four such entries in the expressive-baseline pack.
- **Parametric** — luminance/hue/chroma range conditions captured at authoring time inside `blendop_params`. The synthesizer treats `blendop_params` as opaque (ADR-008), so the engine needs no work; you just author in darktable's blend GUI and ship.

**Phase 3 is the work of authoring more of these.** The engine work is done. The contribution is purely vocabulary.

## The mask flavors

| Mask kind | What it is | Authored | Cost | Available |
|-|-|-|-|-|
| **Drawn-form (geometric)** | Hand-set gradient / ellipse / rectangle baked into the entry's `mask_spec`; serialized into the XMP at apply time | At authoring time, declared in the manifest | Cheap; portable across images; not subject-aware | ✅ v1.5.0 |
| **Parametric** | Range-based selection (luminance, chroma, hue, lightness) captured inside `blendop_params` | At capture time in darktable's blend GUI | Cheap; portable; semi-content-aware (responds to image stats) | ✅ Always (engine treats `blendop_params` as opaque) |
| **Drawn-form (path/brush)** | More complex shapes — N-corner paths, brushed regions — beyond the three v1.5.0 forms | In darktable's GUI, exported to a `.dtstyle` carrying the geometry inside `blendop_params` (Path A) | Cheap; portable; image-shape-specific | ✅ Available today via Path A; v1.5.x may add direct `mask_spec` support |
| **Content-aware** | Pixel-precise organic regions (subject silhouettes, eyes, fur edges) | Phase 4 sibling project producing darktable drawn-form geometry | Per-image; precise; requires the sibling project | ⬜ Phase 4 |

The v1.5.0 architecture (ADR-076) made everything in the first three rows go through the same darktable drawn-form wire format. Phase 4 will produce that same wire format from a content-aware masker.

## What masked vocabulary looks like

Examples that fit the convention:

| Name | Mask shape | Use case |
|-|-|-|
| `expo_+0.5_shadows_only` | Parametric, lightness range 0–35% | Lift exposure restricted to dark zones |
| `tone_lift_highlights_clipped` | Parametric, lightness range 80–100% | Recover highlights without touching mid-tones |
| `wb_warm_water_only` | Parametric, hue range cyan-blue | Warm only the water in underwater shots |
| `colorcal_neutral_skin_only` | Parametric, hue range orange-pink, saturation > 20% | Neutralize skin while leaving the background colors alone |
| `gradient_top_dampen_highlights` | Drawn-form gradient | Reduce harsh top light (sun, sky) **— ships in v1.5.0** |
| `gradient_bottom_lift_shadows` | Drawn-form gradient | Lift the foreground **— ships in v1.5.0** |
| `radial_subject_lift` | Drawn-form ellipse, centered | Subject-area emphasis **— ships in v1.5.0** |
| `rectangle_subject_band_dim` | Drawn-form rectangle, mid-band | De-emphasize a horizon line **— ships in v1.5.0** |
| `vignette_subtle` | Drawn-form ellipse with falloff | Subtle attention-pulling vignette |
| `parametric_warm_only_highlights` | Parametric, lightness 70–100% | Warm only the bright zones (golden-hour feel) |

Drawn-form entries declare `mask_spec` in the manifest. Parametric entries don't need any extra schema — the mask geometry rides inside `blendop_params`.

## Drawn-form vs parametric vs content-aware

Same module (e.g., shadow lift), different mask flavors:

```
tone_lifted_shadows                   ← unmasked: lifts ALL shadows globally
tone_lifted_shadows_lightness         ← parametric: lifts shadows in lightness 0–35%
                                        (works on every image, no AI)
gradient_bottom_lift_shadows          ← drawn-form: lifts the bottom half of the frame
                                        (placement-driven, no AI; v1.5.0 ships this)
tone_lifted_shadows_subject           ← content-aware: lifts shadows on a detected subject
                                        (per-image, requires Phase 4 sibling project)
```

All four coexist conceptually. The first three are authorable today; the fourth waits on Phase 4.

Rule of thumb:

- Want to lift shadows everywhere → unmasked entry
- Want to lift dark zones only → parametric entry (cheap, universal, no AI)
- Want to lift the bottom half / a centered area / a band → drawn-form entry (cheap, universal, geometric)
- Want to lift shadows on the manta only → content-aware (Phase 4)

The Phase 3 insight: **a lot of moves you'd reach for as content-aware masks would work fine as parametric or drawn-form masks**, with no AI needed. "Warm the highlights" is parametric. "Dampen the top half" is drawn-form. Reserve content-aware for things that genuinely require knowing *what* a region is.

## What to watch for in Phase 2 that signals Phase 3

As you run sessions in Phase 2, watch for these moments:

### Strong signal — Phase 3 is right here

- **The agent reaches for a content-aware mask but a drawn-form one would do the job.** "Mask the bright sky" → really you mean "the top third of the frame" → `gradient_top_*`.
- **You log gaps that have a clear range condition.** "Need a move that warms only the cyan parts" / "lift shadows but not the deepest blacks" / "saturation boost but not on skin." These are parametric masks waiting to be authored.
- **You log gaps that have a clear placement.** "Need to dampen the right side of the frame" / "lift just the bottom-left corner" → drawn-form masks waiting to be authored (gradients, rectangles, off-center ellipses).
- **Same masked move keeps coming up across different images.** "On every underwater shot I want to warm the water" — that's a parametric WB move (`wb_warm_water_only`), not a 50-image content-aware loop.

### Medium signal

- **You notice the agent describing a region in terms of *properties* of the pixels** (their lightness, their hue) rather than *what they are*. Both flavors are vocabulary-authorable today.

### Weak signal

- **Single-image gaps with a regional component.** Could be parametric, drawn-form, or content-aware. Watch if it recurs.

### Not a Phase 3 signal — actually Phase 4

- **Subject-aware masking.** "Mask the manta" / "the bird's eye" / "this person's face." Drawn-form can't capture organic silhouettes; parametric can't isolate "this animal vs the other animal at the same luminance." Phase 4 handles these via the sibling content-aware masker.

## How to dabble during Phase 2

You don't need to wait for Phase 3 to start.

### Authoring a parametric-mask entry

1. **In darktable's GUI**, open a representative photo for the move you want to author.
2. **Apply the module** (exposure, color calibration, tone equalizer, etc.).
3. **Click the blend tab** for that module → choose "uniformly" → "parametric mask".
4. **Set up the parametric mask** — pick the range channel (lightness, hue, etc.) and adjust the curves to match what you want masked.
5. **Render preview** in darktable to confirm the move feels right.
6. **Export the style** (Styles → Create New Style → select the module → export).
7. **Drop into your personal pack** at `~/.chemigram/vocabulary/personal/layers/L3/<module>/`.
8. **Add a manifest entry.** No `mask_spec` needed — parametric masks ride inside `blendop_params` and the engine treats them as opaque.
9. **Validate** with `./scripts/verify-vocab.sh ~/.chemigram/vocabulary/personal`.
10. **Tell the agent** in your next session.

### Authoring a drawn-form-mask entry

1. **Pick the form** — gradient (top/bottom/sides), ellipse (centered/off-center), or rectangle (band/box). For everything else, see the Path A note below.
2. **Author the dtstyle** for the module you want to bind (exposure, colorbalancergb, etc.) the same way you'd author any vocabulary entry.
3. **Add a manifest entry with `mask_spec`** declaring the form and parameters:
   ```json
   {
     "name": "gradient_left_warm_subject",
     "mask_spec": {
       "dt_form": "gradient",
       "dt_params": {"anchor_x": 0.0, "anchor_y": 0.5, "rotation": 90.0, "compression": 0.5}
     }
   }
   ```
4. **Validate** with `./scripts/verify-vocab.sh`.
5. **Tell the agent** — `apply_primitive` will route through `apply_with_drawn_mask` automatically because `mask_spec` is set.

**Path A alternative for shapes the geometric forms don't cover:** author the mask hand-drawn in darktable's GUI, capture it as a regular `.dtstyle`, and the geometry rides inside `blendop_params` as opaque bytes. No `mask_spec` needed; the engine treats it like any other dtstyle.

This is what "Phase 3 may dissolve into Phase 2" means. There's no transition ceremony. You just start authoring entries with masks when you reach for them.

## Compositional power

The real win of masked vocabulary isn't single moves — it's **composition**. The agent can apply two or three masked entries in sequence:

```
agent: I'll lift shadows in the dark zones (tone_lift_shadows_lightness),
       dampen the bright sky (gradient_top_dampen_highlights), and warm the
       water (wb_warm_water_only). Render?
```

Each move is targeted (mask scopes the effect), composable (they don't fight each other because they affect different ranges/regions), and reproducible (same dtstyle works on every image). That's vocabulary working at full power.

## What Phase 3 is NOT

- **Not content-aware mask generation.** That's Phase 4 (sibling project producing darktable drawn-form geometry from natural-language prompts). Phase 3 is mask flavors that don't need a per-image AI provider.
- **Not engine work.** The engine ships drawn-form serialization in v1.5.0 and treats parametric masks as opaque (ADR-008). Phase 3 is purely vocabulary-author work plus, optionally, additional drawn-form encoders if the gradient/ellipse/rectangle set proves too narrow.
- **Not Phase 5.** Phase 5 is *continuous parametric control* via hex encoders (Path C — programmatic generation of `expo_+0.42`). Phase 3 is *static masks* baked into pre-authored vocabulary.

## Resources

- `docs/IMPLEMENTATION.md` — current phase status
- `docs/concept/04-architecture.md` § 6 (drawn-mask vocabulary entries)
- `docs/adr/ADR-076-drawn-mask-only-mask-architecture.md` — the v1.5.0 mask architecture (supersedes ADR-021/022/055/057/058/074)
- `docs/adr/ADR-008-opaque-blob-carriers.md` — why blendop_params stays opaque (and what that means for parametric masks vs Phase 5)
- `docs/prd/PRD-004-local-adjustments.md` — the user-experience case for masked vocabulary
