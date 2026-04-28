# underwater.md — underwater photography preferences

*~18 entries. Last revised: 2027-04-15.*

Preferences specific to underwater photography (snorkeling, freediving, dive). Loads when `brief.md` declares `underwater` in its `Tastes` field.

---

## Color

- Slate-blue water for cold-pelagic shots; cyan-pop reads tropical and is wrong for Galápagos / La Ventana / Baja work. (2026-05-02)
- Recover red channel subtly underwater; full red recovery overshoots and reads as fake. (2026-05-12)
- For surface marine animals (mantas, mobulas), background blue should desaturate slightly to push the subject forward. (2026-07-21)
- Particulate in the water column should stay visible; over-clarifying it sells the illusion that this is studio work. (2026-08-18)

## Tone

- Avoid `tone_compress_highlights` on bright water surfaces — it reads as fake / over-processed. Better to let highlights blow out a bit. (2026-08-18)
- Underwater shadows on subject undersides need explicit lift; ambient down-light from surface alone leaves them too dark. (2026-09-12)

## Sharpening / structure

- Don't sharpen water particles or background blur. They should stay soft. (2026-08-18)
- Subject-only sharpening; background water column must remain unsharpened to preserve depth. (2026-10-30)

## Local adjustments

- Subject mask is the most-used local target. Background mask for water-column adjustments is the second-most-used. (2026-07-21)
- For mantas / mobulas / large pelagic subjects: mask the body, lift shadows; separately mask the surrounding water, slightly desaturate. (2026-07-21)
- Avoid masking individual fins / wing-tips; the masker doesn't get them reliably and refining isn't worth it for those small areas. (2026-10-30)
- Eye contrast on cetaceans matters; small tight mask + `contrast_eye_punch` works better than wider subject-mask treatment. (2026-12-04)

## Vocabulary patterns

- I reach for `wb_cooler_subtle` constantly underwater to push the slate-blue target. Almost always applies. (2026-09-03)
- `colorcal_recover_blue_subtle` rarely needs to be applied underwater — water is already blue. Useful only when warm-cast strobe lighting overpowered the ambient. (2027-01-09)
- The pair (`tone_lift_shadows_subject` on subject mask) + (`wb_cooler_subtle` on background mask) is my single most-common move set for marine subjects. (2027-02-14)

## What I avoid

- Cyan-pop / "tropical reef" looks (already noted in color section, repeated for emphasis).
- Aggressive denoise on subject — texture matters more than noise does. (2026-09-03)
- Highlight reconstruction that pushes overexposed water back to neutral — looks fake. (2026-08-18)
