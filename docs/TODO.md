# Chemigram — TODO and Research Backlog

*Things we want to keep our eyes open for, enable when ready, but aren't building right now.*

This is not the implementation plan. The implementation plan is in `docs/IMPLEMENTATION.md` (Phases 0–5). This is the **lower-priority surface** — research directions, possible side projects, "if we ever invent secret sauce" hooks. Items here should be revisited when the core is working.

---

## Slice 1 deferrals

Things explicitly punted from Slice 1 as documented in closing ADRs. Track here so they don't get lost.

### Path B — new-instance addition in the synthesizer

**Status:** Deferred per **ADR-051** (closes RFC-006). RFC-001 is `Decided` but its iop_order origin question remains open.

**The gap:** `synthesize_xmp` raises `NotImplementedError` whenever an input plugin's `(operation, multi_priority)` tuple is not present in the baseline XMP (the "add new instance" case). Phase 0 iteration 1 confirmed darktable 5.4.1 silently drops new-instance entries that lack `iop_order`, but neither `.dtstyle` nor XMP carries that attribute in 5.4.1 — so the synthesizer has no source of truth.

**Trigger to revisit:** when a vocabulary primitive needs to add a module instance not present in the baseline auto-presets pipeline (e.g., a drawn-mask gradient, a custom denoise level). At that point, write a follow-up RFC (or amend RFC-001) covering iop_order origin: lookup table per `(operation, modversion)`, vocabulary-manifest declaration, runtime probe of darktable, etc.

**Workaround for Slice 1:** primitives that target operations already present in the baseline (every operation in darktable's auto-applied pipeline) hit Path A and work today.

### dtstyle parser does not validate same-`(operation, multi_priority)` collisions inside one file

**Status:** Deferred per **ADR-051** (RFC-006 proposal #1 not implemented in Slice 1).

**The gap:** the parser accepts a `.dtstyle` containing multiple `<plugin>` records with the same `(operation, multi_priority)`. They each get applied in document order during synthesis (last-writer-wins per ADR-051 rule 3). The original RFC-006 proposal #1 wanted this to be a `DtstyleSchemaError` at parse time.

**Trigger to revisit:** when a real misauthored vocabulary entry surfaces this confusion (vocabulary review process is the first line of defense; CI manifest validation is the second). If/when surfaced, add a parser check.

### `chemigram-mcp` PyPI entry point

**Status:** Removed from `pyproject.toml` `[project.scripts]` until Slice 3.

**The gap:** declaring `chemigram-mcp = "chemigram.mcp.server:main"` before `chemigram/mcp/server.py` exists makes `chemigram-mcp` from the shell raise `ModuleNotFoundError`. Re-add when Slice 3 lands the MCP server.

---

## Color science reverse-engineering across sensors

**Status:** research direction, possible side project.

**Idea:** fitting Fuji film simulations (or any look-committed L2) to bodies that didn't produce them. A `fuji_acros` `.dtstyle` that's calibrated to *Sony A1* color science, not Fuji X-Trans, so it produces an Acros-like look from ARW input rather than a spirit-of-Acros-but-not-quite.

**What this involves:**
- Capture color checker on each target body in even daylight.
- Capture matched scenes on a Fuji body in the target sim.
- Fit a transform (3D LUT + tone curve) per (target_body, source_sim) pair.
- Output: a per-body family of `.dtstyle` files, e.g. `fuji_acros_for_sony_a1.dtstyle`.

**Why this is interesting:**
- Genuine value to the broader community of Nikon/Canon/Sony shooters who want Fuji looks.
- Procedural, repetitive work — strong candidate for Mode B autonomous fitting.
- Per-sensor calibration is a small, scoped research project of its own.

**Why we're not doing it now:**
- Out of scope for the core feedback-loop research question.
- Needs Chemigram's color-science extensibility hook (see next item) to land cleanly.
- Best done once the core engine is stable and Mode B is working — then this becomes a *use case* of Mode B rather than a separate effort.

**Watch for:** when the core is solid and Mode B exists, this is a natural first "applied" Mode B project. It also doubles as an evaluation harness for Mode B itself — color checker fitting has a clear ground truth, so we can measure the agent's convergence quality objectively.

---

## Programmatic vocabulary entry generation (Path C)

**Status:** stretch goal — but **Phase 0 testing strengthened the case** for building this earlier than originally planned.

For modules with well-understood param structure (exposure, color calibration, tone equalizer, color balance rgb), the agent could generate `.dtstyle` entries on the fly: encode the hex `op_params` from a desired parameter set, wrap in the XML schema, save. Closes vocabulary gaps without authoring everything in advance.

**The catch:** each module's param-encoding is its own engineering project (modversion-pinned C struct serialization). Doing this for *all* modules is the same combinatorial cost as authoring vocabulary by hand.

**Realistic scope:** a small set of high-value modules (probably 4-5) where the agent can fluently generate entries. Modules with continuous-numeric parameter spaces are best candidates — they're where vocabulary granularity bites hardest.

### Exposure is the natural first candidate (Phase 0 evidence)

Phase 0 testing established three independent reasons exposure is the right module to start Path C with:

1. **Simplest param structure** — exposure's `op_params` is a 28-byte struct with a single user-relevant float at predictable byte offset. Iteration 3 of Phase 0's experiment 4 directly demonstrated programmatic editing: changing `0000003f` (+0.5 EV) to `00000040` (+2.0 EV) at the right position produced the expected render. ~10 lines of Python suffices.

2. **darktable GUI cannot author literal zero** — exposure slider has minimum granularity ~0.009 EV. A true `expo_+0.0` no-op primitive cannot be authored through the GUI alone. This is the only way to produce a literal-neutral exposure entry.

3. **Continuous control is genuinely useful for exposure** — the agent often wants slightly different exposure values than what's in the discrete vocabulary (`+0.3`, `+0.5`, `+0.8`). With Path C exposure, the agent can compose `+0.42` directly when the photographer's brief calls for that.

**Trigger to build:** earlier than originally planned, possibly as part of Phase 1's polish phase. The exposure encoder is small (~50 lines), well-understood, and unlocks both literal-zero primitives and continuous exposure control.

**Trigger for additional modules:** when `vocabulary_gaps.jsonl` shows specific other modules (probably color calibration WB, tone equalizer, color balance rgb shadows/highlights) repeatedly appearing in gap reports across many sessions, those become the next Path C candidates.

**Architectural fit:** lands as a new `ProgrammaticVocabularyGenerator` subsystem. The agent calls it via a tool: `generate_primitive(module, params, name) -> dtstyle_path`. The new entry registers in the vocabulary for the rest of the session (and, if the photographer accepts it, persists).

---

## taste.md synthesis tooling

**Status:** part of `agent-context.md`'s end-of-session pattern. v1 has the propose-and-confirm flow; periodic synthesis is v2.

After every 10-20 sessions, `taste.md` may have redundant entries, contradictions, or outdated notes. The agent should be able to synthesize:

- Detect overlapping notes ("prefer subtle structure" vs. "tend to use subtle over strong" — same observation, two notes)
- Detect contradictions ("avoid clarity_strong" but used 4 times last month)
- Propose a re-organized v2 of taste.md for photographer review

Lightweight tooling: read taste.md, read recent session logs, propose diff. Photographer accepts or revises. Same propose-and-confirm discipline as in-session updates.

**Trigger to build:** when taste.md crosses ~50 entries and starts being unwieldy.

---

## Specialist mask caching by subject

**Status:** observed in worked examples; build when there's a pattern.

When prompted segmentation succeeds for a specific subject ("iguana eyes," "mobula belly," "manta gills"), it would be useful to cache the successful prompt + segmentation approach for future sessions on similar subjects. Faster turnaround, more consistent masking.

**The shape:**
- A `mask_recipes.jsonl` per workspace (or shared across workspaces?) that records (subject, prompt, generator config, success rating).
- Agent consults this when generating a mask for a known target type.
- Photographer can review and refine recipes over time.

**Open question:** is this useful enough to build, or does it add machinery for marginal benefit? Real Mode A use will tell.

---

## Mask overlay render mode

**Status:** small UX improvement, build when render-preview-with-overlay would speed up sessions.

Currently, mask verification requires a separate render mode showing the mask boundary. A combined render that shows both the photo and the mask overlay (semi-transparent boundary lines, color-tinted mask region) would speed up mask review.

**Trigger to build:** if mask review is consistently a 2-turn process (verify mask, then apply move) when it could be a 1-turn process (apply with mask shown in preview).



**Status:** small architectural commitment for v1, supports the item above when it comes.

**Idea:** users (or future Chemigram tooling) drop custom color-science assets into the vocabulary directory and reference them from `.dtstyle` entries.

**Specifics:**
- A `chemigram-vocabulary/profiles/` directory holding `.icc` profiles, 3D LUTs (`.cube`), basecurve presets.
- L1/L2 vocabulary entries can reference these via relative path.
- XMP synthesizer copies the path into the relevant module config; darktable reads the asset at render time.
- Validator checks referenced files exist at vocabulary load time.

**Why this is in TODO and not architecture:**
- Architectural surface is small (~50 lines in synthesizer + validator).
- We don't *use* it in v1 — but we don't want to retrofit it either.
- Document the directory structure now, implement when the first use case appears.

**Cleanest landing:** a paragraph in `vocabulary.md` (when written) plus a stubbed-out `profiles/` directory in the bundled vocabulary. Empty for now.

---

## Mode B evaluation function — keep all hypotheses open

**Status:** open research question. Don't commit to a single approach.

When Mode B (autonomous fine-tuning loop) gets built, the eval function is the central design question. Three candidates, all worth exploring:

1. **Reference-based.** Photographer provides one or more reference images; agent scores candidates by perceptual similarity (LPIPS, CLIP embedding distance, or similar). Strong signal when reference exists. Doesn't generalize to "make this image great" without a target.

2. **Vision-model self-eval against criteria.** "Does this image satisfy the brief?" — agent uses its own vision capability to judge. Subject to the same biases as the generator. Easiest to implement; possibly weakest signal.

3. **Learned critic from Mode A history.** After accumulated Mode A sessions, train a small classifier on (candidate_a, candidate_b, photographer_preferred) tuples. The critic encodes *this photographer's* taste. Slowest to bootstrap (needs preference data), highest aligned signal once trained.

**Likely path:** combine. Reference-based when a reference is available. Self-eval as a baseline. Learned critic as it becomes available, weighted in over time.

**Action item:** when Mode A is shipping and accumulating session data, instrument it to capture preference pairs cleanly so the learned-critic option is available when wanted.

---

## Auto-fit tooling for color science

**Status:** future Mode B application, depends on color-science hook landing.

Standalone-ish tool: takes a pair of color-checker captures (target body + reference sim), runs an iterative fit (Mode B autonomous loop with perceptual eval), produces a `.cube` LUT and `.dtstyle` wrapper.

This is what makes "color science reverse-engineering" practical for non-experts. Without auto-fit, fitting one sim to one body is hours of work; with it, it's an overnight Mode B run.

**Watch for:** valuable if Mode B works well. Becomes the killer use case for Mode B.

---

## External processor / GenAI integration as pipeline stages

**Status:** keep architectural door open. Build only when first concrete use case appears.

Per `architecture.md`, the render pipeline is a **sequence of stages**, of which v1 has one (darktable-cli). The abstraction admits future stages:

- **Local Python processors** — custom algorithms, "secret sauce", pretrained models.
- **External CLIs** — `rawtherapee-cli`, `art-cli`, ImageMagick passes.
- **GenAI tools via MCP** — upscalers, sky replacement, generative fill, denoise models, super-resolution.
- **Specialist sub-agents** — narrow-task agents invoked as a pipeline stage.

**Why in TODO:** v1 doesn't need any of these. But the pipeline-stages abstraction in architecture.md keeps the door open at near-zero cost.

**Watch for:** when a specific use case emerges that genuinely can't be expressed as a darktable module + vocabulary entry, build the second pipeline stage. Resist building it speculatively.

---

## "Secret sauce" image processing

**Status:** open door, no plans.

If Chemigram ever invents image-processing capability darktable doesn't have — a specialized backscatter remover, a learned underwater color recovery model, anything — it lands as a pipeline stage (see above) or as a custom module via darktable's plugin system.

**Why in TODO:** preserves optionality without committing engineering. The "darktable does the photography, Chemigram does the loop" principle in `architecture.md` is the *current* discipline; it doesn't preclude a future where Chemigram earns its own image-processing capability for a specific reason.

**The bar to cross:** any custom processing must be (a) something darktable genuinely can't do, (b) good enough to justify maintaining it long-term, (c) clearly improving the research question, not just feature-adding.

---

## DAM, taxonomy, classification — out of scope, possibly a sibling project

**Status:** deliberately deferred. Possibly an entirely separate project later.

Image classification, tagging, taxonomy management, catalog organization, search, smart collections — none of this is Chemigram. The temptation is real (vision models are good at classification, the agent loop and pipeline-stages substrate would mostly transfer), but the risks are:

- **Scope creep the project can't survive.** Chemigram is a research probe into taste transmission. A DAM is a multi-year product. Trying to do both means doing neither well.
- **Different change rates.** Editing is per-image deep work; tagging is bulk shallow work. Coupling them couples concerns that should evolve independently.
- **Different research questions.** Editing asks "can I transmit taste"; tagging asks "is this vision model accurate enough at classification." Both interesting, but not the same experiment.
- **Different users.** A photographer might want Chemigram for one image and a real DAM for the other 49,999. Forcing them to pick is bad.

**The honest framing:** this would be a separate sibling project that *shares substrate* with Chemigram (vision model access, agent loop infrastructure, raw file reading, XMP read/write, possibly the pipeline-stages contract) but *not architecture* (different tool surface, different research question, different user-facing shape).

Possible name for the future sibling: TBD. Possibly "Taxon" or similar — the point is it's not Chemigram, it's a separate thing.

**What such a project might look like (preserved here so we don't lose the thinking):**

- *Tagging splits into hierarchies:* identification (what's literally in frame, vision model's job), classification (what kind of photo, vision + heuristics), curation (is this any good — photographer's job), context/story (EXIF + manual), personal taxonomy (idiosyncratic categories — taste, hardest).
- *Vision models are good at identification + classification, mediocre at context (with EXIF help), bad at curation and personal taxonomy.* The automation surface is genuinely the first two.
- *Tags belong in standard XMP fields* (`dc:subject`, `xmp:Label`, `xmp:Rating`) so they travel between tools. A derived index for fast querying is fine, but XMP is the source of truth.
- *Taxonomy schemas are user content,* not engine content. A photographer authors (or borrows) a hierarchical schema; the system provides mechanism, not policy.
- *The bulk workflow shape* is a Mode-B-like pipeline: process N raws in parallel, vision-model classifies, high-confidence tags written automatically, low-confidence surfaced for review. Confidence thresholds tunable.
- *Integration with Chemigram* would be loose: tags could drive L2 suggestions ("photo tagged underwater_pelagic → suggest `underwater_pelagic_blue`"), or filter Mode B campaigns ("run autonomous editing on every photo tagged `wildlife + golden_hour`"). But Chemigram doesn't *require* tags — it works on a single raw with no taxonomy.

**Watch for:** any signal that Chemigram is being asked to do classification, smart collections, search, catalog management, library organization, or anything DAM-shaped. That's a sign to either (a) say no, or (b) acknowledge that the sibling project's time has come and start it as a separate effort.

**Explicit non-goals for Chemigram that this clarifies:**

- No catalog. Chemigram is per-image.
- No search beyond filename / image_id.
- No smart collections.
- No tag management UI.
- No bulk-tagging tools.
- Reading existing XMP tags as input to L2 suggestions (e.g. honoring `FujiFilmSimulation`) is fine because it's *consuming* metadata, not managing it.

---

## L1 learned binding suggestions

**Status:** small enhancement to the existing L1 rules system, build when there's a use case.

The L1 rules in `config.toml` are user-authored. As the photographer works through Mode A sessions, patterns emerge: applied `lens_correct_full + denoise_auto` to twenty D850+24-70 images in a row, never overrode. Chemigram could *notice* and *suggest*: "I've seen you apply this binding 20 times for D850+24-70. Want me to write it into your config?"

Three properties matter:

1. **Surface, don't enact.** The agent doesn't silently start applying L1 it inferred. It tells the photographer, the photographer confirms, the rule lands in `config.toml` where it can be reviewed and edited like any other config.
2. **The rules file is the single source of truth.** Whether written by hand or accepted from a suggestion, rules live in the same place, in the same format. No "learned rules" hidden in a database.
3. **Rules support compound conditions.** Not just camera+lens — also ISO ranges, focal length ranges, time of day from EXIF, etc. Overlays (rules that *add* to whatever else matched) are a useful pattern: "always strong denoise above ISO 3200, regardless of which lens."

**Open question:** what's the threshold for surfacing a pattern? "Applied 5+ times consistently for the same EXIF signature, no overrides" is a starting heuristic. Tunable.

**Why this matters:** turns Chemigram from a tool you configure once into a tool that helps you crystallize what works, while keeping the photographer in the loop on every commitment. Aligns with the stance that L1 is opt-in and photographer-driven, not assumed.



**Status:** speculative, not on roadmap.

Possible futures:

- Shared vocabulary repos that multiple photographers contribute to (community L3 vocabularies for specific genres).
- Comparing your taste vs. another photographer's via their captured Mode A preference data.
- A "vocabulary marketplace" — but this risks becoming a product instead of a research project.

**Watch for:** keep these as warning signals. If we drift toward building any of these, we've drifted away from the research question. Useful only if they support the question.

---

## Engine operations not in MCP surface (yet)

A few engine capabilities deliberately not exposed to the agent in v1:

- `gc(image)` — garbage-collect unreachable snapshots
- `merge_pick(image, source_hash, primitives)` — cherry-pick primitives across branches
- `compact(image)` — reorganize objects directory
- Direct vocabulary editing from the agent (the agent can't author new primitives, only use existing ones)

**When to expose:** only when there's a concrete use case. Keeping the agent's surface narrow is a feature.

---

## Items to capture as they emerge

(Append below. Lightweight, no formatting standards required.)

- ...
