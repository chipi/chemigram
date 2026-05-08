# RFC-030 — Deployed sibling-provider scaffolding for precision-tier AI masks

> Status · Draft v0.1 (deferred)
> TA anchor · /components/masking · /contracts/mcp-tools · /constraints/byoa
> Related · RFC-026 / ADR-086 (LLM-vision-as-provider; the MVP this RFC layers above), ADR-076 (drawn-mask only architecture), ADR-007 (BYOA principle), ADR-084 / RFC-029 (compositional masks at apply time; the wire), ADR-085 / RFC-024 (parametric range-mask substrate), RFC-025 (spot removal; AI content-aware variants land here)
> Closes into · ADR-NNN (pending — provider Protocol contract); ADR-NNN (pending — `detect_*` MCP tool surface); possible additional ADRs for vocabulary-surface integration
> Why this is an RFC · RFC-026 ships LLM-vision-as-provider as the MVP for AI-derived masks. That covers the dominant content-derived masking use cases (coarse subject regions, sky/foreground splits, color-range estimation) at zero deployment cost. It does not cover precision-tier use cases: pixel-perfect silhouettes (single-strand hair, fine edges), dense content-aware spot detection (200+ small regions), and depth-range masks (per-pixel depth estimation). Those need deployed ML models — SAM-class for subjects, MiDaS-class for depth, specialized detectors for spots. RFC-030 holds the architectural design for that deployed-sibling-provider scaffolding. **Deferred to a future milestone** — not blocking v1.9.0 — because the LLM-vision workflow already covers the workflows the user named as priority. RFC-030 ships when (a) photographers hit the LLM-vision precision ceiling on real workflows, and (b) the cost of installing a sibling project is justified by the workflow gap.

---

## The question (deferred)

When LLM-vision-as-provider (RFC-026) isn't precise enough, what's the architectural shape for deployed sibling providers that produce pixel-precise masks?

Three sub-arcs with materially different cost shapes:

1. **Subject-mask precision tier.** SAM / BiRefNet / U2-Net class. Polygon output via Douglas–Peucker simplification at the provider boundary; vertex budget 50-1000 per mask. Quality: pixel-precise.
2. **Spot detection.** Smaller specialized model. List of `(x, y, radius)` tuples. RFC-025 owns the integration into retouch byte serialization.
3. **Depth masks.** MiDaS / ZoeDepth class. Returns either a depth raster the engine thresholds into a far/near polygon, or pre-thresholded polygon directly.

All three follow the same provider Protocol shape: separate MCP server, polygon/region output, ADR-076-compliant (drawn-form geometry darktable consumes).

---

## Use cases (precision-tier, beyond LLM-vision)

1. **Pixel-perfect subject silhouette.** Portrait where the photographer wants to lift the face *exactly* — hair edges, glasses frame, fine features. SAM/BiRefNet returns ~500-vertex polygon; LLM-vision returns ~12 vertices that approximate. RFC-030.

2. **Content-aware spot detection.** Manta's belly with 200+ scattered white spots. LLM can't enumerate hundreds of small region centers reliably. Specialized spot detector returns the list; engine emits N retouch forms via RFC-025's path. RFC-030.

3. **Depth-range mask.** "Dehaze only the far mountains." Needs per-pixel depth. LLMs cannot estimate depth well; MiDaS / ZoeDepth do. Returns a depth raster the engine thresholds, or a pre-thresholded far-band polygon. RFC-030.

4. **Multi-subject scene with overlapping subjects.** "Brighten only the foreground person, not the person in the background." Subject detection with instance segmentation. RFC-030.

5. **Real-time iterative refinement.** Photographer iterates on a SAM mask through edge-prompt feedback ("trim left edge"); the provider re-runs and returns updated polygon. Long-tail UX, RFC-030.

---

## Goals (deferred design)

- **Pick the provider Protocol shape** that handles subject masks, depth masks, and content-aware spot detection under one interface.
- **Honor ADR-076's structural lesson** — provider output must land as bytes darktable consumes via the existing `mask_spec` wire.
- **Honor ADR-007 (BYOA)** — providers are sibling projects; `chemigram.core` never imports torch / onnx / etc.
- **Bound vertex explosion.** SAM-class masks are million-pixel rasters. Polygon simplification (Douglas–Peucker) at the provider boundary, with a target vertex budget ≤1000.
- **Compose with RFC-026's LLM-vision workflow.** RFC-030's MCP tools (`detect_subjects`, etc.) should be drop-in replacements when photographers want precision — same `mask_spec` shape, just a different polygon source.
- **Minimize installation friction.** Realistic UX: photographers shouldn't need to manage torch versions, model checkpoints, or CUDA. Distribution mechanism (pip install, Docker, prebuilt binary) is part of this RFC.

---

## Constraints (carry-over from RFC-026 v0.1)

- **ADR-076**: provider output must be drawn-form bytes darktable's mask system consumes.
- **ADR-007**: no AI dependencies in `chemigram.core`. Providers are sibling projects.
- **ADR-033** (narrow MCP tool surface): RFC-030 may add 1-3 tools (`detect_subjects` / `detect_spots` / `detect_depth_band` or unified `mask.detect`). Each addition justifies its presence.
- **ADR-006** (single-process MCP): provider runs in its own process, talks via MCP. The engine never invokes the provider in-process.
- **CLAUDE.md three foundational disciplines**: agent-only-writer, darktable-does-the-photography, BYOA.

---

## Proposed approach (sketch — full design when this RFC unfreezes)

**Sibling MCP project pattern.** A subject-detection provider is a separate Python package (e.g., `chemigram-masker-sam`, `chemigram-masker-birefnet`) that:

- Registers as an MCP server under `chemigram.mask_provider.v1`.
- Exposes `detect` taking image path + optional query.
- Returns `[{label, vertices, confidence, bbox}, ...]` — vertices in normalized [0, 1], pre-simplified to vertex budget.
- Owns its model weights, dependencies (torch, onnxruntime, etc.).

### MCP tool surface (sketch)

```python
@tool
def detect_subjects(image_id: str, query: str | None = None,
                    *, provider: str | None = None,
                    max_subjects: int = 5) -> list[DetectedSubject]:
    """Run the configured subject-detection provider; return polygons."""

@tool
def detect_spots(image_id: str, *, provider: str | None = None,
                 target: str | None = None) -> list[DetectedSpot]:
    """Run content-aware spot-detection; return (x, y, radius) regions."""

@tool
def detect_depth_band(image_id: str, *, band: str,  # "near" | "far" | etc.
                      provider: str | None = None) -> dict:
    """Run depth-aware band detection; return polygon for the band."""
```

(Final shape: one tool with a `kind` parameter, or three separate tools — TBD when this RFC unfreezes.)

### Vocabulary-surface integration

When deployed providers ship, the agent flow becomes: `detect_subjects(image_id, "fish")` → polygon vertices → wrap as `mask_spec.dt_form="path"` → `apply_primitive(..., mask_spec=...)`. Same wire as RFC-026; just the polygon source upgrades.

### Per-image caching

`masks/<image_id>/ai_cache.json` keyed by `(provider, model_version, query)` — avoids re-running expensive inference per apply call.

### Provider configuration

`~/.chemigram/providers.toml` registers known providers with model paths, default selection, fallback behavior. Schema TBD.

---

## Alternatives (sketch)

- **Skip RFC-030 entirely; LLM-vision is enough forever.** Rejected — precision-tier workflows are real (portrait retouchers, wildlife photographers wanting exact silhouettes). LLM-vision's ~12-vertex polygon ceiling won't satisfy them.
- **Bundle SAM in core.** Rejected — violates ADR-007.
- **One unified `chemigram-mask-provider` for all three (subject/depth/spots).** Possible but couples model lifecycles. Probably three sibling projects, each with focused scope.
- **Cloud API providers (Anthropic, OpenAI, etc.) instead of local models.** API keys / billing / latency / privacy trade-offs. Worth considering when this RFC unfreezes.

---

## When does this RFC unfreeze

Triggers — any one of:

1. **Photographer evidence.** Real workflow logs show photographers hitting LLM-vision precision limits and requesting precision-tier masks.
2. **Compositional gap from RFC-024 / RFC-025.** A compositional case (e.g., "AI-subject ∩ drawn-radial") becomes the dominant ask, and LLM-vision polygons aren't precise enough for the intersection to make sense.
3. **Spot-detection demand.** RFC-025's user-marked-spot path proves valuable but photographers want "find all the spots automatically" for high-volume retouching.
4. **Depth-mask demand.** Photographer evidence for "dehaze only the far mountains" / "blur only the background" patterns where the drawn approximation is unsatisfying.

Until one of these triggers, RFC-030 stays Draft and deferred. Phase 2 carry-over content from earlier RFC-026 v0.1 drafts is preserved here for when work begins.

---

## Open questions (deferred)

1. **Provider Protocol details:** polygon-vs-raster output, vertex budget ceiling, MCP tool surface shape (one unified vs three separate), provider config schema, per-image caching policy, AI-detection cost amortization across multiple apply calls.
2. **Distribution mechanism:** pip install + bundled checkpoints? Docker images? CUDA-vs-CPU support? macOS Metal support?
3. **Cloud-API path:** lightweight Anthropic-API / GPT-4-Vision-API wrapper as an "easier to install" option distinct from the deployed-local-model arc?
4. **Cost model:** how to surface inference cost (latency, $) to the agent so it can choose between LLM-vision (fast, free in the conversation) and deployed providers (slower, costs deployment + maybe API $).

---

## How this closes

When this RFC unfreezes:

- **ADR-NNN — Deployed-sibling-provider Protocol contract.** The provider interface (registration, `detect` shape, polygon output, model-version metadata).
- **ADR-NNN — `detect_*` MCP tool surface.** The agent-facing tools that route to providers.
- **Possibly an ADR for the cloud-API path** (Anthropic / OpenAI wrapper) if that path proves preferable.

---

## Links

- TA/components/masking
- TA/contracts/mcp-tools
- TA/constraints/byoa
- ADR-076 (drawn-mask only architecture)
- ADR-007 (BYOA principle)
- ADR-084 / RFC-029 (compositional masks at apply time)
- ADR-085 / RFC-024 (parametric mask encoding)
- ADR-086 / RFC-026 (LLM-vision-as-provider; the MVP this RFC layers above)
- RFC-025 (spot removal; AI variants land here)
- capability-survey.md § 7
