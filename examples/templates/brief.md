# brief.md — Format and example

> Per-image intent document (ADR-030 tier 2).
> Status · v0.1 draft format

The `brief.md` for an image lives at `~/Pictures/Chemigram/<image_id>/brief.md`. It captures the photographer's intent for *this specific image*. Read by the agent at session start via `read_context`.

The brief is **stable across sessions** for one image. Updates are rare — usually only when the intent shifts substantially. It is not a session log (that's `notes.md`).

---

## Format

```markdown
# <short title>

**Image:** <filename or image_id>
**Date captured:** <YYYY-MM-DD>
**Captured at:** <location>
**Intended use:** <portfolio | print | book | client | personal>

## Subject

<1–2 sentences naming the subject and what makes it the subject in this frame>

## Setting

<1–2 sentences on environment, depth, weather, time of day — whatever's relevant>

## Light

<1–2 sentences describing the light: direction, quality, color, problems>

## Intent

<2–4 sentences. The "what I want this image to be." Mood, story, what it
should evoke. Specific enough to be useful, not so specific that every
session has to re-fight the brief.>

## Constraints

<bullet list, optional>
- Things the photographer wants to preserve
- Things to avoid
- Hard limits (aspect ratio, output size, color profile)

## Reference (optional)

<link to a reference image, mood board, or prior edit if applicable>
```

---

## Example: iguana-galapagos brief

```markdown
# Marine iguana, Cabo Marshall, Galápagos

**Image:** iguana_galapagos_2024_03_14.NEF
**Date captured:** 2024-03-14
**Captured at:** Cabo Marshall, Isabela Island, Galápagos
**Intended use:** portfolio + book candidate

## Subject

Adult marine iguana, half-submerged near a volcanic rock, eyes just above the
waterline. Looking right of frame.

## Setting

Cold-water dive, surface conditions calm, late morning. Background is open
pelagic blue with some volcanic rock visible behind the iguana. Particulate
in the water column near the surface.

## Light

Overcast day, soft top-down lighting through the surface. Slight blue cast
from the water; iguana's dark skin reads as deep without much shadow detail.
Some hot spots on the rock from filtered sun.

## Intent

This image should feel quiet and weighty. The iguana is the focus; the
water column is supporting cast, not competition. I want the slate-blue
of cold pelagic water — not the cyan-pop of tropical reef shots. Shadow
detail on the iguana's belly and legs matters; deep-shadow zones can stay
crushed.

## Constraints

- Preserve the texture on the iguana's skin (no aggressive denoise)
- Slate-blue water cast, not cyan
- Don't lose the rock shapes in the background
- Final crop: roughly 3:2, leaving room above the subject

## Reference

None for this image — first time shooting marine iguanas above water.
```

---

## Notes on usage

- **Length target: 200–400 words.** Longer briefs become walls of text that the agent skims. If the brief grows past 400 words, split it (mood goes in `taste.md` if it's actually cross-image).
- **Update sparingly.** The brief is stable. Session-by-session reasoning lives in `notes.md`, not the brief.
- **The agent never silently writes to brief.md.** The photographer is the only writer. The agent may *suggest* edits ("Proposed brief.md addition: 'Subject's eye should remain in focus'") but never applies them without confirmation.
- **Frontmatter is optional.** The fields above are conventions, not a strict schema. Photographers who prefer prose can write everything as paragraphs.
