# 03 — Data and Content Catalog

*What feeds the system. Sources, characteristics, access. The substrate Chemigram builds on.*

This document inventories what the system works with — every external data source, content type, and substrate that Chemigram depends on. For each: what it provides, how Chemigram accesses it, its characteristics, and what creative or functional potential it has.

The discipline: Chemigram orchestrates; everything in this catalog is *used*, not built. Per `04`'s "darktable does the photography" and "BYOA" principles, every capability described here comes from outside the engine.

## Substrate sources

### darktable

| Property | Detail |
|-|-|
| What it provides | Complete image-processing pipeline: demosaic, color science, all parametric modules (exposure, color calibration, tone equalizer, filmic, color balance rgb, masks, etc.), rendering to JPEG/TIFF/PNG |
| Access mechanism | `darktable-cli` invocation against an isolated `--configdir`. Headless. No GUI required. |
| Format | XMP sidecars (RDF/XML) hold edit state. `.dtstyle` XML files capture single-module styles. |
| Version pinning | darktable 5.x stable. Module `modversion` numbers are version-specific; vocabulary requires re-capture when darktable's modversions change. |
| Characteristics | Mature (15+ years), active development, scene-referred pipeline, Apple Silicon native since 4.4.2, OpenCL via macOS Metal/MPS |
| Creative potential | Genuinely competitive with Lightroom and ahead in some areas (parametric masks, contrast equalizer, diffuse-or-sharpen). Local-adjustment surface is broader than LR's. |
| Constraints | XMP `op_params` and `blendop_params` are hex-encoded C structs — not human-editable. We treat them as opaque blobs and copy them between `.dtstyle` and XMP. See `04`/XMP composition. |

### Lensfun (via darktable)

| Property | Detail |
|-|-|
| What it provides | Lens correction profiles (distortion, vignetting, TCA) for thousands of camera+lens combinations |
| Access | Bundled with darktable; no separate installation |
| Characteristics | Excellent F-mount (Nikon) coverage. Patchy for newer Sony G Master and similar mirrorless lenses. |
| Used by | L1 vocabulary entries that enable lens correction |

### darktable noise profiles

| Property | Detail |
|-|-|
| What it provides | Per-camera-body profiled denoise data (`noiseprofiles.json`) |
| Access | Bundled with darktable |
| Coverage | Hundreds of camera bodies, including all major Sony/Nikon/Canon/Fuji models from the last decade |
| Used by | L1 vocabulary entries that enable profiled denoise |

### Embedded lens correction metadata (camera-side)

| Property | Detail |
|-|-|
| What it provides | Lens distortion polynomial coefficients embedded in raw files by some manufacturers |
| Format | TIFF tags / maker notes; darktable reads via `--apply-method=embedded` |
| Coverage | Sony ARW, Fuji RAF (APS-C), Olympus ORF — the cameras that bake corrections into raws |
| Significance | For Sony A1 + GM glass, embedded metadata is *better* than Lensfun (which lacks profiles for newer lenses). darktable defaults to embedded when present. |

## Photographer-authored content

### Vocabulary primitives (`.dtstyle` files)

The agent's action space. The most important content type in the project.

| Property | Detail |
|-|-|
| What it is | Single-module darktable styles, each capturing one named move (`expo_+0.5`, `colorcal_underwater_recover_blue`, etc.) |
| Format | XML per darktable's `.dtstyle` schema. Each `<plugin>` entry has `<operation>`, hex `<op_params>`, gzip+base64 `<blendop_params>`, modversion, iop_order |
| Authoring | In darktable GUI: set one module to desired value, save as named style, export as `.dtstyle` |
| Layer attribution | L1 (technical correction), L2 (look establishment), L3 (taste/agent vocabulary) — see `04`/Layer model |
| Mask kinds | `none` (global), `parametric` (luminance/hue/chroma masks in `blendop_params`), `drawn` (geometric primitives — gradient/ellipse/rectangle/path — encoded into `masks_history` and bound via patched `blendop_params`). Per ADR-076 the earlier raster-PNG path was retired in v1.5.0. |
| Lifecycle | Authored once, used many times. Versioned alongside darktable releases. |
| Distribution | Bundled starter (this monorepo, MIT). Community packs (this monorepo, attributed). Personal vocabularies (separate private repos). See `docs/LICENSING.md`. |

### Vocabulary manifest

```json
{
  "name": "gradient_top_dampen_highlights",
  "layer": "L3",
  "subtype": "exposure",
  "path": "layers/L3/masked/gradient_top_dampen_highlights.dtstyle",
  "touches": ["exposure"],
  "tags": ["mask", "gradient", "highlights", "dampen"],
  "description": "Dampen top-half highlights via -0.5 EV through a top-bright gradient.",
  "mask_spec": {
    "dt_form": "gradient",
    "dt_params": {"anchor_x": 0.5, "anchor_y": 0.5, "rotation": 0.0, "compression": 0.5}
  },
  "modversions": {"exposure": 7},
  "darktable_version": "5.4",
  "source": "expressive-baseline",
  "license": "MIT"
}
```

The manifest is the vocabulary's API. The `.dtstyle` files are the payload.

## Photographer's context (per-photographer)

### `~/.chemigram/taste.md`

The photographer's taste, externalized as durable prose. Read at every session start. Curated over months.

| Property | Detail |
|-|-|
| Format | Markdown. Free-form within sections. |
| Structure | Working preferences, recurring patterns, vocabulary affinities, brief language, camera notes, session preferences |
| Authoring | Initial draft by photographer (1 hour, imperfect, useful from day 1). Subsequent additions: agent proposes, photographer confirms. |
| Lifecycle | Living document. Periodic synthesis (every 10-20 sessions) consolidates redundant entries. |
| Persistence | User's machine, version-controllable. Never uploaded automatically. |

### `~/.chemigram/config.toml`

The user's configuration. Vocabulary sources and L1/L2 binding rules.

```toml
[vocabulary]
sources = [
    "$CHEMIGRAM_INSTALL/vocabulary/starter",
    "$CHEMIGRAM_INSTALL/vocabulary/packs/fuji-sims",
    "~/private/chemigram-vocabulary-marko",
]

[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Nikkor 24-70mm f/2.8E ED VR"
template = "lens_correct_full + denoise_auto"

[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Fisheye Nikkor 8-15mm f/3.5-4.5E ED"
template = "denoise_auto"   # NO lens correction, preserve fisheye
```

Photographer-edited TOML. No GUI for configuration. Auto-resolution from EXIF chooses the right binding per image.

## Per-image content (per photo project)

Each image is its own project (per `04`/Project structure):

```
~/Pictures/Chemigram/<image_id>/
  raw/                                   # symlink to original raw
  brief.md                               # what this image is for
  notes.md                               # what we've learned
  metadata.json                          # EXIF cache, layer bindings
  current.xmp                            # synthesized from current snapshot
  objects/                               # snapshot store (versioning)
  refs/                                  # branches, tags, HEAD
  log.jsonl                              # operation log
  sessions/                              # transcripts
  previews/                              # render cache
  exports/                               # final outputs
  vocabulary_gaps.jsonl                  # gaps surfaced this image
```

### `brief.md`

Photographer's intent for this image. Written at session start, sometimes updated mid-session if the goal shifts. Read at every session on this image.

### `notes.md`

What we've learned about this image across sessions. Subject identification, lighting facts, decisions made, branches explored, open questions. Both photographer and agent contribute (agent proposes, photographer confirms).

### `metadata.json`

EXIF cache + layer binding decisions:

```json
{
  "exif": {
    "camera": "X-Pro2",
    "lens": "XF 35mm f/2 R WR",
    "iso": 200,
    "fuji_sim": "Acros"
  },
  "auto_binding": {
    "l1": "fuji_xpro2_default",
    "l2_suggested": "fuji_acros",
    "l2_applied": "fuji_acros"
  }
}
```

The agent reads this to know what baseline it's working from.

### XMP snapshots (`objects/`)

Content-addressed by SHA-256 over canonical XMP serialization. Each snapshot is a complete edit state. See `04`/Versioning.

### Session transcripts (`sessions/`)

Full conversation logs from Mode A sessions. Per-session: goal, brief at start, full transcript, snapshots produced, vocabulary used, gaps surfaced, outcome. JSONL format, one entry per turn.

### Mask geometry (inside the XMP)

Drawn-form masks ride inside the XMP they belong to — `<darktable:masks_history>` carries the geometry, plugins' `blendop_params` reference it via `mask_id`. There is no separate mask directory or registry; the snapshot's content hash captures both the dtstyle and its mask binding atomically. Per ADR-076 (the v1.5.0 cleanup), the previous PNG-based `masks/` directory was retired — darktable never read those files, so the path was a silent no-op.

## External AI capability (BYOA — Bring Your Own AI)

Per `04`'s BYOA principle, AI capabilities are not bundled with Chemigram. They're configured by the photographer.

### The photo agent (Mode A driver)

| Property | Detail |
|-|-|
| Role | Reads photographer's context, drives the editing loop, surfaces uncertainty, catches composition tensions, proposes context updates |
| Access | MCP — Chemigram's MCP server is called by whatever agent the photographer configures (Claude, GPT, Gemini, local model, etc.) |
| Required capabilities | Vision (to look at preview JPEGs), tool use (to call Chemigram's MCP tools), reasoning over reasonably-long context (~50-100K tokens for a typical session) |
| Not required | Specific model family. The system prompt is portable. |

### Mask provision

| Property | Detail |
|-|-|
| v1.5.0 | Drawn-form geometry baked into vocabulary entries' `mask_spec`. Three forms supported: gradient, ellipse, rectangle. Encoded directly into the XMP's `masks_history` at apply time; no AI involved. See ADR-076. |
| Phase 4 | Sibling project (working name `chemigram-masker-sam`) producing darktable-compatible drawn-form geometry from natural-language prompts. Wire format is the same darktable schema the geometric primitives use today — not PNG bytes. The apply path stays unchanged when content-aware masking lands. |
| Out of scope | PNG-based mask interchange. The earlier `MaskingProvider` Protocol (returning PNG bytes) was retired in v1.5.0 — verified that darktable never reads external PNGs for raster masks. |

### Mode B evaluators (future)

Not in v1. Planned as `EvaluatorProvider` protocol — reference-based perceptual similarity, vision-model self-eval, learned critic from accumulated session data. See `04`/Modes and `docs/TODO.md`.

## Borrowed vocabulary (community packs)

| Property | Detail |
|-|-|
| What | Pre-existing vocabulary collections from the darktable community, redistributed with attribution |
| Examples | Fuji film simulations from `bastibe/Darktable-Film-Simulation-Panel` and `t3mujinpack`, Nikon picture-control emulations |
| Format | Same `.dtstyle` files as native vocabulary. Wrapped in pack directory with `manifest.json` and `ATTRIBUTION.md` |
| License | Per-upstream (typically MIT or CC variants). Preserved in pack distribution. |
| Calibration note | Fuji sims are calibrated to Fuji X-Trans color science. Applying to Sony/Nikon/Canon raws produces "spirit" matches, not pixel-identical. Documented in vocabulary metadata. |

## Custom color science assets (extensibility hook)

A hook for users who want to bring their own color science:

```
chemigram-vocabulary/
  profiles/
    *.icc                    # custom ICC input profiles
    *.cube                   # 3D LUTs
    *.basecurve              # custom basecurve presets
```

Vocabulary entries can reference these via relative path. Engine copies path into module config; darktable reads asset at render time. Empty in v1; documented for future use including potential per-sensor color-science fitting (see `docs/TODO.md`).

## Session data is local-only

A key principle: session data — transcripts, taste evolution, preference history, vocabulary gaps — never leaves the photographer's machine automatically. No telemetry. No phone-home. No cloud dependency.

If a photographer chooses to publish anonymized insights, that's their choice. The project provides no infrastructure for publishing session data and no encouragement to do so by default.

This is part of the agent-is-the-only-writer discipline — not just an architectural property of edit operations, but a privacy property of everything Chemigram observes.

## Catalog summary

| Source | Type | Authored by | Lifetime |
|-|-|-|-|
| darktable | Substrate | Upstream project | External; we pin versions |
| Lensfun, noise profiles | Bundled with darktable | Upstream | External |
| Embedded lens metadata | Camera-baked | Hardware | Per-image |
| Vocabulary primitives | Authored content | Photographer or community | Per-vocabulary |
| Vocabulary manifest | Structured metadata | Generated from above | Per-vocabulary |
| `taste.md` | Photographer's taste | Photographer (agent-assisted) | Persistent across sessions |
| `config.toml` | User configuration | Photographer | Persistent |
| Per-image briefs/notes/metadata | Image context | Photographer (agent-assisted) | Per-image |
| XMP snapshots | Edit state | Agent (writes), photographer (reads) | Per-image, versioned |
| Session transcripts | Conversation logs | Both, captured automatically | Per-session, append-only |
| Mask geometry | Spatial selections | Authored into vocabulary entries' `mask_spec` (or, in Phase 4, produced by a sibling project) | Inside the XMP |
| Photo agent | AI capability | BYOA — photographer configures | External |

What feeds Chemigram comes from four directions: darktable provides processing, photographer provides taste, configured agents provide AI capability, community provides vocabulary packs. Chemigram itself produces orchestration and accumulated state.

---

*03 · Data and Content Catalog · v1.0*
