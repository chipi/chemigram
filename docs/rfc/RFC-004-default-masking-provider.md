# RFC-004 — Default masking provider — coarse vs SAM

> Status · Draft v0.1
> TA anchor ·/components/ai-providers ·/constraints/byoa
> Related · ADR-007, ADR-021
> Closes into · ADR (pending) — settles the v1 default
> Why this is an RFC · ADR-007 commits to BYOA (no bundled AI), but the v1 release needs *some* default masking capability or first-time users hit a wall. Two viable defaults exist with different trade-offs around quality, dependencies, setup friction, and user expectations. The choice shapes onboarding and what "out of the box Chemigram" feels like.

## The question

What ships as Chemigram's default masking provider? Two candidates:

- **Coarse agent-based provider** — uses the photo agent's vision capability. The agent looks at the image, identifies the subject, and emits bbox/gradient/color-region descriptors that the engine converts into darktable parametric/drawn masks. No ML dependency. Quality is bounded by what the agent can describe.

- **SAM-based provider** — bundled or sibling project (`chemigram-masker-sam`). Subject masking via Segment Anything Model. PyTorch dependency, model weights, GPU/MPS configuration. High quality.

The decision must balance: ADR-007's BYOA principle, first-time-user experience, the maturity of the masking pattern (whether photographers will be willing to swap providers), and Chemigram's identity as a substrate vs a turnkey tool.

## Use cases

- A new user installs Chemigram, opens an underwater image, asks the agent to "lift the shadows on the fish." The default masking provider must produce *something* that approximates a fish mask.
- A serious user invests in a quality masker (SAM, a hosted service, a custom-trained model). They expect to swap the default cleanly.
- The agent-coarse provider's quality is genuinely insufficient for production work but adequate for v1 demos and initial experimentation.

## Goals

- Out-of-the-box masking that works for first-time users
- BYOA principle preserved (engine doesn't depend on PyTorch)
- Clear path for users to upgrade to better masking
- Default is adequate for demos and initial experimentation but not pretending to be production-grade

## Constraints

- TA/constraints/byoa — engine has no PyTorch dependency
- ADR-007 — AI capabilities are MCP-configured, not bundled in `chemigram.core`
- No GPU/MPS configuration in the engine setup

## Proposed approach

**Ship `CoarseAgentProvider` as the v1 default. Document `chemigram-masker-sam` as the recommended production upgrade.**

Rationale:
- The coarse provider runs without any ML dependency — first-time users are masking immediately.
- BYOA stays clean: PyTorch never enters `chemigram.core`'s dependency graph.
- Photographers who hit the coarse provider's quality ceiling have a clear, documented upgrade path.
- The coarse provider is a useful **fallback** even after upgrading: when SAM is misconfigured or the photo agent's vision is preferred for fast iteration, falling back to coarse keeps the workflow alive.

`CoarseAgentProvider` implementation:
- Receives a render of the image, a `target` ("subject", "sky", "highlights"), an optional natural-language prompt.
- Calls the photo agent with the image + a structured request: "produce a bbox, gradient direction, or color/luminance range that approximates the masked region."
- Gets back structured JSON.
- Converts to a darktable parametric mask (luminance/chroma range) or drawn mask (gradient/circle) via the synthesizer.
- Writes a "mask description" to the registry alongside the actual rendered raster (yes, raster — we render the parametric/drawn mask to a PNG so other vocabulary entries can reference it the same way they reference SAM-generated masks).

`chemigram-masker-sam`:
- Sibling project, separate repo, separate release.
- Implements `MaskingProvider` Protocol via MCP.
- User installs separately: `pipx install chemigram-masker-sam`.
- Configures via `~/.chemigram/config.toml` to register as the masking provider.
- Engine doesn't know about it; it's just an MCP server the agent's photo client connects to.

## Alternatives considered

- **Bundle SAM as v1 default:** rejected — adds PyTorch + MPS configuration to setup, ties release cadence to model availability, makes "Chemigram for Apple Silicon" different from "Chemigram for Linux + CUDA." The friction is substantial for what's ultimately one optional capability. Violates BYOA.

- **Bundle a tiny model (MobileSAM):** considered as a middle ground. Lighter than SAM but still adds PyTorch as a hard dependency. Defer until the coarse provider is shown inadequate in real use.

- **No default at all (force users to install a provider before any masking works):** rejected — too steep an onboarding cliff for a v1 release. First-time users need to see something work to get hooked.

- **Coarse provider as default, SAM bundled as opt-in via extra dependency group (`pip install chemigram[sam]`):** rejected — still pollutes the dependency surface, makes the "what does Chemigram require?" answer non-binary. Cleaner to keep SAM in a sibling project.

## Trade-offs

- Coarse provider's quality ceiling is real — it can't isolate "the fish but not the rocks" reliably. Users discovering this upgrade to a better provider.
- The MCP-as-masking-provider pattern means setup involves running another MCP server alongside the agent. Documentation makes this explicit.
- Two-provider system (coarse + SAM) adds documentation complexity. Mitigated: the docs structure (default vs upgrade) is straightforward.

## Open questions

- **What's the threshold for users hitting the upgrade cliff?** If the coarse provider is *almost good enough* most of the time, users may stay there forever and the upgrade story stays theoretical. Needs real-session evidence to calibrate.
- **Should the engine surface "this mask is approximate" hints?** The coarse provider's output is parametric/drawn; quality is harder to assess than SAM's pixel-level segmentation. Should the registry's metadata include a quality estimate? Proposed: yes — `provider_quality_estimate: "approximate" | "production"` field.
- **Hybrid: use coarse for quick iteration, SAM for final?** Workflow pattern, not a v1 design question — surfaces from real use.
- **Caching of SAM results.** SAM is expensive (1-3 seconds on Apple Silicon). Caching keyed by render hash + target + prompt is obvious. Defer to RFC-009 (mask provider protocol shape) for the caching contract.

## How this closes

- **An ADR locking the v1 default** — `CoarseAgentProvider` ships as default; `chemigram-masker-sam` is documented as the recommended upgrade path.
- This ADR may be revisited if v1 evidence shows the coarse provider is dramatically inadequate for the dominant use cases.

## Links

- TA/components/ai-providers
- TA/constraints/byoa
- ADR-007 (BYOA)
- ADR-021 (three-layer mask pattern)
- RFC-009 (mask provider protocol shape)
