# Mask-applicable controls

> Companion to ADR-076 (drawn-mask-only architecture). What can be applied through a mask, what can't, how to do it.

Chemigram supports binding **any vocabulary primitive** to a drawn mask region (gradient, ellipse, or rectangle). The four mask-bound primitives shipped in `expressive-baseline` (`gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim`) are *examples* of common photographic moves, not the boundary of what's possible. The underlying mechanism — `chemigram.core.helpers.apply_with_drawn_mask` — works on every loaded vocab entry mechanically. The differences this guide covers are about whether the *photographic result* of masking a particular module is sensible.

This guide answers three questions:

1. What does the engine do when you mask a primitive?
2. Which primitives are reasonable to mask, and which aren't?
3. How do you mask an arbitrary primitive?

---

## 1. What the engine does when you mask a primitive

`apply_with_drawn_mask(baseline, dtstyle, mask_spec)`:

1. Builds a `DrawnMaskForm` from `mask_spec` (a `gradient | ellipse | rectangle` schema with darktable-native parameters).
2. Patches **every plugin's** 420-byte `blendop_params` blob in the dtstyle:
   - `mask_mode = ENABLED | MASK = 3` (drawn mask on)
   - `mask_id = <form id>`
   - `opacity = 100.0` (default)
3. Synthesizes a new XMP applying that patched dtstyle on top of the baseline.
4. Injects `<darktable:masks_history>` with the form encoded in darktable's wire format (verified against `darktable 5.4.1` source: `src/develop/masks.h`, `src/common/exif.cc`).

The patched XMP, when rendered by `darktable-cli`, applies the primitive's effect *only* in the masked region (with the form's natural feathering / falloff), leaving the rest of the frame untouched.

**This works the same way for every vocabulary entry.** The unit test [`test_apply_universality`](https://github.com/chipi/chemigram/blob/main/tests/unit/core/masking/test_apply_universality.py) verifies the apply path completes for every loaded entry × every drawn-form spec. There are no "this primitive can't be masked" cases in the engine.

The interesting questions are at the photographic layer: does masking a particular module *make sense*, and does darktable's renderer produce the result you'd expect?

---

## 2. Compatibility matrix

The matrix below maps each darktable module touched by the chemigram vocabulary to "is it useful to mask?" and "is the photographic result well-defined?" The mechanical apply path works for everything in the **Engine** column; the **Photographic** column is where the nuance lives.

| Module | Vocabulary entries | Engine | Photographic | Notes |
|--------|-------------------|--------|--------------|-------|
| `exposure` | `expo_+0.5`, `expo_-0.5`, `expo_+0.3`, `expo_-0.3`, `shadows_global_+/-`, `gradient_*`, `radial_*`, `rectangle_*` | ✅ | ✅ | The 4 shipped masked primitives use this. EV deltas through a region are the canonical use case (dodge/burn). |
| `colorbalancergb` | `sat_*`, `vibrance_+0.3`, `grade_*`, `chroma_boost_*` | ✅ | ✅ | Saturation and grading through a region work cleanly — collapse a background to monochrome, warm the subject, etc. Verified by [`test_lab_grade_masked_universality`](https://github.com/chipi/chemigram/blob/main/tests/e2e/test_lab_grade_masked_universality.py) (sat_kill through a center mask leaves corner chroma intact). |
| `sigmoid` | `contrast_low/high`, `blacks_lifted/crushed`, `whites_open` | ✅ | ⚠️ Use with care | s-curves are tone benders — applying one in a region can produce visible seam where the curve transitions between masked and unmasked areas. Soft falloff helps. Sometimes the right call; sometimes you want a global contrast move and a regional luma move instead. |
| `bilat` (localcontrast) | `clarity_strong`, `clarity_painterly` | ✅ | ✅ | Local-contrast through a region is photographically clean (sharpen a face, soften a background). Edge enhancement respects the mask. |
| `vignette` | `vignette_subtle/medium/heavy` | ✅ | ❌ Don't | The vignette module is itself geometric — it produces a radial darkening centered on the frame. Pairing it with a mask is two competing geometries; the result is rarely what you want. Use exposure-through-a-mask for region darkening instead. |
| `temperature` (white balance) | `wb_warm_subtle`, `wb_cool_subtle` | ✅ | ⚠️ Pipeline-position caveat | `temperature` runs early in darktable's pipeline (before `colorin`), so masking it has a *different visual effect* than masking a downstream color move. For "warm the subject", prefer `grade_highlights_warm` or a `colorbalancergb` move through a mask — the photographic result is more predictable. |
| `channelmixerrgb` | (currently unused; planned in #63) | ✅ | ✅ | When the v1.6.0 B&W trio ships, mask binding will follow the colorbalancergb pattern (mid-pipeline, uniform per-patch effect). |
| `grain` | `grain_fine/medium/heavy` | ✅ | ⚠️ Edge artifact risk | Grain texture is randomized per-pixel; through a mask, you'll see a visible boundary where grain stops. Acceptable if the mask has soft falloff and the grain is subtle. |
| `highlights` | `highlights_recovery_subtle/strong` | ✅ | ⚠️ Limited usefulness | Highlights recovery operates on raw / pre-demosaic data; it works through the mask but the photographic value of "recover only some highlights" is rare. Usually you either want all highlights recovered or none. |

### Legend

- **Engine ✅**: `apply_with_drawn_mask` completes cleanly; the rendered XMP is well-formed.
- **Photographic ✅**: The masked render produces what the photographer would intuitively expect.
- **Photographic ⚠️**: It renders, but think carefully — there's a caveat (seam, pipeline position, edge artifact).
- **Photographic ❌**: Don't. The combination doesn't make photographic sense.

### Per-module rationale (anchor targets)

Stable link targets for the per-row notes in the [visual proofs gallery](visual-proofs.md). One short paragraph per module with the rationale already implied by the matrix above.

<a id="temperature"></a>
**`temperature`** — drawn-mask binding is silently ignored at render time. darktable's temperature module runs early in the pipeline (before `colorin`), and the masking machinery operates on data that's already been white-balanced. Empirically, a masked `wb_warm_subtle` produces a render byte-identical to its global counterpart. Consequence: the gallery suppresses the masked column for `wb_*` entries; for "warm the subject," reach for `grade_highlights_warm` or a `colorbalancergb` move with a mask instead.

<a id="vignette"></a>
**`vignette`** — geometric × geometric is a contradiction. The `vignette` module produces its own radial intensity profile peaking at the frame edges; a centered ellipse mask is `1` where the vignette is `0`, and vice versa. The two geometries cancel; the masked render returns near-baseline. Consequence: the gallery suppresses the masked column for `vignette_*` entries. For region darkening, reach for `exposure` through a mask.

<a id="highlights"></a>
**`highlights`** — works through a mask, but only matters where input has clipping. The synthetic ColorChecker chart has no blown highlights, so the rendered effect is below the visible threshold. Consequence: the gallery annotates `highlights_recovery_*` rows as near-baseline-on-this-input rather than suppressing them; on a real raw with clipped sky or specular highlights the masked variant is photographically meaningful.

<a id="grain"></a>
**`grain`** — works through a mask, but the texture is hard to see on flat chart patches. Grain is per-pixel high-frequency noise; on uniform colored patches the diff vs baseline is small. Consequence: the gallery annotates `grain_*` rows as near-baseline-on-this-input. On a real photograph with continuous tone the grain is clearly visible inside the mask region.

---

## 3. How to mask an arbitrary primitive

Three paths: direct CLI, vocabulary authoring, and Python.

### From the CLI (one-off, ad hoc masking)

`chemigram apply-primitive` accepts `--mask-spec '<json>'` to apply any primitive through an ad-hoc drawn mask:

```bash
chemigram apply-primitive <image_id> --entry sat_kill \
  --pack expressive-baseline \
  --mask-spec '{"dt_form":"ellipse","dt_params":{"center_x":0.5,"center_y":0.5,"radius_x":0.3,"radius_y":0.3,"border":0.1}}'
```

The JSON shape matches the manifest's `mask_spec` field (gradient / ellipse / rectangle with their `dt_params` — schema reference below). When both `--mask-spec` and the entry's manifest `mask_spec` are present, the CLI flag overrides — useful for re-shaping a shipped masked entry on a specific photograph.

For repeatable moves, prefer authoring a vocabulary entry that bakes the mask in (next section); the CLI flag is for ad-hoc work.

### Authoring a mask-bound vocabulary entry

The 4 shipped masked entries are good templates. A masked `.dtstyle` is just a regular `.dtstyle` file — the binding lives in the manifest entry, not the file:

```json
{
  "name": "subject_warm_lift",
  "layer": "L3",
  "subtype": "colorbalancergb",
  "path": "layers/L3/colorbalancergb/subject_warm_lift.dtstyle",
  "touches": ["colorbalancergb"],
  "tags": ["subject", "warm", "mask", "radial"],
  "description": "Warm highlights + chroma boost on the subject only.",
  "modversions": {"colorbalancergb": 5},
  "darktable_version": "5.4",
  "source": "personal",
  "license": "MIT",
  "mask_spec": {
    "dt_form": "ellipse",
    "dt_params": {
      "center_x": 0.5,
      "center_y": 0.5,
      "radius_x": 0.25,
      "radius_y": 0.3,
      "border": 0.1
    }
  }
}
```

When the engine applies this entry, `apply_with_drawn_mask` automatically routes through the masked path because `mask_spec is not None`. The `.dtstyle` file itself is the global version of the move; the manifest's `mask_spec` overlays the geometry at apply time. See [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) for the full flow.

### From an MCP agent (one-off, ad hoc masking)

The `apply_primitive` MCP tool accepts an optional `mask_spec` argument with the same JSON shape:

```json
{
  "tool": "apply_primitive",
  "args": {
    "image_id": "<id>",
    "primitive_name": "sat_kill",
    "mask_spec": {
      "dt_form": "ellipse",
      "dt_params": {
        "center_x": 0.5, "center_y": 0.5,
        "radius_x": 0.3, "radius_y": 0.3,
        "border": 0.1
      }
    }
  }
}
```

Same precedence as the CLI: `mask_spec` from the agent overrides the entry's manifest `mask_spec` if both are present.

### From Python (programmatic, one-off)

```python
from chemigram.core.helpers import apply_with_drawn_mask
from chemigram.core.vocab import load_packs
from chemigram.core.xmp import parse_xmp

baseline = parse_xmp(workspace / "current.xmp")
vocab = load_packs(["starter", "expressive-baseline"])

# Pick any global primitive
entry = vocab.lookup_by_name("sat_kill")

# Apply it through a centered radial mask
mask_spec = {
    "dt_form": "ellipse",
    "dt_params": {
        "center_x": 0.5, "center_y": 0.5,
        "radius_x": 0.3, "radius_y": 0.3,
        "border": 0.1,
    },
}
applied = apply_with_drawn_mask(baseline, entry.dtstyle, mask_spec)
# `applied` is a new Xmp with sat_kill bound to the ellipse.
# Render it through `chemigram.core.pipeline.render(...)`.
```

`mask_spec` schemas:

| Form | Required keys | Optional keys |
|------|--------------|---------------|
| `gradient` | `anchor_x`, `anchor_y`, `rotation` | `compression`, `steepness`, `curvature`, `state` |
| `ellipse` | `center_x`, `center_y`, `radius_x`, `radius_y` | `rotation`, `border`, `flags` |
| `rectangle` | `x0`, `y0`, `x1`, `y1` | `border` |

All coordinates are normalized image coordinates `[0, 1]`. See `chemigram.core.masking.dt_serialize` for parameter semantics (with citations to the darktable source for each field).

---

## 4. Verifying mask localization on a custom primitive

If you author a masked entry and want laboratory-grade confirmation that it's localizing correctly:

1. **Add an entry to `EXPECTED_EFFECTS`** in [`tests/e2e/_lab_grade_deltas.py`](https://github.com/chipi/chemigram/blob/main/tests/e2e/_lab_grade_deltas.py), using `_check_zone_dampen` or `_check_zone_lift` with the appropriate ColorChecker zones (constants `_CC_TOP_HALF`, `_CC_CENTER_4`, etc.).
2. **Run the lab-grade suite**: `pytest tests/e2e/test_lab_grade_primitives.py -v`. The chart-based isolation will measure your primitive's spatial effect against synthetic ColorChecker patches and tell you whether the mask is localizing as expected.
3. **For module-level validation** (a category not yet in `MASK_COVERAGE`), add to [`tests/e2e/test_lab_grade_masked_universality.py`](https://github.com/chipi/chemigram/blob/main/tests/e2e/test_lab_grade_masked_universality.py).

The visual gallery at [`docs/guides/visual-proofs.md`](visual-proofs.md) shows the rendered before/after for every primitive (including the 4 mask-bound ones). The lab-grade tests check the same renders programmatically.

---

## See also

- [`authoring-vocabulary-entries.md`](authoring-vocabulary-entries.md) — full flow for shipping a new vocabulary entry (with or without mask)
- [`vocabulary-patterns.md`](vocabulary-patterns.md) — composition recipes including mask combinations
- [`visual-proofs.md`](visual-proofs.md) — chart-based before/after gallery for every shipped primitive
- [ADR-076](../adr/ADR-076-drawn-mask-only-mask-architecture.md) — the architectural decision that drawn-form masking is the only path
- [`docs/concept/04-architecture.md`](../concept/04-architecture.md) §3.1 — masking in the synthesizer
