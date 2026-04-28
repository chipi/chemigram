# PRD-004 — Local adjustments through AI masking

> Status · Draft v0.1 · 2026-04-27
> Sources · 01/The work, 02/Local adjustments, 04/Masks, ADR-021, ADR-022
> Audiences · photographer (PA/audiences/photographer) — specifically the expedition photographer and the exploratory editor sub-shapes
> Promises · agent-as-apprentice, the-loop-is-fast, byoa-extensibility, inspectable-state (PA/promises)
> Principles · byoa, darktable-does-the-photography, restraint-before-push, honest-about-limits, compounding-over-throughput (PA/principles)
> Why this is a PRD · Local adjustments are the single highest-friction part of conventional photo editing and the single highest-leverage place an agent can help. They are also where AI masking — a fundamentally novel capability — meets the rest of the system. The user-value argument for *how* this integration shows up in the loop is distinct enough from PRD-001 (Mode A) that it deserves its own treatment. Mode A is *that* there's a session; this is what becomes possible inside it.

A manta ray glides through water that's gone slightly too cold and slightly too blue, the way water always does at depth. The shot is good — the angle is right, the eye is in focus, the whole creature is in the frame. But the underbelly is sunk in shadow. The water column has a faint shimmering of suspended particulate near the surface that pulls the eye upward, away from the subject. The manta's eye, the one the photographer waited two dives to catch, sits two stops too dark relative to where it should land. In darktable today, fixing these things is a forty-minute exercise: a parametric mask on luminance to lift the shadows, then a drawn mask to constrain it to the manta only because the parametric leaks into the water; a separate drawn mask on the eye, feathered carefully, then a localized contrast adjustment; a luminance-and-color parametric for the particles, then trial-and-error on the falloff. By the time the photographer gets the four adjustments to coexist, they've forgotten the original feeling that prompted them. In a Chemigram session, this is four turns. *Lift the shadows on the manta. A bit more contrast on the eye, just a touch. Warm the water column slightly. Knock back those particles up top.* Each turn is a render, a glance, a snapshot. The photographer's attention stays on the photograph.

## The problem

Local adjustments in conventional editing are where the cost of editing detaches from the *thought* of editing. The thought "lift the shadows on the manta only" takes half a second to form. Executing it on a touchscreen or with a mouse takes minutes — drawing the mask, feathering it, refining the boundary on the wing tip, checking it against the subject's edges, rebalancing when the parametric mask's luminance threshold blew through. The cost is high enough that photographers regularly skip local adjustments they would otherwise want. They settle for a global compromise — a tone curve that's slightly wrong everywhere instead of right where it matters and untouched elsewhere.

This isn't a niche frustration. The expedition photographer's most common shot — a subject against a difficult background — is the exact case where local adjustments matter most. The marine animal in colored water. The bird against a blown-out sky. The wildlife in dappled forest light. In each, the right edit is local and the cost of executing it locally is what limits how often it gets done.

The leverage from AI masking specifically (as opposed to faster mask-drawing tools, smarter parametric masks, etc.) is that *the agent identifies where the adjustment goes* in addition to applying it. "Lift the shadows on the manta" is two operations turned into one: localize the manta, then lift shadows there. The conversational interface lets the photographer skip the "localize" step entirely — the mask is generated from a description, not a drawn boundary. That's the user-value case being argued.

The risk is that this only works if the masks are good enough. A sloppy AI mask — bleeding into the water around the manta's silhouette, missing a wing tip — turns "lift shadows on the manta" into a fight. The photographer ends up correcting the mask, which is the cost they were trying to avoid. The masking quality is therefore *the gating constraint* on this feature being useful at all. PRD-004 has to address that honestly.

## The experience

The photographer is in a session in Mode A, image opened, baseline applied, talking through the photograph. They say *the manta's underbelly is too dark.* The agent reads this as a local adjustment request — the modifier *the manta's* localizes it. It calls `generate_mask` with target `"the manta"` and a prompt-shaped description. The masking provider returns a mask: a PNG, 8-bit grayscale, the manta's silhouette feathered slightly at the edges. The mask gets registered in the per-image mask registry under the symbolic name `current_subject_mask`. The agent then applies a vocabulary primitive — `tone_lifted_shadows_subject`, an L3 entry whose `mask_ref` field points to `current_subject_mask` — and renders. Two seconds later, a preview returns. The photographer judges it. *Yes. Bit more on the deepest shadows.* The agent applies a second primitive, also bound to the subject mask. Another snapshot, another preview.

The photographer says *the eye, just a hair more contrast.* The agent calls `generate_mask` again with target `"the manta's eye"`. The mask is small, oval, registered as `current_eye_mask`. The agent applies `contrast_eye_punch`, a small L3 primitive whose `mask_ref` is the temporary mask just registered. Another preview. *Perfect.* The agent has now done two local adjustments using two different masks, both registered and reusable.

When the photographer says *and warm the water column*, the agent generates a *negative* mask — everything outside the manta. It registers this as `current_background_mask`. The vocabulary primitive `wb_warming_pelagic_subtle` gets applied with that mask. Each move was: identify the region, apply the primitive, render, judge. The mechanical work — drawing, feathering, refining boundaries — is gone.

The masks themselves remain inspectable. The photographer can ask *show me the manta mask* and the agent renders the mask as an overlay on the preview. If the mask is wrong — missing a wing tip, leaking into the water — the photographer says *the mask is missing the right wing tip*, and the agent calls `regenerate_mask` with a refinement prompt. The mask is replaced (versioned via the registry), the dependent adjustments rerender automatically. This refinement loop is a few seconds, not a few minutes.

Across the session, the mask registry compounds. The manta has been masked once and is now reachable as `current_subject_mask` for any further adjustment. The eye has been masked and stays available. The photographer never sees the masks unless they ask. The agent keeps the registry as part of the per-image state, surfacing it through `list_masks` when the photographer wants to see what's there.

The masking provider is configured at the MCP level. The default — `CoarseAgentProvider` — is vision-only; it uses the agent's own multimodal capability to identify regions, no extra dependency. Quality is reasonable for clear subjects, weaker for fine detail. The production path is `chemigram-masker-sam`, a sibling project that wraps Segment Anything Model. Photographers who care about mask quality (most expedition photographers, eventually) install it and configure it as their masker. The engine doesn't care which masker is in use; the protocol is the same. A future masker provider — better, faster, optimized for marine animals — slots in identically.

## Why now

Three things converge to make this the right time:

The masking technology is good enough. SAM has matured to where mask quality on natural subjects (animals, people, objects against backgrounds) is consistently usable. Coarse agentic masking — using the multimodal capabilities of the agent itself to identify regions — is also viable as a default, even if not as sharp as SAM. Two years ago, neither existed at production quality.

The local-adjustment friction has not improved on the tool side. darktable's local adjustment surface is roughly what it was three years ago. Drawn masks, parametric masks, raster masks — the same primitives, the same UX. The opportunity to compress this with AI masking has been sitting there.

The vocabulary architecture (PRD-003) makes local adjustments composable in a way that requires no new editing capability — only mask binding. The L3 layer in the three-layer model is already designed for masked primitives. Mask-bound vocabulary entries are a darktable-native feature; the only thing we add is the mask itself.

If we waited, the architectural cost of *retrofitting* local adjustments into a Chemigram already in use would be higher than building it in from v1. And without local adjustments, the Mode A experience (PRD-001) is missing its highest-impact use case.

## Success looks like

A photographer with a hard image (marine animal, difficult water, fine details to refine) does four to seven local adjustments in a single session, in five to ten minutes total session time including the masking. None of those adjustments require them to draw a mask manually. At least 80% of generated masks are accepted as-is on first generation; the remaining 20% are refined with a single refinement prompt. The mask registry persists across the session — the same `current_subject_mask` gets used by three different vocabulary primitives without regeneration.

The provider abstraction works as designed: a photographer can switch from `CoarseAgentProvider` to `SAMProvider` (or a future provider) with a config change, and the session experience is identical except for mask quality. No code change in the engine. No vocabulary changes. The mask file format (PNG, 8-bit grayscale) accepts any provider's output.

A new local adjustment vocabulary entry (`tone_lifted_shadows_subject_subtle`, say) authored once gets reused in dozens of subsequent sessions across many images. Photographers report that local adjustments — formerly a thing they avoided — become a thing they reach for casually. The center of gravity of edits shifts from global to local.

## Out of scope

**Custom mask-drawing within Chemigram.** The agent doesn't draw masks. If the AI masking provider can't produce a usable mask for some target, the photographer falls back to darktable's drawn mask tools directly, then exports as a `.dtstyle` and registers via tagging (see `tag_mask`). Building drawing UI inside Chemigram would violate `darktable-does-the-photography` and add scope we don't need.

**Mask versioning beyond the registry.** Masks are content-addressed in the per-image objects store (RFC-003), but they don't get their own DAG. When a mask is regenerated, the old version is replaced in the registry but stays in objects/ for snapshots that referenced it. There's no "mask history" UI, no merge of mask edits, no diff between mask versions. The simplification stays.

**Mask-time prompting beyond a single string.** "Make a mask of the manta" is the interaction. We do not introduce structured inputs (segmentation classes, polygon hints, point prompts at the photographer level). Some providers (SAM) accept point prompts internally — the masker abstraction can pass them through if the agent generates them — but the photographer-facing interface is natural language only.

**Multi-image masks (catalog-wide subject identification).** Each mask is per-image. We do not propagate masks across an image series, even when subjects recur. That's bulk-edit territory; outside scope (`gracefully-bounded`).

**Provider quality benchmarking inside Chemigram.** We document mask quality expectations for each provider in CONTRIBUTING.md and in the masker repo's README. We don't ship in-engine benchmarking, mask-quality metrics, or provider comparison tools. Photographers evaluate by using.

## The sharpest threat

**Mask quality on the default provider may be insufficient for the work the project's primary audience does.** The expedition photographer's subjects — marine animals in colored water, animals partially occluded by foliage, birds against bright skies — are exactly the cases where mask quality matters most and where coarse agentic masking is weakest. SAM is dramatically better but adds a setup step (Python environment, model download, ~2.5GB). If photographers try the default, find it insufficient, and don't follow through to install SAM, they conclude *local adjustments don't work* and leave.

This isn't a build-risk; we can ship it. It's an impact-risk. The default user experience determines whether this feature succeeds.

Mitigations under consideration:
- **Make the default honest.** Don't pretend coarse agentic masking is good. The first time a session uses a generated mask, the agent flags the masker in use and what its limits are: *"Using the default masker (vision-only). For sharper masks on fine detail, install chemigram-masker-sam."* Sets expectations.
- **One-command SAM install.** A bundled installer script that handles the Python environment + model download + MCP config in one step. Removes the install friction without bundling the dependency in the engine.
- **Quality-aware mask refinement.** If the agent can detect (or be told) that a mask is poor, it can offer to regenerate with the alternative provider if available. The photographer says *the mask isn't great* and the agent responds *want me to try SAM if you have it installed?*
- **Document the SAM path heavily.** README, CONTRIBUTING, the post-install message, the first-session welcome — all point toward SAM as the production path. Coarse agentic is the *zero-friction try-it-out* path, not the *production* path.

If mask quality with SAM proves insufficient even for the work, then the answer becomes a better masker — likely a domain-specialized one (marine animals, wildlife) as a sibling project. The architecture allows this without engine changes, but the lead time is real. This is the threat to monitor.

## Open threads

- **RFC-004 (default masking provider — coarse vs SAM)** — the deliberation that closes into the v1 default choice. Currently leaning toward `CoarseAgentProvider` as default with SAM as documented production path, on `byoa` and friction grounds. Awaiting evidence from real session use.
- **RFC-009 (mask provider protocol shape)** — the protocol contract that lets providers slot in. Affects this PRD because the protocol determines what kinds of providers are admissible.
- **`chemigram-masker-sam` repo scaffolding.** The sibling project doesn't exist yet. Needs to be created, MIT-licensed, with the same MCP-server pattern as the engine itself.
- **Mask refinement UX in the agent prompt template.** When a photographer says *the mask is wrong*, what's the standard agent response shape? Currently informal. Worth codifying so refinement feels predictable.
- **The "first-session masker disclosure."** Should the agent warn about masker capabilities on first use, on every session, or only when masks fail? Behavioral choice that affects how users form expectations. Recorded in TODO.
- **Cross-session mask reuse** — if a photographer comes back to the same image two days later, can `current_subject_mask` be regenerated identically, or is it a fresh mask? Answer: fresh, because masking provider quality may have changed. But documented.

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
- ADR-021 (three-layer mask pattern)
- ADR-022 (mask registry per image with symbolic refs)
- ADR-033 (MCP tool surface — masking tools)
- RFC-004 (default masking provider)
- RFC-009 (mask provider protocol)
- Related: PRD-001 (Mode A — the editing surface this lives in), PRD-003 (Vocabulary as voice — the L3 primitives that get mask-bound)
