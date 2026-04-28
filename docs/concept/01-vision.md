# 01 — Vision

> *Chemigram is to photos what Claude Code is to code.*

## The question

Can a photographer transmit taste through language and feedback? And does an agent develop something resembling judgment when given good tools, good vocabulary, and a real craftsperson in the loop?

Chemigram is a craft research project that asks this question concretely. It's not a Lightroom replacement. It's not a digital asset manager. It's not a service that automates editing or replaces the photographer. It's a probe — into where photographic taste lives, how it transmits, and what an agent can do with the right substrate.

## The premise

Photo editing is an act of taste. When a photographer works through a raw file in Lightroom or darktable, what's happening isn't slider-pushing — it's intent expressed through tooling. The slider is the *medium*; the move is the *intent*. Tools that make the slider easier to find don't change what's hard about photo editing. The hard part is the move, not the slider.

Modern agents can hold language richly. They can read intent. They can look at images. They can reason about composition. And they have infinite patience for iteration. The question is whether all that capability, given a substrate built for collaboration rather than automation, can become something more than a slider-pushing tool — a partner in the work.

## What this looks like

A photographer drops a raw into a workspace. Writes a brief: *"underwater shot of an iguana in the Galápagos. Adjust for underwater and color correct to get nice blues, but make sure iguana and rest of the photo stays in their natural colors. Remove highlight at top from the sun gradually toward down. Put more attention to eyes and make them a bit more clear. Overall make iguana more stand out from the background with some crispness."*

The agent reads the photographer's accumulated taste from a `taste.md` file. Reads the brief. Looks at the image. Does background research on iguana coloration if relevant. Generates masks for the subject and the eyes. Applies vocabulary primitives — `colorcal_underwater_recover_blue`, `gradient_top_dampen_highlights`, `structure_subject_subtle`. Renders previews. Surfaces uncertainty when masking is imprecise. Catches composition tensions the brief glossed over. Snapshots at every meaningful state. Proposes additions to `taste.md` at session end.

The photographer reads previews. Says yes or no. Branches when curious. Tags the result. Exports.

Twenty-five conversational turns. One photo, deeply edited. Five new vocabulary entries surfaced as gaps for later authoring. Two new lines added to `taste.md` that future sessions inherit. The next image will go faster because the project has accumulated state.

## Why this earns existence

Three reasons that, together, make this worth doing now.

**Photography editing is actually agent-shaped.** Most creative work isn't — it requires too much continuous human judgment to delegate. But raw-to-final photo development is iterative, parameter-rich, well-suited to vocabulary, well-suited to AI subject masking, and (crucially) has previews — meaning every move is checkable in a few seconds. The loop is tight; the agent has tools; the photographer judges. This is a domain where the apprenticeship model fits.

**The Claude Code analogy is real, not metaphorical.** Coding assistants found a working shape: project context, agent loop, accumulated state, version control, iterative tools, propose-and-confirm. Chemigram applies that exact shape to photo work. A photo is a project. `taste.md` is `CLAUDE.md`. Vocabulary primitives are filesystem tools. Snapshots are commits. The shape transfers.

**The substrate exists.** darktable provides the rendering, color science, masks, modules — all already mature, all OSS. MCP provides the agent protocol. SAM provides AI segmentation. Every piece needed to build this is available. The novel contribution is the integration layer and the agent's behavioral patterns — bounded engineering, not research uncertainty.

## What success looks like

Not "the agent edits well." Something deeper.

A photographer who's used Chemigram for six months has:

- A `taste.md` that articulates their photographic intent in a structured, evolving way — readable by them, by the agent, by another photographer trying to understand their work
- A vocabulary of 100-200 named moves capturing how they actually edit, encoded as portable `.dtstyle` files
- Hundreds of session transcripts showing how their taste developed in negotiation with the agent
- Per-image notes carrying forward subject identifications, lighting decisions, branch explorations
- Sessions that take 12 turns instead of 25 because context compounds

That's a research artifact in itself: a portrait of how one photographer edits, externalized through use. It's also a working tool that gets better the more it's used.

The compounding is the point. The first session is interesting; the fiftieth is what justifies the project.

## What this is not

| Not a... | Because... |
|-|-|
| **Lightroom replacement** | Chemigram is per-image research, not a daily-driver photo workflow. Use your real DAM for cataloging, ratings, exports at scale. Use Chemigram when you want to work with an apprentice on a specific image. |
| **Bulk-editing automation tool** | The whole point is depth, not throughput. One photo at a time, deeply. |
| **Digital asset manager** | No catalog, no smart collections, no search. Out of scope by design. (See `docs/TODO.md` — this could be a sibling project later.) |
| **"Make my photos professional" service** | Chemigram doesn't have taste of its own. It has *your* taste, articulated through use. The starter vocabulary is deliberately minimal so users build their own voice rather than inheriting a generic one. |
| **A test of whether AI can replace the photographer** | The opposite. The agent makes the photographer's work tractable and the loop fast. Every meaningful decision still goes through the photographer. The compounding is real but bounded — the agent is an apprentice, not a successor. |

## The deeper bet

Most attempts to apply AI to creative work either over-claim ("AI does the creative work") or under-claim ("AI assists with mechanical tasks"). Both miss the interesting middle: **AI as partner in articulating craft**.

A photographer's taste lives partly in language ("subtle red recovery"), partly in the moves they reach for repeatedly, partly in pre-verbal judgment they recognize when they see it. None of these is fully captured by any current tool. Chemigram bets that the right substrate — vocabulary as action space, agent as patient reader of intent, externalized context that compounds — can capture all three, in a way the photographer is in control of.

If the bet works, the photographer ends up with something more than edited photos: an articulated craft. If it doesn't, we'll have learned where craft resists language, where agent-collaboration breaks down, and what shape of tool would actually help.

Either way, the question is worth asking.

---

*01 · Vision · v1.0*
