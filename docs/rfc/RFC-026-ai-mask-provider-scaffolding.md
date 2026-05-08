# RFC-026 — AI-derived mask provider scaffolding (subject / depth / content-aware spots)

> Status · Draft v0.1
> TA anchor · /components/masking · /contracts/mcp-tools · /constraints/byoa
> Related · ADR-076 (drawn-mask only architecture; this RFC layers on top), ADR-007 (BYOA principle), RFC-024 (range masks; this RFC handles the subject/depth arc deferred there), RFC-025 (spot removal; this RFC handles the content-aware spot detection arc deferred there), RFC-009 / ADR-057 (historical mask-provider Protocol — closed; this RFC defines the *correct* provider shape under ADR-076's lessons), capability-survey.md § 7 (local adjustments — AI-subject mask is the named gap)
> Closes into · ADR-NNN (pending — provider contract shape), ADR-NNN (pending — path-form encoding for N-vertex polygons), possible additional ADRs for vocabulary-surface integration
> Why this is an RFC · ADR-076 retired the PNG-mask Protocol after discovering darktable-cli does not consume raster mask bytes (silent no-op). Its closing observation was that any future content-aware masker would need to produce drawn-form geometry — silhouette polygons that land as `DT_MASKS_PATH` forms in `masks_history`. RFC-024 deferred subject and depth masks here on the grounds that they need ML at inference time and the right provider shape depends on what the provider can return. RFC-025 deferred AI content-aware spot detection here on the grounds that "find the spots" is a different operation from "user-marked this spot." Both deferrals are now load-bearing. The genuinely open question this RFC argues: **what's the provider contract that handles subject / depth / content-aware-spots cleanly, without re-creating the dead-Protocol failure ADR-076 established as the structural lesson?**

## The question

There are three AI-shaped mask gaps the engine cannot serve today: AI-subject masks (Lightroom's "Select Subject" — pick the person, the fish, the building), depth-range masks ("affect only the distant mountains"), and content-aware spot detection ("clean up the manta's belly across 200+ small spots"). All three need ML at inference time. None of them fit `chemigram.core` per ADR-007's BYOA principle. All three have to land as bytes darktable consumes, per ADR-076.

The naive shape — sibling project produces a raster mask, the engine writes the PNG, darktable reads it — was tried in v1.5.0 and discovered to be a silent no-op. ADR-076 retired it. The structural lesson: **the provider's output has to be in a form darktable's mask system actually consumes**, which for irregular shapes means drawn-form geometry (closed Bezier curves serialized into `masks_history`).

The genuinely open question: what's the provider contract? Specifically — (a) does the provider return polygon vertices directly, or a raster mask the engine traces into polygons? (b) how does the engine package a 2000-vertex SAM mask into a darktable path form without exploding XMP size? (c) what's the MCP tool surface the agent calls? (d) how do AI-detected masks compose with drawn / parametric masks under one vocabulary surface?

## Use cases

1. **Subject mask — portrait.** A photographer working a portrait wants to lift the face by +0.3 EV, leave the background alone. Today: drawn radial (centered ellipse, approximate). Future: AI-subject returns the head silhouette exactly.

2. **Subject mask — wildlife / underwater.** A diver shooting a manta wants to dehaze just the manta. Today: drawn radial misses the wing tips, catches the water. Future: AI-subject returns the manta silhouette; dehaze applies through it; the surrounding blue water stays untouched.

3. **Subject mask — landscape with sky.** A landscape photographer wants to lift shadows in the foreground but not affect the sky's tonality. Today: drawn gradient (top-to-bottom). Future: a sky-detection model returns the sky polygon; the inverse mask becomes the foreground.

4. **Depth mask.** A photographer wants to dehaze just the distant mountains, leaving the foreground intact. Needs a depth map (MiDaS-class model). The depth-mask provider returns either (a) a depth raster the engine thresholds into a far-band polygon, or (b) the polygon directly.

5. **Content-aware spot removal.** A diver wants the manta's belly cleaned up — 200+ small white spots scattered across the body. Manual mark-each-spot is impractical. The provider returns a list of `(x, y, radius)` regions. The engine emits 200 retouch forms via the RFC-025 path.

6. **Compositional masks.** A photographer wants AI-subject AND a drawn radial centered on the face — the intersection — to lift just the eyes. The vocabulary surface has to compose AI-derived masks with drawn masks.

## Goals

- **Pick the provider contract** that handles subject masks, depth masks, and content-aware spot detection under one architectural shape.
- **Honor ADR-076's structural lesson** — provider output must land as bytes darktable consumes. No raster mask Protocol that produces dead bytes.
- **Honor ADR-007 (BYOA)** — no AI dependencies in `chemigram.core`. Providers are sibling projects; the engine never imports torch / onnx / etc.
- **Bound the vertex explosion.** A SAM-class subject mask is a million-pixel raster. The engine cannot write a million-vertex path form into XMP. The contract has to specify polygon simplification (Douglas–Peucker / similar) at the provider boundary, with a target vertex budget the engine can encode efficiently.
- **Compose with existing mask_spec.** AI-derived masks are not architecturally separate from drawn / parametric masks. The vocabulary surface stays unified: a `mask_spec` field with a new `kind: "ai_subject"` (or similar) that the engine resolves at apply time by calling the configured provider.

## Constraints

- **ADR-076** (drawn-mask only architecture, post-PNG-Protocol-retirement): provider output must be drawn-form geometry, not raster.
- **ADR-007** (BYOA): no AI dependencies in `chemigram.core`. Providers are sibling projects.
- **ADR-033** (narrow MCP tool surface): adding tools requires an ADR. Subject / depth / spot detection adds at most 2 tools (`detect_subjects`, `detect_spots` — or a unified `mask.detect` with a `kind` parameter).
- **ADR-006** (single-process MCP): provider runs in its own process, talks via MCP. The engine never invokes the provider in-process.
- **CLAUDE.md three foundational disciplines**: agent-only-writer (mask configuration via tool calls); darktable-does-the-photography (mask math runs in darktable); BYOA (AI providers are sibling projects).
- **Pixel-truth from ADR-076**: whatever bytes the provider produces must be bytes darktable's `masks_history` reader consumes today, on whichever darktable version we target.

## Proposed approach

**Three-layer architecture: byte-level encoder (in-engine) ← MCP tool surface (in-engine, calls provider) ← AI provider (sibling project, BYOA).**

### 1. Byte-level encoder: `DT_MASKS_PATH` form, N-vertex closed polygon

Foundation work, not AI-shaped. Generalize `encode_rectangle_path_points` (which already encodes a 4-vertex closed Bezier path) to `encode_path_form_points(vertices, *, border)` taking a list of `(x, y)` pairs in normalized [0, 1] coordinates. Add `build_path_form(mask_id, vertices, *, border)` that produces a `DrawnMaskForm` with the existing `DT_MASKS_PATH` constant. Hook into `build_form_from_spec` for `shape: "path"`.

Each vertex is a `dt_masks_point_path_t` struct (corner + 2 Bezier control handles + 2 border floats + 1 state uint32, 9 floats + 1 uint = 40 bytes). Sharp corners use degenerate handles (ctrl1 = ctrl2 = corner) — same trick the rectangle encoder uses. For smoother subject silhouettes, the provider can supply explicit Bezier handles, or the engine can synthesize handles via Catmull–Rom fitting (open question).

Vertex budget: we test against darktable-cli with synthetic 50 / 200 / 1000 / 5000-vertex polygons to find the practical ceiling. Hypothesis: 500–1000 vertices is comfortable; 5000+ may bloat XMP and slow render. The provider contract caps vertex count and applies Douglas–Peucker simplification at the provider boundary to hit the budget.

This piece ships independently of any AI provider — it's useful for human-supplied polygons too (programmatic mask construction in scripts, debugging, fixture authoring).

### 2. MCP tool surface

Two new MCP tools, both in `chemigram.mcp`:

```python
@tool
def detect_subjects(
    image_id: str,
    query: str | None = None,
    *,
    provider: str | None = None,
    max_subjects: int = 5,
) -> list[DetectedSubject]:
    """Run the configured subject-detection provider against the image.

    Returns a list of detected subjects, each with label, vertices
    (normalized [0,1]), and confidence. The agent picks one and uses
    its vertices in a mask_spec.
    """

@tool
def detect_spots(
    image_id: str,
    *,
    provider: str | None = None,
    target: str | None = None,
) -> list[DetectedSpot]:
    """Run the configured content-aware spot-detection provider.

    Returns a list of (x, y, radius) regions. Each region becomes a
    retouch form via RFC-025's serialization path. Useful for
    'clean up the manta's belly' and similar scattered-defect cases.
    """
```

Both tools are pure detection — they do not modify edit state. The agent then calls `apply_primitive(name, value, mask=...)` (per the RFC-029 compositional mask path, if that ships) or applies a mask-bound vocabulary entry that references the detected vertices.

The `provider` argument is optional and falls back to `~/.chemigram/providers.toml` configuration. Multiple providers can be registered; the agent picks by name. Default behavior with no provider configured: tool returns an empty list with a `note` field explaining how to configure one.

### 3. Provider contract (sibling projects)

A subject-detection provider is a separate Python package (e.g., `chemigram-masker-sam`, `chemigram-masker-birefnet`) that:

- Registers itself as an MCP server under a known interface (`chemigram.mask_provider.v1`).
- Exposes a `detect` method taking an image path and optional query string.
- Returns a list of `{label, vertices, confidence, bbox}` objects. Vertices in normalized [0, 1] coordinates, already simplified to the engine's vertex budget.
- Owns its model weights, dependencies (torch, onnxruntime, etc.), and inference code. The engine knows nothing about ML internals.

A spot-detection provider follows the same shape, returning `{regions: [(x, y, radius), ...]}`.

A depth-detection provider returns either a depth raster (the engine thresholds + traces) or pre-thresholded polygons (cleaner; recommended). RFC-026 leaves this choice to the provider; both are encodable as path forms.

### 4. Vocabulary surface

The existing `mask_spec` field on vocabulary entries grows new kinds:

```jsonc
// Drawn (existing)
{"mask_spec": {"kind": "drawn", "shape": "ellipse", "center": [0.5, 0.5], "radius": 0.3}}

// AI subject (new)
{"mask_spec": {"kind": "ai_subject", "query": "person face", "fallback": "drawn_radial_centered"}}

// AI depth (new)
{"mask_spec": {"kind": "ai_depth", "band": "far", "threshold": 0.7}}

// AI compositional (new)
{"mask_spec": {"kind": "compose", "op": "intersect", "operands": [
    {"kind": "ai_subject", "query": "person face"},
    {"kind": "drawn", "shape": "ellipse", "center": [0.5, 0.4], "radius": 0.2}
]}}
```

When the engine sees `kind: "ai_subject"`, it calls the configured provider, gets vertices, and packages them through `build_path_form`. The rest of the apply path is unchanged — same `apply_with_drawn_mask` wire, same `masks_history` XML emission.

The `fallback` field is a graceful-degradation hint: if no provider is configured (or provider returns no match), the engine falls back to the named drawn shape. Lightroom users without a provider configured still get *something* useful.

## Alternatives considered

### Alt 1: Provider returns raster mask, engine writes PNG, darktable reads it

Rejected. This is the path ADR-076 retired. darktable-cli does not consume PNG raster masks for arbitrary shapes — it consumes drawn-form bytes in `masks_history`. The Protocol existed for nine months and produced silent no-ops. Reintroducing it under a different name would re-create the structural failure.

### Alt 2: Provider returns vertices; engine writes them to a `.dtstyle` / sidecar; darktable reads

Rejected as the *only* path. `.dtstyle` is the right format for vocabulary-entry storage but not for the runtime AI-derived mask path — AI detection happens at apply time per image, so writing a `.dtstyle` for every detected subject across every image would explode the vocabulary tree. The proposed approach uses path forms in `masks_history` directly, with no per-image `.dtstyle` proliferation.

### Alt 3: Provider runs in-process via Python imports

Rejected. Violates ADR-007 (BYOA: no AI dependencies in `chemigram.core`). Providers must run in their own processes and talk via MCP. The cost (process boundary, IPC overhead) is justified by the architectural cleanliness — `chemigram.core` stays AI-free, providers can use whatever ML stack they want without leaking dependencies.

### Alt 4: Single `mask.detect(kind="subject"|"depth"|"spots")` tool instead of three separate tools

Considered and partially adopted. The three operations have meaningfully different return shapes (subject = polygons, depth = depth raster or band polygon, spots = (x, y, radius) list). A single tool with a discriminated union return type is plausible; two tools (`detect_subjects` + `detect_spots`) is the recommended split because subject/depth share the polygon return shape and spots is structurally different. Final decision deferred to implementation; both are within the ADR-033 narrow-surface budget.

### Alt 5: Defer AI masks until v2.0; ship only range masks (RFC-024) and drawn masks

Rejected as the long-term answer. Lightroom's AI-subject mask is the most-used masking tool in the modern Lightroom workflow; not having a path forward for it ships a structural gap, not a polish gap. Deferring is fine for v1.9.0 / v1.10.0 (the foundation path-form encoder lands first; provider contract follows); permanent deferral is not.

## Trade-offs

- **Provider boundary is a moving target.** SAM, U2-Net, BiRefNet, MiDaS, ZoeDepth — the ML landscape shifts faster than chemigram releases. The contract has to be stable enough that providers can evolve their internals without breaking the engine. Polygon-vertex output is the stable contract; everything else (model choice, prompt engineering, raster post-processing) lives in the provider.
- **Vertex budget tension.** 500 vertices is enough to look like a person silhouette; not enough to capture hair detail. Photographers who care about hair will see edge artifacts. Mitigation: feathering hides most, and the path form supports per-vertex border floats for variable-width feathering. Long-term: explicit Bezier handles for smooth curves with low vertex counts.
- **No standard AI provider in the v1 release.** The engine ships the contract; users install `chemigram-masker-sam` (or similar) separately. This is BYOA-correct but adds a setup step. CLAUDE.md / install docs need to call this out clearly.
- **Compositional mask semantics get hairier.** Once AI masks compose with drawn and parametric masks via union/intersect/subtract, the vocabulary entry can describe arbitrarily complex mask graphs. The engine has to render this graph into darktable's mask system, which has its own composition operators (mask_id linking, parametric+drawn AND/OR). RFC-024's compose-syntax discussion is the precedent; this RFC extends it to include AI-derived operands.

## Open questions

1. **Vertex budget ceiling.** Empirical: how many vertices can `masks_history` hold per image before XMP size or render performance degrades? Test against darktable-cli with synthetic polygons of 50 / 200 / 1000 / 5000 vertices.
2. **Bezier handle synthesis.** When the provider returns a polygon (sharp corners), should the engine synthesize smooth Bezier handles (Catmull–Rom or similar) for better-looking masks at low vertex counts? Or always emit sharp corners and rely on feathering?
3. **Provider configuration surface.** `~/.chemigram/providers.toml` with named providers, default selection, fallback behavior. Schema TBD.
4. **Vertex coordinate system.** Normalized [0, 1] in image space is the proposal. Confirm against darktable's `dt_masks_point_path_t` (which uses normalized coords in the parent image's coordinate frame, but with crop / orientation applied at render time — needs verification).
5. **Per-image caching.** AI detection is expensive (seconds per image). Should results cache to `masks/<image_id>/ai_cache.json` keyed by `(provider, model_version, query)`? Probably yes; caching policy TBD.
6. **Compositional mask graph syntax.** RFC-024 proposed compose-via-`mask_spec.kind: "compose"` with operands. RFC-026 adopts the same syntax for AI operands. The exact compose semantics (set-theoretic union/intersect/subtract vs darktable's parametric+drawn AND/OR) need codification.
7. **Default sibling-provider implementation.** Even though BYOA means no bundled AI, shipping at least one *reference* sibling project (e.g., `chemigram-masker-sam` with SAM-via-onnx) gives users a working out-of-box path. Decision: ship a reference provider as a separate repo, link from install docs.

## How this closes

Likely two ADRs from this RFC:

- **ADR-NNN — Path-form encoding for N-vertex polygons.** Settles the byte-level encoder shape: generalized `encode_path_form_points`, `build_path_form`, vertex budget, sharp-corner-vs-Bezier-handle policy. Foundation; lands first, independent of provider work.
- **ADR-NNN — AI mask provider contract.** Settles the MCP tool surface (`detect_subjects`, `detect_spots`), the provider interface (`chemigram.mask_provider.v1`), the `mask_spec.kind` extensions (`ai_subject`, `ai_depth`, `compose`), and the configuration shape (`~/.chemigram/providers.toml`).

A third ADR is possible if compositional mask semantics turn out to need their own decision separate from the provider contract. RFC-024's compose-syntax discussion is the candidate; if that ADR closes RFC-024 first, RFC-026 inherits the syntax. Otherwise, RFC-026 defines it.

## Links

- TA/components/masking
- TA/contracts/mcp-tools
- TA/constraints/byoa
- ADR-076 (drawn-mask only architecture; the structural lesson this RFC honors)
- ADR-007 (BYOA principle; the constraint this RFC respects)
- ADR-033 (narrow MCP tool surface)
- RFC-024 (range masks; the subject/depth deferral lands here)
- RFC-025 (spot removal; the AI content-aware spot deferral lands here)
- capability-survey.md § 7 (local adjustments — AI-subject mask is the named gap)
