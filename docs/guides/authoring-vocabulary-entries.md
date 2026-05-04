# Authoring vocabulary entries

> The Phase 2 daily-use flow: open darktable → set up the move → save the style → drop it into your personal pack → use it from the next session on.
>
> This guide is for hand-authored entries built from darktable's GUI. For the programmatic struct-RE path used to ship the `expressive-baseline` pack, see [`expressive-baseline-authoring.md`](expressive-baseline-authoring.md). For drawn-mask-bound entries specifically, see the [Mask-bound entries](#mask-bound-entries) section below.

---

## When to author a new entry

Phase 2 vocabulary growth happens *in response to gaps* surfaced during real sessions, not in a separate authoring sprint. The agent logs gaps via `log_vocabulary_gap` when it reaches for a primitive that doesn't exist.

Periodically — a vocabulary-authoring evening per month is the rhythm — read your gaps and pick the ones worth turning into entries:

```bash
cat ~/Pictures/Chemigram/*/vocabulary_gaps.jsonl | jq -r '.description'
```

The threshold: a gap that **recurred across multiple images** is worth authoring. A one-off intent that won't return is just a workaround note.

---

## The flow

### 1. Open the gap-source image in darktable

Pick the image where the gap was most obvious. You want a real photo to author against because the move's parameter values are scene-dependent in subtle ways — authoring on a flat synthetic frame produces a primitive that doesn't behave on real images.

### 2. Set up the move

Adjust modules in darktable's GUI until the move does what you wanted. **One module per primitive** — keep entries single-module so they compose cleanly. (If a move genuinely requires two modules, that's a *composite* primitive — usually L2 — and is rare.)

For example, to author `wb_warm_water_only` (warm WB restricted to cyan-blue hues via a parametric mask):

1. Enable `temperature` (the WB module).
2. Set the temperature offset to a small positive value.
3. In `temperature`'s blend tab, choose "uniformly" → "parametric mask".
4. Set the parametric mask to restrict by hue range, capturing cyan-blue.
5. Render preview in darktable; confirm the move feels right.

For drawn-form mask-bound entries (gradient/ellipse/rectangle), see the [Mask-bound entries](#mask-bound-entries) section.

### 3. Compress history

**Right-click the history stack** (left panel, near bottom) → **compress history**. This collapses your edits to a single clean state. Without this step, the exported style includes every iteration, which makes the resulting `.dtstyle` huge and inscrutable.

### 4. Save as a style

**Right-click the styles panel** (left panel) → **create style**.

- **Name:** the canonical primitive name following the convention `<module>_<intention>_<context>` (e.g., `wb_warm_water_only`, `tone_lift_highlights_recover`, `radial_subject_lift_subtle`).
- **Description:** one sentence on what the move does. This shows up in `chemigram vocab show` and the agent's `list_vocabulary`.
- **Modules to include:** select **only** the module(s) you set up. If darktable defaults to selecting all enabled modules, deselect everything except your target.

### 5. Export the `.dtstyle`

**Right-click the new style** → **export**.

Save to your personal pack:

```
~/.chemigram/vocabulary/personal/layers/L3/<module>/<name>.dtstyle
```

For example: `~/.chemigram/vocabulary/personal/layers/L3/temperature/wb_warm_water_only.dtstyle`.

L1 entries (camera+lens-bound technical correction) go to `layers/L1/<camera>/`. L2 composite looks go to `layers/L2/look/`. Most entries are L3.

### 6. Add a manifest entry

Open `~/.chemigram/vocabulary/personal/manifest.json` (create it if absent) and add an entry:

```json
{
  "entries": [
    {
      "name": "wb_warm_water_only",
      "layer": "L3",
      "subtype": "wb",
      "path": "layers/L3/temperature/wb_warm_water_only.dtstyle",
      "touches": ["temperature"],
      "tags": ["wb", "warm", "water", "parametric-mask"],
      "description": "Warm WB +200K restricted to cyan-blue hues via parametric mask.",
      "modversions": {"temperature": 4},
      "darktable_version": "5.4",
      "source": "personal",
      "license": "MIT"
    }
  ]
}
```

Required fields per entry: `name`, `layer`, `path`, `touches`, `tags`, `description`, `modversions`, `darktable_version`, `source`, `license`. Optional: `subtype`, `mask_spec`, `global_variant`, `applies_to`. See [`docs/CONTRIBUTING.md`](../CONTRIBUTING.md) for the full schema.

### 7. Validate

```bash
./scripts/verify-vocab.sh ~/.chemigram/vocabulary/personal
```

This runs the manifest-vs-dtstyle audit (per ADR-064 / `tests/integration/core/vocab/test_manifest_dtstyle_consistency.py`). It catches the common bug where the manifest's `touches[]` doesn't match the operations actually in the dtstyle's plugin list. If validation fails, fix the manifest entry; the dtstyle is the source of truth.

### 8. Use it

In your next session, the new entry is in the agent's action space:

```
You: "Try wb_warm_water_only"
Agent: [apply_primitive("wb_warm_water_only")] Applied. Render here.
```

Or run `chemigram vocab list --pack personal` to confirm the entry loaded.

---

## Mask-bound entries

Drawn-form geometric masks (gradient / ellipse / rectangle) are declared via a `mask_spec` field in the manifest. The dtstyle file itself doesn't need a hand-painted mask — the engine encodes the geometry into the XMP at apply time per ADR-076.

### Schema

```json
{
  "name": "gradient_left_warm_subject",
  "layer": "L3",
  "subtype": "exposure",
  "path": "layers/L3/masked/gradient_left_warm_subject.dtstyle",
  "touches": ["exposure"],
  "tags": ["mask", "gradient", "left", "warm"],
  "description": "Warm the left half of the frame via +0.4 EV through a left-bright gradient.",
  "modversions": {"exposure": 7},
  "darktable_version": "5.4",
  "source": "personal",
  "license": "MIT",
  "mask_spec": {
    "dt_form": "gradient",
    "dt_params": {
      "anchor_x": 0.0,
      "anchor_y": 0.5,
      "rotation": 90.0,
      "compression": 0.5
    }
  }
}
```

### `dt_form` and `dt_params`

The three currently-supported `dt_form` values, with their `dt_params` shapes:

**`gradient`** (linear falloff across the frame):
```json
"dt_params": {
  "anchor_x": 0.5,        // gradient anchor, 0=left edge, 1=right edge
  "anchor_y": 0.5,        // gradient anchor, 0=top edge, 1=bottom edge
  "rotation": 0.0,        // 0=top-bright, 90=left-bright, 180=bottom-bright, 270=right-bright
  "compression": 0.5      // falloff width, 0=hard edge, 1=full-frame falloff
}
```

**`ellipse`** (centered or off-center oval region):
```json
"dt_params": {
  "center_x": 0.5,        // 0=left edge, 1=right edge
  "center_y": 0.5,        // 0=top edge, 1=bottom edge
  "radius_x": 0.2,        // horizontal radius, in fractions of frame width
  "radius_y": 0.2,        // vertical radius, in fractions of frame height
  "border": 0.1           // falloff width outside the ellipse, in fractions
}
```

**`rectangle`** (band or box):
```json
"dt_params": {
  "x0": 0.0,              // left edge, 0=frame-left, 1=frame-right
  "y0": 0.4,              // top edge, 0=frame-top, 1=frame-bottom
  "x1": 1.0,              // right edge
  "y1": 0.6,              // bottom edge
  "border": 0.05          // falloff width outside the rectangle
}
```

### Authoring flow for mask-bound entries

The dtstyle authoring is exactly the same as the global flow above (open darktable, set up the module, compress, save style, export). The mask is **not** authored in darktable — it's declared in the manifest's `mask_spec`.

1. In darktable, set up only the *underlying* move (e.g., the +0.4 EV exposure for a gradient-bound entry). **Don't** add a mask in darktable's GUI.
2. Save the style with just the module enabled.
3. Export to `~/.chemigram/vocabulary/personal/layers/L3/masked/<name>.dtstyle`.
4. In the manifest, add `mask_spec` with the form and params you want.
5. Validate: `./scripts/verify-vocab.sh ~/.chemigram/vocabulary/personal`.

The first session that applies your new entry: `apply_primitive` will route through `apply_with_drawn_mask` automatically because `mask_spec` is set; the geometry encodes into the XMP's `masks_history`. Open the result in darktable's GUI and you'll see a real darktable drawn-mask form.

For an example, see the four shipped mask-bound entries in `vocabulary/packs/expressive-baseline/manifest.json` (search for `mask_spec`).

---

## Naming conventions

Per `docs/concept/05-design-system.md` § 3:

- **Three-part is typical:** `<module>_<intention>_<context>` (e.g., `wb_warming_pelagic`, `colorcal_underwater_recover_blue`).
- **Action_quality_target** for tone-shaping moves (`tone_lifted_shadows_subject`).
- **Module_intention_context** for module-bound moves (`wb_warming_pelagic`).
- **Suffixes** for variants: `_subtle`, `_strong`, `_subject`, `_only`. See concept/05 § 3.3 / 3.4 for the suffix conventions.

When in doubt, name what *you* would naturally reach for in conversation — the agent will surface the entry by its description and tags, so name clarity matters more than name consistency.

---

## Common pitfalls

**The exported style includes too many modules.** You forgot to deselect "all enabled modules" in step 4. Open the `.dtstyle` file — it should have one `<plugin>` block. If it has more, re-export with only the target module selected.

**Manifest validation fails with "plugin operations don't match touches[]".** The manifest's `touches` array must equal the set of `<operation>` values in the dtstyle's plugins. If you have a `temperature` plugin in the dtstyle but `touches: ["exposure"]` in the manifest, the audit fails.

**The mask doesn't appear when applying.** For drawn-mask-bound entries, check that:
- `mask_spec` is in the manifest entry (not in the `.dtstyle` file)
- `dt_form` is one of `gradient`, `ellipse`, `rectangle` exactly (no aliases)
- `dt_params` has all the fields for that form (see schema above)

The CLI returns `MASKING_ERROR` (exit code 7) if `mask_spec` is malformed.

**The agent ignores the new entry.** Restart your MCP session; the agent loads vocabulary at session start and won't pick up new entries mid-session. Or run `chemigram vocab show <name>` to confirm the entry is loaded.

---

## See also

- [`vocabulary-patterns.md`](vocabulary-patterns.md) — recipes / patterns combining existing primitives
- [`expressive-baseline-authoring.md`](expressive-baseline-authoring.md) — programmatic struct-RE authoring (Path C)
- [`docs/CONTRIBUTING.md`](../CONTRIBUTING.md) § Vocabulary contributions — full schema and contribution flow
- [`docs/concept/05-design-system.md`](../concept/05-design-system.md) § 3 — naming conventions
- [`docs/adr/ADR-076-drawn-mask-only-mask-architecture.md`](../adr/ADR-076-drawn-mask-only-mask-architecture.md) — the drawn-mask architecture
- [`docs/adr/ADR-064-vocabulary-authoring-workflow.md`](../adr/ADR-064-vocabulary-authoring-workflow.md) — Path B + L1-binding workflow
