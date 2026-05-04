# PRD-003 — Vocabulary as voice

> Status · Draft v0.1 · 2026-04-27
> Sources · 01/The work, 02/Vocabulary, 03/Vocabulary primitives
> Audiences · photographer (PA/audiences/photographer) — specifically the taste-articulator sub-shape; contributor (PA/audiences/contributor)
> Promises · vocabulary-as-voice, compounding-context, gracefully-bounded (PA/promises)
> Principles · darktable-does-the-photography, vocabulary-grows-with-use, restraint-before-push, honest-about-limits (PA/principles)
> Why this is a PRD · The vocabulary system is *the* substrate enabling everything else — Mode A, Mode B, local adjustments, the agent's whole action space. But the vocabulary itself is also a user experience: photographers author it, watch it grow, share it, read it back as a portrait of their craft. The user-value argument here is the central research thesis of the project, and it's distinct enough from "Mode A's conversational loop" that it deserves its own argument.

A year into using Chemigram, the photographer opens `~/.chemigram/vocabulary/personal/manifest.json` and scrolls. There are 187 entries. `wb_pelagic_recovery_subtle`. `radial_subject_lift_warm`. `fuji_acros_red_filter_personal`. `clarity_rock_texture_session_dry`. `gradient_bottom_warm_foreground`. Each one was authored on a specific evening, for a specific image, when the agent didn't have a word for what was wanted. Some were authored once and used hundreds of times. Some were authored once and never used again. Reading the list is unexpectedly moving — it's a self-portrait. Not "what I look like" but "how I edit." The names alone tell a story: the photographer who keeps reaching for *subject* and *recovery* and *rock texture* is someone with a body of work centered on living things in difficult light. They didn't choose those words abstractly; they accumulated them by editing. The vocabulary is the photographer's voice, made visible.

## The problem

The way photographers normally articulate craft is in fragments: a workshop conversation ("I always lift shadows with the parametric mask, never the tone equalizer for portraits"), a forum post ("here's how I handle underwater highlights"), a blog walkthrough of one image. Each is partial, each is occasion-driven, each is hard to share or hand off.

What's missing is a *systematic vocabulary* that captures how a photographer actually edits — not as prose explanation but as *named, executable, inspectable artifacts*. Lightroom's "presets" are the closest existing thing, but they fail in three ways: they're opaque (you can't read what a preset does without applying it), they're not versioned (when Lightroom updates, your presets silently behave differently), and they're not the photographer's *active vocabulary* — they're a frozen archive at the moment they were saved.

The research thesis underneath Chemigram is: if you give a photographer a system that *encourages* them to articulate vocabulary as they edit (not as a separate authoring chore), and the vocabulary is darktable-native and inspectable and versioned, then over months, the photographer accumulates an artifact that represents their craft in a form they can *use* (in sessions), *share* (with another photographer), and *reflect on* (as a self-portrait).

The problem is that this thesis hasn't been tested. There's no comparable artifact existing today. PRD-003's user-value argument is for *the photographer who values their own taste enough to want it articulated* — and is willing to invest the authoring work to get there.

## The experience

The photographer starts with the **starter vocabulary** — a small pack of generic primitives shipped with Chemigram. Maybe 30-50 entries: basic exposure adjustments, common WB moves, generic tone primitives, a couple of L1 templates. Enough for the first few sessions to be productive without immediately hitting gaps. The starter vocabulary is intentionally generic; it's the floor, not the ceiling.

In a session, the agent reaches for `radial_subject_lift` (expressive-baseline) and applies it. The photographer says, "yes, but tighter — the radius is too wide for this composition, and the lift is too aggressive." The agent doesn't have an entry for that exact intention. It improvises (suggests `radial_subject_lift` with the photographer eyeballing the result, or falls back to a global exposure nudge). It logs the gap. The session continues.

Later — that night, or next weekend, or in a focused vocabulary-authoring evening — the photographer opens darktable, sets up the move they want (a tighter ellipse on the subject, smaller falloff, dialed-back exposure), captures it as a `.dtstyle` named `radial_subject_lift_subtle`. Adds a manifest entry: layer L3, subtype `exposure`, touches `exposure`, `mask_spec: {"dt_form": "ellipse", "dt_params": {"center_x": 0.5, "center_y": 0.5, "radius_x": 0.15, "radius_y": 0.15, "border": 0.08}}`, description "subject-area exposure lift, tighter radius and softer falloff than `radial_subject_lift`." Drops both files into their personal vocabulary. From the next session on, this primitive is part of the agent's action space — `apply_primitive` routes through the drawn-mask path automatically because `mask_spec` is set (per ADR-076).

The starter vocabulary stays untouched (or gets updated upstream, never edited locally). The personal vocabulary grows. After 6 months: maybe 50 personal entries. After a year: 150-200. Each one was authored deliberately, for a real need that surfaced in a real session. The vocabulary is *not generic* — it's shaped by the photographer's actual work.

The contributor experience is parallel but distinct. A photographer who's accumulated a coherent thematic vocabulary (e.g., a Fuji shooter with 30 polished film-simulation primitives) can extract a community pack — strip out the personal-specific entries, write attribution, document calibration, submit a PR. Other Fuji shooters install the pack. Quality vocabulary becomes shared infrastructure. The community grows by accumulation, not by central planning.

Throughout, the vocabulary is **inspectable**. `cat fuji_acros_red_filter.dtstyle` shows the XML. The manifest entry's description tells what the move does. Reading another photographer's vocabulary tells you something about how *they* edit. The artifact is a research surface (PA/audiences/researcher) — anonymized vocabulary collections become a corpus for studying how taste articulates differently across photographers.

## Why now

1. **darktable's `.dtstyle` format makes this tractable.** Vocabulary primitives are darktable's native representation of edits — captured by clicking "create style," exported as XML, parseable without proprietary decoders. ADR-001 and ADR-008 commit to this; without darktable's format, vocabulary authoring would require either a custom parameter editor (huge engineering work) or proprietary blob handling (no inspection). darktable made this approach possible.

2. **MCP enables vocabulary use.** Without an agent that can call vocabulary as named tools (`apply_primitive("gradient_top_dampen_highlights")`), the vocabulary is just a file collection. MCP turns it into an action space.

3. **The hunger for non-generic photo tools is real.** Photographers who've spent years on Lightroom presets are increasingly frustrated by their genericness. A tool that produces *their* vocabulary, not a borrowed one, occupies an open space.

A year from now, the case is the same — but the substrate (darktable, MCP, agent reliability) is older and more crowded. Now is the time to build the artifact while the space is open.

## Success looks like

- A photographer who's used Chemigram for 6 months can show their `manifest.json` to another photographer and have it read as recognizably theirs. The naming patterns, the layer distributions, the masking conventions are stable enough across the artifact that the photographer's voice emerges from it.

- Vocabulary expansion happens *in response to gaps*, not as separate authoring sessions. After a session where the agent improvised, the photographer's natural reaction is "I should make that a primitive" — and authoring is fast enough (a few minutes in darktable's GUI plus a manifest entry) that the work happens.

- The starter vocabulary is small enough that it's clearly insufficient. New users immediately encounter gaps; encountering gaps is part of the loop, not a failure.

- At least one community pack exists, contributed by a photographer who isn't the project author, with clear attribution and a coherent theme. Demonstrates the contribution path works.

- The vocabulary's inspectability passes the simplest test: a photographer reading another photographer's pack can guess what the entries do from their names and descriptions, without applying them.

## Out of scope

- **Generic, comprehensive vocabulary "for everyone."** Vocabulary is photographer-shaped. The starter is generic; the personal is specific; community packs are thematic. There's no project goal of "ship 1000 primitives that cover every situation."

- **Auto-generated vocabulary from photographer history.** Tools that watch a photographer's Lightroom session and generate Chemigram primitives are not in scope. Authoring is a deliberate craft act (PA/principles/vocabulary-grows-with-use); auto-generation would defeat the articulation thesis.

- **Cross-darktable-version vocabulary portability.** Vocabulary is modversion-pinned (ADR-026). When darktable bumps a module's modversion, affected primitives need re-authoring. We don't try to magically translate. Per RFC-007, the failure mode is loud (warning), not silent (drift).

- **Continuous-parameter vocabulary by default.** Vocabulary primitives are coarse-grained (`expo_+0.5`, not `expo_+0.42`). Programmatic generation (Path C; RFC-012) is reserved for high-value modules and only when evidence shows the granularity matters.

- **Marketplace / monetized vocabulary.** Community packs are MIT-licensed by default. Commercial vocabulary distribution is not in scope for v1; if a contributor wants to license their pack differently, the per-pack license override path exists (ADR-032 / LICENSING.md) — but the project doesn't host or facilitate sales.

- **Encrypted or proprietary vocabulary.** Vocabulary is plain text + plain `.dtstyle` XML. No proprietary format. Inspection is a feature, not a vulnerability.

## The sharpest threat

The thesis depends on vocabulary authoring being *low-friction enough* that it actually happens. If authoring is a chore — if it interrupts the editing loop, if the manifest schema is fiddly, if `.dtstyle` capture fails for one in five attempts — photographers won't author. Their vocabulary stays at "starter pack + 5 entries I made in a burst of motivation." The compounding promise collapses: after a year, the artifact is barely larger than at the start, and it doesn't represent the photographer's voice.

The frame that breaks: that the *authoring discipline* (ADR-024 — uncheck non-target modules in the create-style dialog), the *manifest schema* (ADR-023 — JSON metadata per entry), and the *modversion pinning* (ADR-026) together produce a workflow that's lightweight enough to be a natural part of editing rather than a separate task.

Specific risks:
- **Authoring discipline is brittle.** Forgetting to uncheck modules produces noisy `.dtstyle` files. The parser is defensive (ADR-010), but reviewers see the noise. If contributors find the discipline annoying, vocabulary submissions slow.
- **Manifest schema is fiddly.** Required fields (layer, subtype, touches, modversions) might be wrong or missing on common entries. Validation errors in CI become friction.
- **darktable's create-style dialog is what it is.** We can't change darktable's UX. If new darktable releases change the dialog in ways that break the authoring flow, we have to adapt.

Mitigations under consideration:
- **Authoring helper tool.** A CLI command that takes a captured `.dtstyle`, asks the photographer 3 questions (name, layer, description), and produces both the file in the right location and a manifest entry. Reduces friction.
- **Authoring tutorials.** Video or written walkthroughs of capturing common move types. Reduces the learning curve.
- **More forgiving validation.** CI warns rather than blocks on non-critical issues; only schema-critical errors block.

If authoring friction proves to be the actual bottleneck, this is the lever to push.

## Open threads

- **CONTRIBUTING.md** — needs to fully document the authoring procedure, contribution path, and review expectations. Already drafted; needs polish.
- **Authoring helper CLI.** Not in v1 unless evidence shows authoring friction is biting. Recorded in TODO.
- **Vocabulary discovery at scale (RFC-008).** As vocabulary grows, browsing it becomes harder. Speculative for now; addresses the "year-2 problem."
- **Programmatic generation (RFC-012).** When coarse vocabulary granularity isn't enough, Path C is the escape. Deferred.

## Links

- PA/audiences/photographer (taste-articulator)
- PA/audiences/contributor
- PA/audiences/researcher
- PA/promises/vocabulary-as-voice
- PA/principles/vocabulary-grows-with-use
- 02/Vocabulary
- 03/Vocabulary primitives
- ADR-001 (vocabulary approach)
- ADR-023 (vocabulary primitives are .dtstyle + manifest)
- ADR-024 (authoring discipline)
- ADR-026 (vocabulary modversion-pinned)
- ADR-032 (distribution split)
- Related: PRD-001 (Mode A), PRD-002 (Mode B), PRD-004 (Local adjustments)
