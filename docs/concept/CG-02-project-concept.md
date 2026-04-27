# CG-02 — Project Concept

*What Chemigram is at the idea level. The loop, the sessions, the accumulating context, the two modes. Read this if you want to understand the whole project end to end.*

The vision (`CG-01`) describes why this exists. The technical architecture (`CG-04`) describes how the engine is built and the architectural disciplines (agent-is-the-only-writer, darktable-does-the-photography, BYOA) that constrain it. This document describes what's actually happening when a photographer uses Chemigram — the user experience at the level of conversations, files, sessions, and how it all compounds over time.

---

## 1. The structuring metaphor

Chemigram is to photos what Claude Code is to code. This isn't rhetoric — it's the design principle. If you've used Claude Code (or Cursor, or any agentic-coding tool with a project-aware assistant), you know the shape:

- A working directory is the unit of work
- A `CLAUDE.md` file captures durable context about the project
- The agent reads context, you describe intent, the agent acts
- Tools touch the filesystem; version control captures every step
- Sessions accumulate; the project gets richer over time
- The agent isn't stateless — its state is externalized into files

Chemigram applies this shape to photo editing. A photo is a project. `taste.md` is the durable context. The agent reads, the photographer briefs, the agent edits via a vocabulary of named moves, previews are the "tests," snapshots are the commits. Across sessions, the project (image + taste + vocabulary + history) accumulates. The agent gets smarter about *this photographer's* work over time.

The transferable patterns:

| Claude Code | Chemigram |
|-|-|
| Code project (a directory) | Photo project (per-image directory) |
| `CLAUDE.md` | `taste.md` (global) + `brief.md` (per-image) + `notes.md` (per-image) |
| Source files | Raw + XMP + masks |
| Filesystem tools | Vocabulary primitives, masks, render, export |
| Test suite | Render preview + photographer judgment |
| Git underneath | Versioning DAG (per `CG-04` § 7) |
| Compile / run | `darktable-cli` render |
| External libs | Vocabulary packs (community-contributed) |
| Issue tracker | Session log + `vocabulary_gaps.jsonl` |
| Pull request | Tagged snapshot ready for export |

The differences are real and matter (photos have judgment, not tests; images are subjective, not symbolic; Mode B is genuinely autonomous in ways code rarely is) — but the shared shape is the foundation.

---

## 2. Two modes

Chemigram operates in two distinct modes, sharing the engine but answering different research questions.

### 2.1 Mode A — the journey (collaborative)

Photographer uploads an image, articulates intent in language, agent proposes moves and renders previews, photographer responds, loop continues until "yes, that's it." Few iterations (5-30). Rich verbal feedback. Photographer in the loop continuously.

The research question: **how does taste transmit through language and feedback?** Where is the photographer's taste verbal vs. pre-verbal? Does the agent develop session-level heuristics? Where does the loop break?

This is the primary mode and the foundation of the project. Mode A sessions are also where preference data accumulates for Mode B.

### 2.2 Mode B — the autonomous fine-tuner

Photographer provides image + brief + **evaluation criteria** + budget ("up to 200 iterations, up to 8 hours"). Agent runs the loop alone, branching to explore variants, self-evaluating against the criteria, converging to a winner (or running out of budget). At the end: best result, the explored tree, an evaluation log.

The research question: **can the agent self-evaluate well enough to converge without human feedback?** The eval function is itself an open question (see `CG-04` § 12.3) — kept open deliberately, with reference-based, vision-self-eval, and learned-critic approaches all viable.

Mode B is inspired by the data/eval/iterate pattern (Karpathy-style), and it's only meaningful with **versioning** in place — autonomous exploration produces a tree of variants, not a sequence. Without a way to record and inspect that tree, the agent's reasoning is opaque.

### 2.3 How the two relate

Mode A first. Mode B inherits Mode A's vocabulary and accumulated preference data. Without Mode A, Mode B has nothing of *your* taste to optimize toward. Without Mode B, every image is hours of your time.

The progression is the experimental arc — not just two features.

---

## 3. The three-tier context model

Claude Code distinguishes global preferences (`~/.claude/CLAUDE.md`) from project-specific context (`<project>/CLAUDE.md`). Chemigram extends this to three tiers, each with a different lifetime and scope.

### 3.1 Global: `~/.chemigram/taste.md`

The photographer's taste, externalized. Read at every session start. Curated over months.

What goes here:

- **Working preferences** — restraint vs. push, natural vs. stylized, default tonal mood
- **Recurring patterns** — what you reach for in different lighting, scenes, subjects
- **Vocabulary affinities** — entries you tend to use, entries you avoid, common combinations
- **Brief language** — what you mean by "stand out," "natural color," "pop," "subtle"
- **Camera-specific notes** — quirks of your bodies that the agent should know
- **Session preferences** — turn-length you prefer, when to show variants, when to commit

What doesn't go here:

- Image-specific facts (those are in per-image notes)
- Vocabulary entries themselves (those are structured `.dtstyle` files)
- Session transcripts (those are in `sessions/`)
- Anything you wouldn't want to be true across all your work

### 3.2 Per-image: `<image_id>/brief.md`

What this image is for. Written at session start, sometimes updated mid-session if the goal shifts. Read at every session on this image.

What goes here:

- **Purpose** — Instagram post, portfolio, print, client deliverable, exploratory
- **Intent** — what you want this photo to feel like
- **Constraints** — color-accuracy requirements, crop ratios, output size
- **Story** — when, where, why, what was happening
- **Reference** — links or paths to reference images that inform the look

The brief is the photographer's *commitment to a direction* for this image. The agent reads it as a frame for every move.

### 3.3 Per-image: `<image_id>/notes.md`

What we've learned about this image. Accumulated through sessions. Both photographer and agent contribute.

What goes here:

- **Subject identification** — "the smaller iguana, not the large one in the background"
- **Image facts** — "sun was harsh, top of frame is blown by ~1.5 stops"
- **Decisions made** — "we chose to keep the underwater feel rather than full color recovery"
- **Branches explored** — "tried warm version on `explore_warmth` branch, didn't work — too saturated"
- **Open questions** — things to revisit next session

This is the per-image equivalent of a developer's per-project README. It's where the work *about* the image lives, separate from the work *on* the image.

---

## 4. Photo project structure

Each image is its own project, structured as in `CG-04` § 7 and extended for context:

```
~/Pictures/Chemigram/<image_id>/
  raw/                                   # symlink to original raw
  brief.md                               # what this image is for
  notes.md                               # what we've learned about this image
  taste.md                               # OPTIONAL per-image taste override
                                         # (rare; usually inherits from ~/.chemigram/taste.md)
  metadata.json                          # EXIF cache, layer bindings
  current.xmp                            # synthesized from current snapshot
  objects/                               # snapshot store (versioning)
  refs/                                  # branches, tags, HEAD
  log.jsonl                              # operation log
  sessions/                              # session transcripts
    2026-04-27-iguana-correction.jsonl
    2026-04-29-followup.jsonl
  previews/                              # render cache
  exports/                               # final outputs
  masks/                                 # registered masks for this image
    current_subject_mask.png
    registry.json
  vocabulary_gaps.jsonl                  # gaps surfaced this image, append-only
```

Three context files at the top (`brief.md`, `notes.md`, optional per-image `taste.md`) that the agent reads at session start. Everything else is engine state.

---

## 5. Session lifecycle

A session has a beginning, a middle, and an end. Each phase has agent obligations.

### 5.1 Session start: read context, orient

When a session opens (photographer says "let's work on this image"), the agent reads in this order:

1. `~/.chemigram/taste.md` — global taste
2. `<image_id>/taste.md` if it exists — image-specific overrides
3. `<image_id>/brief.md` — what this image is for
4. `<image_id>/notes.md` — what we've learned about this image
5. `<image_id>/log.jsonl` (recent entries) — what happened in recent sessions
6. `<image_id>/metadata.json` — EXIF, current layer bindings

After reading, the agent acknowledges:

> "I've read your context. This is a Galápagos marine iguana shot, ISO 200 on the Nikon D850, intended for portfolio. From your taste notes, you generally prefer natural color preservation and restraint. Last session you established the L1+L2 baseline and started exploring blue water recovery. We branched into `explore_warm` but didn't commit. Want to continue from `main` or revisit the warm branch?"

This single message demonstrates that the agent has its bearings. It's the agent equivalent of an apprentice walking into the studio and saying "I see where we left off, what's next?"

### 5.2 Mid-session: act, surface, update

During the session, the agent's behavior is governed by the disciplines (§ 6 below). The key file-touching obligations:

- **Snapshot frequently.** Every meaningful state change becomes a snapshot. Cheap.
- **Append to `log.jsonl`** for every operation, with enough detail that the session is reconstructible later.
- **Append to `vocabulary_gaps.jsonl`** when a needed entry doesn't exist and a workaround was used.
- **Update `notes.md`** when something is learned about the image (subject identification, lighting facts, decisions). Update is propose-and-confirm — the agent suggests, the photographer accepts.

### 5.3 Session end: synthesize, propose, persist

When the session winds down, the agent does end-of-session work:

1. **Tag a snapshot** — what's the result of this session? Photographer chooses.
2. **Synthesize the session transcript** — short summary of what was done, written to `sessions/<date>-<purpose>.jsonl`'s metadata header.
3. **Propose updates** to `taste.md` if patterns were observed:
   > "I noticed you preferred subtle structure twice today and rejected the stronger variant both times. Should I note in `taste.md` that you bias toward subtle structure?"
4. **Propose updates** to `notes.md` for image-specific facts learned.
5. **Identify next-session candidates** — open questions, branches to explore later.

The end-of-session is structured because it's where compounding learning lives. Sessions that end without synthesis don't compound.

---

## 6. Behavioral disciplines

These are the rules the agent operates by. They're prompt-engineering content versioned alongside the engine — project artifacts, not implementation details.

### 6.1 Read before acting

The agent never starts editing before reading context. Even if the photographer's first message is "just punch the highlights" — the agent reads first, *then* applies the move with awareness of the brief and taste. This adds maybe 100ms; the alternative is moves that conflict with the brief.

### 6.2 Surface uncertainty rather than guess

When the agent doesn't know something (whether a mask captured the right subject, whether "natural color" means species-typical or scene-typical, whether a vocabulary entry exists for what's needed), it asks. Glibly proceeding under uncertainty is the failure mode.

The pattern:

> "I'm going to attempt X. Quality may vary because Y. Here's what I tried — does this match your intent?"

Versus:

> "Done." [user has to discover failure on their own]

The first costs one extra turn. The second costs trust and many extra turns once the failure becomes visible.

### 6.3 Show your work

Every move is followed by a render preview. The photographer sees the result before the next move is proposed. No silent chains of edits.

For multi-step plans the agent has in mind, it can describe the plan first ("I'll cool the water, then protect the iguana, then dampen the highlights") but executes one step at a time with previews. The plan is a proposal, not a commitment.

### 6.4 Snapshot at every meaningful state

Photographer says "yes, that works" — snapshot, label. Agent finishes a multi-step move — snapshot. Branch is created — base of the branch is snapshotted. The history should be navigable.

The cost is small (a few KB per snapshot) and the value is large (every state recoverable, every variant inspectable).

### 6.5 Surface vocabulary gaps explicitly

When the agent works around a missing entry, it says so:

> "I don't have a single entry for water-only blue recovery while protecting the subject. I'm composing it from `colorcal_underwater_recover_blue` (global) + `colorcal_warm_protect_subject` (subject-masked counter). Result should be similar; logging this as a gap for future vocabulary authoring."

The photographer can ignore the gap or address it later. Either way, it's now in `vocabulary_gaps.jsonl` and the agent's next session won't pretend the gap doesn't exist.

### 6.6 Catch composition tensions

When the photographer's brief contains tensions (cool the blues + preserve subject warmth; dampen the bright top + make subject stand out via contrast), the agent surfaces the tension before resolving:

> "Quick note: the bright top of frame was helping separate the iguana from the background. Dampening it loses some of that contrast. We can compensate with structure on the iguana, but this is a tradeoff. Worth flagging before I proceed."

This is the agent earning its keep. An apprentice with composition sense catches these; the agent should too.

### 6.7 Background research when it would inform color or tone

When the brief mentions specific subjects (animals, plants, locations), and the natural appearance of those subjects might inform decisions, the agent does background research before applying corrections:

```
agent: [searches: "Galapagos marine iguana coloration natural color"]
agent: [retrieves 3 reference images]
agent: [analyzes references for typical color characteristics]

agent: "Marine iguanas are typically dark gray to black, with seasonal red/orange.
        Looking at your photo, the iguana is brown-gray, probably from blue water cast.
        I'll target dark slate-gray. Tell me if this is wrong for your specific subject —
        there are subspecies with different coloration."
```

The agent surfaces what it learned and offers the photographer a check. Research is a starting point, not verdict.

### 6.8 Propose context updates, don't commit silently

Updates to `taste.md` and `notes.md` are *proposed*, not silently written. The pattern:

> "Proposed addition to your taste.md: 'For underwater pelagic shots, slate-blue is preferred over cyan-pop.' Accept (Y/N)?"

Accept appends with a session reference. Reject discards. The photographer always knows what's accumulating in their context files.

This matters because `taste.md` is *the* learning artifact. If the agent silently writes to it, the photographer loses control over their own taste articulation. Propose-and-confirm is the right discipline.

### 6.9 Default to global, escalate to local

When the photographer's request is ambiguous about scope, the agent starts global and asks if local refinement is needed. Going global → masked is one extra turn; going masked → global requires reasoning about which mask to discard. The asymmetry favors starting simple.

Exception: when the brief explicitly mentions subjects ("the mobula should be the focus"), even early moves should preferentially target the subject.

### 6.10 Restraint before push

LLMs love to keep tweaking. The agent should bias toward fewer, smaller moves rather than many, larger ones. When in doubt about whether to push further, the agent asks:

> "I think we're close. Want to push further on contrast, or call this good?"

Knowing when to stop is the hardest part of the loop. The agent's bias should match the photographer's stated taste preferences, with restraint as the default if not specified.

---

## 7. How `taste.md` gets written

This is the most important compounding artifact in the system. It's also the most easily-mishandled.

### 7.1 Initial draft (one-time, photographer-authored)

The photographer sits down once and writes what they can articulate. Rough structure:

```markdown
# Taste — [photographer name]

## Working preferences
[a few paragraphs of how I generally approach photo editing]

## Subject preferences
[what I shoot, what I care about preserving]

## Common patterns
[moves I reach for repeatedly]

## Brief language
[what I mean when I say "subtle," "natural," "pop"]

## Camera notes
[quirks of my bodies]

## Things I avoid
[stylistic moves I dislike]
```

An hour of writing. Imperfect but useful from session 1.

### 7.2 Per-session proposals (agent-suggested, photographer-confirmed)

After each session, the agent reflects:

> "I noticed three patterns today:
>  1. You preferred subtle structure twice over strong; should I note 'bias toward subtle structure' in taste.md?
>  2. You corrected my color targets twice — both times pulling toward warmer than I'd estimated. Should I note 'tend to bias warm vs. analytical neutral'?
>  3. You ignored my suggestion to check the warm branch. Should I note 'prefer to commit to one direction rather than maintain branches'?"

Photographer accepts/rejects each. Accepted notes are appended to `taste.md` with a date and session reference.

### 7.3 Periodic synthesis (every 10 sessions or when triggered)

The accumulated `taste.md` may have redundant entries, contradictions, or outdated notes. Periodically the agent does synthesis:

> "Reviewing your taste.md, I see three places where notes overlap or contradict:
>  - 'prefer restraint' (added month 1) and 'don't be afraid of stronger moves on portrait subjects' (added month 3) — should I combine these into a more nuanced note?
>  - 'avoid clarity_strong' (added month 1) — you've used clarity_strong four times in the last month. Outdated, want to revise?"

Synthesis is also propose-and-confirm. The photographer reviews the proposed `taste.md` v2 and accepts, edits, or rejects.

### 7.4 What `taste.md` is NOT

- Not a model — the agent reads it as text context, doesn't fine-tune on it
- Not authoritative — the photographer is, and mid-session corrections override it
- Not vocabulary — those are structured `.dtstyle` files; `taste.md` is unstructured prose
- Not session log — those are in `sessions/`; `taste.md` is the synthesized takeaway

---

## 8. Closing vocabulary gaps without authoring 1000 entries

The vocabulary is finite. Any sufficiently rich brief will hit a gap. Four paths, increasing in ambition.

### 8.1 Path A — agent composes from existing vocabulary

When the needed entry doesn't exist, the agent uses two-or-more existing entries to approximate. Costs more snapshots and turns; works today; no new infrastructure.

### 8.2 Path B — agent surfaces gaps for later authoring

`vocabulary_gaps.jsonl` accumulates. After every few sessions, the photographer reviews and decides which gaps to address. The agent can describe how to author each entry in darktable's GUI:

> "To create `colorcal_underwater_recover_blue_water_only`:
>  1. Open color calibration module
>  2. Set illuminant to 'D65 + tweak'
>  3. In the parametric mask: enable hue mask, range 180-240° (cyan-blue)
>  4. Save as style with that name
>  5. Export the .dtstyle"

The photographer follows the recipe. Vocabulary grows from session evidence.

### 8.3 Path C — agent generates `.dtstyle` programmatically

For modules with well-understood param structure (exposure, color calibration), the agent could encode a `.dtstyle` directly. Each module supported is its own engineering task; do it for high-value modules, fall back to A for the rest. Phase 3+ work; in `docs/TODO.md`.

### 8.4 Path D — vocabulary as living artifact

The reframe. The vocabulary isn't supposed to be complete from day one. It grows with use. Sessions reveal gaps; gaps are surfaced; surfacing leads to authoring; authoring enriches future sessions.

After a year of use, the vocabulary captures *your craft*, articulated through use. After three years, it's a portrait of how you edit. The "1000 vocabularies" problem dissolves because the vocabulary isn't trying to be exhaustive — it's trying to be *yours*.

This isn't infrastructure; it's a stance. But it informs everything: how the agent handles gaps (surface, don't pretend), how it learns (`taste.md`), how the project compounds (sessions feed vocabulary).

---

## 9. The agent's prompt (sketch)

The agent's system prompt at session start, simplified:

```
You are an apprentice photo editor working with [photographer] on photo {image_id}.

CONTEXT (read in order):
1. [photographer]'s taste: {contents of ~/.chemigram/taste.md}
2. This image's brief: {contents of <image_id>/brief.md}
3. This image's notes: {contents of <image_id>/notes.md}
4. Recent session log: {tail of <image_id>/log.jsonl}
5. Image metadata: {<image_id>/metadata.json}
6. Current state: {get_state(image_id)}
7. Available vocabulary: {list_vocabulary()}

DISCIPLINES:
1. Read before acting
2. Surface uncertainty rather than guess
3. Show your work (preview after every move)
4. Snapshot at every meaningful state
5. Surface vocabulary gaps explicitly
6. Catch composition tensions
7. Background research when it would inform decisions
8. Propose context updates; don't commit silently
9. Default global, escalate local
10. Restraint before push

TOOLS: {MCP tool surface — see CG-04 § 10}

WORKFLOW:
- At session start, acknowledge context and orient
- During session, act in single-step previewable moves
- At session end, propose snapshot tagging, taste.md updates, notes.md updates

GOAL: help [photographer] edit this photo well, while accumulating context that
makes future sessions richer. The compounding is the point.
```

This is roughly 1000-2000 tokens of system prompt plus context files. Modest. Falls inside any modern model's context window with room for a long session transcript.

---

## 10. The full user journey

Putting it all together — what a photographer experiences from first install to a hundredth session.

### 10.1 Day 1 — installation and `taste.md`

Install Chemigram. Initial setup creates `~/.chemigram/` with empty `taste.md`, default `config.toml`, isolated darktable configdir. Photographer spends an hour writing initial `taste.md` — what they can articulate about their preferences. Imperfect; fine.

Optionally configure a masking provider beyond the bundled coarse default. For production-quality work on subjects, install `chemigram-masker-sam` sibling project.

### 10.2 First session — Mode A on a single image

Photographer points an MCP-capable agent at the Chemigram MCP server. Selects a raw. Writes a brief. Agent reads context, orients, proposes a baseline. Photographer responds. Loop runs for 25-30 turns.

At end-of-session: agent proposes 2-3 additions to `taste.md`. Photographer accepts. Tags the result. Exports.

Total time: 45-60 minutes. Result: one well-edited photo, `taste.md` slightly richer, vocabulary log shows 1-2 gaps to address.

### 10.3 Sessions 2-10 — accumulation

Each session reads richer `taste.md`, learns the photographer better. Gaps surfaced in earlier sessions get authored in evening darkroom sessions. Vocabulary grows from ~30 starter entries to ~50-60.

By session 10, `taste.md` has 15-25 entries. Sessions average 18-22 turns. Friction has moved from "agent doesn't understand my preferences" to "this specific subject needs a vocabulary entry I haven't authored."

### 10.4 Sessions 10-50 — proficiency

`taste.md` synthesis happens for the first time. Some entries get combined; some get retired; some get refined. Vocabulary is at ~80-100 entries.

Mode A sessions average 12-15 turns. The photographer starts experimenting with branches more — exploring variants, picking winners. Versioning earns its keep.

Some images get returned to across sessions. `notes.md` accumulates for these. The "save this fish mask as 'mobula_main' for future sessions" workflow becomes natural.

### 10.5 Session 50+ — Mode B becomes viable

Enough Mode A preference data exists to bootstrap a learned-critic eval function (per the `CG-04` § 12.3 open question, if that path is taken). Mode B starts being used for tedious-but-tractable work: variants for different output crops, preliminary edits for batch ingestion, exploration of looks the photographer doesn't have time for in Mode A.

The photographer publishes their first research blog post about agent-driven editing. Anonymized session insights feed back into the project.

---

## 11. What success looks like

Success isn't "the agent edits well." Something deeper.

A photographer who's used Chemigram for six months has:

- A `taste.md` that articulates their photographic intent in a structured, evolving way — readable by them, by the agent, by another photographer trying to understand their work
- A vocabulary of 100-200 named moves capturing how they actually edit, encoded as portable `.dtstyle` files
- Hundreds of session transcripts showing how their taste developed in negotiation with the agent
- Per-image notes carrying forward subject identifications, lighting decisions, branch explorations
- Sessions that take 12 turns instead of 25 because context compounds

That's a research artifact in itself: a portrait of how one photographer edits, externalized through use. It's also a working tool that gets better the more it's used.

The compounding is the point. The first session is interesting; the fiftieth is what justifies the project.

---

## 12. Honest limits

What this system gives you:

- An agent that has *your* context at session start, not generic priors
- Compounding learning across sessions
- Externalized, inspectable, version-controllable taste
- A project structure where photo work feels like a structured engagement, not a series of disconnected edits

What it doesn't give you:

- Magic. Bad briefs still produce bad results. Bad vocabulary still limits the agent.
- A trained model of you. The agent reads `taste.md` as text — it doesn't internalize it the way a fine-tuned model would.
- Memory across photos. Each image is its own project. Patterns learned on one image inform `taste.md`, which informs others — but specific facts about Image A don't transfer to Image B.
- Replacement for judgment. The agent can be a great apprentice, but you're still the photographer.

The compounding is real but bounded. It's good enough that sessions get faster and more aligned over time. It's not so much that the agent ever stops needing you. That's the point.

---

*CG-02 · Project Concept · v1.0*
