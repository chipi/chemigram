# PRD-004 — Local adjustments through drawn-form and content-aware masking

> Status · Partially shipped at v1.5.0 (drawn-form geometric masks); content-aware masking deferred to Phase 4
> Sources · 01/The work, 02/Local adjustments, 04/Masks, ADR-076
> Audiences · photographer (PA/audiences/photographer) — specifically the expedition photographer and the exploratory editor sub-shapes
> Promises · agent-as-apprentice, the-loop-is-fast, byoa-extensibility, inspectable-state (PA/promises)
> Principles · byoa, darktable-does-the-photography, restraint-before-push, honest-about-limits, compounding-over-throughput (PA/principles)
> Why this is a PRD · Local adjustments are the single highest-friction part of conventional photo editing and the single highest-leverage place an agent can help. This PRD argues *what* the local-adjustment experience should be in Chemigram. v1.5.0 ships the substrate (drawn-form geometric masks bound to vocabulary entries). The full content-aware experience this PRD describes — "lift the shadows on the manta" with AI-generated subject masking — is Phase 4 work via a sibling project; ADR-076 retired the v0.4.0 PNG-mask infrastructure when it turned out darktable didn't read external PNG masks at all.

A manta ray glides through water that's gone slightly too cold and slightly too blue, the way water always does at depth. The shot is good — the angle is right, the eye is in focus, the whole creature is in the frame. But the underbelly is sunk in shadow. The water column has a faint shimmering of suspended particulate near the surface that pulls the eye upward, away from the subject. The manta's eye, the one the photographer waited two dives to catch, sits two stops too dark relative to where it should land. In darktable today, fixing these things is a forty-minute exercise: a parametric mask on luminance to lift the shadows, then a drawn mask to constrain it to the manta only because the parametric leaks into the water; a separate drawn mask on the eye, feathered carefully, then a localized contrast adjustment; a luminance-and-color parametric for the particles, then trial-and-error on the falloff. By the time the photographer gets the four adjustments to coexist, they've forgotten the original feeling that prompted them. In a Chemigram session, the ambition is four turns. *Lift the shadows on the manta. A bit more contrast on the eye, just a touch. Warm the water column slightly. Knock back those particles up top.* Each turn is a render, a glance, a snapshot. The photographer's attention stays on the photograph.

## The problem

Local adjustments in conventional editing are where the cost of editing detaches from the *thought* of editing. The thought "lift the shadows on the manta only" takes half a second to form. Executing it on a touchscreen or with a mouse takes minutes — drawing the mask, feathering it, refining the boundary on the wing tip, checking it against the subject's edges, rebalancing when the parametric mask's luminance threshold blew through. The cost is high enough that photographers regularly skip local adjustments they would otherwise want. They settle for a global compromise — a tone curve that's slightly wrong everywhere instead of right where it matters and untouched elsewhere.

This isn't a niche frustration. The expedition photographer's most common shot — a subject against a difficult background — is the exact case where local adjustments matter most. The marine animal in colored water. The bird against a blown-out sky. The wildlife in dappled forest light. In each, the right edit is local and the cost of executing it locally is what limits how often it gets done.

Two flavors of "local" matter, and they have different leverage:

**Placement-driven** (gradients, areas of the frame): "dampen the highlights in the top half," "lift the shadows in the bottom third," "warm the central radial area where the subject is," "dim a horizontal band where the horizon distracts." These are *about composition* — the photographer knows where the region is by frame coordinates. AI is unnecessary; geometric forms (gradient / ellipse / rectangle) cover them.

**Subject-driven** (silhouettes, organic shapes): "lift the shadows on the manta," "warm the eye," "knock back the particles in the water column." These require identifying *what* a region is, not where it is. This is where AI masking has the leverage — the agent identifies and the photographer doesn't draw.

v1.5.0 ships the placement-driven path. The subject-driven path is Phase 4 work.

## The experience — v1.5.0 (placement-driven)

The photographer is in a session in Mode A, image opened, baseline applied, talking through the photograph. The image has a bright sky competing with the foreground. They say *dampen the top half a touch.* The agent recognizes this as a placement local adjustment and reaches for `gradient_top_dampen_highlights` — an L3 vocabulary entry whose `mask_spec` declares a top-bright gradient bound to a -0.5 EV exposure. It calls `apply_primitive(image_id, "gradient_top_dampen_highlights")`. The engine encodes the gradient form directly into the XMP's `masks_history` and patches the exposure plugin's `blendop_params` to bind it. Two seconds later, a render. The photographer judges. *Yes. And lift the bottom a hair.* The agent reaches for `gradient_bottom_lift_shadows`. Another preview. *Perfect.*

The four shipped mask-bound entries — `gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim` — cover the most common placement cases. Each binds an exposure adjustment to a geometric form with sensible defaults. New mask-bound entries get authored the same way: declare `mask_spec` in the manifest, bind to the desired plugin operation, ship.

The masks themselves are darktable-native. Once the apply lands, the mask shows up in darktable's UI as a regular drawn mask — the photographer can open the image in darktable and see exactly what was bound, edit it manually if they want, and the change persists in the XMP.

This is honest about its limits. "Dampen the top half" works. "Lift the shadows on the manta" doesn't — there's no manta-shaped form. When a photographer reaches for a region effect that no geometric primitive covers, the agent logs a vocabulary gap describing the region they wanted and falls back to the global version of the adjustment, telling them where the approximation is.

## The experience — Phase 4 (subject-driven)

When `chemigram-masker-sam` (or an equivalent sibling project) ships, the experience above extends naturally. The photographer says *the manta's underbelly is too dark.* The agent recognizes "the manta's" as a subject reference, calls into the sibling project, gets back a polygon (or whatever drawn-form geometry the masker produces — the wire format is darktable's drawn-form schema, not PNG bytes), and binds it to the same drawn-mask apply path that the geometric primitives use today. The photographer judges, refines, snapshots — the same loop, just with a richer set of available shapes.

The architectural seam is already cut at the right place: `apply_with_drawn_mask` accepts a `mask_spec` regardless of who produced it. A future provider that emits darktable-compatible drawn-form geometry (gradient, ellipse, path-with-N-corners, brush, etc.) plugs in. A provider that emits PNG bytes does not — that's the lesson ADR-076 documents.

## Why now (still)

The local-adjustment friction has not improved on the tool side. darktable's local adjustment surface is roughly what it was three years ago. The opportunity to compress this in Chemigram has been sitting there.

The vocabulary architecture (PRD-003) makes local adjustments composable in a way that requires no new editing capability — only mask binding. v1.5.0 ships that binding for geometric forms; Phase 4 extends it to content-aware shapes.

If we waited until Phase 4 to ship any masking, the Mode A experience would be missing its highest-impact compositional use cases (gradients, vignettes, area emphasis) for no reason — those don't need AI. Shipping the placement-driven path now lets photographers do real work in a real loop while the content-aware path matures separately.

## Success looks like

**v1.5.0:** A photographer with a hard image (sky too bright, horizon distracting, foreground needs lift) does three to five placement local adjustments in a session. None require drawing. The vocabulary has a placement-mask entry for each common case; new ones get authored when gaps surface. The drawn-mask apply path is fast (apply + render in 2–3 seconds) and the result matches darktable's native drawn-mask behavior exactly.

**Phase 4 ship:** A photographer with a marine animal shot does four to seven local adjustments — placement and subject mixed — in 5 to 10 minutes. The subject masks come from `chemigram-masker-sam` and are accepted as-is on first generation at least 80% of the time. Refinement, when needed, takes one prompt. The mask geometry persists in the XMP, openable in darktable, identical wire format to a hand-drawn mask.

**Steady state:** The mask-bound vocabulary grows over time — gradient/ellipse/rectangle shipped today, brushed/path/freehand later, subject-aware later still. Each addition is a vocabulary entry plus the drawn-form encoder; no engine architecture change.

## Out of scope

**Custom mask-drawing within Chemigram.** The agent doesn't draw masks pixel-by-pixel. The geometric primitives parameterize known shapes; content-aware masking comes from a sibling project. Building a drawing UI inside Chemigram would violate `darktable-does-the-photography`.

**PNG-bytes mask interchange.** Retired in v1.5.0 (ADR-076). darktable doesn't read external PNGs for raster masks; the wire format is drawn-form geometry encoded into XMP `masks_history`. Future maskers must emit that, not pixels.

**Mask versioning beyond the per-snapshot binding.** Masks are part of the XMP they're bound to; a snapshot captures both the dtstyle and the mask geometry. There's no separate mask history, no mask diff UI, no merge of mask edits.

**Mask-time prompting beyond a single string.** "Make a mask of the manta" is the photographer-facing interface. Structured inputs (segmentation classes, polygon hints, point prompts) are an internal concern of the masker if it accepts them; the photographer-facing surface stays natural language.

**Multi-image masks (catalog-wide subject identification).** Each mask is per-image. No propagation across image series. Bulk-edit territory; outside scope (`gracefully-bounded`).

## The sharpest threat

**The placement-driven vocabulary may not match how photographers actually frame their requests.** A photographer who says "warm the water" doesn't necessarily mean "warm the bottom two-thirds via a gradient." They might mean "warm everywhere except the manta," which v1.5.0 can't do. If the placement primitives feel like rigid stand-ins for what the photographer actually wanted, the gap shows up as friction — they get told "the closest available is `radial_subject_lift`; want me to apply it as an approximation?" too often.

This isn't fatal. The vocabulary-gap log captures every such mismatch; the gaps directly motivate Phase 4 priorities (which subject masks matter most) and inform new geometric primitives if the gap is structural (e.g., "everywhere except a central region" → an inverted-radial primitive).

Mitigations:

- **Be honest about the placement framing.** When the photographer says "warm the water" and the available primitive is `radial_subject_lift` inverted, the agent doesn't pretend that's what was asked. It says: *the closest I have is a radial inversion — it'll warm everything outside a center oval; want me to try, or hold for a real water mask?*
- **Log every miss.** A gap with a region description is the cleanest possible Phase 4 spec. Aggregated across sessions, it tells us which subject masks matter and how to prioritize the sibling project's work.
- **Don't over-author the geometric pack.** Resist authoring a `radial_inverted_water_warm` to paper over a missing subject mask — that's vocabulary bloat that confuses both photographer and agent. Better to leave the gap visible.

If the placement primitives aren't useful enough on their own to make v1.5.0 worth shipping, the answer is clearer Phase 4 prioritization, not more shape primitives. Phase 4 is where the leverage is for the work this project's primary audience does.

## Open threads

- **`chemigram-masker-sam` repo scaffolding (Phase 4).** The sibling project doesn't exist yet. When it ships, it must produce darktable drawn-form geometry, not PNG bytes — that's the ADR-076 lesson.
- **What drawn forms beyond gradient/ellipse/rectangle should ship before content-aware masking?** Path-with-N-corners (already in dt_serialize.py) is plausibly authorable today. A vocabulary-gap survey across the next set of real sessions decides priority.
- **Cross-session mask reuse.** v1.5.0 binds the mask geometry into the XMP per snapshot; when a photographer returns to the same image, the masks come back exactly because the XMP did. No registry lookup, no regeneration.
- **The "first-session masker disclosure"** is moot in v1.5.0 — there is no masker. When Phase 4 lands, the question reopens.

## Links

- PA/audiences/photographer (expedition photographer)
- PA/promises/agent-as-apprentice
- PA/promises/the-loop-is-fast
- PA/promises/byoa-extensibility
- PA/principles/byoa
- PA/principles/honest-about-limits
- 02/Local adjustments
- 04/Masks
- ADR-007 (BYOA — no bundled AI)
- ADR-076 (drawn-mask-only architecture; supersedes ADR-021/022/055/057/058/074)
- Related: PRD-001 (Mode A — the editing surface this lives in), PRD-003 (Vocabulary as voice — the L3 primitives that get mask-bound)
