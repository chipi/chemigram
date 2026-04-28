# notes.md — Format and example

> Per-image accumulated session reasoning (ADR-030 tier 3).
> Status · v0.1 draft format

The `notes.md` for an image lives at `~/Pictures/Chemigram/<image_id>/notes.md`. It captures **per-image reasoning that accumulates across sessions** — what was tried, what worked, what didn't, why decisions were made.

Unlike `brief.md` (intent, stable) or `taste.md` (preferences, cross-image), `notes.md` is **the running session log for a single image**. Append-only by convention. Each session adds a dated entry.

---

## Format

```markdown
# Notes — <image title>

## YYYY-MM-DD — Session N

<what was tried, decided, deferred for this session>

<key tradeoffs surfaced, decisions made, branches explored>

<open questions for next session, if any>

## YYYY-MM-DD — Session N+1

<...>
```

Each session block is 1–4 paragraphs. Long enough to capture reasoning, short enough that 6 months of sessions doesn't become a wall.

The agent **proposes notes.md updates at end-of-session** via `propose_notes_update` + `confirm_notes_update`. The photographer can edit the proposed text before confirming.

---

## Example: iguana-galapagos notes (after 4 sessions)

```markdown
# Notes — Marine iguana, Cabo Marshall

## 2026-05-02 — Session 1

Established baseline: filmic_neutral + colorcal_neutral_d65. Confirmed the
slate-blue water target works (vs. cyan-pop alternative we tried briefly).

Tried subject-masked shadow lift on the iguana's belly — first version of the
mask was sloppy on the wing flippers. Refined twice with regenerate_mask.
Final mask: 'current_subject_mask' (hash a3f291...).

Open: eye contrast still feels flat. Might need a small eye-only mask
next session.

## 2026-05-12 — Session 2

Eye mask worked. Used contrast_eye_punch with a tight oval mask.
Photographer noted: tight mask matters more than primitive intensity here.

Tried `colorcal_recover_red_subtle` to give the iguana's mottled brown
some warmth. Read as too warm — backed it out. Settled on no red recovery
on this shot.

Branched 'explore_warmer' to test a more neutral filmic curve. Photographer
preferred 'main' (the original soft-shadow version). Branch retained for
reference.

Decision: 'main' is the working direction. Eye is final. Subject mask
is final. Water column is the remaining work.

## 2026-06-08 — Session 3

Water-column work. Generated a background mask (current_background_mask,
hash b71204...). Applied wb_cooler_subtle through the mask to nudge the
water toward slate-blue. Worked first try.

Considered desaturating the background slightly to push the subject
forward (per taste.md note 2026-07-21). Tried it on a branch
(desaturated_background); felt too processed. Backed out.

Still feels a touch flat overall. Considering a subtle vignette next time.

## 2026-07-04 — Session 4

Added vignette_subtle. Resolved the flatness. Snapshot 'final_v1' tagged.

Exported at full resolution. Done for now.

Decision: this is the portfolio version. If we revisit, branch from
'final_v1' and don't touch 'main'.
```

---

## Notes on usage

- **Append-only by convention.** Don't rewrite past sessions; add new entries. Old entries stay even when their decisions are revised — the trail of reasoning is the value.
- **Length per session: 1–4 paragraphs.** A 200-word session entry is healthy. A 50-word entry probably skipped reasoning; a 500-word entry is dragging things out.
- **Decisions get explicit dates.** "Decision: 'main' is the working direction" stamps the choice.
- **Branches and snapshots get referenced by hash.** When the agent or photographer reads notes.md a month later, the reference points back to a real reproducible state.
- **The agent proposes notes.md updates only at end-of-session.** Mid-session reasoning is in the session transcript (JSONL); notes.md captures the distilled outcome.
- **Open questions belong at the end of an entry.** They become the prompt for the next session.

---

## A note on the three context files together

Together, `brief.md` + `taste.md` + `notes.md` form the agent's working memory:

| File | Scope | Mutability |
|-|-|-|
| `taste.md` | Cross-image, cross-session | Stable; rare additions via propose-and-confirm |
| `brief.md` | Per-image | Stable; rarely updated |
| `notes.md` | Per-image, per-session | Append-only; updated at end of each session |

The agent reads all three at session start (plus the recent operation log). The compounding-context promise rests on these files growing meaningfully over time.
