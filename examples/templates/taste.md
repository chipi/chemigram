# taste.md — Format and example

> Cross-image, cross-session preferences document (ADR-030 tier 1).
> Status · v0.1 draft format

The `taste.md` lives at the photographer's `~/.chemigram/taste.md` (location TBD per RFC-011). It captures preferences and patterns the photographer has articulated **across sessions and across images**. Read by the agent at every session start.

Unlike `brief.md` (per-image, stable) or `notes.md` (per-image, session log), `taste.md` is **the longitudinal record of taste**. It compounds across the project's lifetime — that's the central thesis of compounding context (PA principle).

---

## Format

Loose markdown organized by category. No strict schema. Each entry is:

- A short statement of preference (one sentence)
- Optionally, a date added or last revised
- Optionally, a short justification

Categories evolve as the photographer's vocabulary grows. Don't pre-define them; let them emerge.

The **agent never silently edits taste.md**. Updates go through `propose_taste_update` + `confirm_taste_update`. Each accepted addition gets dated.

---

## Example: a year of use

```markdown
# Taste — Marko's preferences

*Curated over time. Last revised: 2027-04-15. ~80 entries.*

## Color

- Slate-blue water for cold-pelagic shots; cyan-pop reads tropical and is wrong
  for Galápagos / La Ventana / Baja work. (2026-05-02)
- Recover red channel subtly underwater; full red recovery overshoots and
  reads as fake. (2026-05-12)
- For surface marine animals (mantas, mobulas), background blue should
  desaturate slightly to push the subject forward. (2026-07-21)
- Don't lift the green channel under any circumstances; it reads sickly. (2026-09-03)
- Warm tones on rocks/coral are fine, even slight orange — not a problem
  the way warm casts on water would be. (2026-11-14)

## Tone

- Lift shadows on subjects, almost always. Marine animals need detail
  in their underbellies / underbodies. (2026-05-02)
- Crush deep shadows to true black. Doesn't bother me; I want the contrast. (2026-05-02)
- Avoid `tone_compress_highlights` on bright water surfaces — it reads as
  fake / over-processed. Better to let highlights blow out a bit. (2026-08-18)
- Midtone lift for portraits of land animals (iguanas, sea lions, birds);
  not needed for fish in motion. (2027-01-09)

## Sharpening / structure

- `structure_subtle` for skin / scales / textured surfaces. Never `structure_strong`
  — it reads aggressive. (2026-06-10)
- `sharpen_standard` is fine on output; pre-sharpening with structure has
  to be subtle to avoid haloing. (2026-06-10)
- Don't sharpen water particles or background blur. They should stay soft. (2026-08-18)

## Local adjustments

- Subject mask is the most-used local target. Eye masks for portraits where
  eye-pop matters. Background masks for water-column adjustments. (2026-07-21)
- For mantas / mobulas / large pelagic subjects: mask the body, lift shadows;
  separately mask the surrounding water, slightly desaturate. (2026-07-21)
- Avoid masking individual fins / wing-tips; the masker doesn't get them
  reliably and refining isn't worth it for those small areas. (2026-10-30)

## Aesthetic / mood

- Quiet over dramatic for animal portraits. Let the subject be the story. (2026-05-02)
- Grain is fine and even welcome at high ISO; don't over-denoise. (2026-09-03)
- Crop tight when the subject earns it; loose when the environment
  is part of the story. (2027-01-09)

## What I avoid

- Vivid / saturated looks. Reads tropical, reads commercial, not me. (2026-05-12)
- Heavy clarity / Lightroom-style "punch." (2026-05-12)
- Symmetric vignettes. They flatten the frame. Subtle / asymmetric only. (2026-08-18)

## Workflow notes

- I prefer to see 2–3 candidates before committing to a direction; branching
  is encouraged. (2026-06-10)
- When I correct color targets, you tend to estimate slightly cool. Bias
  warmer when in doubt. (2026-09-03)
- I don't use Mode B much; my work is per-image. Don't push autonomous
  exploration unless I ask. (2027-02-14)
```

---

## Notes on usage

- **No length limit.** A year-old `taste.md` might be 50–150 entries. The agent reads it fully every session — that's the point.
- **Conflict is normal.** As taste evolves, older entries may contradict newer ones. The agent surfaces conflicts when they appear (e.g., "I see 'avoid clarity_strong' from 2026-05-12 but you've used it four times in the last month — outdated?"). Resolution is the photographer's call.
- **Categories are emergent.** Don't try to predefine them. Let them grow as the photographer's vocabulary grows.
- **Dates matter.** Each entry's date helps the agent prioritize newer preferences when older ones conflict.
- **Justifications are optional.** Some preferences are aesthetic and don't need justification ("I don't like cyan-pop"). Others benefit from one ("recover red subtly because full recovery reads fake").
