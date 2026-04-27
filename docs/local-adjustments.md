# Chemigram — Local Adjustments

*Where craft lives. The substrate, the mechanism, and the agent's role.*

## Why this is the most consequential subsystem

Global moves get an image to "working." Local moves are where it becomes the photograph the photographer saw — *that* highlight on *that* fish, the sky dampened, the subject pulled forward, the water held in its place.

Local adjustments are also where Chemigram's value proposition concretizes. A photographer at LR sliders and a brush is doing pixel-pushing — they know what they want but the tool requires manual labor to get there. An agent driving local adjustments through *intent* ("warm the highlights on the fish") translates to *vocabulary + masking* automatically, the labor disappears, and the photographer's role becomes pure judgment: yes / no / that / not that.

This doc specifies how that loop works.

## What darktable gives us

Three local-adjustment mechanisms, all serializing to the same XMP `<rdf:li>` per module application — local-ness is a property of *how a module is configured*, not a separate kind of edit.

### 1. Parametric masks

Every darktable module supports parametric masking via `blendop_params`. The mask isn't a spatial region — it's a *condition* over pixel values: "apply this module only where luminance is in this range, hue is in this range, chroma is in this range, saturation is in this range." Up to four channels can be combined (multiplied or added).

**Strengths:** mathematically defined, deterministic across renders, no spatial drawing required, serializes cleanly into a `.dtstyle`. Authorable by a human in the GUI, then frozen as a vocabulary entry.

**Examples that work cleanly:**
- "Apply warmth only to the brightest 25% of luminance values" (highlights mask)
- "Apply this color shift only where the existing hue is cyan-blue" (water mask in underwater shots)
- "Apply structure only where saturation is high" (subject vs. neutral background, when subject is colorful)

**Limits:** can't isolate "the fish" from "everything else fish-colored." Parametric masks are content-agnostic — they don't know what's a fish.

### 2. Drawn masks

Spatial primitives: circles, ellipses, paths (closed bezier), gradients (linear, radial), brushes (freeform strokes). Each is parameterized — a gradient has start/end points and width, a circle has center and radius and feather.

**Strengths:** spatial precision, exactly what you'd reach for in LR for a graduated filter or a vignette.

**Limits for our purposes:** Brushes are sequences of human-painted strokes. An agent cannot author these meaningfully — what does "paint this region" mean to an LLM that's never held a stylus? Geometric primitives (circle, ellipse, gradient, simple path) *could* in principle be agent-authored ("circular mask centered at 60% width, 40% height, radius 300px, feather 0.4"), but doing so well requires spatial reasoning that LLMs are mediocre at.

**Our compromise:** drawn masks are pre-baked into vocabulary entries by the photographer in the GUI. `gradient_top_dampen_highlights` has a fixed top-down gradient mask captured once. The agent picks the entry; doesn't author the geometry.

### 3. External raster masks

Added in darktable 5.2. A module references a PNG file on disk; the PNG's grayscale values become the mask. This is the **AI subject masking path**: Python-side SAM (or FAST-SAM, MobileSAM, GroundingDINO+SAM, whatever) generates a PNG, the XMP references its path, darktable reads the PNG at render time.

**Strengths:** content-aware. Can isolate "the fish", "the sky", "the subject" — anything a vision model can segment.

**Use:** the agent calls a tool, generates a mask for a target ("subject" / "sky" / a custom prompt), the mask is registered, vocabulary entries reference it symbolically, the engine resolves the symbolic reference to the actual PNG path at XMP synthesis time.

**This is the path that makes Chemigram genuinely better at local work than a slider-driven flow.** The other two mechanisms are darktable's existing capability dressed in agent-callable form. AI raster masks are where the agent's reasoning meets pixel-level segmentation, and the photographer never has to draw.

## Two kinds of "local"

Worth distinguishing crisply, because they're handled differently.

**Spatially local** — masked. The effect applies in a bounded region of pixels. Mechanism: parametric, drawn, or external raster masks. Use when the photographer's intent is about a *part of the frame*: "the fish", "the sky", "the corners".

**Parametrically local** — zone- or frequency- or hue-based. The effect applies everywhere in the frame, but with intensity varying by some pixel property. Examples:
- **Tone equalizer** — different intensities at different luminance zones. Lift -2EV by 0.3, leave -1EV alone, push +1EV down by 0.2. Not masked; everywhere-different.
- **Contrast equalizer** — different intensities at different spatial frequencies. Boost mid-frequency texture, leave large-scale contrast alone. Not masked; everywhere-different.
- **Color equalizer / channel mixer** — different responses at different hue ranges. Pull cyan saturation, leave reds intact. Not masked spatially.

Parametrically-local moves go in the regular L3 vocabulary alongside global moves. They aren't part of "local adjustments" as this doc defines the term — they're just nuanced global moves. Worth flagging because they cover a lot of underwater work where parametric subtlety matters more than spatial isolation.

**The rest of this doc is about spatially-local adjustments.** When we say "local" without qualifying, we mean masked.

## The three-layer mask pattern

Vocabulary entries that include masking come in three flavors, increasing in agent involvement:

### Layer 1 — Pre-baked masks in vocabulary entries

The mask is part of the `.dtstyle`. Photographer authored it once in the GUI; it's frozen.

**Examples:**
- `gradient_top_dampen_highlights` — graduated filter from top, reduces highlights in upper portion
- `vignette_subtle` — radial darkening from edges
- `parametric_warm_only_highlights` — parametric mask on luminance, warmth only applies above midtones

**When the agent uses these:** when the *type* of mask is implied by the move's name and a photographer-authored geometry suffices. The agent picks the entry; the mask comes for free.

**Authoring:** photographer in GUI sets up the module + mask + values, saves as style, exports `.dtstyle`. Same vocabulary-authoring flow as everything else.

**The bulk of the masked vocabulary should be Layer 1.** It's the cheapest to build, most predictable to apply, requires no AI infrastructure.

### Layer 2 — AI-masked vocabulary entries (symbolic references)

The vocabulary entry has a *placeholder* for an external raster mask. The placeholder is a symbolic name like `current_subject_mask` or `current_sky_mask`. At XMP synthesis time, the engine resolves the symbol to whatever's in the mask registry.

**Examples:**
- `tone_lifted_shadows_subject` — lift shadow zones, masked to whatever the registry says is `current_subject_mask`
- `warm_highlights_subject` — warmth on highlights, masked to current subject
- `sharpening_subject` — diffuse-or-sharpen, masked to current subject
- `dampen_sky` — exposure reduction + saturation pull, masked to `current_sky_mask`

**When the agent uses these:** when content-aware isolation is needed. The agent has either already generated the relevant mask, or generates it now, *then* applies the entry.

**The conversation flow:**
```
User: "Make the fish stand out"
Agent: [reasons: this needs subject isolation]
Agent: generate_mask(image, target="subject")  → registers `current_subject_mask`
Agent: apply_primitive(image, "tone_lifted_shadows_subject")
Agent: apply_primitive(image, "warm_highlights_subject")
Agent: render_preview()
```

Two vocabulary applications, both reusing the same generated mask.

**Authoring of Layer 2 entries:** photographer in GUI sets up the module with an external raster mask pointing at a *placeholder PNG* (a sentinel image of known properties), saves as style, exports `.dtstyle`. The engine recognizes the placeholder PNG at synthesis time and substitutes the real mask path.

This authoring trick keeps the entry valid in plain darktable (the placeholder renders as if no mask) while letting Chemigram swap in the real mask at synthesis time. Implementation detail, but worth flagging.

### Layer 3 — Agent-described composite masks

*Not in v1.* Listed for completeness because it's a natural future extension.

The agent describes a mask compositionally: "subject mask, expanded by 20px, intersected with luminance > 0.6." Or: "sky mask, refined to exclude clouds, plus a feathered gradient from top."

This requires the engine to support mask operations (union, intersection, dilation, erosion, refinement) and the agent to reason about composition. Useful for cases where neither pre-baked nor pure-AI masks suffice.

**Why deferred:** the LR/PS-equivalent capability we want (graduated filter on sky, subject mask on fish, both applied via the same engine) is satisfied by Layers 1 and 2. Layer 3 is the next frontier when those become limiting.

## The mask registry

A small subsystem owned by the engine. Tracks generated masks for a given image during a session.

### Registry contents

```
~/Pictures/Chemigram/<image_id>/
  masks/
    current_subject_mask.png       # most recent subject mask
    current_sky_mask.png           # most recent sky mask
    fish_2024_pelagic.png          # named user mask, persistent
    ...
  masks/registry.json              # metadata for each mask
```

Each mask entry in `registry.json`:

```json
{
  "name": "current_subject_mask",
  "path": "masks/current_subject_mask.png",
  "target": "subject",
  "prompt": null,
  "generator": "sam_v2",
  "generator_config": { "model": "sam2_hiera_b+", "threshold": 0.5 },
  "generated_from_render_hash": "a3f291...",
  "created_at": "2026-04-27T15:23:11Z"
}
```

### Lifecycle

### Masking providers (BYOA)

Per the Bring Your Own AI principle in `architecture.md`, Chemigram does not bundle a specific masking model. Maskers are pluggable behind a `MaskingProvider` protocol; the photographer chooses implementations per use case via `config.toml`.

```python
class MaskingProvider(Protocol):
    name: str

    def generate(
        self,
        image_path: str,                    # current preview render
        target: str,                         # "subject" | "sky" | "background" | "custom"
        prompt: str | None = None,           # for "custom"
        hints: dict | None = None,           # bboxes, click points, refinement
    ) -> MaskResult:
        ...

class MaskResult:
    mask_png_path: str                       # the actual output
    confidence: float                         # provider's self-reported confidence
    description: str                          # what the provider thinks it segmented
    refinement_options: list[str]             # things this provider can do if asked
```

This is the same kind of protocol as `PipelineStage` — small, MCP-friendly, swap-in/swap-out replaceable.

### Provider categories

Real implementations photographers can configure:

- **SAM-via-MCP (sibling project: `chemigram-masker-sam`).** A standalone MCP server wrapping SAM, SAM 2, or MobileSAM. Local install, GPU-accelerated on Apple Silicon via MPS. Production-quality subject masking. **The recommended default for users who want quality.**
- **Prompted segmentation via GroundingDINO + SAM (sibling project).** For text-prompted feature isolation ("iguana eyes," "fish gills"). Same MCP-server pattern.
- **Hosted services via MCP** (Replicate, Modal, etc.). Pay per call; near-zero local resource usage; quality comparable to local SAM. Configure with API token in `config.toml`.
- **Coarse agentic provider (bundled default).** Uses the photo agent's vision capability to identify regions and produces *coarse* masks: bounding boxes, gradients, color-region floods. Not pixel-precise, but enough for many use cases (sky gradients, top/bottom dampening, rough subject isolation). Free, no extra installation.
- **Custom photographer-trained specialists.** A photographer who shoots underwater could fine-tune a masker on their own subjects, expose it as MCP, configure Chemigram to use it for their genre. Real path for advanced users.

### Default in v1

v1 ships with the **coarse agentic provider** as the bundled default. This means:

- Out of the box: no PyTorch dependency, no model weights, no GPU configuration. Chemigram works with any vision-capable agent.
- Coarse masks (bboxes, gradients, color regions) are sufficient for many sessions, especially Layer 1 vocabulary that uses pre-baked masks rather than runtime generation.
- For production-quality masking: `pip install chemigram-masker-sam` (or similar), point `config.toml` at it, get SAM-quality results.

This is the right default because it makes Chemigram immediately usable without forcing every user through ML model setup. Quality is a path of progressive opt-in.

### Configuration

```toml
[masking]
default_provider = "sam-mcp"                 # which provider for default cases

[masking.providers.sam-mcp]
type = "mcp"
endpoint = "http://localhost:7811"            # the local SAM-MCP server
config = { model = "sam2_hiera_b" }

[masking.providers.replicate-sam]
type = "mcp"
endpoint = "https://api.replicate.com/v1/mcp"
auth = { token_env = "REPLICATE_TOKEN" }
config = { model = "meta/sam-2" }

[masking.providers.coarse-agent]
type = "agent"                                # uses the user's configured photo agent
config = { capability = "rectangular_and_gradient_only" }

# Per-target provider overrides
[masking.targets]
subject = "sam-mcp"
iguana_eyes = "replicate-sam"                 # use higher quality for fine work
sky = "coarse-agent"                          # rectangular gradient is fine for sky
```

The agent's `generate_mask(image, target, prompt?)` tool resolves the appropriate provider from this config, calls it, and registers the result in the mask registry.

### Why agentic masking is philosophically right

Mode A is "agent + photographer working through a photo." If masking is a black-box ML pipeline, that's a hole in the conversational fabric — agent says "let me mask the subject" and a model runs without any reasoning the photographer can intervene in. Whereas if the masker is itself agentic (or wrapped in MCP), the masking participates in the conversation:

> "I think the subject is the iguana — the warm-toned gray animal in the center-left. Generating a mask for that. Want to refine before I apply moves?"

The photographer can correct mid-mask: "no, the smaller iguana behind the rock." That's the loop working as designed all the way down.

### Honest limits

- **Agentic-only masking (the bundled default) is genuinely worse than SAM** at pixel-precise segmentation. Eye-level work needs a real segmentation model. v1 default is a fallback; production users will want SAM-MCP.
- **MCP latency for remote providers is real** (1-3s per mask for hosted services). Fine for occasional use; might be noticeable in dense Mode A sessions. Local providers have near-zero latency.
- **Provider failures need graceful handling.** Agent surfaces ("masker is unavailable") and offers fallbacks ("want to use the coarse provider, or skip this move?").
- **Configuration complexity grows with provider count.** Good defaults matter — most users should never need to touch `config.toml` for masking unless they want non-default quality.

## Vocabulary patterns for masked entries

### Manifest metadata

Each masked entry adds fields beyond the standard vocabulary entry:

```json
{
  "name": "tone_lifted_shadows_subject",
  "layer": "L3",
  "path": "layers/L3/local/tone_lifted_shadows_subject.dtstyle",
  "touches": ["toneequalizer"],
  "tags": ["tone", "shadows", "local", "subject"],
  "description": "Lift shadow zones, restricted to the subject mask.",
  "mask_kind": "raster",
  "mask_ref": "current_subject_mask",
  "global_variant": "tone_lifted_shadows"
}
```

Two new fields:

- `mask_kind`: one of `"none"` (global), `"parametric"` (mask in `blendop_params`, no external dependencies), `"drawn"` (geometric mask in `blendop_params`), `"raster"` (external PNG via `mask_ref`)
- `mask_ref`: for `raster` only, the symbolic mask name to resolve at synthesis time
- `global_variant`: the name of the unmasked equivalent, when one exists. Lets the agent reason about "fall back to global if mask generation fails or isn't relevant."

### Naming conventions

Pattern: `<base_move>_<mask_indicator>` for masked variants.

- Base: `tone_lifted_shadows`, `warm_highlights`, `clarity_subtle`
- Subject-masked: `tone_lifted_shadows_subject`, `warm_highlights_subject`
- Sky-masked: `dampen_sky`, `tone_lifted_shadows_sky` (rare but legal)
- Parametric-masked: `warm_highlights_only` (the `_only` suffix suggests the parametric restriction is integral to the move)
- Drawn-masked: `gradient_top_<effect>`, `vignette_<effect>`

Consistent suffixes give the agent a pattern to recognize. When a vocabulary entry exists in both global and subject-masked variants, the suffix tells the agent which is which.

### SET semantics for masked entries

A nuance worth being explicit about: how does SET semantics interact with masked variants?

**Same module, different masks** — `tone_lifted_shadows` (global) and `tone_lifted_shadows_subject` (raster-masked subject) both touch `toneequalizer` with `multi_priority=0`. Under strict SET-by-`(operation, multi_priority)`, applying one replaces the other.

**Is this what we want?** Mostly yes. The photographer's intent is usually "lift the shadows, here's how"; switching from global to masked is a *change of intent*, not an addition. So SET semantics handle this correctly: applying the subject-masked variant after the global one replaces the global one.

**The exception:** when the photographer wants *both* — global lift AND extra subject lift. This requires two separate `multi_priority` values. The vocabulary handles this by including a `_extra` variant: `tone_lifted_shadows_subject_extra` has `multi_priority=1`, applies *on top of* whatever's at priority 0.

In practice: rare. Most local-adjustment work is "lift this region", not "lift everything plus extra in this region". When the latter is needed, the `_extra` variants exist.

## Worked examples

Concrete walkthroughs of the conversation and engine flow for representative cases.

### Example 1 — Gradient on the sky to dampen the sun

Photographer's request: *"Add gradient filter from top, reduce highlights and a bit of exposure to dampen the sun."*

This is a Layer 1 case — pre-baked drawn mask in vocabulary.

```
[ agent reasoning: top-down gradient + highlight/exposure dampening; pre-baked entry exists ]

agent: apply_primitive(image, "gradient_top_dampen_highlights")
        → entry includes a top-down linear gradient mask
        → reduces highlights by ~0.5 stops, exposure by ~0.2
agent: render_preview()
agent: snapshot(label="dampen_sky")

[ photographer reviews ]

photographer: "More on the highlights, less on the exposure"

agent: apply_primitive(image, "gradient_top_dampen_highlights_strong")
        → SET semantics replace previous entry
agent: render_preview()
```

Two vocabulary entries needed: `gradient_top_dampen_highlights` (subtle) and `gradient_top_dampen_highlights_strong` (more aggressive). Both are Layer 1 — drawn-mask + module config baked in. Authoring is one GUI session.

### Example 2 — Select that fish, lift midtones, open blacks

Photographer's request: *"Select that fish and add some more highlights and open blacks to make it stand out."*

This is a Layer 2 case — AI subject mask + multiple masked vocabulary entries reusing it.

```
[ agent reasoning: subject isolation needed, multiple moves on the same subject ]

agent: generate_mask(image, target="subject")
        → SAM segments the fish from the water
        → registers as `current_subject_mask`
agent: apply_primitive(image, "tone_lifted_highlights_subject")
        → toneequalizer lifting upper zones, masked to subject
agent: apply_primitive(image, "open_blacks_subject")
        → toneequalizer lifting lower zones, masked to subject
        → SET semantics: same module (toneequalizer) — but wait, both touch toneequalizer
```

Hmm — both vocabulary entries touch the same module with the same `multi_priority`. Under strict SET, the second replaces the first. That's not what we want here; we want both lifts to compose.

**Resolution:** the toneequalizer module operates on multiple zones simultaneously. A single toneequalizer entry can lift highlights *and* open blacks at the same time. So the right vocabulary entry is `tone_lifted_highlights_and_blacks_subject` (one entry, one module, both lifts), or the two-entry case uses `multi_priority` 0 and 1 to coexist.

This surfaces a real design discipline: **vocabulary entries that touch the same module need to either (a) use distinct `multi_priority` values, or (b) be combined into one entry**. For the toneequalizer-based local adjustments, combined entries are usually better — the module is already multi-zone.

For modules where two simultaneous applications make sense (e.g. two `colorbalancergb` instances, one for shadows and one for highlights), `multi_priority` 0 and 1 give us coexistence.

```
[ revised agent flow ]

agent: generate_mask(image, target="subject")
agent: apply_primitive(image, "tone_lifted_highlights_and_blacks_subject")
        → single toneequalizer entry doing both lifts, masked to subject
agent: render_preview()
```

Cleaner. One subject mask, one combined move.

### Example 3 — Underwater backscatter pattern

Photographer's request: *"There's some backscatter in the water column. Reduce it without killing the texture in the fish."*

Mixed case — parametric masking for the backscatter (luminance-based: small bright specks against darker water), combined with subject preservation (don't touch the fish).

This is hard. Backscatter reduction is itself an L3 move (probably using `diffuse-or-sharpen` in denoise mode). Restricting it to the water (excluding the subject) requires inverse subject masking.

```
agent: generate_mask(image, target="subject")
        → registers `current_subject_mask`
agent: apply_primitive(image, "denoise_backscatter_water_only")
        → diffuse-or-sharpen denoise preset
        → masked to inverse of subject (i.e. NOT subject)
        → also parametric-masked to high-luminance specks (avoids smoothing the water gradient)
agent: render_preview()
```

The vocabulary entry `denoise_backscatter_water_only` has `mask_kind: "raster"` with `mask_ref: "current_subject_mask"` and a flag for inverted, *plus* a parametric component. This is a **composite mask** — raster + parametric, combined inside the entry's `blendop_params`.

darktable supports this natively (parametric and drawn masks can compose in `blendop_params`). The vocabulary entry author sets it up once in the GUI; the agent applies it without needing to reason about the composition.

### Example 4 — Mask reuse fails (photographer changed their mind)

Photographer's request, mid-session: *"Actually, I want to apply these effects to the school of fish, not just the lead one."*

Mask is wrong. Need to regenerate.

```
[ context: agent has been applying subject-masked moves, current_subject_mask is the lead fish ]

agent: regenerate_mask(image, target="subject", prompt="all the fish in the frame")
        → uses prompted SAM/GroundingDINO
        → overwrites `current_subject_mask`
agent: render_preview()
        → existing masked entries in the XMP now reference the new mask
        → render automatically picks up the change
```

Important property: **the XMP doesn't reference a mask path; it references a placeholder that the engine resolves at synthesis time**. So regenerating a mask doesn't require re-applying every primitive that used it. The XMP synthesis at next render picks up the new mask file automatically.

This is the payoff of symbolic mask references over hardcoded paths.

### Example 5 — Named persistent masks

Photographer's request: *"Save this fish mask as 'mobula_main' — I want to come back to this image later and have the same mask available."*

Custom name, persistent across sessions.

```
agent: tag_mask(image, source="current_subject_mask", new_name="mobula_main")
        → copies the PNG, registers under new name
        → mobula_main is now persistent and won't be overwritten by new subject mask generations
```

Vocabulary entries can reference custom mask names: `tone_lifted_highlights_masked` with `mask_ref: "mobula_main"` (set at apply time, not in the entry's manifest — the agent overrides via tool parameters).

This is the bridge to multi-session workflows on the same image: a complex selection done once, named, reused across sessions.

## The agent's reasoning model

When does the agent reach for masked vs. unmasked? Three signals.

### Signal 1 — Subject in the verbal request

"Lift the shadows" → global. "Lift the shadows on the mobula" → subject-masked. "Lift the shadows in the foreground" → likely subject-masked. "Brighten the sky" → sky-masked.

The agent looks for *spatial qualifiers* in the photographer's language: object names, region words ("foreground", "background", "sky", "edges"), positional phrases ("upper-left", "in the corners"). These shift the move from global to local.

### Signal 2 — Composition implication

"Make the fish stand out" doesn't have an explicit subject of the verb, but "stand out" implies *separation from background*, which implies *local moves on the subject*. The agent should recognize composition language and reach for masked variants even when the surface grammar doesn't demand it.

Other examples: "make this pop" (subject), "calm the background" (inverse subject), "draw the eye" (subject), "open the scene" (likely global), "balance" (likely global).

### Signal 3 — Default to global, escalate to masked

When ambiguous, start global. The photographer can ask for a masked refinement next turn. Going global → masked is one extra turn; going masked → global is one extra turn plus reasoning about which mask to discard. The asymmetry favors starting global.

Exception: when the photographer's brief explicitly mentioned a subject ("the mobula should be the focus", "water cool but not cyan"), even early-loop moves should preferentially target the subject.

## MCP tool surface for local adjustments

Adding to the existing surface in `architecture.md`:

```
generate_mask(image, target, prompt?, name?) -> {mask_id, name}
  # Run masker over current preview, register PNG.
  # target: "subject" | "sky" | "background" | "custom" (with prompt)
  # name: optional override; default `current_<target>_mask`

list_masks(image) -> [{name, target, prompt, generator, created_at, persistent}]
  # Inspect registered masks for this image.

regenerate_mask(image, name, target?, prompt?) -> {mask_id}
  # Replace an existing mask. Same name; new content.

invalidate_mask(image, name) -> {ok}
  # Remove a mask from the registry. XMP entries that referenced it
  # will fail at next render (or fall back to no mask, if entry supports).

tag_mask(image, source, new_name) -> {mask_id}
  # Copy a mask under a persistent name. Useful for multi-session workflows.

apply_primitive(image, primitive_name, mask_override?) -> {state_after, snapshot_hash}
  # Existing tool; new optional `mask_override` parameter.
  # If primitive has mask_ref="current_subject_mask" but agent wants to use
  # a custom mask name, pass mask_override="mobula_main".
```

Six tools added to the MCP surface (five new, one parameter extension). All small, all consistent with the rest of the surface. No vocabulary editing, no mask editing, no compositional mask operations (deferred to Layer 3 / future work).

## Integration with versioning

Masks are part of the edit state, not session ephemera. When a snapshot is committed, the masks referenced by the XMP are versioned with it.

### Storage

```
~/Pictures/Chemigram/<image_id>/
  objects/
    a3/f291...xmp                  # snapshot XMP
    a3/f291...masks/               # masks active at this snapshot
      current_subject_mask.png
      mobula_main.png
```

Or, more space-efficient, content-address the masks separately:

```
  objects/
    a3/f291...xmp                  # snapshot XMP, references masks by content-hash
    masks/
      d8/12fa....png                # content-addressed mask PNG
```

The XMP at this snapshot would symbolically reference `current_subject_mask` and the snapshot metadata maps that symbol to `d812fa...png`. Same content addressing as XMP snapshots; same dedup benefits.

### Implications

- Snapshot hash includes mask content. Two snapshots with same XMP but different subject masks are different snapshots.
- `checkout` to a previous snapshot restores both XMP and the masks active at that point.
- `gc` walks both XMP and mask references; unreferenced masks are collected.
- `diff(hash_a, hash_b)` includes mask changes ("subject mask regenerated" as a diff entry).

This is mild additional complexity in the versioning subsystem, but it's the only way local-adjustment work is reliably reproducible.

## What we deliberately don't support

To set expectations:

- **Brush masks** — agent can't author them. Photographer pre-bakes via vocabulary if needed. Not on the v1 critical path.
- **Pixel-level editing** — Chemigram doesn't paint pixels. If a workflow needs frequency separation + dodge/burn at the pixel level, it belongs in PS / Affinity Photo, not in our parametric pipeline.
- **Arbitrary mask composition by the agent** — Layer 3 from the three-layer model. Deferred to v2.
- **Mask refinement gestures** — "shrink the mask 10px", "feather more", "exclude this corner". Could be added later as MCP tools, but not v1.
- **Multiple subject masks with disambiguation** — "the front fish, not the back one". Requires prompted segmentation with spatial constraints. v2.

## Phase ordering

Concrete sequence for getting local adjustments into the project:

### Phase 1.5 — Layer 1 (parametric and drawn pre-baked)

Lands with the rest of Phase 1. No new infrastructure required:

- Author 8-12 vocabulary entries with parametric or drawn masks pre-baked
- `mask_kind` field in manifest
- Standard `apply_primitive` flow handles them

Just authoring work plus a small manifest schema extension.

### Phase 2A — MaskingProvider protocol + coarse default (~5 days)

The BYOA mask architecture lands here. Chemigram-internal:

- Implement the `MaskingProvider` protocol (~40 lines)
- Implement the mask registry subsystem (~250 lines)
- Implement the coarse agentic default provider (~150 lines) — uses the photo agent's vision to produce bbox/gradient/color-region masks
- Add `generate_mask`, `list_masks`, `regenerate_mask`, `invalidate_mask`, `tag_mask` to MCP surface
- Implement symbolic mask reference resolution at XMP synthesis time
- Integrate masks into versioning (snapshots include referenced masks)
- Author 6-10 Layer 2 vocabulary entries with symbolic mask refs

End state: the iguana session works; mask quality is coarse but workflow is complete. No PyTorch dependency in Chemigram core.

### Phase 2B — `chemigram-masker-sam` sibling project (~5 days, separable)

Production-quality masking as an opt-in sibling project:

- Standalone MCP server wrapping SAM 2 / MobileSAM
- Apple Silicon support via PyTorch + MPS
- Local install, no network calls
- Conforms to Chemigram's `MaskingProvider` protocol via MCP
- Photographer installs separately, configures in `config.toml`

End state: production-quality subject and prompted-feature masking available. Can also be a reference implementation for other sibling masker projects (custom specialists, hosted-API wrappers).

This split is the BYOA principle made concrete. Chemigram core has zero ML dependencies; users opt into quality.

### Phase 3 — Polish and edge cases

- Persistent named masks (`tag_mask` workflow refinement)
- Mask invalidation heuristics (when does `current_subject_mask` get stale?)
- Better composite mask vocabulary (raster + parametric combined)
- Provider failure handling and fallback chains in config

### Phase 4+ — Layer 3 (agent-described composites)

Deferred. Build only when Phases 1.5–3 reveal a clear need.

## Why this subsystem matters more than it looks

A few observations worth ending on.

**Local adjustments are where the agent shines or fails.** Global moves are easy — every vocabulary system can do exposure and WB. Local adjustments require *content awareness* and *spatial reasoning*, both of which translate poorly to slider-based tools. The agent's value here isn't that it can move sliders fast; it's that it can express "lift the midtones on the fish" as a single instruction and have it execute correctly.

**The vocabulary discipline gets harder here.** A masked vocabulary entry encodes both *what to do* (the module config) and *how to scope it* (the mask). Naming, composition, and reuse all get more complex than the global case. The discipline pays off — a finite vocabulary of well-named masked moves is dramatically more legible than a continuous slider+brush surface — but the authoring cost is real.

**This is where Mode B becomes interesting.** Autonomous fine-tuning can explore different mask refinements ("what if the subject mask were dilated 10px? what if we used a luminance-based water mask vs. a content-based subject mask?") in a way no human would have patience for. The exploration tree gets richer, the eval function more meaningful. Mode B was always going to need the local-adjustment substrate; this doc specifies it.

**This is where the "why darktable" answer matters.** LR's local-adjustment surface is fine but limited and getting LR-locked. darktable's parametric + drawn + external raster mask combination is genuinely more powerful, and now that AI subject masks via raster modules work cleanly, darktable surpasses LR for the agent-driven case. The choice we made early — darktable not LR — pays off most clearly in this subsystem.
