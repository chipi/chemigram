# ADR-030 — Three-tier context model (taste/brief/notes)

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/mcp-server
> Related RFC · RFC-011

## Context

The agent's effectiveness depends on what it knows when entering a session. Without context, the agent reverts to generic "make this look professional" behavior. With well-organized context, the agent acts as an apprentice who's been on the project long enough to have bearings.

Different kinds of knowledge have different scopes and lifetimes:
- The photographer's **enduring taste** ("I prefer subtle structure to aggressive clarity") — applies across all images, evolves slowly.
- A specific **image's brief** ("for this iguana, lift the subject and dampen the highlights") — specific to one image, set at session start.
- Per-image **working notes** ("the WB looks too cool here despite the brief saying neutral") — accumulate across multiple sessions on the same image.

Conflating these into one file or one mechanism either loses scope distinctions or makes the agent's reading order ambiguous.

## Decision

Three explicit context tiers, each in a known location:

**Global taste** — `~/.chemigram/taste.md`. The photographer's enduring craft preferences. Single file. Read at every session start. Updated through propose-and-confirm during sessions.

**Per-image brief** — `<image_id>/brief.md`. The intent for this specific image. Single file per image. Set at first-session start, mostly stable, rarely revised.

**Per-image notes** — `<image_id>/notes.md`. Accumulated working observations from sessions on this image. Append-only across sessions. Read alongside the brief at every per-image session start.

The agent loads all three at session start (RFC-011 specifies the order and format). Each can be updated through propose-and-confirm (ADR-031) during a session.

## Rationale

- **Scope clarity.** Each tier has a clear scope: global, per-image-fixed, per-image-evolving. The agent (and the photographer) know where each kind of information lives.
- **Lifetime alignment.** Files match how their content evolves. `taste.md` rarely changes but accumulates over months; `brief.md` is set once per image and rarely revised; `notes.md` grows session-by-session per image.
- **Inspectability.** Each is a plain `.md` file. The photographer can read or hand-edit any of them between sessions.
- **Aligns with research thesis.** `taste.md` over months becomes the research artifact (a portrait of how this photographer edits); `brief.md` and `notes.md` per image are the working memory.

## Alternatives considered

- **Single `context.md` per image (no global taste):** rejected — loses the cross-image accumulation that's central to the research thesis.
- **Single global file (no per-image scope):** rejected — per-image specifics (this image's brief, this image's notes from prior sessions) are critical for context.
- **Database-backed context:** rejected — opaque, hard to inspect, contradicts the filesystem-as-state principle (ADR-006).
- **Five-tier context (e.g., separate brief/intent/desired-mood/avoid-list/...):** rejected — over-models. Three tiers cover the common cases; new tiers require a superseding ADR with evidence.

## Consequences

Positive:
- Clear scope boundaries
- Each file has a natural update pattern
- Inspection and hand-editing work via standard tools
- Compounds over months: the `taste.md` becomes increasingly valuable

Negative:
- Three locations to track (mitigated: convention is consistent and documented)
- Photographers must understand the distinction between brief and notes (mitigated: documented in starter docs; the agent reinforces by example)

## Implementation notes

`src/chemigram_core/context.py` provides functions: `read_context(image_id)` returns dict with all three (plus recent log entries). `propose_taste_update`, `confirm_taste_update`, `propose_notes_update`, `confirm_notes_update` are the mutation operations. Brief is updated via direct edit (or a separate tool not in the propose-and-confirm flow because briefs are rarely updated mid-session). RFC-011 specifies the loading format in detail.
