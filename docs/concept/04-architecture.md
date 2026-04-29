# 04 — Technical Architecture

*How Chemigram is built. Decisions with rationale, alternatives considered, locked commitments, and the open questions that become Phase 2 RFCs.*

This document covers the engine's architecture in full: design principles, subsystems, the layer model, versioning, local adjustments, the MCP tool surface, and pipeline stages. Open questions are consolidated in the final section as the input to Phase 2 RFC work.

---

## 1. Design principles

Three load-bearing disciplines, equal in weight. Each constrains the project's scope; together they make the project tractable.

### 1.1 Agent is the only writer

The photographer reads previews and gives feedback; the agent is the sole mutator of edit state. This propagates through the architecture in three specific ways:

| Decision | Why it follows |
|-|-|
| Isolated configdir + workspace | The agent must never touch the photographer's real catalog. Isolation is a safety boundary. |
| `apply_primitive` is SET, not ADD | The agent has no human-style undo intuition. Idempotent SET semantics keep its action space predictable. |
| Vocabulary, not slider parameters | A finite, named action space is cleaner for agent reasoning than continuous values. Same logic as why function-calling beats freeform text for tool use. |

Where the architecture looks like it's picking the more constrained option, this is why.

### 1.2 darktable does the photography, Chemigram does the loop

> Chemigram contributes orchestration, vocabulary, agent loop, versioning, session capture. Every image-processing capability comes from darktable.

Concrete implications for v1:

- No Chemigram color profiles — darktable has them.
- No Chemigram lens database — Lensfun + embedded metadata, both via darktable.
- No Chemigram noise model — darktable's profiled denoise.
- No Chemigram tone curves, masks, sharpening, dehaze, clarity — darktable's modules.

The pipeline-stages abstraction (/8) keeps the door open for future custom processors without committing to any of it now. v1 ships with a single darktable-cli stage.

### 1.3 Bring Your Own AI (BYOA)

> Chemigram doesn't ship AI capabilities; it integrates them via MCP. Maskers, evaluators, the photo agent itself are all photographer-configured. Chemigram is the orchestration layer.

Concrete implications:

- **No PyTorch in Chemigram core.** No model weights bundled. No GPU/MPS configuration in the engine.
- **Every AI capability is one MCP call away.** Even when the implementation is a local model, it's wrapped behind an MCP boundary so it's pluggable.
- **Default providers are minimal.** v1 ships a coarse default masker (rectangular and gradient masks via the agent's vision capability). Production-quality masking comes from sibling projects the photographer opts into.
- **Provider configuration is the photographer's domain.** Quality, speed, and cost tradeoffs are explicit choices in `config.toml`, not engine decisions.

This makes Chemigram consistently a substrate that orchestrates AI capabilities chosen by the photographer, not a project that ships its own AI.

---

## 2. Subsystems

Chemigram has five subsystems with stable boundaries:

| # | Subsystem | Responsibility |
|-|-|-|
| 1 | **XMP composition engine** | Read/write `.dtstyle` files, parse/synthesize XMPs, enforce SET semantics, partition by layer. Pure file operations. |
| 2 | **Render pipeline** | Sequence of stages producing a JPEG from an XMP. v1 has one stage (darktable-cli). See/8. |
| 3 | **Versioning** | Content-addressed DAG of XMP snapshots, refs, HEAD. The "mini git for photos." See/7. |
| 4 | **AI provider layer** | Pluggable maskers (and later: evaluators, generators) behind protocol-based interfaces. Per BYOA. |
| 5 | **MCP server** | Adapts subsystems 1-4 as agent-callable tools. |

The five are decoupled enough that 1-4 are testable without an agent involved, and the MCP server is a thin layer over the rest.

The **masking component** (subsystem 4 — AI provider layer) shipped in v0.4.0 (`chemigram.core.masking`). The `MaskingProvider` Protocol (ADR-057) is the contract every masker implements. The bundled default is `CoarseAgentProvider` (ADR-058): it asks the calling agent (e.g., Claude with vision) for a region descriptor via MCP sampling, then rasterizes the descriptor to a grayscale PNG via Pillow. No PyTorch in core. Production-quality masking lives in the sibling `chemigram-masker-sam` project (Phase 4) and implements the same Protocol — substituting providers is a one-line `build_server(masker=...)` change.

The **context component** (`chemigram.core.context`, shipped in v0.5.0) loads the agent's first-turn information per RFC-011 → ADR-059: tastes (multi-scope per ADR-048 — `~/.chemigram/tastes/_default.md` plus brief-declared genre files), `brief.md` (with `Tastes:` declaration), `notes.md` (with line-truncation summarization for long files), recent log entries, recent vocabulary gaps. All loaders tolerate missing files. Conflicts (same line in two genre files) surface to the agent for mediation, not auto-resolved by the engine. The companion **session component** (`chemigram.core.session`) writes JSONL transcripts per ADR-029 — one record per tool call, proposal, and confirmation; closed with a footer summary. The MCP server's tool dispatch auto-records when `build_server(transcript=...)` is configured. Vocabulary-gap records follow the full RFC-013 → ADR-060 schema (session_id and snapshot_hash auto-populate). End-of-session synthesis is agent-orchestrated per ADR-061 (no engine `end_session` tool); the agent uses existing tools (`propose_*`, `log_vocabulary_gap`, `tag`, `snapshot`) to wrap up.

The **MCP component** (subsystem 5) is implemented in `chemigram.mcp` and shipped in v0.3.0. It boots the official `mcp` SDK over stdio, loads vocabulary + prompts at startup, and dispatches every tool through a small registry (`chemigram.mcp.registry`). Tools return structured `ToolResult` payloads — `{success, data, error}` with a closed `ErrorCode` enum — so agents can branch on category without parsing messages. Tool implementations live under `chemigram.mcp.tools.*` (vocab/edit, versioning, rendering, ingest, masks, context stubs); they're thin wrappers around `chemigram.core` plus the workspace registry. ADR-056 (closing RFC-010) locks the parameter shapes and error contract.

The **prompt system** (`chemigram.mcp.prompts`, also v0.3.0) is the agent's pre-loaded operating manual. Templates live as Jinja2 files at `<task>_v<N>.j2`; `MANIFEST.toml` declares which version is active per task. The MCP server renders the active version of `mode_a/system` at session start and provides it to the agent as the system prompt. Versions are append-only — once `system_v1.j2` ships, new iterations land alongside as `system_v2.j2`, `system_v3.j2`, etc., independent of package SemVer. ADR-043/044/045 cover the design; RFC-016 closes with the v0.3.0 implementation.

The **workspace orchestrator** (`chemigram.core.workspace.Workspace`) is the runtime handle for one image. `Workspace.ingest_workspace(raw_path, …)` symlinks the raw, reads EXIF, runs the L1 binding lookup, builds a baseline XMP, snapshots it, tags `baseline`, and returns a `Workspace` ready for the rest of the tools to operate on. The MCP server's tool context carries a per-session `dict[str, Workspace]` keyed by `image_id` — `ingest` populates it, every other tool reads from it. The directory layout under each workspace follows `TA/contracts/per-image-repo`.

---

## 3. The XMP foundation

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

The structurally important fact: **`params` is a hex-encoded C struct** specific to the module and its `modversion`. Not JSON. Not human-editable. To programmatically set `exposure = +0.42`, you'd need a Python encoder that knows the exposure module's binary layout for that modversion.

`blendop_params` is gzip+base64 (`gz12` prefix). Mask data lives there.

**This single fact reshapes the architecture.** We do not decode hex blobs. Instead, we use the **vocabulary approach** (/4): pre-author single-module styles in darktable's GUI, save as `.dtstyle` files, and copy the hex blobs verbatim from `.dtstyle` into XMPs we synthesize.

### 3.1 The `.dtstyle` schema

```xml
<darktable_style version="1.0">
  <info>
    <n>expo_+0.5</n>
    <description>Single-module exposure +0.5 EV primitive for Chemigram</description>
    <iop_list>rawprepare,0,invert,0,temperature,0,...</iop_list>
  </info>
  <style>
    <plugin>
      <num>1</num>
      <module>5</module>
      <operation>exposure</operation>
      <op_params>0000000040a0093bd8ce374000004842000080c0</op_params>
      <enabled>1</enabled>
      <blendop_params>gz12eJxjYGBgkGAAgRNODESDBnsIHll8ANNSGQM=</blendop_params>
      <blendop_version>11</blendop_version>
      <multi_priority>0</multi_priority>
      <multi_name></multi_name>
      <iop_order>47,474747</iop_order>
    </plugin>
  </style>
</darktable_style>
```

**Note on `<iop_list>`:** Phase 0 testing (darktable 5.4.1) showed that `<iop_list>` is **only present in multi-module style exports**. Clean single-module dtstyles (the canonical vocabulary form) omit the element entirely. The example above shows it for completeness; in practice most vocabulary files won't have it. Parsers must treat it as optional.

**Authoring discipline:** When creating a vocabulary primitive in darktable's GUI, the create-style dialog presents an "include modules" checklist of every module in the active pipeline. The default is "all checked" — accepting the default produces a noisy 12-14 module dtstyle file that includes darktable's `_builtin_*` defaults (scene-referred default exposure, sigmoid, channelmixerrgb; auto flip; full L0 stack: rawprepare, demosaic, colorin, colorout, gamma, etc.). To author a clean single-module primitive, **explicitly uncheck every module except the target operation** before clicking create. The export will then contain just one `<plugin>` entry. See `CONTRIBUTING.md`/Vocabulary contributions for the full authoring procedure.

### 3.2 Mapping `.dtstyle` → XMP

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

`darktable:num` is renumbered per-XMP (sequential across the history stack). `<darktable:history_end>` is set to the new entry count.

### 3.3 SET semantics

The synthesizer has two paths depending on whether the target module already exists in the XMP history:

**Path A — Replace (the common case).** When applying a vocabulary entry whose `operation` and `multi_priority` match an existing history entry:

1. Parse the existing XMP
2. Look up entries with matching `(operation, multi_priority)` — typically there's one (e.g., `exposure` at `multi_priority=0`)
3. Replace its `op_params`, `enabled`, `blendop_params`, `blendop_version`, `multi_name` (set to empty string for user-authored entries) with values from the new `.dtstyle`
4. **Keep the existing `darktable:num` and do NOT supply iop_order** — the replacement inherits the pipeline position of the entry it replaces
5. Update `<darktable:history_end>` if no count change

This is the dominant path because most vocabulary entries replace darktable's auto-applied `_builtin_*` defaults (scene-referred default exposure, channelmixerrgb, sigmoid, etc.) at `multi_priority=0`.

**Path B — Add new instance.** When applying a vocabulary entry whose `(operation, multi_priority)` doesn't match any existing entry (e.g., adding a second exposure instance for layered effect, or adding a module that isn't in the baseline pipeline like a drawn-mask gradient):

1. Append a new `<rdf:li>` with the next available `darktable:num`
2. **Must supply `darktable:iop_order`** — copy from the source `.dtstyle` file's `<iop_order>` element (note: `.dtstyle` uses comma as decimal separator due to locale; XMP requires period: `47,474747` → `47.474747`)
3. If iop_order isn't supplied, darktable emits `cannot get iop-order for <operation> instance N` and silently drops the entry
4. Increment `<darktable:history_end>`

**Why two paths.** Phase 0 testing established that darktable's pipeline position for new instances must be explicit, but for replacements the existing position is preserved. The two paths reflect this:
- Path A is simpler (no iop_order math) and covers most vocabulary applications
- Path B is necessary for additive moves (multi-instance modules, modules not in baseline)

This is all XML editing — no hex param decoding. Gives clean SET semantics without fighting darktable's append behavior.

---

## 4. The vocabulary approach

Three architectures were considered for how the agent specifies edits:

### 4.1 Architecture A — hex param manipulation (rejected for v1)

Decode/encode each module's binary params struct in Python. Per-module engineering. Schemas drift with darktable releases. Complex modules (filmic, color balance rgb) have dozens of fields including enums, arrays, masks. Not the MVP path — too much code before the first feedback loop runs.

### 4.2 Architecture B — vocabulary (chosen)

Pre-author named single-module styles in darktable's GUI:

- `expo_+0.0`, `expo_+0.3`, `expo_+0.5`, `expo_+0.8`, `expo_-0.3`, `expo_-0.5`
- `wb_underwater_warm`, `wb_underwater_neutral`, `wb_underwater_cool`
- `colorcal_uw_recover_red_strong`, `colorcal_uw_recover_red_subtle`
- `filmic_neutral`, `filmic_punchy`, `filmic_lifted_shadows`
- `tone_eq_subject_lift`, `tone_eq_water_compress`
- `denoise_low`, `denoise_medium`, `denoise_high`

Each is a one-module history captured once in the GUI and saved as a `.dtstyle` XML. The agent composes an edit by selecting which entries to include in the XMP. SET semantics on `(operation, multi_priority)` make multiple primitives composable.

The vocabulary becomes the project's **voice**. Bad vocabulary makes the agent stupid; good vocabulary makes it expressive. This is a feature — it forces the photographer to articulate what they reach for. The vocabulary itself is a research artifact.

**Authoring caveats discovered in Phase 0** (darktable 5.4.1):

- The create-style dialog's "include modules" checkboxes do filter what gets serialized — but only when explicitly used. Default behavior produces a noisy 12-14 module dtstyle. See `CONTRIBUTING.md`/Vocabulary contributions.
- Some moves naturally touch multiple coupled modules. WB adjustment with the modern scene-referred pipeline updates both `temperature` (white balance module) AND `channelmixerrgb` (color calibration). To author single-module WB primitives, color calibration must be disabled before adjusting WB. Vocabulary primitives that touch multiple coupled modules are valid (and supported by manifest's `touches: [...]` list); the choice is whether to capture the coupling or decouple it.
- darktable's GUI cannot author literal-zero values for some sliders (exposure has minimum granularity ~0.009 EV). For true no-op primitives, programmatic generation is required — see `docs/TODO.md` Path C.

### 4.3 Architecture C — Lua bridge (rejected)

The path `darktable-mcp` (w1ne) takes — Python bridge to a running darktable via Lua API. Recreates the Lightroom-SDK fragility we picked darktable to escape. App must stay open and focused. Don't.

### 4.4 Verdict

**Vocabulary (B) is v1.** Hex manipulation (A) reserved as a future path for high-value modules where continuous control matters; tracked in `docs/TODO.md`. **Phase 0 testing demonstrated hex op_params manipulation is feasible for exposure** (one float at predictable byte offset), validating Path A as a low-cost enrichment when needed rather than a deferred research bet.

---

## 5. Layer model

Edits stack in three layers. The layer model separates *who authors what when*. The discipline that limits the model to three: **layers separate authorship moments, not editing moves.**

| Layer | What | Authored by | Cadence | Mutable in loop? | Default |
|-|-|-|-|-|-|
| **L0** | darktable internals (rawprepare, demosaic, color profiles) | darktable | Always-on | No | Always present |
| **L1** | Technical correction (lens, profiled denoise, hot pixels) | Photographer, per-camera+lens | Once per binding | No | **Empty by default — opt-in** |
| **L2** | Look establishment (baseline exposure, view transform, color cast recovery, *or* a film simulation) | Photographer, per-image | Once per image | No | Optional — chosen template or none |
| **L3** | Taste (vocabulary primitives) | Agent | Continuous | Yes | Always — the loop |

### 5.1 L1 is empty by default

A photographer shooting fisheye doesn't want lens correction. A photographer shooting clean low-ISO doesn't want denoise. So L1 is never assumed-on. The photographer opts in via per-camera+lens bindings in `config.toml`:

```toml
[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Nikkor 24-70mm f/2.8E ED VR"
template = "lens_correct_full + denoise_auto"

[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Fisheye Nikkor 8-15mm f/3.5-4.5E ED"
template = "denoise_auto"   # NO lens correction — preserve fisheye projection
```

Templates available in starter vocabulary:

- `lens_correct_full` — lens module on, auto-method (Lensfun or embedded metadata), all corrections
- `lens_correct_distortion_only` — TCA + distortion, no vignetting
- `denoise_auto` — profiled denoise with database lookup
- `chromatic_aberration_only` — for vintage glass

Auto-resolution by EXIF: exact match (camera+lens), then camera-only fallback, then nothing.

### 5.2 L2 has two flavors

- **Neutralizing L2** (`underwater_pelagic_blue`, `topside_neutral`) — recovers raw murk to a sane working state. Most of the look is L3.
- **Look-committed L2** (Fuji film simulations, etc.) — already commits to a look. The agent's L3 work refines *within* it.

Both are L2 because both are pre-agent, photographer-set baselines. They differ only in how much taste they pre-commit. Worked example with Fuji X-Pro2 + Acros: when the photographer shot Acros, applying `fuji_acros` as L2 *recovers the intent they had at capture*, not making a fresh creative choice now.

L2 templates are unrestricted across bodies — a `fuji_acros` template applied to a Sony A1 produces a spirit-of-Acros result. The honest caveat ("calibrated to Fuji X-Trans, on other sensors expect spirit not exact match") lands in vocabulary metadata, not enforcement.

### 5.3 The baseline XMP

Each image enters the loop with a pre-baked XMP. The history stack is partitioned:

```
[ L1 entries ][ L2 entries ][ L3 entries ]
              ^             ^
              |             baseline_end
              technical_end
```

Two integers stored in sidecar metadata mark the boundaries. `apply_primitive`, `remove_module`, and `reset` only touch the L3 segment. L1 and L2 entries are read-only mid-session.

`reset(image_id)` does *not* go to empty history — it goes to `baseline_end`. That's the floor the agent works from.

### 5.4 Vocabulary metadata

Each entry's manifest declares which modules it touches:

| Entry | Layer | Touches |
|-|-|-|
| `fuji_acros` | L2 | `tonecurve`, `channelmixerrgb`, `colorlookuptable`, `monochrome` |
| `tone_lifted_shadows` | L3 | `tonecurve` |
| `warm_highlights` | L3 | `colorbalancergb` |
| `acros_red_filter` | L3 | `channelmixerrgb` |

The agent reasons over this metadata. *"I'm modifying Acros's tonecurve. Acros's character also comes from `channelmixerrgb` and `colorlookuptable`, which I'm leaving intact."* Without it, the agent has no way to predict whether an L3 move preserves or breaks the L2 look.

### 5.5 Color science extensibility hook

L1 and L2 templates can reference custom assets via relative paths into `chemigram-vocabulary/profiles/`:

- `.icc` files (custom input color profiles, e.g. extracted from Capture NX)
- `.cube` files (3D LUTs)
- Basecurve presets

The XMP synthesizer copies the path into the relevant module config; darktable reads the asset at render time. Empty in v1; documented for future use including potential per-sensor color-science fitting (see `docs/TODO.md`).

---

## 6. Local adjustments

Local adjustments — masked, spatial, content-aware — are where Chemigram's value concretizes. Global moves are tractable in any vocabulary system. Local moves are where intent ("warm the highlights on the fish") translates to vocabulary + masking automatically.

### 6.1 Two kinds of "local"

- **Spatially local** (masked) — effect applies in a bounded region. Uses parametric, drawn, or external raster masks. This section.
- **Parametrically local** (zone/frequency/hue-based) — effect applies everywhere differently. Tone equalizer (zones), contrast equalizer (frequencies), color equalizer (hues). Lives in regular L3 vocabulary alongside global moves.

### 6.2 Three-layer mask pattern

| Layer | Mechanism | When |
|-|-|-|
| **1** | Pre-baked mask in `.dtstyle` (parametric or drawn) | Most masked vocabulary. Photographer authored once in GUI; frozen. |
| **2** | AI raster mask + symbolic reference | Content-aware isolation. Agent generates mask via provider, registers, vocabulary entry references it symbolically. |
| **3** | Agent-described composite masks | *Not in v1.* Compositional mask operations (intersect, dilate, refine). |

Layer 1 examples: `gradient_top_dampen_highlights`, `vignette_subtle`, `parametric_warm_only_highlights`.

Layer 2 examples: `tone_lifted_shadows_subject`, `warm_highlights_subject`, `dampen_sky`, `sharpening_subject`.

### 6.3 Mask registry subsystem

```
~/Pictures/Chemigram/<image_id>/
  masks/
    current_subject_mask.png       # most recent subject mask
    current_sky_mask.png
    fish_2024_pelagic.png          # named persistent mask
    registry.json                  # metadata
```

Registry entry:

```json
{
  "name": "current_subject_mask",
  "path": "masks/current_subject_mask.png",
  "target": "subject",
  "prompt": null,
  "generator": "sam-mcp",
  "generator_config": { "model": "sam2_hiera_b" },
  "generated_from_render_hash": "a3f291...",
  "created_at": "2026-04-27T15:23:11Z"
}
```

Lifecycle:

- **Generation**: agent calls `generate_mask(image, target, prompt?)`. Engine runs configured provider over current preview render, saves PNG, registers under name.
- **Reference**: vocabulary entries with `mask_kind: "raster"` declare `mask_ref: "current_subject_mask"`. Engine resolves to actual PNG path at XMP synthesis time.
- **Reuse**: same mask referenced by multiple vocabulary applications. Generate once, apply many.
- **Invalidation**: photographer regenerates, or new mask of same target overwrites `current_<target>`, or persistent custom-named masks survive.
- **Persistence**: masks are part of edit state — versioned with snapshots (/7).

### 6.4 Masking providers (BYOA)

```python
class MaskingProvider(Protocol):
    name: str

    def generate(
        self,
        image_path: str,
        target: str,                    # "subject" | "sky" | "background" | "custom"
        prompt: str | None = None,
        hints: dict | None = None,
    ) -> MaskResult:
        ...

class MaskResult:
    mask_png_path: str
    confidence: float
    description: str
    refinement_options: list[str]
```

Provider categories:

- **Coarse agentic provider (bundled default)** — uses the photo agent's vision capability. Bbox/gradient/color-region masks. No PyTorch dependency. Sufficient for many cases, especially Layer 1 vocabulary that uses pre-baked masks.
- **`chemigram-masker-sam` sibling project** — standalone MCP server wrapping SAM/MobileSAM. Local install with PyTorch + MPS. Pixel-precise. **Recommended for production-quality.**
- **Hosted services** — Replicate, Modal, etc. via MCP. Pay per call.
- **Custom photographer-trained specialists** — fine-tuned models exposed as MCP. Real path for advanced users.

Per-target overrides in `config.toml`:

```toml
[masking]
default_provider = "sam-mcp"

[masking.targets]
subject = "sam-mcp"
iguana_eyes = "replicate-sam"        # higher quality for fine work
sky = "coarse-agent"                 # gradient is fine for sky
```

---

## 7. Versioning

Each image is a **content-addressed DAG of XMP snapshots** with refs (branches, tags) and a HEAD pointer. "Mini git for photos."

### 7.1 Why this exists

darktable has linear edit history with `<darktable:history_end>` as a pointer. No branches, no named states, no comparison across alternatives. For Mode A (collaborative), this is mildly limiting — you mostly want linear undo. For Mode B (autonomous), it's structurally inadequate — autonomous exploration produces a tree of variants, not a sequence.

### 7.2 Repo structure

```
~/Pictures/Chemigram/<image_id>/
  raw/
    DSCF1234.RAF                     # symlink to original raw
  brief.md
  notes.md
  metadata.json
  current.xmp                        # synthesized, what darktable-cli reads
  objects/                           # content-addressed snapshot store
    a3/f291d2e8b....xmp
    b7/1204a99c1....xmp
    c0/8815f3b22....xmp
  refs/
    heads/
      main                           # text file: c08815f3b22...
      explore_warm                   # text file: b71204a99c1...
    tags/
      v1_export
      instagram_crop
    HEAD                             # text file: ref: refs/heads/main
  log.jsonl                          # append-only operation log
  previews/                          # JPEG cache, regenerable
  sessions/                          # transcripts
  masks/                             # mask registry
  vocabulary_gaps.jsonl              # gaps surfaced this image
```

Cloned-from-git mental model: SHA-256 content addressing, `refs/heads/`, `refs/tags/`, `HEAD` pointer. Inspectable with `cat` and `grep`.

### 7.3 Operations

Engine API:

```
snapshot(image, label?, parent=HEAD) → hash
checkout(image, ref_or_hash) → state
branch(image, name, from=HEAD) → ref
switch(image, ref) → state
log(image, ref=HEAD, limit=20) → list of {hash, label, parent, ops_summary}
diff(image, hash_a, hash_b) → list of vocabulary primitive changes
merge_pick(image, source_hash, primitives) → new hash on current branch
tag(image, hash, name) → ref
gc(image) → freed_bytes
```

MCP-exposed subset (the agent-visible tools): `snapshot`, `checkout`, `branch`, `log`, `diff`, `tag`. Engine-internal: `gc`, `merge_pick`. Keep agent surface narrow.

### 7.4 Mask integration

When a snapshot is committed, masks referenced by the XMP are versioned with it. Two storage options under consideration:

**Option A:** Mask PNGs stored alongside XMP in object store, both content-addressed:

```
objects/
  a3/f291...xmp                    # snapshot XMP
  d8/12fa....png                   # content-addressed mask PNG
```

XMP at this snapshot symbolically references `current_subject_mask`; snapshot metadata maps that symbol to `d812fa...png`.

**Option B:** Masks stored under per-snapshot subdirectories.

Option A wins on dedup (identical masks share storage); Option B simpler. Open question/12.4.

### 7.5 What we're NOT building

- No remote / push / pull. Local repos only.
- No three-way merge. Photo edits don't merge in the source-code sense.
- No CRDT-style multi-user concurrent editing.
- No reflog. If user `gc`s, branches they didn't ref are gone.
- No partial XMP staging.

---

## 8. Pipeline stages

The render pipeline is a sequence of stages. v1 has one stage; the abstraction admits N.

### 8.1 The contract

```python
class PipelineStage(Protocol):
    name: str

    def inputs(self) -> set[str]:
        # what this stage requires from previous stage
        # e.g. {"raw_path", "xmp_path"} or {"image_path"}
        ...

    def outputs(self) -> set[str]:
        # what this stage produces for next stage
        ...

    def run(self, context: StageContext) -> StageResult:
        # do the work; return paths/handles to outputs
        ...
```

The pipeline runner takes `[stage1, stage2, stage3]`, validates `stage1.outputs() ⊇ stage2.inputs()` etc., runs them in sequence, threads outputs as next inputs.

### 8.2 v1 stage

`DarktableCliStage` — `inputs: {"raw_path", "xmp_path"}`, `outputs: {"image_path"}`, runs the canonical CLI invocation:

```bash
darktable-cli \
  /workspace/<image_id>/raw/original.raw \
  /workspace/<image_id>/current.xmp \
  /workspace/<image_id>/previews/step_NNN.jpg \
  --width 1024 \
  --height 1024 \
  --hq false \
  --apply-custom-presets false \
  --core --configdir /chemigram/dt-configdir
```

`--apply-custom-presets false` prevents user auto-presets from contaminating render. `--hq false` for previews; `--hq true` for final exports.

**Important:** `--core` is the separator between cli-specific flags (above it) and core darktable flags (`--configdir` and similar, below it). It is valid for `darktable-cli` only — the GUI launcher `darktable` does NOT accept `--core` and exits with help text if passed it. The architecture's render path uses `darktable-cli` exclusively, so this is fine; just don't pattern-match the invocation onto GUI launches when scripting setup work. **Do not use `--style NAME`** for vocabulary application — its lookup behavior is unreliable in 5.4.1 (only finds GUI-imported styles, not GUI-created ones, despite both producing the same files). Always pass the synthesized XMP file directly as a positional argument, as shown above.

### 8.3 Future stages (not v1)

Per BYOA discipline, kept as architectural option:

- **Local Python processors** — custom algorithms, "secret sauce", pretrained models
- **External CLIs** — RawTherapee, ART, ImageMagick passes
- **GenAI tools via MCP** — upscalers, sky replacement, generative fill, denoise models
- **Specialist sub-agents** — narrow-task agents invoked as a stage

Cost of keeping this door open: ~100 lines (Protocol + runner + composition validation). Worth it.

---

## 9. EXIF auto-binding

When an image is ingested, Chemigram reads EXIF and suggests L1 and L2 bindings. Where the engine "earns its keep" — photographer hands Chemigram a raw, engine has already made reasonable defaults.

### 9.1 What's read

- Camera body (`Make`, `Model`)
- Lens model (`LensModel` or via maker notes)
- ISO (`ISOSpeedRatings`)
- Focal length, aperture
- Camera-set white balance
- For Fuji especially: `FujiFilmSimulation` if present

### 9.2 Resolution rules

**For L1:** walk user's `config.toml` bindings, take first match:

1. Exact: camera + lens binding
2. Camera-only fallback
3. Camera-system fallback
4. Nothing — image gets no L1

**For L2:** suggest, never apply silently. Priority:

1. If `FujiFilmSimulation` EXIF tag present and matching L2 template exists → suggest (e.g. `fuji_acros`). Honoring intent at capture.
2. If `[[layers.L2.bindings]]` matches camera+scene tags → suggest.
3. Otherwise no suggestion.

Result logged in `metadata.json`:

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

Agent reads this state to know baseline.

---

## 10. MCP tool surface

Grouped by subsystem. Parameter shapes concrete enough to implement.

### 10.1 Vocabulary and edit operations

```
list_vocabulary(layer?, tags?) → [{name, layer, modules_touched, tags, description, notes}]
get_state(image_id) → {entries: [{layer, module, primitive_name, multi_priority}], head: hash}
apply_primitive(image_id, primitive_name, mask_override?) → {state_after, snapshot_hash}
remove_module(image_id, module_name) → {state_after, snapshot_hash}
reset(image_id) → {state_after, snapshot_hash}
```

### 10.2 Rendering

```
render_preview(image_id, size=1024, ref_or_hash?) → {jpeg_path}
compare(image_id, hash_a, hash_b, size=1024) → {jpeg_path}
export_final(image_id, ref_or_hash?, size=None, format="jpeg") → {output_path}
```

### 10.3 Versioning

```
snapshot(image_id, label?) → {hash}
checkout(image_id, ref_or_hash) → {state}
branch(image_id, name, from?) → {ref}
log(image_id, ref?, limit=20) → [{hash, label, parent, ops_summary}]
diff(image_id, hash_a, hash_b) → [{primitive, change}]
tag(image_id, name, hash?) → {ref}
```

### 10.4 Local adjustments and AI masks

```
generate_mask(image_id, target, prompt?, name?) → {mask_id, name}
list_masks(image_id) → [{name, target, prompt, generator, created_at}]
regenerate_mask(image_id, name, target?, prompt?) → {mask_id}
invalidate_mask(image_id, name) → {ok}
tag_mask(image_id, source, new_name) → {mask_id}
```

### 10.5 Ingestion and binding

```
ingest(raw_path, image_id?) → {image_id, exif_summary, suggested_bindings}
bind_layers(image_id, l1_template?, l2_template?) → {state_after}
```

### 10.6 Context (agent's working memory — see the project concept doc)

```
read_context(image_id) → {taste_md, brief_md, notes_md, recent_log}
propose_taste_update(content, category) → {proposal_id}
confirm_taste_update(proposal_id) → {ok}
propose_notes_update(image_id, content) → {proposal_id}
confirm_notes_update(proposal_id) → {ok}
log_vocabulary_gap(image_id, description, workaround) → {ok}
```

### 10.7 Notably absent

- No catalog/library tools — Chemigram is not a DAM
- No batch tools — per-image research, not bulk processing
- No generic `set_module_param` — would push toward direct hex manipulation
- No vocabulary editing tools — agent uses vocabulary, doesn't extend it

---

## 11. Project layout

```
chemigram/                              # OSS monorepo (engine + vocabulary, per ADR-049)
  src/
    chemigram/
      core/
        xmp.py                          # parse + synthesize XMP
        dtstyle.py                      # parse .dtstyle into entries
        vocab.py                        # vocabulary loading + filtering
        versioning.py                   # objects, refs, log, DAG operations
        pipeline.py                     # PipelineStage protocol + runner
        stages/
          darktable_cli.py              # the v1 stage
        exif.py                         # EXIF read for L1 binding (Slice 1)
        binding.py                      # L1 binding via exact-match identity (Slice 1)
        masking/
          __init__.py                   # MaskingProvider protocol
          coarse_agent.py               # bundled default
        context.py                      # taste.md / brief.md / notes.md
        sessions.py                     # session lifecycle
      mcp/
        server.py                       # MCP tool definitions
        prompts/                        # versioned templates (Slice 3, per RFC-016)
  vocabulary/
    starter/                            # OSS starter pack — ships in chemigram wheel
      manifest.json
      ATTRIBUTION.md
    packs/                              # community packs (per ADR-032)
  tests/
  pyproject.toml

~/Pictures/Chemigram/                   # user data (per-image repos)
  <image_id>/
    raw/                                # symlink
    objects/
    refs/
    log.jsonl
    previews/
    sessions/
    masks/
    metadata.json
    current.xmp

~/.chemigram/                           # software state
  config.toml
  taste.md                              # global photographer context
  community-packs/
  dt-configdir/                         # isolated darktable configdir
  logs/
```

Single Python process, no daemon, no IPC between subsystems. Each `render_preview` spawns a `darktable-cli` subprocess. State is the filesystem.

---

## 12. Open questions for Phase 2

These are the questions whose answers require either implementation evidence or deliberation that hasn't yet happened. Each becomes one RFC document in Phase 2 work.

### 12.1 Same-module collision behavior in darktable

**Context:** SET semantics (/3.3) assume we can replace entries by `(operation, multi_priority)` and produce predictable results. Empirically untested on this machine.

**Question:** Does darktable's render handle two same-module entries with the same `multi_priority` in the way our SET-by-replacement assumes? Specifically: if our composition layer fails to dedupe and the XMP contains two `exposure` entries at `multi_priority=0`, does darktable last-wins, error, or accumulate?

**Closing evidence:** Phase 0 lab notebook experiment 5. Composition test with two `expo_*` entries.

**Likely outcome:** last-wins by `darktable:num` order, in which case our SET implementation is correct. If first-wins or accumulative, we adapt the synthesis layer.

### 12.2 Canonical XMP serialization for stable hashing

**Context:** Versioning (/7) hashes XMP content with SHA-256. Hash determinism requires canonical serialization — whitespace and attribute-order-invariant.

**Question:** What's the canonical XMP serialization that produces stable hashes when the semantic content is identical? Standard XML canonicalization (XML-C14N), custom serializer, or a simpler convention?

**Closing evidence:** Round-trip tests. Identical edit produces identical hash across save/load cycles.

### 12.3 Mode B evaluation function

**Context:** Mode B (autonomous fine-tuning) requires an eval function the agent uses to score candidates. Three approaches viable: reference-based perceptual similarity, vision-model self-eval, learned critic from accumulated Mode A history.

**Question:** Which eval function approach (or combination) produces useful Mode B convergence? What's the metric for "useful"?

**Closing evidence:** First Mode B implementation. Probably Phase 4+, deferred per `docs/TODO.md`.

### 12.4 Mask storage in versioning

**Context:** Section 7.4 lists Option A (content-addressed masks alongside XMPs) vs. Option B (per-snapshot subdirectories). Both have trade-offs; only one should be implemented.

**Question:** Which storage scheme balances dedup benefit against implementation complexity?

**Closing evidence:** Phase 2 versioning subsystem implementation. Choose A; fall back to B if dedup turns out not to matter at v1 scale.

### 12.5 Default masking provider quality vs. dependency cost

**Context:**/6.4 names two paths for v1 default: coarse agentic provider (no ML dependency) vs. bundled SAM (heavy dependency, better quality).

**Question:** Is the coarse agentic default usable enough that v1 ships without ML dependencies, or does sub-par masking degrade Mode A enough to require SAM as a v1 hard dependency?

**Closing evidence:** Phase 2 implementation + a few real Mode A sessions. Decision based on session friction, not theory.

**Bias:** start with coarse, recommend SAM as opt-in sibling. Reverse only if forced.

### 12.6 modversion drift across darktable releases

**Context:** When darktable bumps a module's `modversion`, our captured `.dtstyle` files become invalid for that module./5.4 acknowledges this; mitigation strategy not fully specified.

**Question:** What's the operational policy when darktable updates and modversions change? Auto-detect, warn-and-degrade, hard-fail?

**Closing evidence:** First darktable update during a Phase 1+ project. Decision based on observed pain.

### 12.7 Vocabulary discovery at scale

**Context:** As vocabulary grows (Phase 2: ~50 entries; Phase 3: ~150 entries; long-term: 200+), `list_vocabulary()` becomes an unwieldy response for the agent.

**Question:** How does the agent discover relevant vocabulary efficiently when the catalog is large? Tag-based filtering, semantic search, hierarchical browsing?

**Closing evidence:** Vocabulary actually growing past 100 entries. Speculative until then.

### 12.8 Session vs. snapshot relationship

**Context:** Sessions are append-only transcripts of conversations; snapshots are content-addressed XMP states. Section 7.2 keeps them in separate directories without specifying how they cross-reference.

**Question:** Should session log entries reference the snapshots produced during that turn? If so, in what format?

**Closing evidence:** First Phase 1 implementation that actually produces session transcripts.

### 12.9 Specialist masker caching

**Context:** TODO.md notes that successful prompted segmentations could be cached as recipes for similar subjects (e.g. "iguana eyes" works with prompt X + threshold Y).

**Question:** Is mask-recipe caching useful enough to justify the machinery, or does it add complexity for marginal benefit?

**Closing evidence:** Multiple sessions where the same target type is masked. Wait until friction is observed.

---

*04 · Technical Architecture · v1.0 · Open questions consolidated for Phase 2 RFC handoff*
