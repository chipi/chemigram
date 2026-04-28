# wildlife.md — wildlife photography preferences

*~12 entries. Last revised: 2027-03-22.*

Preferences specific to wildlife photography — animal subjects above water (terrestrial, surface marine, birds). Loads when `brief.md` declares `wildlife` in its `Tastes` field. Often paired with `underwater` for marine wildlife above-water shots (e.g., basking iguanas, surfacing mantas viewed from above).

---

## Tone

- Midtone lift for portraits of land animals (iguanas, sea lions, birds); not needed for fish in motion. (2027-01-09)
- For dark-skinned subjects (marine iguanas, black-feathered birds), lift shadows aggressively on the subject mask — eyes need to be readable. (2027-02-14)

## Color

- Skin / scale tones lean warm rather than neutral. A 100K warm push on the subject mask reads more lifelike than perfect neutrality. (2027-01-09)

## Local adjustments

- Eye masks for portraits where eye-pop matters. Tight mask + small `contrast_eye_punch` is the workhorse. (2026-05-12)
- For animal subjects with prominent texture (scales, feathers, fur): subject mask + `structure_subtle` outperforms global structure. (2026-07-21)
- Don't mask individual feathers / scales / claws; the masker isn't precise enough. Subject-level only. (2026-10-30)

## Composition / crop

- Animal portraits crop tight; environment rarely earns its frame share for these. (2027-01-09)
- Eye contact framing matters — when the subject is looking at the lens, leave less negative space on the gaze side. (2027-02-14)

## What I avoid

- Saturating animal subjects to make them "pop." Reads taxidermy. (2026-11-14)
- Sharpening eyes harder than the rest of the face; small mask + gentle contrast lift looks more natural. (2027-01-09)

## Vocabulary patterns

- The triplet (subject_mask + `tone_lift_shadows_subject` + `structure_subtle`) is my default for animal portraits. Tightens the subject without overprocessing. (2027-02-14)
- For eyes specifically: tight oval mask + `contrast_eye_punch`. The mask shape matters more than the primitive intensity. (2026-05-12)
