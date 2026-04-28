# PRD-001 — Mode A: the editing session

> Status · Draft v0.1 · 2026-04-27
> Sources · 01/The work, 02/The Mode A loop
> Audiences · photographer (PA/audiences/photographer)
> Promises · compounding-context, agent-as-apprentice, vocabulary-as-voice, photographer-controls-everything, the-loop-is-fast (PA/promises)
> Principles · agent-is-the-only-writer, restraint-before-push, compounding-over-throughput (PA/principles)
> Why this is a PRD · Mode A is *the* user experience Chemigram exists to deliver. Everything else (vocabulary system, versioning, masking, BYOA) is plumbing that serves this. The user-value argument lives or dies here.

It's just past 11 PM. The iguana raw is open. You haven't touched it in three weeks; tonight you're going to finish it. You drop the brief into the conversation: "the iguana on the rock, late afternoon. I want the subject to feel present without being pushed. Subtle." The agent reads, takes a moment, comes back: "I see the image. Looking at your taste, you reach for `tone_lifted_shadows_subject` for this kind of subject-ground relationship — should I start there? I notice the highlights are clipping a bit on the rock; we might also want `dampen_highlights_skin_protective`." You say yes to the first, defer the second. Render. The shadow lifts; the iguana steps forward. You snapshot, branch to "v1," try a more aggressive tone move, judge it as too much, abandon the branch, return to v1 and refine. Twenty minutes pass. The image is done. The agent asks: "I noticed you reach for the subject mask + tone_lifted pattern often when working with a clear subject-ground relationship — should that pattern be in your taste?" You say yes. The session closes; `taste.md` grows by one line. Next time, the agent will already know.

## The problem

Photographers who care about depth on individual images are not well-served by current tools. Lightroom and Capture One are optimized for throughput — process 500 wedding photos in an evening — and their AI features ("AI mask the sky," "auto-tone," "preset packs") are similarly throughput-shaped: opaque actions, generic targets, no relationship with the photographer's actual craft.

What's missing isn't another auto-edit feature. It's a *collaborator*. Someone (something) the photographer talks to about their image, who has bearings (read your context first), opinions (raise composition tensions), and limits (defer to your judgment on ambiguity). Someone whose moves are named, inspectable, and accumulating into a portrait of how you edit. Someone who, after fifty sessions, knows what you reach for. There are no products like this. The closest things in adjacent fields — Cursor for code, Claude Projects for writing — show what compounding context plus a deliberate collaboration loop produce. Photo editing has had no equivalent.

The problem isn't that AI can't edit photos. The problem is that AI photo-editing tools have no shared substrate with the photographer's actual craft — no vocabulary, no taste artifact, no notion of "what you've been working on." Chemigram is the substrate that makes the collaboration possible.

## The experience

The photographer opens an image. The agent loads context — `taste.md` from `~/.chemigram/`, `brief.md` and `notes.md` for this image, recent log of sessions on this image. It reads the EXIF, applies the configured L1 (lens correction, denoise) and L2 (chosen baseline) automatically. Renders a preview. Now the conversation begins.

The agent's opening turn is informed: "I see the image. Looking at your taste, the way you've been handling this kind of subject-ground relationship suggests starting with X. The brief calls for subtle; that fits Y. What's your read?" The photographer responds in their voice — "yes, start there" or "actually, the highlights worry me first" — and the agent applies primitives from the vocabulary and renders.

Each move is a vocabulary application. `apply_primitive("tone_lifted_shadows_subject")` takes a known shape — the agent knows it touches the tone equalizer, restricted to the subject mask. The render comes back in 2 seconds. The photographer judges: "yes, that's the move." Or: "too much." The agent adjusts: "I can either dial back to `tone_lifted_shadows_subject_subtle`, or undo and try `tone_eq_zone_specific`." The photographer chooses; the agent applies; the loop continues.

When the agent doesn't have a vocabulary entry for what the photographer wants — "I want just the highlights in the water, not the sky" — it improvises with masking + existing primitives, and logs the gap. "We don't have a clean entry for highlight-isolated luminance lifting in zone-restricted regions; here's what I improvised." The improvisation gets a snapshot. The gap is recorded. Later — tonight or next session — the photographer might author that vocabulary entry and add it to the pack.

Throughout, the photographer can branch and tag. "Let me try a more aggressive version on a branch." `branch("aggressive_tone")`. Three more moves on the branch. "No, that's not it." Return to main, abandon the branch (or tag it as `archived_v0` if there's a kernel of value worth keeping). Tag the version they like as `v1_export`.

The session ends naturally. The agent reflects: "I noticed you reached for `tone_lifted_shadows_subject` more than typical for this image type. Should that be in your taste? Also, the WB feels too cool here despite the brief saying neutral — adding to notes?" The photographer confirms or declines each. `taste.md` grows. `notes.md` grows. Next session on this image (or a similar one), the agent reads richer context.

## Why now

Three things converge to make this the right moment:

1. **MCP (Model Context Protocol)** has matured enough that tool-using agents can reliably orchestrate complex multi-step workflows. A year ago, the synthesizer + render pipeline orchestration was theoretical; now it's straightforward to express through an MCP server.

2. **darktable 5.x's scene-referred pipeline** is high-quality and headless-stable. Phase 0 testing confirmed `darktable-cli` produces reproducible renders in 1-3 seconds for previews. The substrate is ready.

3. **Photographers are exhausted by throughput-optimized tools.** Lightroom AI features feel generic; Capture One presets feel borrowed. There's a hunger for tools that meet photographers where they actually are — at home, after work, with one image they care about. The space for a per-image research tool is open.

A year from now, it might be too late. Either someone else builds this (the OSS shape becomes harder to land), or the underlying capabilities (MCP, agent reliability) shift in ways that change what's tractable. Now is the moment.

## Success looks like

- After 5 sessions across different images, the photographer notices: the agent's first proposal is meaningfully informed by what they did in earlier sessions. They can cite specific examples ("the agent suggested X because of Y from last week").

- `taste.md` after 30 sessions reads as a recognizable portrait — someone reading it could anticipate what the photographer would reach for on an unfamiliar image. The artifact has acquired a voice.

- Sessions that are 12 turns long now would have been 25 turns at the start. The agent doesn't have to re-learn things; the loop is faster.

- The photographer reports: "I'm finishing more images than I used to." Not because they're processing more — because the per-image loop is fast enough that finishing doesn't feel like a burden.

## Out of scope

- **Bulk editing.** Mode A is one image at a time, deeply. People who want to process 500 images in an evening are using a different tool. (See PA/audiences/not-an-audience/bulk-edit-users.)

- **Catalog management.** Chemigram doesn't manage a photo library. The photographer has their own catalog (Lightroom, Capture One, Aperture, files-in-folders) and ingests the raws they want to work on.

- **Non-darktable processing.** All image processing goes through darktable (ADR-014, ADR-025). RawTherapee, ART, Capture One workflows aren't in scope.

- **Real-time edits.** "Move the slider as I drag" is not the loop shape. Each action is a discrete vocabulary application with a render-then-judge cycle. The friction is intentional.

- **Photographer-direct edits.** ADR-024 — the agent is the only writer. Photographer doesn't bypass the agent to twiddle parameters.

- **Subject masking quality at production level by default.** v1's coarse default masking provider gets you started. Production-quality subject masking is opt-in via `chemigram-masker-sam` (RFC-004).

## The sharpest threat

The compounding-context promise depends on `taste.md` actually accumulating something useful — not generic platitudes ("prefer subtle moves," "avoid over-saturation") but specific, recognizable taste. If the agent's taste-update proposals are generic by default — extracted by an LLM that doesn't really know the photographer's craft — `taste.md` becomes noise rather than signal. After 30 sessions, the photographer reads it and feels nothing recognizes them.

This is the assumption that, if wrong, breaks the frame: that an LLM agent, given session transcripts, vocabulary, briefs, and notes, can produce taste observations that feel like the photographer's craft articulated rather than autocomplete sludge. The propose-and-confirm loop (ADR-031) is the immediate safeguard — the photographer declines bad proposals — but if the agent's hit rate is too low, the friction itself becomes the experience and the project's research thesis collapses.

We don't yet know the agent hit rate. v1 is partly a test of whether good context + structured vocabulary + propose-and-confirm produces the right experience. If the answer is no, the project needs to revisit how observations are generated (better prompts, structured templates, multi-step reflection?), or accept that taste articulation is partly photographer-driven and the agent only contributes raw material.

## Open threads

- **RFC-001** — XMP synthesizer architecture. The mechanism that makes vocabulary application actually render correct images.
- **RFC-009** — Mask provider Protocol shape. The local-adjustments experience (PRD-004) depends on this.
- **RFC-011** — Agent context loading. The shape of what the agent sees at session start.
- **RFC-014** — End-of-session synthesis flow. Where compounding context happens.

## Links

- PA/audiences/photographer
- PA/promises/compounding-context
- PA/promises/agent-as-apprentice
- PA/promises/vocabulary-as-voice
- PA/principles/agent-is-the-only-writer
- PA/principles/restraint-before-push
- 01/The work
- 02/The Mode A loop
- Related: PRD-002 (Mode B), PRD-003 (Vocabulary as voice), PRD-004 (Local adjustments)
