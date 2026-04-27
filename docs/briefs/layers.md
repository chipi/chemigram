# Chemigram — Layer Model

*How edits stack, who authors what, and where the agent operates.*

## The model

Three layers. Each has different authorship, different cadence, different mutability. The whole point of naming them is to keep the agent's responsibility — and the experiment's research question — narrow and clean.

| Layer | What | Authored by | Cadence | Mutable in loop? | Default |
|-|-|-|-|-|-|
| **L0** | darktable internals (rawprepare, demosaic, color profiles) | darktable | Always-on | No | Always present |
| **L1** | Technical correction (lens, profiled denoise, hot pixels) | Photographer, per-camera+lens (or borrowed from community) | Once per camera+lens | No | **Empty by default — opt-in** |
| **L2** | Look establishment (baseline exposure, view transform, color cast recovery, *or* a film simulation) | Photographer, per-image (or borrowed from community packs) | Once per image | No | Optional — image enters with chosen template or none |
| **L3** | Taste (vocabulary primitives) | Agent | Continuous | Yes | Always — the loop |

L0 is given. L1 and L2 are baked into the image's starting XMP before the agent ever sees it, when present. L3 is the agent's playground.

### L1 is empty by default

A photographer shooting fisheye doesn't want lens correction. A photographer shooting clean low-ISO doesn't want denoise on. So L1 is never assumed-on: a freshly-imported image with no L1 binding gets nothing applied, and the agent works from the raw demosaic-and-color-profile baseline.

The photographer opts *in* by binding their image (or their camera+lens combination) to an L1 template. Bindings are per-camera+lens, not just per-camera, because the right L1 changes between a 24-70 zoom and an 8-15 fisheye on the same body.

Templates available in the bundled vocabulary:

- `lens_correct_full` — lens module on, auto-method (Lensfun or embedded metadata), all corrections
- `lens_correct_distortion_only` — TCA + distortion, no vignetting (preserves dramatic falloff)
- `denoise_auto` — profiled denoise with database lookup at the shot's ISO
- `lens_correct_full + denoise_auto` — common combination
- `chromatic_aberration_only` — for vintage glass that has nothing else in Lensfun

A user binding via `config.toml`:

```toml
[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Nikkor 24-70mm f/2.8E ED VR"
template = "lens_correct_full + denoise_auto"

[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Fisheye Nikkor 8-15mm f/3.5-4.5E ED"
template = "denoise_auto"      # NO lens correction — preserve fisheye projection
```

The auto-resolver matches via EXIF: exact (camera+lens), then camera-only fallback, then nothing. Each match is logged in the session metadata so the photographer can review which L1 was applied to a given image.

### L2 is unrestricted across bodies

Earlier drafts of this doc proposed restricting Fuji film-sim L2 templates to Fuji bodies. Wrong call — non-Fuji shooters love Fuji looks too. A `fuji_acros` template applied to a Sony A1 ARW produces an Acros-spirit result; not pixel-identical to a Fuji JPEG (calibrated to X-Trans color science, not Sony's), but recognizably Acros.

The honest caveat lands in vocabulary metadata, not enforcement:

```json
{
  "name": "fuji_acros",
  "layer": "L2",
  "subtype": "look_committed",
  "notes": "Calibrated to Fuji X-Trans color science. On other sensors, expect spirit not exact match."
}
```

For sensor-specific fitting (e.g. a Sony-A1-calibrated Acros), see TODO.md — that's a research direction enabled by the color-science extensibility hook (below) but not built in v1.

### Color science extensibility hook

L1 and L2 templates can reference custom color-science assets (`.icc` profiles, 3D LUTs, basecurve presets) via relative paths into a shared `chemigram-vocabulary/profiles/` directory. The XMP synthesizer copies the path into the relevant module config; darktable reads the asset at render time.

This costs ~50 lines in the synthesizer + validator and supports three use cases:

1. *Now:* users drop in ICC profiles extracted from Capture NX, ART, or commercial sources.
2. *Later:* per-sensor fitting (TODO #2) writes 3D LUTs into this directory, referenced from sensor-specific L2 templates.
3. *Speculative:* community packs of fitted color science.

Empty `profiles/` ships with v1. The hook is in place; nobody uses it yet.

## Why three and not four (or five)

The instinct to add layers is real — Chemigram surfaces lots of distinctions. The principle that holds the line at three:

> **Layers separate authorship moments, not editing moves.**

Authorship has three moments: camera setup (L1), pre-loop intent (L2), in-loop taste (L3). Beyond that you're carving up the editing *process* rather than *who's responsible for what*. Composition within L3 is handled by SET semantics on the `(operation, multi_priority)` key — that's what the replace-not-accumulate decision was for. Adding more layers would re-introduce the accumulation problem.

So when a question like "should fine-tuning be L4?" comes up, the answer is almost always: it's still L3, and SET semantics handle the override.

## The artifact: a baseline XMP per image

Each image enters the loop with a pre-baked XMP. The history stack is partitioned:

```
[ L1 entries ][ L2 entries ][ L3 entries ]
              ^             ^
              |             baseline_end
              technical_end
```

Two integers stored in sidecar metadata mark the boundaries. `apply_primitive`, `remove_module`, and `reset` only touch the L3 segment. L1 and L2 entries are read-only mid-session.

`reset(image_id)` does *not* go to empty history — it goes to `baseline_end`. That's the floor the agent works from.

## Worked example: Fuji X-Pro2 + film simulations

This is the case that makes the model crisp.

### What a Fuji film sim actually is

Fuji's in-camera sims (Provia, Velvia, Astia, Classic Chrome, Acros, Pro Neg, Eterna, Classic Neg, Nostalgic Neg) are a combination of:

1. A tone curve — contrast shape, shoulder/toe behavior
2. Color response — saturation per hue, hue shifts (Velvia pushes blues toward cyan, Classic Chrome desaturates everything but pulls reds warm)
3. Sometimes per-channel curves — Acros has distinct R/G/B response producing its monochrome character
4. Implicit shadow/highlight rolloff baked into the JPEG engine

When you shoot RAF and develop in darktable, you start from linearized scene-referred raw — the sim is *not applied*. Implementing a sim in darktable means stacking modules that produce a final image visually matching what the camera's JPEG engine would have made. This is what `darktable-chart` does, and what existing community projects (bastibe's Film Simulation Panel, t3mujinpack) have already built `.dtstyle` files for.

### Why a Fuji sim is L2, not L3

The X-Pro2 is a camera where **the look starts at capture**. You chose Acros when you raised the camera. The sim isn't a post-hoc creative decision — it's intent embedded in the act of shooting.

Treating `fuji_acros` as L2 honors that: applying it when you ingest the RAF is *recovering the intent you had at capture*, not making a fresh creative choice. The agent's L3 work then refines *within* the look you committed to behind the viewfinder.

This means L2 has two flavors in practice:

- **Neutralizing L2** — `underwater_pelagic_blue`, `topside_neutral`. Recovers the image from raw murk to a sane working state. The agent's job is to develop a look from there.
- **Look-committed L2** — `fuji_acros`, `fuji_classic_chrome`, `fuji_velvia`. Already commits to a look. The agent's job is to refine within it.

Both are L2 because both are pre-agent, pre-loop, photographer-set baselines. They differ only in how much taste they pre-commit.

### How "fine-tuning" Acros works

The instinct: "L4 for fine-tuning the Fuji sim." The actual answer: it's still L3, and the existing SET semantics handle it.

If `fuji_acros` (L2) sets `tonecurve` with Acros's specific shape, and the agent applies `tone_lifted_shadows` (L3), the L3 entry replaces the L2 tonecurve entry by `(operation, multi_priority)`. The agent has fine-tuned Acros without a new layer.

What if the L3 entry touches a module Acros didn't include — say, the agent applies `warm_highlights` (which uses `colorbalancergb`) when `fuji_acros` doesn't have a `colorbalancergb` entry? Same SET logic: there's no existing entry to replace, so it adds one. The Fuji character is preserved (tonecurve, channelmixerrgb, colorlookuptable from L2 are untouched), and a new module is layered on top.

This is the payoff of replace-not-accumulate semantics. Both "modify Acros's tonecurve" and "add warmth on top of Acros" are clean, predictable operations. No new layer needed.

### Vocabulary tagging: which modules each entry touches

The Fuji case shows why vocabulary metadata should declare *which modules* each entry touches:

| Entry | Layer | Touches |
|-|-|-|
| `fuji_acros` | L2 | `tonecurve`, `channelmixerrgb`, `colorlookuptable`, `monochrome` |
| `fuji_classic_chrome` | L2 | `tonecurve`, `channelmixerrgb`, `colorlookuptable` |
| `tone_lifted_shadows` | L3 | `tonecurve` |
| `warm_highlights` | L3 | `colorbalancergb` |
| `acros_red_filter` | L3 | `channelmixerrgb` |

The agent reasons over this metadata: *"I'm modifying Acros's tonecurve. Acros's character also comes from channelmixerrgb and colorlookuptable, which I'm leaving intact."* Without this, the agent has no way to predict whether an L3 move preserves or breaks the L2 look.

### Single-module L3 entries

The Fuji case implies a discipline for L3 vocabulary design: **L3 entries should touch exactly one module where possible**. Multi-module L3 entries get hard to compose with L2 templates because you can't tell what's overriding what. Single-module entries make SET semantics legible.

Multi-module entries are still allowed when they're conceptually inseparable (e.g. a paired `tonecurve` + `colorbalancergb` move that only makes sense together), but they should be the exception, and the metadata should call them out.

## Vocabulary curation for the Fuji case

Building Fuji-sim support on top of Chemigram is a small project of its own:

**Phase A — L2 templates.** Capture `fuji_provia`, `fuji_velvia`, `fuji_astia`, `fuji_classic_chrome`, `fuji_acros`, `fuji_classic_neg` as `.dtstyle` files. Two paths: use `darktable-chart` against color-checker shots, or borrow from community projects (bastibe/Darktable-Film-Simulation-Panel, t3mujinpack/t3mujinpack, RandomLegend/Darktable-Presets).

**Phase B — sim-agnostic L3.** Build a small L3 vocabulary for modifying-within-any-sim: `tone_lifted_shadows`, `tone_crushed_blacks`, `warm_highlights`, `cool_shadows`, `extra_contrast`, `softer_contrast`. Single-module each, work across all sims because each replaces or adds one specific module.

**Phase C — sim-specific L3.** For Acros, emulate Fuji's color-filter options: `acros_red_filter`, `acros_yellow_filter`, `acros_green_filter`. These touch `channelmixerrgb` only and replace Acros's L2 channel-mixer entry with a filter-modified version. Idiomatic to one sim, lives in a tagged subset of the vocabulary.

This mirrors how a Fuji photographer actually thinks: *"Acros, but with the red filter, and lift the shadows a touch."* Three composable moves, three vocabulary entries, clean SET composition over the L2 baseline.

## How a session begins

Pseudo-flow for ingesting an X-Pro2 RAF:

1. Photographer drops `DSCF1234.RAF` into Chemigram's workspace.
2. Photographer (or a thin CLI on top of Chemigram) tags it: `camera_profile=fuji_xpro2_35mm`, `scene_template=fuji_acros`.
3. Chemigram synthesizes the baseline XMP: L0 (implicit) + L1 entries from `fuji_xpro2_35mm.dtstyle` + L2 entries from `fuji_acros.dtstyle`. Records `technical_end` and `baseline_end`.
4. Image is now ready for the agent. `get_state` returns the baseline; `apply_primitive` operates on the L3 segment only.

The agent never sees the L1/L2 distinction directly — it sees a `get_state` response that says "here's what's currently in the history; here are the L3 entries you can mutate; here's the vocabulary tagged by which modules each entry touches." That's enough for it to reason about composition.

## What this clarifies about the experiment

The Fuji case sharpens a research question that was implicit: **how much of "taste" is the L2 template, and how much is the L3 refinement?**

When you shoot Acros, most of the look is already committed. The agent's L3 work is comparatively small — nudges within an established frame. When you shoot raw with no in-camera intent (e.g. underwater pelagic), L2 is just neutralizing and most of the look is L3.

This means the experiment will look very different across these two cases — and that difference is itself informative. With Fuji sims, you're testing *can the agent refine within a committed look*. With underwater raws, you're testing *can the agent develop a look from neutral*. Both are interesting; they're testing different things.

A future session log should record which mode a given session is in. Not because the agent needs to know — it doesn't — but because *you* need to know when reviewing what worked and what didn't.
