# Chemigram — Architecture

*Technical companion to `chemigram.md`. Concrete enough to write code from.*

## Design driver: agent is the only writer

Before any of the technical choices below, one fact shapes everything: Chemigram is **fully agent-driven**. The photographer never writes to the system mid-loop — the agent is the sole mutator, the photographer reads previews and gives verbal feedback. This means the architecture optimizes for *agent legibility* over *human ergonomics* in three specific ways:

| Decision | Why it follows from agent-only-writer |
|-|-|
| Isolated configdir + workspace | The agent must never touch the photographer's real catalog. Isolation is a safety boundary. |
| `apply_primitive` is SET, not ADD | The agent has no human-style undo intuition. Idempotent SET semantics keep its action space predictable. |
| Vocabulary, not slider parameters | A finite, named action space is cleaner for an agent to reason over than continuous values. Same logic as function-calling beating freeform text. |

Read the rest of the doc with this in mind: where it looks like we're picking the more constrained option, that's why.

## Discipline: darktable does the photography, Chemigram does the loop

A second design principle, equal in weight to the first:

> Chemigram contributes orchestration, vocabulary, agent loop, versioning, session capture. Every image-processing capability comes from darktable.

Concrete implications for v1:

- No Chemigram color profiles — darktable has them.
- No Chemigram lens database — Lensfun + embedded metadata, both via darktable.
- No Chemigram noise model — darktable's profiled denoise.
- No Chemigram tone curves, masks, sharpening, dehaze, clarity — darktable's modules.

The pipeline-stages abstraction (below) keeps the door open for future "secret sauce" — custom processors, GenAI tool integration — without committing to any of it now. v1 ships with a single darktable-cli stage. See `TODO.md` for what we're deliberately deferring.

## Discipline: Bring Your Own AI (BYOA)

A third design principle, equal weight:

> Chemigram doesn't ship AI capabilities; it integrates them via MCP. Maskers, evaluators, research helpers, and the photo agent itself are all photographer-configured. Chemigram is the orchestration layer.

This principle is what unifies several decisions across the architecture:

- **The photo agent (Mode A driver) is BYOA.** Photographer chooses Claude, GPT, Gemini, a local model — whatever they want, configured via MCP. Chemigram doesn't bundle an agent.
- **Maskers are BYOA.** Subject masks via SAM, prompted segmentation via SAM+GroundingDINO, custom-trained specialists, paid hosted services, or a coarse agentic fallback — all conform to a `MaskingProvider` protocol. Photographer chooses per use case via `config.toml`.
- **Mode B evaluators will be BYOA** (when Mode B exists). Reference-based perceptual similarity, vision-model self-eval, learned critics — all conform to an `EvaluatorProvider` protocol. See TODO.md.
- **Background research is BYOA.** When the agent does Wikipedia lookups for species color, it uses whatever search/research tools the photographer's configured agent has.

Concrete implications:

- **No PyTorch in Chemigram core.** No model weights bundled. No GPU/MPS configuration in the engine.
- **Every AI capability is one MCP call away.** Even when the implementation is a local model, it's wrapped behind an MCP boundary so it's pluggable.
- **Default providers are minimal.** v1 ships a coarse default masker (rectangular and gradient masks via the agent's vision capability) — enough to demonstrate the loop. Production-quality masking comes from sibling projects (`chemigram-masker-sam`, etc.) the photographer opts into.
- **Provider configuration is the photographer's domain.** Quality, speed, and cost tradeoffs are explicit choices in `config.toml`, not engine decisions.

This makes Chemigram consistently a *substrate that orchestrates AI capabilities chosen by the photographer*, not a project that ships its own AI. Same pattern as Claude Code: integration with model-of-choice rather than bundled model.

The framing also opens a path for advanced users: building specialist providers (a custom underwater-trained masker, a personal-taste-trained evaluator) without modifying Chemigram. Bring Your Own AI extends to Bring Your Own Specialist AI.

## Subsystems

Chemigram has five subsystems with stable boundaries:

1. **XMP composition engine** — read/write `.dtstyle` files, parse/synthesize XMPs, enforce SET semantics, partition by layer. Pure file operations.
2. **Render pipeline** — sequence of stages producing a JPEG from an XMP. v1 has one stage (darktable-cli). See `pipeline-stages` section below.
3. **Versioning** — content-addressed DAG of XMP snapshots, refs, HEAD, the "mini git for photos." Spec lives in `versioning.md`.
4. **AI provider layer** — pluggable maskers (and later: evaluators, generators) behind protocol-based interfaces. Per the BYOA principle. v1 ships a coarse default; sibling projects extend.
5. **MCP server** — adapts subsystems 1–4 as agent-callable tools.

The five are decoupled enough that 1, 2, 3, and 4 are testable without an agent involved, and the MCP server is a thin layer over the rest.

## What we're working with

darktable's edit state lives in an **XMP sidecar** (`photo.raw.xmp`) — RDF/XML containing a `<darktable:history>` block with one `<rdf:li>` per module application:

```xml
<rdf:li
  darktable:operation="exposure"
  darktable:enabled="1"
  darktable:modversion="5"
  darktable:params="0000000040a0093bd8ce374000004842000080c0"
  darktable:multi_name="1"
  darktable:multi_priority="0"
  darktable:blendop_version="7"
  darktable:blendop_params="gz12eJxjYGBgkGAAgRNODESDBnsIHll8ANNSGQM="/>
```

The structurally important fact: **`params` is a hex-encoded C struct** specific to the module and its `modversion`. Not JSON. Not human-editable. To programmatically set `exposure = +0.42`, you need a Python encoder that knows the exposure module's binary layout for that modversion.

`blendop_params` is gzip+base64 (the `gz12` prefix). Mask data lives there.

This single fact reshapes the whole architecture.

## Rendering is solved

`darktable-cli` is real and clean:

```
darktable-cli photo.raw photo.raw.xmp out.jpg --width 1024 \
  --apply-custom-presets false \
  --core --configdir ./chemigram-config
```

- Headless (no GUI), works for our preview loop
- `--apply-custom-presets false` is critical: prevents the user's auto-presets from contaminating the render (also lets us run multiple instances in parallel)
- Custom `--configdir` isolates Chemigram from the user's everyday darktable library
- Render time is roughly 1–3s per image at 1024px on a modern machine

This is a non-issue. The hard problem is upstream of it: **how does the agent specify what to put in the XMP?**

## Three architectures considered

### A. Hex param manipulation

Decode/encode each module's binary params struct in Python. Read the C header for the module, write a `struct.pack` / `struct.unpack` pair, version-pin to a specific modversion.

- **Control:** Maximal. Every slider, every continuous value.
- **Cost:** Per-module engineering. Schemas drift with darktable releases. Complex modules (filmic, color balance rgb) have dozens of fields including enums, arrays, masks.
- **Prior art:** `wmakeev/darkroom-xmp-tools` (Node.js) covers a handful of modules. Not Python, and intentionally narrow.
- **Verdict:** Not the MVP path. Too much code to write before the first feedback loop runs.

### B. Style vocabulary (chosen)

Pre-author a vocabulary of named single-module styles inside darktable's GUI:

- `expo_+0.0`, `expo_+0.3`, `expo_+0.5`, `expo_+0.8`, `expo_+1.2`, `expo_-0.3`, `expo_-0.5`
- `wb_underwater_warm`, `wb_underwater_neutral`, `wb_underwater_cool`
- `colorcal_uw_recover_red_strong`, `colorcal_uw_recover_red_subtle`
- `filmic_neutral`, `filmic_punchy`, `filmic_lifted_shadows`
- `tone_eq_subject_lift`, `tone_eq_water_compress`
- `denoise_low`, `denoise_medium`, `denoise_high`

Each style is a one-module history captured once in the GUI and saved as a `.dtstyle` XML. The agent composes an edit by selecting which entries to include in the XMP. Multiple styles for the same module overwrite each other (darktable's append semantics replace by module name) — so the vocabulary acts like a SET operation, not ADD.

- **Control:** Coarse but composable. Continuous values become discrete choices from a curated set.
- **Cost:** Very low code. Authoring the vocabulary is darkroom work, not programming.
- **Honest constraint:** The vocabulary is the project's "voice". A bad vocabulary makes the agent stupid; a good one makes it expressive. This is a feature — it forces the photographer to articulate what they reach for.
- **Verdict:** This is the MVP. Start here.

### C. Hybrid (later)

Vocabulary scaffolds the edit; hex encoding handles one or two modules where continuous control matters. Most likely candidate for hex: `exposure` (one float — easy) and possibly `colorbalancergb` shadows/highlights lift values.

Add this incrementally when the loop hits a clear ceiling. Not v1.

### D. Lua bridge (rejected)

w1ne's path. Recreates the Lightroom-SDK fragility we picked darktable to escape. Don't.

## The vocabulary approach in detail

### Authoring

In darktable GUI, for each desired primitive:

1. Open a representative raw on a clean history
2. Set exactly one module to the intended value (e.g. exposure +0.5 EV)
3. Save as a style with a deterministic name (`expo_+0.5`)
4. Export the style to `.dtstyle` — this is the artifact Chemigram uses

The `.dtstyle` XML contains the same hex `params` blob as XMP would. We never decode it; we just copy it into XMPs we synthesize.

### Composition

Chemigram's Python layer:

1. Reads the parsed `.dtstyle` XML for each chosen primitive — extracts the `<plugin>` entry containing `operation`, `op_params`, `enabled`, `blendop_params`, etc.
2. Synthesizes a fresh XMP for the target raw, with a `<darktable:history>` block containing the chosen entries in pipeline order
3. Sets the `<darktable:history_end>` integer correctly
4. Writes the XMP next to the raw and invokes `darktable-cli`

Pipeline order matters. darktable enforces a fixed module ordering internally — we just need to emit `iop_order` values that respect it. The `.dtstyle` files carry this info; we preserve it.

### Mask strategy

Three tiers:

1. **No mask (v1).** Most edits are global. Start here.
2. **Parametric masks (v1.5).** darktable's parametric masks work on luminance/chroma/hue ranges and serialize cleanly to `blendop_params`. Authorable as styles in the GUI like everything else. A "subject brightness mask" or "cool water mask" can be a vocabulary entry.
3. **External raster masks (v2).** darktable 5.2 added an external raster masks module that imports a PNG mask from disk. This is our AI-mask integration point: Chemigram runs Segment Anything (or similar) in Python, writes a PNG mask, and references it in the XMP. The module is documented and stable. **No Lua bridge needed** for AI masks.

Native darktable AI masks (the `FAST-SAM` work in PR #18722) are not yet shipped as of darktable 5.x. We don't depend on them.

## MCP tool surface

Grouped by subsystem. Parameter shapes concrete enough to implement.

### Vocabulary and edit operations

```
list_vocabulary(layer?, tags?) -> [{name, layer, modules_touched, tags, description, notes}]
  # Returns vocabulary entries optionally filtered by layer and/or tags.
  # modules_touched lets the agent reason about composition (which L3
  # entries replace L2 modules, which add new ones).

get_state(image_id) -> {entries: [{layer, module, primitive_name, multi_priority}], head: hash}
  # Current XMP parsed into a readable shape. Includes layer attribution
  # for each entry. head is the current snapshot hash.

apply_primitive(image_id, primitive_name) -> {state_after, snapshot_hash}
  # Apply an L3 vocabulary entry. SET semantics: same (operation, multi_priority)
  # is replaced. Auto-snapshots after applying.

remove_module(image_id, module_name) -> {state_after, snapshot_hash}
  # Drop L3 entries for this module. L1/L2 entries protected.

reset(image_id) -> {state_after, snapshot_hash}
  # Truncate to L1+L2 baseline (NOT to empty). The agent's L3 work is cleared.
```

### Rendering and comparison

```
render_preview(image_id, size=1024, ref_or_hash?) -> {jpeg_path}
  # Run pipeline (currently just darktable-cli), return preview JPEG.
  # Optional ref_or_hash to render an arbitrary snapshot, not just HEAD.

compare(image_id, hash_a, hash_b, size=1024) -> {jpeg_path}
  # Side-by-side composite of two snapshots. Critical for variant picking
  # in Mode A and reviewing branches in Mode B.

export_final(image_id, ref_or_hash?, size=None, format="jpeg") -> {output_path}
  # Full-resolution export. Defaults to HEAD; can export any tagged snapshot.
```

### Versioning (see `versioning.md`)

```
snapshot(image_id, label?) -> {hash}
  # Hash current XMP, store, advance HEAD. Optional label for the log.

checkout(image_id, ref_or_hash) -> {state}
  # Move HEAD. Detached if hash, attached if ref name.

branch(image_id, name, from?) -> {ref}
  # Create a branch at HEAD or specified hash. Doesn't switch.

log(image_id, ref?, limit=20) -> [{hash, label, parent, ops_summary, timestamp}]
  # DAG walk backward from ref or HEAD. ops_summary is human-readable
  # vocabulary primitives applied since parent.

diff(image_id, hash_a, hash_b) -> [{primitive, change}]
  # Higher-level than XML diff: vocabulary-primitive level changes.

tag(image_id, name, hash?) -> {ref}
  # Static reference; doesn't move with new snapshots. Use for export-ready
  # states ("v1_final", "instagram_crop").
```

### Local adjustments and AI masks

```
generate_mask(image_id, target, prompt?) -> {mask_id}
  # Run SAM/FAST-SAM (or configured masker) over the current preview,
  # produce a PNG raster mask, register it for use by L3 vocabulary
  # entries that reference "current_subject_mask" symbolically.
  # target: "subject" | "sky" | "background" | "custom" (with prompt)

list_masks(image_id) -> [{mask_id, target, prompt, created_at}]
  # Inspect masks generated for this image so far.
```

The mask stays around for the session and is referenced by symbolic name from vocabulary entries (`subject_lift_highlights` includes `"raster_mask: current_subject_mask"`). The XMP synthesizer resolves the symbol to the actual PNG path at render time.

### Ingestion and binding

```
ingest(raw_path, image_id?) -> {image_id, exif_summary, suggested_bindings}
  # Add a raw to the workspace. Reads EXIF, suggests L1/L2 bindings
  # based on camera+lens auto-resolution. Returns suggestions, doesn't
  # apply them.

bind_layers(image_id, l1_template?, l2_template?) -> {state_after}
  # Apply L1 and/or L2 templates to the image's baseline XMP.
  # This is the photographer's pre-loop choice, exposed via the agent
  # only as an inspection tool.
```

### Notably absent

- No catalog/library tools — Chemigram is not a DAM.
- No batch tools — per-image research, not bulk processing.
- No generic `set_module_param` — would push toward direct hex-param manipulation, which we deliberately avoided.
- No `gc` or `merge_pick` — engine-internal until there's a use case.
- No vocabulary editing tools — the agent uses vocabulary, doesn't extend it.

## Pipeline stages

The render pipeline is a sequence of stages. v1 has one stage; the abstraction admits N.

### The contract

```python
class PipelineStage(Protocol):
    name: str

    def inputs(self) -> set[str]:
        # what this stage requires from the previous stage
        # e.g. {"raw_path", "xmp_path"} or {"image_path"}
        ...

    def outputs(self) -> set[str]:
        # what this stage produces for the next stage
        ...

    def run(self, context: StageContext) -> StageResult:
        # do the work; return paths/handles to outputs
        ...
```

`StageContext` is a small struct: paths to raw, current XMP, working directory, image metadata (EXIF cached), per-stage config dict. `StageResult` returns produced artifacts (e.g. `{"image_path": "/path/to/output.jpg"}`).

The pipeline runner takes `[stage1, stage2, stage3]`, validates `stage1.outputs() ⊇ stage2.inputs()` etc., runs them in sequence, threads outputs as next inputs.

### What ships in v1

A single stage: `DarktableCliStage`.

- `inputs()`: `{"raw_path", "xmp_path"}`
- `outputs()`: `{"image_path"}`
- `run()`: invokes `darktable-cli` with the configured CLI args, returns the JPEG path.

That's it. The `PipelineStage` protocol exists but has one implementation.

### What it leaves room for

Future stages, none built in v1:

- **Local Python processors** — custom algorithms, "secret sauce". Implement `PipelineStage`, drop into pipeline config.
- **External CLIs** — RawTherapee, ART, ImageMagick. The stage shells out and returns paths.
- **GenAI tools via MCP** — upscalers, sky replacement, generative fill, denoise models. The stage calls a remote MCP tool and downloads the result.
- **Specialist sub-agents** — narrow-task agents invoked as a stage.

The architectural cost of keeping the door open: ~100 lines (the Protocol + runner + composition validation). Worth it.

The discipline is to *not* build any of these speculatively. The protocol exists so v2's external processor doesn't require redesigning the engine. v1 ships with one stage.

## EXIF auto-binding

When an image is ingested, Chemigram reads EXIF and suggests L1 and L2 bindings. This is where the engine "earns its keep" — the photographer hands Chemigram a raw and the engine has already made reasonable defaults from the image's metadata.

### What's read

- Camera body (`Make`, `Model`)
- Lens model (`LensModel` or via maker notes)
- ISO (`ISOSpeedRatings`)
- Focal length, aperture, shutter speed
- Capture timestamp
- Camera-set white balance (for Fuji especially: `FujiFilmSimulation` if present)

### Resolution rules

**For L1:** walk the user's `config.toml` bindings list, take the first match:

1. Exact: camera + lens explicit binding
2. Camera-only fallback (any lens for this body)
3. Camera-system fallback (e.g. "any Sony Alpha")
4. Nothing — image gets no L1

**For L2:** suggest, never apply silently. Suggestions in priority:

1. If `FujiFilmSimulation` EXIF tag is present and a matching L2 template exists (e.g. `fuji_acros`), suggest it — the photographer chose this look at capture, recovering it is honoring intent.
2. If a `[[layers.L2.bindings]]` entry matches camera+scene tags, suggest it.
3. Otherwise no suggestion. The photographer or agent picks.

The result is logged in the image's `metadata.json`:

```json
{
  "exif": {"camera": "X-Pro2", "lens": "XF 35mm f/2 R WR", "iso": 200, "fuji_sim": "Acros"},
  "auto_binding": {
    "l1": "fuji_xpro2_default",
    "l2_suggested": "fuji_acros",
    "l2_applied": "fuji_acros"
  }
}
```

The agent can read this state via `get_state` and inspect `metadata.json` to know what baseline it's working from.

### Why this matters

For Mode A: the photographer drops in a RAF and the agent already knows it's Acros, so the brief and feedback can refer to "within this Acros look" rather than "the look".

For Mode B: autonomous fitting against criteria can use the L1+L2 baseline as the starting state, so all exploration happens in L3 — the agent doesn't waste budget on technical correction or rediscovering the chosen look.

## Project layout (sketch)

```
chemigram/                                # source repo
  src/
    chemigram_core/
      xmp.py                              # parse + synthesize XMP
      dtstyle.py                          # parse .dtstyle into entries
      vocab.py                            # vocabulary loading + filtering
      versioning.py                       # objects, refs, log, DAG operations
      pipeline.py                         # PipelineStage protocol + runner
      stages/
        darktable_cli.py                  # the v1 stage
      bind.py                             # EXIF auto-binding
      mask.py                             # raster mask registry + SAM integration
    chemigram_mcp/
      server.py                           # MCP tool definitions, ~thin layer
  tests/
  pyproject.toml

chemigram-vocabulary/                     # bundled content (separate repo or directory)
  layers/
    L1/                                   # opt-in templates
    L2/
      neutralizing/
      film_sims/
    L3/
  profiles/                               # ICC, LUTs, basecurves (extensibility hook)
  manifest.json
  ATTRIBUTION.md

~/Pictures/Chemigram/                     # user data (per `versioning.md`)
  <image_id>/
    raw/                                  # symlink
    objects/                              # snapshot store
    refs/                                 # branches, tags, HEAD
    log.jsonl
    previews/                             # cache
    sessions/
    metadata.json
    current.xmp                           # synthesized for darktable-cli to read

~/.chemigram/                             # software state
  config.toml                             # storage roots, vocab sources, bindings
  community-packs/                        # opt-in vocabulary packs
  dt-configdir/                           # isolated darktable configdir
  logs/
```

Single Python process, no daemon, no IPC between subsystems. Each `render_preview` spawns a `darktable-cli` subprocess (the v1 pipeline stage). State is the filesystem.

## Implementation phases

### Phase 0: feasibility (a few hours)

- Install darktable, build a minimal vocabulary by hand: 3 exposure presets, 2 white balance presets, 1 filmic
- Manually compose an XMP from the `.dtstyle` files, run `darktable-cli`, confirm the rendered JPEG looks correct
- This validates that the vocabulary-composition approach actually works before any Python code is written

### Phase 1: minimum viable loop (a weekend)

- Python that reads `.dtstyle`, synthesizes XMP, calls `darktable-cli`, returns a JPEG path
- MCP server with the eight tools above
- Vocabulary of ~20 entries: exposure (5), color calibration WB (4), color calibration channel mixer for underwater (4), filmic (3), tone equalizer (2), denoise (2)
- One real image, one real conversation. See if the loop converges.

### Phase 2: vocabulary expansion (a week, intermittent)

- Grow the vocabulary based on what the loop kept reaching for and not finding
- This is darkroom work, not coding. The agent's failures tell you what to author.

### Phase 3: parametric masks in vocabulary (when needed)

- Add masked variants: `expo_+0.5_subject_only`, `wb_warm_water_only`
- Each is a vocabulary entry where the underlying style includes a parametric mask captured in the GUI

### Phase 4: AI masks via external raster module (if needed)

- Python-side SAM or FAST-SAM, writes PNG mask to disk
- New tool `generate_subject_mask(image_id) -> mask_id`
- Existing primitives can reference an external mask via a new vocabulary axis

### Phase 5: hex encoder for one continuous parameter (if needed)

- Likely candidate: `exposure` — single float, modversion stable
- Adds tool `set_exposure(image_id, ev: float)`
- Only do this when the discrete vocabulary becomes a real bottleneck for taste expression

## Resolved questions (closing the loop)

These were open in the first draft. Research has closed them.

### Q: `--style` chaining vs. writing XMP ourselves?

**Resolved: write XMP ourselves.** `darktable-cli` accepts only one `--style` flag per invocation, and the agent needs to compose multiple primitives per render. We don't use `--style` at all. The CLI gets `darktable-cli photo.raw photo.xmp out.jpg`. We construct the XMP from `.dtstyle` source files in Python.

### Q: iop_order — preserve from source dtstyle?

**Resolved: yes, preserve as-is.** Three facts settle this:

- darktable applies modules in fixed pipeline order regardless of history-stack order. The order of `<rdf:li>` entries in the XMP doesn't affect the rendered output.
- The stable key for mapping history → pipeline position is `(operation, multi_priority)`, not iop_order.
- darktable 5.x defaults to module order v5.0. As long as our entire vocabulary is captured against darktable 5.x with v5.0 ordering (which is the default — no special action needed), iop_order values are consistent across `.dtstyle` files and we can copy them into the XMP unchanged.

### Q: `--apply-custom-presets`?

**Resolved: `false`.** This flag only disables the loading of user-defined auto-apply presets from `data.db`. Mandatory pipeline modules (demosaic, input/output color profile, etc.) are added regardless — they're not "presets" in this sense. Setting `false` gives a clean reproducible pipeline and enables running multiple `darktable-cli` instances in parallel. With our isolated empty configdir, there are no custom presets anyway, but `false` is good belt-and-suspenders.

### Q: same-module collisions with second-wins semantics?

**Resolved: handle in our XMP synthesis layer, not via darktable.** When the agent calls `apply_primitive(image, "expo_+0.5")` on an image that already has an `expo_+0.3` entry:

1. Parse the existing XMP
2. Look up entries with matching `(operation, multi_priority)` — there'll be one for "exposure", `multi_priority=0`
3. Replace its `op_params`, `enabled`, `blendop_params`, `blendop_version`, `multi_name`, `iop_order` with the values from the new `.dtstyle`
4. Re-emit the XMP

This is all XML editing — no hex param decoding required. The only extra bookkeeping is renumbering the `darktable:num` indices and updating `<darktable:history_end>`.

## Concrete data formats (now known)

### `.dtstyle` schema

```xml
<darktable_style version="1.0">
  <info>
    <name>expo_+0.5</name>
    <description>Single-module exposure +0.5 EV primitive for Chemigram</description>
    <iop_list>rawprepare,0,invert,0,temperature,0,...</iop_list>
  </info>
  <style>
    <plugin>
      <num>1</num>
      <module>5</module>                       <!-- modversion -->
      <operation>exposure</operation>
      <op_params>0000000040a0093bd8ce374000004842000080c0</op_params>
      <enabled>1</enabled>
      <blendop_params>gz12eJxjYGBgkGAAgRNODESDBnsIHll8ANNSGQM=</blendop_params>
      <blendop_version>11</blendop_version>
      <multi_priority>0</multi_priority>
      <multi_name></multi_name>
      <multi_name_hand_edited>0</multi_name_hand_edited>
      <iop_order>47,474747</iop_order>
    </plugin>
  </style>
</darktable_style>
```

Notes on the param formats encountered in the wild:

- `op_params` is either **plain hex** (`00000000...`) or **gzip+base64** with a `gz0X` prefix where X is the compression-version byte. We don't decode either — just shuffle them as opaque strings.
- `blendop_params` is always gzip+base64 with `gz1X` prefix (different compression family).
- `<module>N</module>` is the modversion of the *module's* parameter struct. Stable within a darktable major release; can change across releases.

### Mapping `.dtstyle` → XMP `<rdf:li>`

Each `<plugin>` element becomes one `<rdf:li>` with attribute mapping:

| dtstyle element | XMP attribute |
|-|-|
| `<operation>` | `darktable:operation` |
| `<enabled>` | `darktable:enabled` |
| `<module>` | `darktable:modversion` |
| `<op_params>` | `darktable:params` |
| `<blendop_params>` | `darktable:blendop_params` |
| `<blendop_version>` | `darktable:blendop_version` |
| `<multi_priority>` | `darktable:multi_priority` |
| `<multi_name>` | `darktable:multi_name` |
| `<iop_order>` | `darktable:iop_order` |

`darktable:num` is renumbered per-XMP (sequential across the history stack).

### macOS Apple Silicon notes

- darktable has been native arm64 since 4.4.2. Use the official arm64 build from darktable.org, not Rosetta-translated x86_64.
- OpenCL on Apple Silicon: works via Apple's deprecated-but-functional OpenCL stack. darktable will use it for GPU acceleration of expensive modules (denoise, local contrast, diffuse).
- Realistic render times: 1024px preview ~1–3s, full-res export ~3–8s on M-series. Acceptable for the loop.
- Apple does not support Metal in darktable. Don't expect that.
- darktable 5.x ships with reasonable Apple Silicon performance; no special build flags needed.

## Concrete `darktable-cli` invocation

```
darktable-cli \
  /workspace/<image_id>/original.raw \
  /workspace/<image_id>/current.xmp \
  /workspace/<image_id>/previews/step_NNN.jpg \
  --width 1024 \
  --height 1024 \
  --hq false \
  --apply-custom-presets false \
  --core --configdir /chemigram/chemigram-config
```

`--hq false` for previews (faster resampling, fine for a 1024px JPEG). Use `--hq true` for `export_final`.

The `chemigram-config` directory is created once, empty except for whatever `library.db` darktable needs to bootstrap. We never touch the user's `~/.config/darktable`.

## Phase 0 plan (now concrete)

A single evening's work to validate end-to-end before any Python:

1. Install darktable 5.x arm64 from the official release.
2. Open one La Ventana raw in an isolated configdir: `/Applications/darktable.app/Contents/MacOS/darktable --core --configdir /tmp/chemigram-test`
3. Set exposure to +0.5, save as style `expo_+0.5`. Reset history. Set color calibration to a warm-water-recovery setting, save as `wb_warm`. Reset.
4. Export both styles to `.dtstyle` files via the styles panel.
5. By hand (text editor), assemble an XMP from a fresh-import baseline, append the two `<rdf:li>` entries derived from the `.dtstyle` plugin entries.
6. Run the `darktable-cli` invocation above. Confirm the JPEG looks like a +0.5 EV warm-WB version of the input.
7. Bonus: do step 5 twice with two different `expo_*` styles in the XMP, confirm second-wins (or that the wrong one wins — if so, our composition logic needs to enforce it explicitly).

Step 7 is the critical test. It validates the composition story end-to-end before any Python.

If step 7 reveals that darktable doesn't actually do second-wins for same-module entries with the same `multi_priority`, we'll need to handle the deduplication ourselves — find and replace the existing entry rather than append. That's still cheap, but worth knowing before Phase 1.

## Known risks (things that could still bite Phase 1)

Honest list of failure modes the resolved questions don't fully eliminate:

- **modversion drift across darktable releases.** When darktable bumps a module's modversion, our captured `.dtstyle` files become invalid for that module. Mitigation: pin Chemigram to a specific darktable version (start with whatever 5.x stable is current at Phase 0). Document the version in the repo. Re-capture vocabulary on upgrade. Acceptable cost for a research project.
- **The `(operation, multi_priority)` collision assumption.** Phase 0 step 7 specifically tests this. If darktable's append semantics don't behave as the docs suggest for our composition pattern, we handle dedup ourselves — also cheap.
- **`iop_list` mismatch in `<info>`.** Newer dtstyle files include a full module-order list in `<info><iop_list>`. If our composed XMP needs a unified iop_list and the captured ones disagree, we need a merge strategy. Hopefully irrelevant since we're using the v5.0 default order across all captures, but worth verifying in Phase 0.
- **Apple Silicon OpenCL flakiness.** Apple's deprecated OpenCL stack occasionally regresses with macOS updates. Fallback is CPU rendering, which is slower but still works. Not a blocker.
- **Self-imposed vocabulary blind spots.** The vocabulary IS the action space. If we forget to author entries the agent needs, it fails silently — picking the closest available primitive rather than telling us "I want to do X but can't." Mitigation: explicit "I want X but I don't see a primitive for it" output convention in the agent's prompts.

### Pinned versions

- darktable: 5.x stable (whatever ships at Phase 0)
- Module order: v5.0 (default, do not change)
- macOS: 14+ on Apple Silicon
- Python: 3.11+

## Why this is the right architecture for Chemigram specifically

Chemigram is a **research project about taste transmission**, not a production tool. The vocabulary approach is well-matched to that goal in a way that pure parametric control isn't:

- It forces the photographer to articulate the moves they actually make. Authoring `colorcal_uw_recover_red_subtle` is itself a craft act and a research artifact.
- It gives the agent a meaningful, finite action space — closer to how a human apprentice would learn (here are the moves I make; pick one) than to a slider-tweaking optimizer.
- The vocabulary is editable, inspectable, versionable. After a session you can look at what the agent reached for and decide whether your vocabulary captured your taste correctly.

If we'd picked Architecture A, we'd be spending the project on encoder engineering and the research question would be subordinate to the plumbing. With B, the plumbing is small and the vocabulary becomes the locus of the experiment.
