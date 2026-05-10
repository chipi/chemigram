# Changelog

All notable changes to Chemigram will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
per ADR-041.

## [Unreleased]

## [1.10.0] — 2026-05-10

**Photographer-survey vocabulary expansion + workflow primitives.**

v1.10.0 grounds chemigram's L2 vocabulary in how working photographers
actually post-process. A 6-genre survey (`docs/photographer-workflows-survey.md`)
extracted recurring moves across 36 photographers spanning portrait /
landscape / wedding / B&W / nature-wildlife / food-product genres; the
vocabulary delta and workflow primitives below implement the gaps that
survey identified. Three new RFCs ship as Decided (impl shipped) with
their closing ADRs in Draft until darkroom-session visual validation
flips them to Accepted.

### Stats

- Tests: 1811 → **1845** (+34: dtstyle drift + framing-bound + strength + propagate + mixed-op)
- ADRs: 87 → **90** (ADR-088 / ADR-089 / ADR-090; all Draft pending darkroom)
- RFCs Decided: 27 → **30** (RFC-035 / RFC-036 / RFC-037)
- Vocabulary entries: 83 → **102** (+29 L2 looks across 6 genres + bw_convert v2)
- New MCP tools: `propagate_state`, `wb_from_gray_card` + mixed-op shape on `apply_per_region`
- New CLI verbs: `propagate-state`, `wb-from-gray-card` + `--strength` flag on `apply-primitive`

### Vocabulary expansion (29 new L2 looks + bw_convert v2)

29 new L2 looks composed from the parameterized L3 primitives:

- **5 B&W** (survey Round 2): `look_bw_classic_neutral`, `_high_contrast_chiaroscuro`, `_landscape_dramatic`, `_silver_efex_zone_balanced`, `_split_tone_warm_shadows`.
- **8 Landscape** (Round 1): `look_landscape_atmospheric_haze`, `_autumn_pop`, `_blue_hour_cool`, `_dramatic_moody`, `_golden_hour`, `_grand_vista`, `_intimate_quiet`, `_sky_enhance`, `_water_silk`.
- **5 Portrait** (Round 1): `look_portrait_background_dim`, `_editorial`, `_natural_skin`, `_skin_warm_lift`, `_split_tone_moody`.
- **5 Wildlife** (Round 3): `look_wildlife_background_blur`, `_eye_lift`, `_high_iso_recovery`, `_natural_warm`, `_subject_sharpen`.
- **4 Food / 1 Product** (Round 3): `look_food_appetizing_warm`, `_green_natural`, `_orange_pop`, `_texture_subtle`, `look_product_packshot_clean`.

`bw_convert` redesigned from channelmixerrgb-mv3 (3 hard-coded grey-weight variants) to colorequal-based with 8 Adams-school `bright_X` axes per hue band. The chemigram analog of Photoshop's Channel Mixer (Monochrome) and Silver Efex's color filters. Old `bw_sky_drama` and `bw_foliage` preserved for the channel-mixer mechanic.

### RFC-035 / ADR-088 — Parametric L2 strength (Path B)

L2 looks now accept a `--strength` flag (range `[0.0, 1.0]`; default `1.0`). Each parameterized field interpolates linearly between identity and authored: `interpolated = identity + strength * (authored - identity)`. Non-parameterized fields preserve authored values. Composes cleanly with masks.

```
chemigram apply-primitive --entry look_landscape_dramatic_moody --strength 0.6
```

### RFC-036 / ADR-089 — Mixed-op `apply_per_region`

`apply_per_region` accepts a second payload shape — each region carries its own `ops` array. Composite moves like "lighten the iris and sharpen the lashes" land as one snapshot. Per-(op, region) `multi_priority` allocation; cap of 64 (op × region) pairs; atomic validate-then-apply.

### RFC-037 / ADR-090 — `propagate_state` MCP verb

LR-Sync analog: nail post-processing on one anchor, propagate to N targets. Inherit-everything-by-default with framing-bound auto-exclusion (`ashift` / `crop` / `retouch` / `lens` plus drawn-mask-bound entries). Parametric range masks DO propagate. Atomic. Cap 200 targets.

```
chemigram propagate-state --source <anchor> --targets <id1>,<id2>,<id3> \
    --label "wedding-reception-2026-05-08"
```

### Engineering follow-ups (post-RFC retro — all 5 gaps closed)

- **Vocab-load dtstyle-modversion drift check** (Gap A) — sister to ADR-082. Walks each plugin's `<module>` byte at vocab load and warns/raises (strict mode) on mismatch. Caught a v1.10.0-author-time bug class where wrong modversion bytes hung darktable for 60s × 25 entries.
- **L2-composite test-skip** (Gap B) codified as a structural rule (`layer == "L2"` auto-skips lab-grade); replaces ~36 hand-written per-entry SKIP_REASONS rationales.
- **`FRAMING_BOUND_OPS` registry** (Gap D) extracted to a dedicated `chemigram.core.framing_bound` module — single source of truth.
- **`bw_convert` lab-grade** restored to EXPECTED_EFFECTS with chroma-zero base-mechanic check; per-axis behavior unit-tested (Gap E policy).
- **Visual-proof gallery regenerated** — 102 entries × 2 chart targets = 785 renders + baseline.

### What's next

- Darkroom-session validation pass on items 7-11 of `darkroom-session-debt.md`. Flips ADR-088/089/090 from Draft to Accepted; tunes the 29 L2 looks against real raws.
- Phase 2 vocabulary maturation continues; open v1.10.0 issues moved to v1.11.

## [1.9.0] — 2026-05-08

**Mask + retouch architecture trilogy — structurally complete.**

v1.9.0 closes RFC-024 (parametric range masks), RFC-025 (spot heal/clone),
RFC-026 (LLM-vision-as-provider for AI masks), and RFC-029 (compositional
masks at apply time / build-by-words). Photographers can now compose
spatial masks (drawn shapes), parametric range filters (luminance + HSL
color), LLM-vision-derived content masks (chat-client native), and spot
heal/clone retouch — all through one unified `mask_spec` wire and one new
MCP tool. RFC-030 (deployed sibling-provider scaffolding for the precision
tier) is drafted and deferred.

### Stats

- Tests: 1451 → **1811** (+360)
- ADRs: 83 → **87** (ADR-084..087)
- RFCs Decided: 23 → **27** (RFC-024 / RFC-025 / RFC-026 / RFC-029)
- Vocabulary entries: 78 → **83** (+5 compositional-mask L2 looks)
- New MCP tool: **`apply_spot`** (sister to `apply_primitive`)
- New CLI verbs: `vocab validate`, `cache {list, size, clear}`

### The mask trilogy

#### RFC-029 / ADR-084 — Compositional masks at apply time (build-by-words)

The wire (`apply_primitive` accepts inline `mask_spec`) was already
shipped pre-v1.9.0 but undiscoverable. v1.9.0 formalizes it as the
canonical agent-facing pattern: photographer says "lift the bottom
third"; agent translates to `{dt_form: "gradient", dt_params: {anchor_y:
0.67, rotation: 180, compression: 0.5}}` and applies.

- New docs guide `docs/guides/mask-shapes-from-words.md` with 30+
  phrase→spec examples covering halves/thirds, hard-edged regions,
  ellipses at rule-of-thirds, diagonals, and polygons.
- Path geometry added — `dt_form: "path"` with N-vertex closed polygons
  (RFC-026 substrate; AI subject masks land here when they ship).
- 12 visual proofs against the synthetic grayscale ramp.
- 5 e2e tests verifying named shapes produce the expected spatial
  signature through real darktable.
- Lint test ensures every guide example round-trips through the
  encoder.

The deterministic-hash `mask_id` provides reuse semantics for free —
same spec across N apply calls = same mask in darktable's
`masks_history`. No `make_mask` tool needed.

#### RFC-024 / ADR-085 — Parametric range-filter masks

`mask_spec` gains optional `range_filter` field:

```jsonc
{
  "dt_form": "ellipse",                            // spatial (optional)
  "dt_params": {...},
  "range_filter": {                                 // pixel-level (optional)
    "kind": "luminance" | "color_h" | "color_s" | "color_l",
    "min": 0.0, "max": 0.3, "feather": 0.05, "invert": false
  }
}
```

- Encoded into darktable's `blendif` byte fields (4 control points per
  channel; 16 channel slots; 64 total floats).
- HSL color kinds set `blend_cst` to `IOP_CS_HSL` automatically.
- Three valid combinations: drawn only, parametric only, drawn +
  parametric (intersection — the canonical "dark pixels in this
  region" workflow).
- `mask_combine` hardcoded to AND for v1.9.0; OR / SUBTRACT / INVERT
  deferred.
- 13 unit tests + 3 e2e tests verifying the wire end-to-end.
- 5 visual-proof JPEGs in the gallery showing parametric-only and
  composite refinement.

#### RFC-026 / ADR-086 — LLM-vision-as-provider for AI masks

Reframed from RFC-026 v0.1's deployed-provider-only architecture:
the chat-client (Claude.ai / ChatGPT / Claude Code) already has vision
in the conversation. The agent calls `render_preview`, the LLM sees the
JPEG, and constructs `mask_spec` from spatial reasoning. **Zero deployment
cost**; covers ~70% of content-derived masking workflows.

- New docs guide `docs/guides/llm-vision-for-masks.md` with 6 workflow
  patterns: subject region, polygon trace, sky/foreground split,
  color-range estimation, subject-vs-background routing, iterative
  refinement.
- Honest limitations called out (single-strand hair, dense spot
  enumeration, per-pixel depth — those route to RFC-030).
- Zero new MCP tools; the wire was already there.
- Deployed-provider precision tier moved to **RFC-030** (Draft,
  deferred) — unfreezes when LLM-vision precision becomes the
  bottleneck on real workflows.

#### RFC-025 / ADR-087 — Retouch byte encoding + `apply_spot` MCP tool

The largest portrait gap from capability-survey § 10 closes.
Photographers can now remove sensor dust, blemishes, distracting
elements, and clone source regions — all via one MCP call.

- New MCP tool `apply_spot(image_id, kind, x, y, radius, source_x?,
  source_y?)` — sister to `apply_primitive` for the structurally
  different primitive class of pixel replacement.
- Byte encoders verified against darktable 5.4.1 `src/iop/retouch.c`:
  13260-byte op_params (300-form fixed array of 44 bytes each +
  60-byte global tail), 16-byte circle mask form, 8-byte clone mask_src.
- v1.9.0 scope: HEAL + CLONE on CIRCLE geometry, single form per call.
  AI auto-detection (multi-form batched) routes to RFC-030.
- 12 unit tests + 4 e2e tests against real darktable.
- ADR-033's narrow MCP surface preserved with this single addition.

### Compositional-mask L2 looks (5 new entries)

Pre-baked vocabulary demonstrating the full mask trilogy:

| Entry | Composition |
|-|-|
| `look_subject_lift_dark_only` | Drawn ellipse + luminance shadows filter |
| `look_sky_blue_deepen` | Gradient (top half) + color_h cyan-blue range |
| `look_horizon_warm_glow` | Horizontal gradient + color_h warm tones |
| `look_subject_brighten_highlights` | Drawn ellipse + luminance highlights filter |
| `look_dark_pixels_global_lift` | Pure parametric range_filter (no spatial mask) |

### CLI ergonomics

- `chemigram vocab validate <name>` — runs 6 consistency checks per entry
  (manifest, dtstyle exists + parses, modversions agree, blendop bytes
  decode, parameters match dtstyle plugins). Useful mid-authoring.
- `chemigram cache {list, size, clear}` — preview cache management
  (sister to gap-log / session-log; `--since`, `--image`, `--yes`).
- 26 new CLI integration tests (18 vocab + 8 cache).

### Drift cleanup

Comprehensive doc-alignment pass following the trilogy ship:

- CLAUDE.md PNG-mask references retired (ADR-021 historical) and
  per-image-repo layout updated (the dead `masks/` directory removed).
- RFC-024's 11 cross-references updated to the RFC-026 / RFC-030 split.
- capability-survey § 10 + § 13 reflect today's closures.
- mask-applicable-controls.md gains `range_filter` + `apply_spot`
  sections.
- `apply_with_drawn_mask` renamed to `apply_with_mask` (backcompat
  alias preserved); after ADR-085 the function handles drawn /
  parametric / drawn+parametric.
- Concept package (00, 03, 04) updated with v1.9.0 mask architecture.
- README + docs/index + IMPLEMENTATION + PA + CONTRIBUTING + pack
  READMEs all aligned.

### Backward compatibility

- `apply_with_drawn_mask` retained as a module-level alias for
  `apply_with_mask`; existing callers continue to work.
- All v1.8.0 mask-bound vocabulary entries continue to function; the
  `mask_spec` schema is purely additive (added `range_filter`,
  `dt_form: "path"`).
- CLI verbs and MCP tools are additive only.

### Deferred to future releases

- RFC-027 (multi-photographer review phase plan) — not yet drafted.
- RFC-028 (pack management / vendor packs) — not yet drafted.
- RFC-030 (deployed sibling-provider scaffolding) — Draft v0.1.
- Recipe book, onboarding guide, architecture diagrams, fuzz tests.
- `#94` manual tone curve, `#95` lens EXIF auto-binding, `#96` denoise
  wavelet baseline, `#98` colorzones HSL precision — all under the
  `#100` darktable-session umbrella.

## [1.8.0] — 2026-05-07

**Lightroom daily-use parity — 51/52 controls (98%) across 6 panels.**

v1.8.0 closes the bulk of the Lightroom-parity work tracked under the v1.8.0
milestone. The capability-survey § 13 daily-use surface count moved from 12/23
covered (pre-v1.7.0) to 45/47 (post-v1.7.0) to **51/52 (post-v1.8.0)**. Only
manual tone curve (#94) remains, blocked on the darktable-session empirical-
baseline work tracked under #100.

### Closed Lightroom-parity gaps

**Color panel (4/4 covered):**
- WB Tint via `temperature.green_coeff` (#90 Bucket A.3).
- WB Kelvin/Tint UX wrapper via `wb_kelvin_delta` (#102) — photographic-units
  axes layered on the existing temperature decoder.

**Color Mixer panel (24/24 covered):**
- HSL Hue / Saturation / Luminance per 8 colors via `colorequal` mv4
  (RFC-023 / ADR-083 / #93). 3 multi-axis vocabulary entries
  (`hsl_hue` / `hsl_saturation` / `hsl_luminance`), 24 axes total.
- First formal Tier 3 → Tier 2 promotion under ADR-081's policy.

**Color Grading panel (7/7 covered):**
- Per-zone hue × 3 + per-zone saturation × 3 + blending (shadows_weight /
  highlights_weight) + balance (white_fulcrum) via 9 new `colorbalancergb`
  axes (#91 Bucket A.5).
- Midtones grade discrete entries (`grade_midtones_warm` / `_cool`, #90 Bucket A.4).

**Effects panel (5/5 covered):**
- Texture via `diffuse-or-sharpen` mv2 (#92 Bucket A.6).
- Dehaze via `hazeremoval` mv3 (#90 Bucket A.2).

**Transform panel (5/5 covered, NEW):**
- Rotation, vertical/horizontal perspective, shear, aspect via `ashift` mv5
  (#101 Bucket A.7).

### Tier 3 promotions (darktable-specific power)

Beyond Lightroom parity, three Tier 3 modules promoted to Tier 2 under ADR-081's
"feature commit + cite ADR + 5-layer coverage" pattern:

- **Lens correction** (`lens` mv10, #95) — 10 magnitude axes for manual TCA /
  vignette / per-correction-type strengths. The 356-byte struct includes two
  embedded char[128] arrays for lensfun identifier strings; EXIF auto-binding
  to populate them is sequenced under #100.
- **Denoise** (`denoiseprofile` mv12, #96) — 4 magnitude axes (denoise_strength,
  denoise_shadows, denoise_radius, denoise_scattering). The 416-byte struct
  contains 84 floats of wavelet-frequency curves; baseline is constructed,
  empirical verification under #100.
- **Filmic v6** (`filmicrgb` mv6, #97) — 8 magnitude axes parallel to sigmoid
  for users who want explicit log-encoding control.

### Architecture

- **ADR-083** closes RFC-023 — picks `colorequal` over `colorzones` for HSL
  parity; reclassifies HSL from Tier 3 to Tier 2.
- 18 Path C decoders in the registry (was 11 at v1.7.0); 38 parameterized
  vocabulary entries (was 18 at v1.7.0).
- 5-layer coverage gate per ADR-080 covers all 38 parameterized entries.
- Modversion drift detection (ADR-082) registers all 18 modules.

### Deferred (tracked under #100 darktable-session umbrella)

- **#94 manual tone curve** (`tonecurve` mv5) — 520-byte spline-curve struct
  needs darktable-GUI baseline capture.
- **#95 lens EXIF auto-binding extension** — populate lensfun camera/lens
  strings from raw EXIF at apply time.
- **#96 denoise wavelet-curve baseline verification** — confirm or fix the
  constructed `x[6][7]/y[6][7]` baseline against a darktable-emitted dtstyle.
- **#98 colorzones spline-curve HSL precision fallback** — discrete-only
  presets for the 5% workflow that needs Lightroom HSL Range slider precision.

### Stats

- Tests: 1127 → **1451** passing (+324).
- Path C decoders: 11 → **18**.
- Parameterized vocabulary entries: 18 → **38**.
- ADRs: 82 → **83** (ADR-083 closes RFC-023).
- Lightroom daily-use parity: 12/23 → **51/52** (98%).

## [1.7.0] — 2026-05-07

**Phase 4 close + RFC-022 Tier 2 + brilliance + B&W trio + L2 looks.**

See GitHub release notes — v1.7.0 wrapped Phase 4's 8 magnitude-ladder
parameterizations and shipped the first Tier 2 expansion batch (sharpen,
crop, additional colorbalancergb axes, toneequalizer 9-axis).

## [1.5.0] — 2026-05-03

**Mask architecture cleanup — drawn-mask only.**

While shipping path 4a in v1.4.0 we discovered the previous PNG-mask
path was a silent no-op: darktable never reads external PNG files for
raster masks (verified against darktable 5.4.1 source — `src/develop/blend.c`
resolves raster masks from in-pipeline pointers, not the filesystem).
The bundled `MaskingProvider` Protocol, `CoarseAgentProvider`, geometric
providers, mask registry, `materialize_mask_for_dt` helper, and the
`generate_mask`/`regenerate_mask`/`list_masks`/`tag_mask`/`invalidate_mask`
tools were all infrastructure for a path that never connected to pixels.

This release rips that dead infrastructure entirely. **Breaking changes.**

**ADR-076** (supersedes ADR-021/022/055/057/058/074): drawn-mask only.
Mask-bound vocabulary entries declare `mask_spec` and route through
`apply_with_drawn_mask` automatically — no providers, no registry, no
PNG.

**Removed:**

- **Production code:** `chemigram.core.masking.MaskingProvider` Protocol,
  `MaskResult`, `MaskingError`, `MaskGenerationError`, `MaskFormatError`;
  `chemigram.core.masking.coarse_agent` (CoarseAgentProvider);
  `chemigram.core.masking.geometric` (Gradient/Radial/RectangleMaskProvider);
  `chemigram.core.versioning.masks` (mask registry, MaskEntry,
  register_mask, get_mask, list_masks, tag_mask, invalidate_mask);
  `chemigram.core.helpers.materialize_mask_for_dt`,
  `serialize_mask_entry`, `ensure_preview_render`.
- **MCP tools:** `generate_mask`, `regenerate_mask`, `list_masks`,
  `tag_mask`, `invalidate_mask`.
- **CLI sub-app:** `chemigram masks ...` (list / generate / regenerate /
  tag / invalidate).
- **Vocabulary schema:** `mask_kind`, `mask_ref` fields. `mask_spec` is
  now the only mask declaration.
- **Tool surface:** `apply_primitive`'s `mask_override` argument (CLI
  flag and MCP arg).
- **Server wiring:** `build_server(masker=...)`, `ToolContext.masker`.
- **Workspace layout:** `Workspace.masks_dir` property and the
  `masks/` subdir creation. `numpy>=1.26` runtime dep dropped.

**Vocabulary changes:**

- `tone_lifted_shadows_subject` (#62) retired from the starter pack —
  was doubly broken (wrong dtstyle content awaiting a real darktable
  session AND the raster path it depended on never worked). Starter
  drops 5 → 4 entries. Future "lift shadows on subject" can be
  re-authored as a drawn-mask entry when there's evidence to support it.
- The four expressive-baseline mask-bound entries (gradient_top_dampen_highlights,
  gradient_bottom_lift_shadows, radial_subject_lift, rectangle_subject_band_dim)
  are unchanged — their `mask_spec` was already the load-bearing field;
  the now-redundant `mask_kind: "drawn"` marker was stripped.

**Prompt template:** `mode_a/system_v4.j2` is the new active version
per ADR-043 (append-only). Drops references to the removed tools and
the `mask_kind: "raster"` schema; rewrites the "Local adjustments"
section around the built-in geometric mask types.

**Tests:** ~2200 lines of dead test code removed (10 files); the
3 e2e tests that survived prove drawn-mask shapes effect end-to-end
against real darktable. `tests/integration/cli/test_stdin_batch.py`
fixed (pre-existing `from tests.* import` that couldn't resolve).

**No PyPI** (deferred per the v1.4.0 ship direction).

## [1.4.0] — 2026-05-02

**Vocabulary expansion + masks + CLI ergonomics + infra cleanup.**

The "ambitious 1.4" milestone: closes the v1.4.0 extension plan with
2 new ADRs, 1 amended ADR, 3 RFC closures, 11 GH issues. Total: 23
new tests (700 → 723), 14 commits across 7 batches.

**New capabilities:**

- **Built-in geometric mask providers (ADR-074).** Three deterministic,
  parameter-driven mask providers — `GradientMaskProvider`,
  `RadialMaskProvider`, `RectangleMaskProvider` — under
  `chemigram.core.masking.geometric`. Each implements the existing
  `MaskingProvider` Protocol unchanged (ADR-057). Adds `numpy>=1.26`
  to runtime deps for per-pixel field math; defended in ADR-074 as
  pure infrastructure (same tier as Pillow, not a BYOA-007 violation).
- **CLI mask integration (#73).** `chemigram masks generate` and
  `regenerate` accept `--provider {gradient|radial|rectangle}` plus
  `--config <JSON>`. Without `--provider`, the v1.3.0 MASKING_ERROR
  surface is preserved.
- **Vocabulary mask_spec field.** `VocabEntry.mask_spec` (optional)
  declares which built-in provider + config should generate a
  raster mask if it isn't already in the registry. v1.4.0 stores
  the field; the auto-generation hook in `apply_primitive` lands
  in v1.5.x. Both adapters (CLI vocab show, MCP list_vocabulary)
  surface the field.

**Vocabulary completion:**

- 31 expressive-baseline entries authored programmatically across 9
  darktable iop modules using reverse-engineered C struct layouts.
  22 e2e direction-of-change tests passing against real darktable
  5.4.1. Authoring guide at `docs/guides/expressive-baseline-authoring.md`.
- **ADR-073** formalizes Path C (programmatic vocabulary authoring
  via reverse-engineered structs) as an accepted complement to
  hand-authoring. Closes RFC-012.
- 4 entries pending user darktable seeds (#62 starter pack
  tone_lifted_shadows_subject content bug; #63 channelmixerrgb B&W
  ×3) — both blocked on hand-authored darktable sessions and
  deferred to v1.4.x.

**CLI ergonomics:**

- **Shell completion (#67).** Typer's `--install-completion` and
  `--show-completion` flags surface in root help. Bash, zsh, fish,
  and PowerShell all supported. Closes RFC-020 §Q1.
- **Workspace auto-discovery (#69).** New
  `discover_workspace_from_cwd` helper walks up from cwd looking
  for an image root. Wired via the `image_id == "."` shortcut:
  `cd ~/Pictures/Chemigram/iguana && chemigram get-state .`
  works without flags. Closes RFC-020 §Q3.
- Stdin support (#68) deferred — needs verb-signature changes
  across 8+ files, lower priority than the wins shipped here.

**Infrastructure:**

- **Linux CI matrix (#70).** `.github/workflows/ci.yml` adds
  `ubuntu-latest` alongside `macos-latest`. ADR-075 amends ADR-040
  with the rationale: CI tier doesn't invoke darktable, so Linux
  runners exercise identical Python paths as macOS.
- **Manifest↔dtstyle audit (#71).** New integration test asserts
  every entry's dtstyle plugin `<operation>` set equals its
  manifest `touches[]` set, across starter + expressive-baseline
  packs. Would have caught #62 at CI time.
- **Helpers refactor (#66).** 6 MCP-private helpers
  (`summarize_state`, `current_xmp`, `parse_xmp_at`,
  `materialize_mask_for_dt`, `stitch_side_by_side`,
  `serialize_mask_entry`) lifted to `chemigram.core.helpers`.
  Closes the "future cleanup" promise in ADR-071. The CLI no
  longer cross-imports MCP private internals.
- **Preview render lift.** `ensure_preview_render` lifted to
  `chemigram.core.helpers` for shared use by both adapters'
  mask generation paths.

**RFC closures:**

- **RFC-012** (programmatic vocabulary generation / Path C) →
  Decided. Closes via ADR-073.
- **RFC-018** (vocabulary expansion for expressive taste) →
  Decided. Closes via ADR-063, ADR-064, ADR-073.
- **RFC-019** (reference-image validation baseline) → Decided.
  Closes via ADR-066, ADR-067, ADR-068.

**No PyPI** — distribution stays GitHub-only per the user's
explicit v1.4.0 statement.

## [1.3.0] — 2026-05-03

**chemigram CLI (RFC-020 / PRD-005).**

A subprocess-callable adapter alongside the existing MCP server, mirroring
the tool surface verb-for-verb (with `_` → `-` for shell ergonomics). For
batch processing, custom agent loops, watch-folder daemons, and CI
pipelines where MCP's session model is the wrong shape. PRD-005 frames
the user-value case; RFC-020 locks the design.

**Adapter:**

- New `chemigram.cli` package with `chemigram` entry point on `$PATH`
  (alongside `chemigram-mcp`). 22 verbs total, organized as: status,
  ingest, apply-primitive, remove-module, reset, get-state, snapshot,
  branch, tag, checkout, log, diff, bind-layers, render-preview,
  compare, export-final, masks list/generate/regenerate/tag/invalidate,
  read-context, log-vocabulary-gap, apply-taste-update,
  apply-notes-update, vocab list/show.
- Global flags: `--json`, `--workspace` (env: `CHEMIGRAM_WORKSPACE`),
  `--configdir` (env: `CHEMIGRAM_DT_CONFIGDIR`), `--quiet`, `--verbose`.
- Output: human-readable text by default, NDJSON via `--json`. The
  output schema version is locked at `1.0` (independently of package
  SemVer per RFC-020, the same pattern as ADR-045 for prompts) and
  surfaced via `chemigram status`.
- 11-value `ExitCode` IntEnum maps each `chemigram.mcp.errors.ErrorCode`
  to a distinct non-zero code. The `match` statement is mypy-exhaustive;
  a runtime audit-style integration test catches drift.

**Architectural decisions:**

- Both MCP and CLI are thin wrappers over `chemigram.core` (ADR-071).
  No domain logic in either adapter; lint-enforced via
  `scripts/audit-cli-imports.py` (wired into `make ci` step 7/10).
- The conversational propose/confirm pair (`propose_taste_update`,
  `confirm_taste_update`, plus notes counterparts) stays MCP-only.
  The CLI ships direct apply verbs (`apply-taste-update`,
  `apply-notes-update`) because cross-process proposal storage would
  race under parallel batch invocations. RFC-020 §F documents the
  divergence.
- Mask `generate` / `regenerate` exit `MASKING_ERROR (7)` because the
  CLI has no provider-injection path equivalent to MCP's
  `build_server(masker=...)`. List/tag/invalidate work fully without
  a provider.
- Pre-existing core helper `append_markdown` lifted from
  `chemigram.mcp.tools.context` to `chemigram.core.workspace` so
  both adapters share one implementation.
- Pre-existing core helper `current_xmp` / `summarize_state` /
  `_serialize_entry` etc. stay in `chemigram.mcp` for now; pragmatic
  shared imports until a future "lift to core helpers" refactor.

**Documentation:**

- README — new "Quickstart — scripts and agent loops (CLI)" section
  alongside the existing MCP block.
- `docs/getting-started.md` — new "Driving Chemigram from a script
  or agent loop" section after the MCP first-session walk-through.
  Includes the canonical Python integration pattern (subprocess +
  NDJSON + ExitCode branching).
- `docs/guides/cli-reference.md` — auto-generated from
  `chemigram --help`. CI step `[10/10]` runs the generator with
  `--check` to fail on drift between live `--help` and the
  checked-in file.
- `docs/index.md` — tagline updated to mention both adapters; new
  "Two planes of control" section explaining when to reach for each.
- `docs/concept/04-architecture.md` — subsystems table grew from 5
  to 6 (CLI as subsystem 6); new §2.1 "Two planes of control".

**ADR closures pending v1.3.0 release (#61):**
ADR-069 (CLI alongside MCP), ADR-070 (Typer framework), ADR-071
(thin-wrapper discipline + lint), ADR-072 (output format + exit codes).
RFC-020 will move from Draft v0.1 to Decided.

**Tests:** 674 unit + integration green (was 556 pre-CLI). 4 e2e
session tests against real darktable: ingest → apply → get-state →
reset; render-preview + export-final round-trip; compare across two
snapshots; standalone status. ruff + mypy + audit + cli-reference
sync check all green.

## [1.2.0] — 2026-05-02

**Engine unblock + reference-image validation infrastructure.** Closes
the synthesizer's Path B gap (RFC-018 v0.2) and ships a CI-safe
colorimetric assertion library (RFC-019 v0.2) — the two pieces that
gate the future 35-entry `expressive-baseline` vocabulary authoring
work (now scoped to v1.4.0). The CLI work (RFC-020 / PRD-005) ships
next as v1.3.0.

**Engine — Path B unblocked:**

- `synthesize_xmp` now appends new-instance history entries for
  vocabulary primitives whose `(operation, multi_priority)` tuple
  isn't in the baseline (closes RFC-001's open Path B question;
  ADR-063). Empirical evidence
  (`tests/fixtures/preflight-evidence/`) showed darktable 5.4.1
  resolves pipeline order from `iop_order_version` + the internal
  `iop_list` regardless of per-entry `iop_order`, so appended entries
  ship with `iop_order=None` — no probe script, no manifest schema
  fields. Supersedes ADR-051's "Path B deferred" stance.
- `HistoryEntry.iop_order` type widened from `int | None` to
  `float | None` so rendered XMP sidecars (which can carry float
  values) round-trip cleanly.
- `VocabularyIndex` now accepts `Path | list[Path]` and ships
  `load_packs(["starter", "expressive-baseline"])` for multi-pack
  loading. Cross-pack name collisions raise a clear error naming
  both pack roots.

**Reference-image validation (RFC-019 v0.2 → ADR-066/067/068):**

- `chemigram.core.assertions` — hand-rolled CIE DE2000, sRGB ↔ Lab
  D50 (Lindbloom Bradford adaptation), patch extraction, and
  high-level helpers (`assert_color_accuracy`, `assert_tonal_response`,
  `assert_exposure_shift`, `assert_wb_shift`). Validated against the
  Sharma/Wu/Dalal 2005 reference test pair (DE2000 = 2.0425).
- `tests/fixtures/reference-targets/` — synthetic CC24 + grayscale
  ramp PNGs paired with X-Rite published L\*a\*b\* D50 ground truth.
  CI-safe (no darktable, no real RAW). Tier B (real-RAW reference
  shooting) is deferred per ADR-068.

**Prompts:**

- Mode A `system_v3.j2` is now active. Filter-first vocabulary
  navigation guidance, multi-pack enumeration, and explicit
  `end_session` orchestration. Adds `vocabulary_packs` to required
  context. v1 + v2 stay loadable for eval reproducibility (ADR-045).

**Vocabulary scaffolding:**

- `vocabulary/packs/expressive-baseline/` skeleton (empty manifest,
  README, L3 module subdirectories). Authoring of the 35 entries
  is hands-on darktable work and lives in v1.4.0.

**Closing ADRs:** 063 (Path B unblocking, closes RFC-001 + RFC-018),
064 (vocabulary authoring workflow, closes RFC-018), 066
(synthetic-only reference fixture policy, closes RFC-019), 067
(pixel-level assertion protocol, closes RFC-019), 068 (darktable
version gate, deferred — closes RFC-019). ADR-065 is deliberately
gapped — see `docs/adr/index.md` Conventions.

**Tests:** 556 unit + integration pass. New: 34 unit tests for the
assertion library, 9 integration tests for the synthetic CC24
round-trip, 16 e2e scaffolds for `expressive-baseline` (auto-skip
until entries are authored).

**Phase plan reshaped (2026-05-02):** Phase 1.2 originally bundled
engine + 35-entry authoring under v1.2.0. Authoring is hands-on
darktable work and was decoupled from the engine slice; engine +
assertion library ship as v1.2.0; CLI ships as v1.3.0; the 35-entry
authoring sprint ships as v1.4.0. Phase 2 now begins post-v1.4.0.

## [1.1.0] — 2026-04-30

**Comprehensive validation milestone.** A from-first-principles testing
strategy + 8 GH issues (#31–#38) of capability-matrix coverage work that
closed real engine bugs before they reached photographers.

The shipped capability matrix lives in [GH #30](https://github.com/chipi/chemigram/issues/30);
the full philosophy and standards live in [`docs/testing.md`](docs/testing.md).

**Engine bugs found and fixed by the new test surface (3):**

- **`reset` was detaching HEAD** (closes ADR-062). The MCP `reset` tool
  called `checkout(baseline-tag)` which detaches HEAD per ADR-019;
  subsequent `apply_primitive` then raised "cannot snapshot from a
  detached HEAD". The implementation contradicted ADR-015's spec
  ("reset goes to baseline_end, ready to keep applying"). New engine
  op `reset_to(repo, ref_or_hash)` rewinds the current branch to the
  baseline hash and re-attaches HEAD if previously detached. Matches
  `git reset --hard` semantics. Surfaced by the e2e MCP-level
  regression in #31.
- **`branch` and `checkout` resolved input inconsistently.** `branch()`
  called `repo.resolve_ref(from_)` directly which only accepts `"HEAD"`
  or full `"refs/..."` form; `checkout()` used `_resolve_input` which
  also accepts bare branch/tag names and hashes. So
  `branch(repo, "exp", from_="baseline")` failed while
  `checkout(repo, "baseline")` worked — same input, different verbs.
  `_resolve_input` extended to accept full ref form too, and `branch()`
  routed through it. Surfaced by the integration tests in #31.
- **Provider exceptions escaped the MCP boundary** (ADR-007 BYOA
  invariant). `generate_mask` / `regenerate_mask` only caught
  `MaskingError`; any other exception (RuntimeError, ImportError,
  anything from a third-party `MaskingProvider`) escaped and the agent
  saw an empty content envelope instead of a structured error. Both
  handlers now catch broad `Exception` and convert to a structured
  `masking_error` with the exception's type + message. Surfaced by the
  integration tests in #33.

**Other fixes during this milestone:**

- `_render_to` in `mcp/tools/rendering.py` now unlinks the deterministic
  preview path before invoking darktable-cli. Previously, when the
  output file already existed, darktable silently auto-appended `_01`
  to the filename, so two consecutive `render_preview` calls returned
  the *first* render's bytes. Surfaced by the original e2e MCP session
  test (committed as part of the test/e2e suite, pre-#31).

### Added

- `docs/testing.md` (~14 KB) — testing strategy from first principles.
  Five rules: test through the agent boundary; test against real bytes;
  direction-of-change not magnitudes; skip cleanly on missing prereqs;
  cover the full surface as a capability matrix.
- `docs/adr/ADR-062-reset-rewinds-current-branch.md` — locks the
  reset-rewinds-current-branch implementation, mirrors `git reset --hard`
  semantics, includes the rationale + alternatives considered.
- `chemigram.core.versioning.ops.reset_to(repo, ref_or_hash) -> Xmp` —
  new public engine op (exported via `__all__`). Resolves
  branch/tag/hash, force-writes the current branch's ref, re-attaches
  HEAD if detached, appends a `reset` log entry with `prior_hash`.
- `tests/e2e/` gains: `test_full_mcp_session.py` (3 tests),
  `test_render_validation.py` (6), `test_versioning_combinations.py`
  (3), `test_vocabulary_primitives.py` (2), `test_mask_shaping.py` (1),
  `test_export_pipeline.py` (4), `test_ingest_lifecycle.py` (3),
  `test_compare_and_persistence.py` (2). All gated to `make test-e2e`
  per ADR-040; skip cleanly when Phase 0 fixtures aren't available.
- `tests/integration/mcp/test_error_paths.py` — every reachable
  `ErrorCode` round-trips as a structured envelope through the MCP
  harness; an audit-style test fails if a new enum value is added
  without classifying it as reachable or reserved.
- `tests/integration/mcp/tools/test_versioning_ops_via_mcp.py` —
  per-tool integration coverage for the versioning surface.
- `tests/integration/mcp/tools/test_export_via_mcp.py` — error-path
  coverage for `export_final`.
- `docs/CONTRIBUTING.md` — testing-standards section enforcing the bar
  for code PRs; revised E2E fixtures section reflects the actual Phase
  0 env-var convention (`CHEMIGRAM_TEST_RAW`, `CHEMIGRAM_DT_CONFIGDIR`,
  `DARKTABLE_CLI`).
- `pyproject.toml` `version = "1.1.0"`.

### Changed

- `chemigram.core.versioning.ops._resolve_input` extended to accept
  full ref form (`"refs/heads/X"`, `"refs/tags/X"`) in addition to
  bare names + hashes. `branch()` now routes through it (was: direct
  `resolve_ref` call). Symmetric behavior with `checkout()`.
- MCP `reset` tool description rewritten to call out destructive-on-
  current-branch semantics.
- `chemigram.mcp.tools.masks._generate_mask` and `_regenerate_mask`
  catch broad `Exception` and convert to `masking_error` — provider
  exceptions never escape the MCP boundary as raw stack traces.
- `chemigram.mcp.tools.rendering._render_to` unlinks `output_path`
  before invoking darktable-cli, preserving the function's contract
  that the bytes at `output_path` are this render's output.
- `chemigram.mcp.errors.ErrorCode` class docstring documents
  `SYNTHESIZER_ERROR`, `PERMISSION_ERROR`, `NOT_IMPLEMENTED` as
  reserved-for-future-use (no current callsite, preserved because
  removing enum values is a breaking MCP-contract change). The
  ADR-056 error-code table mirrors this with reserved-as-of-v1.1.0
  notes.

### Closed

- GH #30 — v1.1.0 tracking issue + capability matrix
- GH #31 — versioning operation coverage
- GH #32 — vocabulary primitive e2e coverage
- GH #33 — mask pipeline coverage
- GH #34 — error-path coverage + reachability audit
- GH #35 — export pipeline coverage
- GH #36 — ingest pipeline coverage
- GH #37 — session transcript coverage
- GH #38 — context loading coverage

### Numbers

- Test count: 435 → 519 (+84). Wall-clock for the full suite
  (unit + integration + e2e against real darktable): ~90 seconds.
- One ADR (ADR-062). Three engine bugs root-caused and fixed.
- Three `ErrorCode` values formalized as reserved.

## [1.0.0] — 2026-04-29

**Phase 1 closed.** Minimum viable loop shipped end-to-end.

`pip install chemigram` produces a working Mode A agent loop out of the
box: read context, generate masks via the calling agent's vision, apply
mask-bound vocabulary primitives, render previews, snapshot, branch,
checkout, propose-and-confirm taste/notes updates, log vocabulary gaps,
write JSONL session transcripts.

**Cumulative scope across v0.1.0 → v1.0.0:** dtstyle parser + XMP r/w +
synthesizer + render pipeline + EXIF binding (v0.1.0); content-addressed
versioning with snapshots/branches/tags + mask registry (v0.2.0); MCP
server + 27 tools + workspace orchestrator + Jinja2 prompt system
(v0.3.0); MaskingProvider Protocol + CoarseAgentProvider sampling-based
default + real `generate_mask` / `apply_primitive(mask_override=...)`
(v0.4.0); multi-scope context loaders + JSONL session transcripts + real
`read_context` + propose/confirm tools + RFC-013 vocabulary-gap schema
(v0.5.0); minimal starter vocabulary pack + verify-vocab CI check + Mode
A prompt v2 (v1.0.0).

**13 of 17 RFCs closed** via ADR-050..061 (and RFC-016 via ADR-043/044/045).
Remaining RFCs are Phase 2+ scope: RFC-007 (modversion drift), RFC-008
(vocabulary discovery at scale), RFC-012 (programmatic generation Path C).

### Added
- `pyproject.toml` `version = "1.0.0"`; classifier `Pre-Alpha` → `Beta`.
- `chemigram-mcp` server reports `version="1.0.0"` on the MCP handshake.
- Phase status surfaces (`docs/IMPLEMENTATION.md`,
  `docs/concept/00-introduction.md`, `README.md`, `CLAUDE.md`) updated:
  Phase 1 closed; Phase 2 (vocabulary maturation) in progress.
- Slice 6 marked `✅ shipped (v1.0.0)` in IMPLEMENTATION.md.

### What lands after this

Phase 2: use-driven vocabulary maturation. Photographers run real
sessions; the agent logs gaps; vocabulary grows organically. Phase 2
doesn't decompose into slices the way Phase 1 did — work is
intermittent and use-shaped.

## [0.6.0] — pre-release

(Slice 6's pre-tag work, all integrated into 1.0.0; no separate 0.6.0
tag was cut.)

### Added
- **Mode A prompt v2** (`src/chemigram/mcp/prompts/mode_a/system_v2.j2`).
  Refinements based on the v0.4.0 (masking real) and v0.5.0 (context
  real) shipping. v1 stays on disk for eval reproducibility per
  ADR-045; `MANIFEST.toml` bumps `active = "v2"`.
- v2 changes vs v1: drops the `{% if masker_available %}` conditional
  (masking is bundled per ADR-058); concretizes `read_context` shape
  references (`tastes.conflicts`, recent_gaps as part of context, notes
  summarization); names the `propose_taste_update` `category` enum
  (`appearance | process | value` per ADR-031) and `file` default; adds
  a "Vocabulary gaps" section documenting the full RFC-013 schema
  (intent, intent_category, missing_capability, satisfaction, etc.);
  updates the end-of-session sequence to reference ADR-061 (no engine
  `end_session` tool — agent orchestrates via existing tools); removes
  future-tense hedging from flows that are now real.
- `system_v2.changelog.md` — cumulative version log (v2 + v1 entries);
  `system_v1.changelog.md` removed (its content is in v2's log).
- 6 new/updated tests cover v2 active version + render content +
  category-enum references + end-of-session orchestration; `v1` still
  loadable explicitly via `version="v1"`.

### Added
- `scripts/verify-vocab.sh` — CI manifest-validation check, same shape
  as `verify-prompts.sh`. Runs `VocabularyIndex(pack_root)` + asserts
  the eager-load succeeds; exits ≠0 on `ManifestError`. Picks up `uv
  run python` if available, falls back to bare `python3` for activated
  venvs. Wired into `make ci` (step 8/8) and
  `.github/workflows/ci.yml`.
- **Starter vocabulary pack populated.** `vocabulary/starter/` ships 5
  entries (deliberately small per IMPLEMENTATION.md; Phase 2 grows the
  pack from real session evidence): `expo_+0.5`, `expo_-0.5`,
  `wb_warm_subtle`, `look_neutral` (L2 baseline), and
  `tone_lifted_shadows_subject` (mask-bound L3 referencing
  `current_subject_mask`). Calibrated to darktable 5.4.1.
- `pip install chemigram` now produces a working starter pack out of
  the box. `chemigram.core.vocab.load_starter()` succeeds without
  requiring user setup. The bundled pack ships as
  `chemigram/_starter_vocabulary/` (per ADR-049, force-included via
  `pyproject.toml`).
- `vocabulary/starter/README.md` rewritten — drops the planning stub
  text; documents what's shipped, what's deferred to Phase 2, and the
  personal-vocabulary growth pattern (`~/.chemigram/vocabulary/personal/`).
- `tests/integration/core/vocab/test_starter_load.py` no longer skips;
  asserts the real pack contents.

### Changed
- `chemigram.core.vocab.load_starter()`'s in-repo fallback path
  corrected (`parents[4]` was `parents[3]`); editable-install
  development now resolves the in-repo `vocabulary/starter/` directly.

## [0.5.0] — 2026-04-29

Slice 5 of Phase 1 — context layer + session transcripts.

### Added
- **End-to-end context gate test** (`tests/integration/mcp/test_full_session_with_context.py`)
  drives read_context → apply_primitive ×2 → propose_taste_update +
  confirm_taste_update → log_vocabulary_gap (RFC-013 shape) →
  propose_notes_update + confirm_notes_update → read_context (sees gap +
  log entries) through the in-memory MCP harness with a real
  SessionTranscript writer attached. Asserts files updated, transcript
  JSONL contains all events in order.
- **ADR-059** — closes RFC-011 (agent context loading order and format).
  Locks the loading sequence (tastes → brief → notes → recent_log →
  recent_gaps), the structured-top + prose-body shape, the long-notes
  line-truncation rule (10 + 30 + ellision), and missing-file tolerance.
- **ADR-060** — closes RFC-013 (vocabulary gap JSONL schema). Locks the
  full record shape with auto-populated `session_id` + `snapshot_hash`,
  and the backwards-compat reader that handles both v0.3.0 minimal and
  full records.
- **ADR-061** — closes RFC-014 (end-of-session synthesis). Documents
  that wrap-up is agent-orchestrated (no engine `end_session` tool); the
  Mode A v1 prompt's "End of session" section names the canonical
  sequence (0–2 taste proposals, gap recap, 1 notes proposal, optional
  tag).
- TA `components/context` and `components/session` added as `(shipped
  v0.5.0)`. ADR-059/060/061 added to `## map` and `adr/index.md`.
  RFC-011/013/014 status `Draft v0.1` → `Decided`.
- `docs/concept/04-architecture.md` gains a context-component +
  session-component paragraph documenting loaders, transcript shape,
  and the agent-orchestrated wrap-up.
- `docs/IMPLEMENTATION.md` Slice 5 marked `✅ shipped`; Phase 1 status
  synced across `README.md`, `concept/00`, `CLAUDE.md`.
- `pyproject.toml` `0.4.0` → `0.5.0`.

## [0.4.0] — 2026-04-29

Slice 4 of Phase 1 — real masking provider.

### Added
- **End-to-end masking gate test** (`tests/integration/mcp/test_full_session_with_masks.py`)
  drives ingest → generate_mask → list_masks → apply_primitive(mask_override) →
  regenerate_mask → log through the in-memory MCP harness with a fake
  sampling-based masker injected via `build_server(masker=...)`.
- **ADR-057** — closes RFC-009 (MaskingProvider Protocol shape). Locks the
  sync `generate` / `regenerate` keyword-only contract, the `MaskResult`
  dataclass shape, the exception → MCP-error mapping (`MaskGenerationError`
  → `MASKING_ERROR` recoverable; `MaskFormatError` → `MASKING_ERROR`).
- **ADR-058** — closes RFC-004 (default masking provider). Locks the
  bundled default as `CoarseAgentProvider` (sampling-based, BYOA-aligned)
  with `chemigram-masker-sam` (Phase 4 sibling) as the recommended
  production upgrade.
- TA `components/ai-providers` moves `(planned)` → `(shipped v0.4.0)`;
  ADR-057 + ADR-058 added to `## map` and `adr/index.md`. RFC-004 +
  RFC-009 status `Draft v0.1` → `Decided`.
- `docs/concept/04-architecture.md` gains a masking-component paragraph
  documenting the Protocol + sampling pattern.
- `docs/IMPLEMENTATION.md` Slice 4 marked `✅ shipped`; Phase 1 status
  synced across `README.md`, `concept/00`, `CLAUDE.md`.
- `pyproject.toml` `0.3.0` → `0.4.0`.

### Changed
- **Vocabulary gap schema upgrade (RFC-013).**
  `chemigram.mcp.tools.ingest._log_vocabulary_gap` now writes records
  with the full RFC-013 shape: `session_id` (auto-populated from
  `ctx.transcript`), `snapshot_hash` (auto-populated from current HEAD),
  `intent`, `intent_category` (default `"uncategorized"`),
  `missing_capability`, `operations_involved`, `vocabulary_used`,
  `satisfaction` (`-1`/`0`/`1`), and `notes`.
- The tool's MCP `inputSchema` adds those optional fields; required
  fields stay `[image_id, description]` for backwards-compat with
  agents written against the v0.3.0 minimal shape.
- `RecentGaps.load` (#21) reads both v0.3.0 minimal and post-upgrade
  records — old records take dataclass defaults for new fields. JSONL is
  append-only; pre-release, no migration concerns.

### Added
- `chemigram.mcp.tools.context` — replaces v0.3.0 `context_stubs.py` with
  real implementations of all 5 slice=5 stubs:
  - `read_context(image_id)` — loads tastes/brief/notes/recent_log/
    recent_gaps via `chemigram.core.context`. Returns the structured-top
    + prose-body shape per RFC-011.
  - `propose_taste_update(content, category, file?)` — registers a
    taste proposal in `ToolContext.proposals`. Validates `category` ∈
    {appearance, process, value} and non-empty content. Auto-adds `.md`
    extension to `file` when missing.
  - `confirm_taste_update(proposal_id)` — atomically appends to the
    target file under `~/.chemigram/tastes/`; clears the proposal.
  - `propose_notes_update(image_id, content)` /
    `confirm_notes_update(proposal_id)` — same pattern, per-image
    `<workspace>/notes.md`.
- `chemigram.mcp.registry.Proposal` dataclass + `ToolContext.proposals:
  dict[str, Proposal]` field. Proposals live in-memory per session;
  unconfirmed ones expire when the session ends. No explicit `decline_*`
  tool — RFC-031's closing ADR documents the lifecycle.
- Tool handlers record proposal/confirmation entries on
  `ctx.transcript` when configured. Failures are logged, never abort.

### Changed
- The 5 context tools no longer return `NOT_IMPLEMENTED slice=5`.
  v0.3.0 `context_stubs.py` removed; tests updated to assert real
  behavior. (Pre-release; no migration concerns.)

### Added
- `apply_primitive(mask_override=…)` real path replacing the v0.3.0
  slice=4 stub. Mask-bound L3 entries (`mask_kind: "raster"`) now require
  a registered mask matching `entry.mask_ref` (or the override) to be
  present in the per-image registry; the tool materializes the PNG to
  `<workspace>/masks/<name>.png` (where darktable-cli reads raster
  masks) before snapshotting.
- `chemigram.mcp.tools._masks_apply.materialize_mask_for_dt(workspace,
  mask_name)` helper. Idempotent — skips the write if the file already
  matches the registered hash.
- Test pack gained `tone_lifted_shadows_subject` mask-bound L3 entry
  (`mask_kind: "raster"`, `mask_ref: "current_subject_mask"`).

### Changed
- `apply_primitive(mask_override=...)` no longer returns
  `NOT_IMPLEMENTED slice=4`; now returns `INVALID_INPUT` if passed on a
  non-mask-bound entry, `NOT_FOUND` if the referenced mask isn't
  registered, or success with the mask materialized otherwise. (Pre-
  release; no migration concerns.)

### Added
- `chemigram.core.session` package per ADR-029. `SessionTranscript`
  writes JSONL transcripts to `<workspace>/sessions/<session_id>.jsonl`:
  header line on open, per-turn entries (`tool_call`, `tool_result`,
  `proposal`, `confirmation`, `note`), footer on close. Append-only,
  flushed per write — crashes lose ≤1 entry. `start_session(workspace,
  …)` factory; uuid4 hex session_id by default.
- `chemigram.mcp.registry.ToolContext.transcript: Any = None` field.
  When a transcript is configured, the server's tool dispatch auto-
  appends `tool_call` (with arguments) + `tool_result` (with success +
  error_code) entries. Transcript I/O failures are caught and logged —
  they never abort tool dispatch.
- `chemigram.mcp.server.build_server(transcript=...)` kwarg.
- `chemigram.mcp.server._dispatch_tool` extracted from the call_tool
  handler so transcript wiring + spec lookup + handler call sit in one
  place; reduces mccabe complexity below the project threshold.
- 14 unit tests (transcript shape + idempotency + serialize-failure
  resilience) + 2 integration tests (transcript wired through MCP
  dispatch + transcript-failure-doesn't-abort-dispatch).

### Added
- MCP `generate_mask` / `regenerate_mask` real implementations replacing
  the v0.3.0 slice=4 stubs. Tools render the current XMP to a cached
  preview (hash-keyed in `<workspace>/previews/_for_mask_*.jpg`), pass it
  to the configured `MaskingProvider`, register the result via
  `chemigram.core.versioning.masks.register_mask`. `regenerate_mask`
  passes the prior PNG to the provider for refinement; `target` is
  inferred from the `current_<target>_mask` name convention or required
  explicitly.
- `chemigram.mcp.registry.ToolContext.masker: Any = None` field. When
  unset, `generate_mask` / `regenerate_mask` surface `MASKING_ERROR`
  ("no masker configured") rather than silently failing.
- `chemigram.mcp.server.build_server(masker=...)` kwarg — production
  callers wire `CoarseAgentProvider` against the MCP session's sampling
  callback at server startup; tests inject fakes.

### Changed
- The two mask-generation tools no longer return `NOT_IMPLEMENTED slice=4`;
  callers that relied on the v0.3.0 stub behavior get clean
  `MASKING_ERROR` instead. (Pre-release; no migration concerns.)

### Added
- `chemigram.core.context` package — loaders for the agent's first turn:
  `Tastes` (multi-scope per ADR-048: `_default.md` + brief-declared genres
  with conflict surfacing), `Brief` (parses `Tastes:` line + intent),
  `Notes` (line-truncation summarization per RFC-011: first 10 + last 30
  + ellision marker), `RecentLog` (tail of `log.jsonl`, newest first,
  partial-line tolerant), `RecentGaps` (handles both v0.3.0 minimal and
  post-#24 RFC-013 schemas).
- `chemigram.core.workspace.tastes_dir()` — resolves the global tastes
  directory; defaults to `~/.chemigram/tastes/`, override via
  `CHEMIGRAM_TASTES_DIR` env var.
- 22 unit tests covering all loaders + the env override + backwards-compat
  for legacy gap records.
- `chemigram.core.masking` package — `MaskingProvider` Protocol, `MaskResult`
  dataclass, exception hierarchy (`MaskingError`, `MaskGenerationError`,
  `MaskFormatError`). Sync contract; async path reserved for a follow-up RFC.
- `chemigram.core.masking.coarse_agent.CoarseAgentProvider` — bundled default
  masker. Uses an injected `ask_agent` callable (production: MCP sampling
  round-trip; tests: a fake) to get a region descriptor, rasterizes via
  Pillow to a grayscale PNG matching the render's dimensions. No PyTorch,
  no model weights — satisfies ADR-007 (BYOA). The MCP wiring lands in
  #18; this issue ships the abstraction in isolation per the v0.4.0 plan.
- `polygon_hint` (≥3 points) takes precedence over `bbox`; under-3 points
  fall back to the bbox; neither-present raises `MaskGenerationError`.
- 16 unit tests cover the Protocol shape and the rasterizer (bbox /
  polygon precedence / dimension matching / failure modes).

## [0.3.0] — 2026-04-29

Slice 3 of Phase 1 — agent-callable MCP tool surface.

### Added
- **End-to-end Mode A gate test** (`tests/integration/mcp/test_full_session.py`)
  drives ingest → bind_layers → list_vocabulary → apply_primitive (×2 across
  branches) → snapshot → branch + checkout → diff → tag → log →
  log_vocabulary_gap → read_context (stub) end-to-end through the in-memory
  client/server harness. The render path is exercised conditionally on
  `darktable-cli` availability; with placeholder raw bytes the contract still
  holds (clean `darktable_error`).
- **ADR-056** — closes RFC-010 with the v0.3.0 surface as evidence. Locks the
  return contract (`{success, data, error}`), the closed `ErrorCode` enum
  (9 codes), the `state_after` shape, and tool-naming conventions. ADR-033
  is preserved; ADR-056 supersedes its implementation-path note.
- ADR-033 implementation-note errata: shipped paths use the `chemigram.mcp`
  / `chemigram.core` namespaces (not the underscore forms in earlier drafts).
- **Doc surface sync:**
  - `docs/concept/04-architecture.md` gained paragraphs on the MCP component,
    prompt system, and workspace orchestrator.
  - `docs/adr/TA.md` `components/mcp-server` and `components/prompts` move
    from `(planned)` → `(shipped)`; `## map` updated for RFC-010 / RFC-016
    closure and ADR-056 acceptance.
  - `docs/IMPLEMENTATION.md`, `docs/concept/00-introduction.md`, `README.md`,
    `CLAUDE.md` — Phase 1 status synced to "Slices 1–3 shipped; Slices 4
    (masking) and 5 (context) parallel-unblocked."
- **Version bump** `0.2.0` → `0.3.0` in `pyproject.toml`.

### Added
- **MCP tool batch 3 (ingest + workspace + masks):**
  - `chemigram.core.workspace.ingest_workspace` plus `workspace_id_for`
    helper. Bootstraps a per-image workspace: creates the directory
    layout, initializes `ImageRepo`, symlinks the raw, reads EXIF,
    suggests L1 bindings, builds + snapshots a baseline XMP (using a
    bundled `_baseline_v1.xmp` stand-in until darktable-cli baseline
    generation lands in a later slice), and tags `baseline`.
  - `ingest(raw_path, image_id?, workspace_root?)` MCP tool wraps the
    bootstrap, returns `{image_id, root, exif_summary, suggested_bindings}`,
    and registers the workspace with the server context.
  - `bind_layers(image_id, l1_template?, l2_template?)` validates layer
    membership, synthesizes the templates onto the current XMP, and
    snapshots. With both omitted, returns the current state.
  - `log_vocabulary_gap(image_id, description, workaround?)` appends a
    JSONL record to the image's `vocabulary_gaps.jsonl`.
  - `list_masks` / `tag_mask` / `invalidate_mask` — real wrappers over
    `chemigram.core.versioning.masks` (useful when masks are registered
    out-of-band).
  - `generate_mask` / `regenerate_mask` — stubs returning
    `NOT_IMPLEMENTED` with `slice=4`.
- `Workspace` gained `exif`/`suggested_bindings` fields populated by
  `ingest_workspace`.
- **MCP tool batch 2 (versioning + rendering):**
  - `snapshot(image_id, label?)` → `{hash}`. Wraps `versioning.ops.snapshot`.
  - `checkout(image_id, ref_or_hash)` → `state_after`-shaped summary. Wraps
    `versioning.ops.checkout` (which moves HEAD).
  - `branch(image_id, name, from_?)` → `{ref}`. `from_` must be HEAD or
    fully qualified (`refs/...`); per `ImageRepo.resolve_ref`.
  - `log(image_id, limit?)` → list of `LogEntry` dicts (newest-first).
  - `diff(image_id, hash_a, hash_b)` → list of `PrimitiveDiff` dicts.
  - `tag(image_id, name, hash?)` → `{ref}`. Re-tag with same name returns
    `VERSIONING_ERROR` per ADR-019 immutability.
  - `render_preview(image_id, size=1024, ref_or_hash?)` → `{jpeg_path,
    duration_seconds}`. Renders to `<workspace>/previews/`.
  - `compare(image_id, hash_a, hash_b, size=1024)` → `{jpeg_path}`.
    Renders both states and stitches into one labeled side-by-side JPEG
    via Pillow.
  - `export_final(image_id, ref_or_hash?, size=None, format="jpeg")` →
    `{output_path, duration_seconds, format}`. Writes to
    `<workspace>/exports/`. `format` ∈ {jpeg, png}; size omitted means
    full resolution (16384 sentinel — darktable-cli treats `--width/--height`
    as upper bounds per ADR-004).
- `Pillow>=10.0` added to runtime deps for the `compare` stitch (pure
  composition; rationale comment in `pyproject.toml`).
- **MCP tool batch 1 (vocab + edit + context stubs):**
  - `list_vocabulary(layer?, tags?)` — wraps
    `VocabularyIndex.list_all` (tags filter is OR per the established
    convention). Returns serialized `VocabEntry` records.
  - `get_state(image_id)` — head_hash + entry_count + per-layer presence
    flags; the canonical `state_after` shape per RFC-010.
  - `apply_primitive(image_id, primitive_name, mask_override?)` —
    synthesizes the entry onto current XMP and snapshots; `mask_override`
    is parameter-stable but returns `NOT_IMPLEMENTED` with `slice=4` until
    the masking provider lands.
  - `remove_module(image_id, module_name)` — strips history entries by
    operation, snapshots; `NOT_FOUND` if no entries match.
  - `reset(image_id)` — checkout the workspace's `baseline_ref` (defaults
    to the `baseline` tag) and return its state summary.
  - 5 context-read stubs (`read_context`, `propose_taste_update`,
    `confirm_taste_update`, `propose_notes_update`,
    `confirm_notes_update`) — return `NOT_IMPLEMENTED` with `slice=5`. The
    surface is shape-stable from v0.3.0 forward.
- `chemigram.core.workspace.Workspace` — runtime per-image handle
  (image_id, root, repo, raw_path, baseline_ref, configdir) plus the
  `init_workspace_root(root)` helper that creates the directory shape
  declared in `contracts/per-image-repo`.
- `chemigram.mcp._state` — shared helpers (`summarize_state`,
  `resolve_workspace`, `current_xmp`) reused across tool batches.
- `chemigram.mcp.tools.register_all()` — idempotent registration of every
  tool batch via `importlib.reload`; called from `build_server()`.
- `chemigram.mcp.server` framework — boots the official `mcp` SDK over stdio,
  loads `VocabularyIndex` and `PromptStore` at startup, and dispatches
  registered tools via `chemigram.mcp.registry`. **Partial RFC-010 closure:**
  the error contract types and parameter validation pipeline lock here; full
  closure is the v0.3.0 gate (#16) once tools land.
- `chemigram.mcp.errors` — `ToolResult`, `ToolError`, `ErrorCode` (per
  RFC-010), helper constructors (`error_invalid_input`, `error_not_found`,
  `error_not_implemented`).
- `chemigram.mcp.registry` — global tool registry (`register_tool`,
  `list_registered`, `get_tool`, `clear_registry`) plus `ToolContext`
  carrier for vocabulary/prompts/workspaces.
- `chemigram.mcp._test_harness.in_memory_session` — async context manager
  that pairs the server with an `mcp.client.session.ClientSession` over
  in-memory streams. Used by per-batch integration tests (#13/#14/#15).
- `pyproject.toml` re-adds `chemigram-mcp = "chemigram.mcp.server:main"` as a
  console script. Bumps `mcp` minimum to 1.27 (the SDK API we're integrating
  against; `>=0.9` was a placeholder).
- `chemigram.mcp.prompts.PromptStore` — Jinja2 prompt loader / renderer driven
  by a top-level `MANIFEST.toml` registry. Closes **RFC-016** (versioned
  prompt system) by landing the implementation behind ADR-043, ADR-044, and
  ADR-045. Public API: `render(path, context, *, version=None, provider=None)`,
  `active_version(path)`, `context_schema(path)`, `list_templates()`. Errors
  exposed as `PromptError` / `PromptNotFoundError` /
  `PromptVersionNotFoundError` / `PromptContextError`.
- `src/chemigram/mcp/prompts/MANIFEST.toml` — active-version registry; first
  entry is `mode_a/system` → `v1`.
- `src/chemigram/mcp/prompts/mode_a/system_v1.j2` — Mode A v1 system prompt,
  migrated verbatim from `docs/agent-prompt.md`. Required context: `image_id`,
  `vocabulary_size`. Optional: `masker_available` (gates the local-adjustments
  guidance).
- `src/chemigram/mcp/prompts/mode_a/system_v1.changelog.md` — per-version
  rationale log; new versions append below.
- `scripts/verify-prompts.sh` — CI consistency check that every active-version
  MANIFEST entry resolves to a `<task>_v<N>.j2` file on disk. Wired into
  `make ci` step 7/7 and `.github/workflows/ci.yml`.
- `chemigram.core.vocab.VocabularyIndex` — eager-loading, validated vocabulary
  pack reader. Reads `manifest.json` (per
  `docs/adr/TA.md::contracts/vocabulary-manifest`) plus the referenced
  `.dtstyle` files, validates entry shape + `touches` ↔ plugin operation
  consistency, and exposes `lookup_by_name`, `list_all(layer=, tags=)`, and
  `lookup_l1(make, model, lens_model)` (satisfying the
  `chemigram.core.binding.VocabularyIndex` Protocol per ADR-053).
- `chemigram.core.vocab.load_starter()` resolves the bundled
  `chemigram/_starter_vocabulary/` resource (ADR-049), with a development
  fallback to in-repo `vocabulary/starter/` for editable installs.
- Tag filter on `list_all` is OR (any-match) — documented in the module
  docstring.
- `tests/fixtures/vocabulary/test_pack/` — hand-stitched validation pack
  symlinking existing `tests/fixtures/dtstyles/` files.
- `docs/CONTRIBUTING.md` — new "v0.3.0+ — registry layout" section in the
  Vocabulary contributions area.
- `docs/agent-prompt.md` reduced to a redirect note pointing at the runtime
  source tree (RFC-016 Open Question #4 answered).
- RFC-016 status moved `Accepted → Decided` in `docs/rfc/index.md` and
  `docs/adr/TA.md` `## map`.

### Changed
- **v0.2.0 polish (pre-tag cleanup):**
  - `chemigram.core.xmp` gains `parse_xmp_from_bytes(data, *, source="<bytes>")`
    so callers with in-memory XMP bytes (e.g., content-addressed reads from
    `chemigram.core.versioning`) avoid a filesystem round-trip. `parse_xmp`
    now delegates its post-find logic to a shared private helper, so both
    paths produce identical output.
  - `chemigram.core.versioning.ops.checkout` and `_load_xmp_for_diff`
    refactored to use `parse_xmp_from_bytes` instead of the
    `tempfile.NamedTemporaryFile + parse_xmp + unlink` pattern. ~16 lines
    of duplicated boilerplate removed.
  - `chemigram.core.versioning.canonical.canonical_bytes` no longer
    re-registers namespaces on every call — the `chemigram.core.xmp` import
    triggers registration once at module load. Defensive but redundant.
  - `chemigram.core.versioning.masks._registry_path` return type annotated
    as `Path` (was `Any`) — closes the type-erasure gap.
  - `chemigram.core.versioning.__init__` docstring rewritten: drops the
    "Future modules" framing (the modules are shipped) and adds a section
    documenting the three sibling exception roots (`RepoError`,
    `VersioningError`, `MaskError`) and how to catch the union.
  - `chemigram.core.versioning.ops._resolve_input` docstring documents
    branch-vs-tag precedence on name collision (branch wins).
  - `tests/integration/core/versioning/test_versioning_integration.py`
    tightened: the ops list assertion is now exact-ordered match (catches
    future regressions that add or reorder log entries) instead of the
    previous "in" / count-based weak assertion.
  - `tests/unit/core/versioning/test_ops.py::test_log_entry_dataclass_shape`
    replaced `dataclasses.MISSING` (a sentinel, not a datetime) with a real
    `datetime.now(UTC)`; added assertions that all default fields are None
    and that `LogEntry` rejects mutation (frozen).
  - 5 new tests for `parse_xmp_from_bytes` (round-trip, source label in
    errors, invalid UTF-8, missing rdf:Description, default source).
  - Doc surfaces synced to v0.2.0: `TA.md` `components/versioning` now
    `(shipped)` with full file list and ADR-054/055 anchored; `README.md`
    Phase 1 row mentions Slice 2; `concept/00`, `CLAUDE.md`,
    `IMPLEMENTATION.md` reflect Slice 3 as next; IMPLEMENTATION.md Slice 2
    section marks RFC-002 / RFC-003 ✅ closed.
  - `pyproject.toml` version bumped `0.0.1` → `0.2.0`.
  - Tests now: 175 unit + 10 integration = 185 passing (was 180); coverage
    94% line / 89% branch.

### Added
- `chemigram.core.versioning.masks` — per-image mask registry + raster
  mask storage (issue #9). Closes **RFC-003** via **ADR-055**: PNG bytes
  share the `objects/` store with XMP snapshots (same content-addressed
  primitives, automatic dedup); `masks/registry.json` maps symbolic
  names to hashes plus provenance (generator, prompt, timestamp).
  Public API: `register_mask`, `get_mask`, `list_masks`, `invalidate_mask`,
  `tag_mask` (immutable alias). PNG validation is byte-magic only in
  v0.2.0 (no Pillow dep; full format validation lands with a masking
  provider that needs it). 17 unit tests + inline `make_test_png`
  fixture (~80-byte 8-bit grayscale PNG via `zlib`+`struct`).
- `chemigram.core.versioning` operations: `snapshot`, `checkout`, `branch`,
  `log`, `diff`, `tag` (issue #8). Pure functions over an `ImageRepo` that
  resolve refs, read/write XMP objects via `canonical_bytes`, and append
  structured `LogEntry` records to `log.jsonl`. Branch checkout sets HEAD
  symbolically; tag/hash checkout detaches. `diff` is the per-(operation,
  multi_priority) symmetric difference between two snapshots, sorted for
  stable output. `tag` is immutable. Detached-HEAD snapshots are refused
  (clear `VersioningError`). 26 unit tests + 1 integration test against
  the v3 reference XMP exercising the full snapshot → branch → checkout
  → modify-via-synthesize → diff → tag flow.
- `chemigram.core.versioning.repo.ImageRepo` — per-image filesystem layout
  + low-level objects/refs/HEAD/log primitives (issue #7). Locks ADR-019's
  git-shaped storage into code: content-addressed `objects/NN/REST...`,
  symbolic `HEAD` (resolves through `refs/heads/<branch>` chains),
  branch + tag refs, append-only `log.jsonl` with auto-timestamping.
  Single-writer per ADR-006; cross-process locking out of scope. 29 unit
  tests covering layout, idempotent init, object dedup, ref resolution
  (incl. circular and depth-exceeded paths), delete semantics, log
  round-trip. No new ADR — implementation matches existing decisions.
- `chemigram.core.versioning` package with `canonical_bytes(xmp) -> bytes`
  and `xmp_hash(xmp) -> str` (issue #6). Deterministic byte form of an
  `Xmp` for content addressing per RFC-002 (closes via **ADR-054**).
  Snapshot tests pin the v3 reference and minimal fixture hashes against
  literal expected values, so any drift in the canonicalization rules
  fails CI loudly. 12 unit tests; 127 unit + 9 integration total.

### Changed
- **Post-Slice-1 cleanup (2026-04-29):**
  - Removed `SynthesisError` from `chemigram.core.xmp` — defined but never raised; YAGNI.
    ADR-050 and ADR-051 amended with implementation notes documenting the removal.
  - Added module docstring to `chemigram.core/__init__.py` (was empty).
  - `parse_xmp` now validates `darktable:history_end ≤ len(history)`; raises
    `XmpParseError` on mismatch (was previously silent).
  - `xmp.label` is now whitespace-stripped on parse to match `dtstyle.description`.
  - `dtstyle.py` adds explicit comment on `multi_name`'s "element required, text
    optional" semantics (ADR-010 user-entry identity marker).
  - `Pipeline.run` replaces `assert` with explicit `RuntimeError` so the invariant
    check survives `python -O`.
  - `DarktableCliStage.clear_locks()` classmethod added for long-running processes
    that cycle through many configdirs (lock-table cleanup).
  - `exif._stringify_tag` strips leading NUL bytes too (was trailing-only).
  - `exif.read_exif` narrows the catch-all `except Exception` to known exifread
    failure modes; truly unexpected exceptions propagate.
  - `render()` docstring documents the tempdir-leak when `configdir=None`.
  - 6 new tests cover error paths previously uncovered (parser missing-element,
    invalid-int, whitespace-only blob, wrong-root; XMP history_end overflow,
    invalid rating, missing description; EXIF malformed focal length, leading-NUL
    stripping; deterministic concurrent-render serialization via mocked subprocess).
  - Coverage: 90% → 96% (line); branch coverage 81% → 88%.
- `chemigram.core.dtstyle.parse_dtstyle` filters `_builtin_*` plugins per ADR-010
  (safety-net per the Phase 0 working notebook). Empty post-filter raises
  `DtstyleParseError`. Two new fixtures cover the filter and the all-filtered case.
- Added two hex-edited dtstyle fixtures (`expo_plus_1p0`, `expo_minus_0p5`) to
  reach Slice 1 gate's "5 different vocabulary primitives" requirement.
- `pyproject.toml` `[project.scripts]` removed `chemigram-mcp` entry point —
  pointed at non-existent `chemigram.mcp.server:main` and would fail at runtime.
  Will re-add when Slice 3 ships the MCP server.
- `docs/IMPLEMENTATION.md`, `README.md`, `docs/concept/00-introduction.md`,
  `CLAUDE.md`: Phase 1 / Slice 1 status updated from "not started" to
  "in progress (3/5 issues; RFC-001 + RFC-006 closed)".
- `docs/adr/TA.md`: `components/synthesizer` "(planned)" → "(shipped)".
- `docs/TODO.md`: new "Slice 1 deferrals" section tracking Path B,
  dtstyle-internal collision validation, and the MCP entry-point re-add.

### Added
- `chemigram.core.exif` + `chemigram.core.binding` — EXIF auto-binding (Slice 1,
  Issue #5). `read_exif` extracts make/model/lens_model/focal_length via
  `exifread`; `bind_l1` resolves L1 vocabulary entries by exact-match on
  `(make, model, lens_model)`. RFC-015 closes into **ADR-053**. 14 unit
  tests + 1 integration test (real D850 NEF).
- `exifread>=3.0` added to runtime deps (pure-Python, no native deps;
  fits BYOA + minimal-core spirit per ADR-007).
- `chemigram.core.pipeline` + `chemigram.core.stages.darktable_cli` — render pipeline
  with `PipelineStage` Protocol, `Pipeline` orchestrator, `DarktableCliStage`
  invoking `darktable-cli` per CLAUDE.md form, and a `render()` convenience entry
  point (Slice 1, Issue #4). Per-configdir threading lock per ADR-005;
  `$DARKTABLE_CLI` env-var override for the macOS .app-bundle case. 13 unit +
  4 integration tests; RFC-005 closes into **ADR-052**.
- `chemigram.core.xmp.synthesize_xmp` — XMP synthesizer (Slice 1, Issue #3).
  Path A only (SET-replace by `(operation, multi_priority)`; last-writer-wins on
  input order; preserves baseline `num` and `iop_order`). Path B raises
  `NotImplementedError` until RFC-001's iop_order question resolves. Closes
  **RFC-001** (parser/synthesizer API → ADR-050) and **RFC-006** (same-module
  collision → ADR-051). 10 unit tests + 1 integration test against real Phase 0
  fixtures.
- `chemigram.core.xmp` — parser + writer for darktable XMP sidecars (Slice 1, Issue #2).
  Public API: `parse_xmp`, `write_xmp`, `Xmp`, `HistoryEntry`, `XmpParseError`.
  Round-trip property (semantic equality) verified against the v3 Phase 0 reference
  (11-entry history with mixed user-authored and `_builtin_*` entries) plus minimal,
  single-entry, and unknown-field fixtures. `iop_order` modeled `Optional[int]` per
  Phase 0 finding (absent in dt 5.4.1 XMPs).
- `chemigram.core.dtstyle` — parser for darktable `.dtstyle` files (Slice 1, Issue #1).
  Public API: `parse_dtstyle`, `DtstyleEntry`, `PluginEntry`, `DtstyleParseError`.
  Calibrated to darktable 5.4.1; opaque blob preservation per ADR-008; user-entry
  identity via empty `<multi_name>` per ADR-010. Uses `defusedxml`.
- Slice 1 prep: `tests/fixtures/{dtstyles,xmps}/` with Phase 0 artifacts;
  hand-stitched `multi_module_synthetic.dtstyle`; `make ci` target mirroring
  `.github/workflows/ci.yml`; smoke tests in `tests/unit/` and `tests/integration/`.
- Phase 2 doc system: PRDs, RFCs, ADRs, reference docs (TA, PA), templates, indexes
- ROADMAP/IMPLEMENTATION plan with slice-by-slice closure-as-gate mapping
- Initial CLAUDE.md operational handbook
- Python project conventions locked via 9 ADRs (ADR-034 through ADR-042)
- Bootstrap project scaffolding (pyproject.toml, pre-commit, CI, release scripts)

### Status

Pre-Phase 1. No published releases yet. The `0.0.x` versions are scaffolding;
the first publishable release will be `0.1.0` at the close of Phase 1 Slice 1.

---

<!--
Format reminder for future releases:

## [0.1.0] - YYYY-MM-DD

### Added
- New features

### Changed
- Behavior changes (still backward-compatible during 0.x)

### Deprecated
- Features marked for removal

### Removed
- Features removed

### Fixed
- Bug fixes

### Security
- Security-relevant changes

### Breaking
- Breaking changes (expected during 0.x; bump minor; document loudly at 1.0+)

[0.1.0]: https://github.com/chipi/chemigram/releases/tag/v0.1.0
-->
