# Worked Example: Galápagos Iguana, Session 1

*A concrete Mode A walkthrough demonstrating the agent loop, its frictions, and what the session produces.*

This example shows the loop from `agent-context.md` in action. It's intended as an onramp for new readers — read this and you understand what Chemigram actually does, before diving into architecture or layer-model docs.

## The setup

**Image:** raw of a marine iguana on Galápagos volcanic rock, taken from underwater (subject partially submerged). Photographer is Marko, primary use case for the project.

**Photographer's brief (typed at session start, written into `brief.md`):**

> "Underwater shot of iguana in Galápagos. Adjust for underwater and color correct to get nice blues, but make sure iguana and rest of the photo stays in their natural colors. Remove highlight at top from the sun gradually toward down. Put more attention to eyes and make them a bit more clear. Overall make iguana more stand out from the background with some crispness."

**Existing context:**

- `~/.chemigram/taste.md` exists from prior sessions — captures Marko's preferences for restraint, natural color, underwater work patterns.
- `metadata.json` populated from EXIF: Sony A1 + 16-35mm at 28mm, ISO 400, f/8, 1/200s.
- Suggested L1 binding: `lens_correct_full + denoise_auto`.
- Suggested L2 binding: `underwater_pelagic_blue` (matches the EXIF + scene-tag heuristic).
- Vocabulary: assume v1 starter + Marko's accumulated underwater entries (~80 entries total).

## The loop

### Turn 1 — Session start, agent reads context

```
[ user opens session on this image ]
[ agent reads ~/.chemigram/taste.md, brief.md, notes.md (empty for new image),
  log.jsonl (empty), metadata.json, get_state(), list_vocabulary() ]

agent: "I've read your context. This is a Sony A1 underwater shot of a
        Galápagos marine iguana, ISO 400, intended for portfolio per the
        brief. From your taste notes: you prefer slate-blue for water over
        cyan, prefer natural color preservation on subjects, and bias
        toward subtle moves on structure work.

        I'll start by applying the suggested L1 (lens correction +
        profiled denoise) and L2 (underwater_pelagic_blue) baseline,
        snapshot, and render so you can see where we're starting from.
        Sound good?"

photographer: "Go"
```

The agent has its bearings. Brief read, context applied, plan stated, pre-execution check. Could have skipped the check — taste.md says "default to acting on clear briefs" — but for a new image with no notes, surfacing is right.

### Turn 2 — Apply baseline, render

```
agent: bind_layers(image_id, l1="lens_correct_full + denoise_auto",
                              l2="underwater_pelagic_blue")
agent: snapshot(label="L1+L2 baseline")
agent: render_preview(image_id, size=1024)

[ photographer sees baseline render: water already substantially de-cast,
  iguana visible but somewhat flat, sun highlight prominent at top ]

agent: "Baseline applied. Water's been pulled toward neutral — slightly
        cool but not aggressive. Iguana looks brown-gray from underwater
        cast, which is expected. Subject mask next, since we'll need it
        for at least three of the brief's items."
```

### Turn 3 — Background research, then subject mask

The agent recognizes "natural color of iguana" as a spec it doesn't fully understand. Per Discipline 7 (background research), it pauses to look up.

```
[ agent searches: "Galapagos marine iguana coloration species typical" ]
[ agent retrieves a few reference images, vision-model analyzes ]

agent: "Quick research: marine iguanas (Amblyrhynchus cristatus) are
        typically dark gray to near-black, with seasonal red/orange
        flush during breeding season (Dec-Mar). Looking at your photo,
        the iguana looks more brown-gray than the references suggest —
        consistent with blue water cast pulling cooler tones up.

        Two questions before I proceed:
        - Was this shot during breeding season? If so, we should preserve
          some of the red/orange you might want.
        - When you say 'natural color,' do you mean species-typical
          slate-gray, or what the iguana looked like that day on that
          rock in that light? They might differ."

photographer: "Not breeding season, just the typical gray. And by natural
                I mean what it actually looked like to my eye — kind of a
                warm dark gray. The water made it look cooler in the raw."

agent: [ writes to notes.md, propose-and-confirm:
         "Subject color target: warm dark gray, photographer's
         visual memory. Not species-typical slate, not raw appearance." ]
agent: "Noted in notes.md. Generating subject mask now."

agent: generate_mask(image_id, target="subject")
agent: render_preview(image_id, with_mask_overlay=True)

[ photographer sees mask overlay on preview ]

agent: "Mask isolated the iguana cleanly. It includes the iguana's body
        and tail but not the rocks. Want me to extend to include rocks
        (treat them as 'subject context'), or keep tight to the animal?"

photographer: "Tight is fine"

agent: snapshot(label="subject mask generated")
```

This turn took several exchanges but did real work: established the color target, captured it in `notes.md`, generated and verified the mask. Three discoveries the photographer benefits from later — including the species research that's now in the agent's working memory for the rest of the session.

### Turn 4 — Water blue recovery, vocabulary gap surfaces

```
agent: "Now the blue water work. Looking for an entry that pulls water
        toward blue while protecting the subject — composite mask."

[ agent scans vocabulary, finds none with both raster mask + parametric ]

agent: "Vocabulary gap: I don't have a single entry for 'water-only blue
        recovery while protecting subject.' Two paths:

        (a) Apply global blue recovery (`colorcal_underwater_recover_blue`),
            then a subject-protection move (`colorcal_warm_protect_subject`)
            that counters the cool shift on the iguana.

        (b) Skip this for now and we'll come back when the entry exists.

        I'd lean (a) — gets you to the right result via two moves
        instead of one. Logging the gap so you can author the
        single-step entry later."

photographer: "(a) is fine"

agent: [ appends to vocabulary_gaps.jsonl:
         "colorcal_underwater_recover_blue_water_only — composite mask
         (parametric hue + inverse subject raster). Worked around with
         global + subject-protection counter. Session 1, image
         iguana_galapagos." ]

agent: apply_primitive(image_id, "colorcal_underwater_recover_blue")
agent: render_preview(image_id)

[ photographer sees: water now firmly blue, iguana now noticeably cooler
  than was acceptable — the cost of fighting the move locally ]

agent: "Now the protection counter. This pulls warmth back into the
        iguana only."

agent: apply_primitive(image_id, "colorcal_warm_protect_subject")
agent: render_preview(image_id)

[ photographer sees: water blue maintained, iguana warmed back toward
  the dark-gray target ]

photographer: "Iguana's still a little gray. Push the warm a touch more"

agent: apply_primitive(image_id, "colorcal_warm_protect_subject_strong")
        # SET semantics replace previous entry
agent: render_preview(image_id)

photographer: "Yes that's it"

agent: snapshot(label="water blue + subject protected")
```

The vocabulary gap was real and got worked around. The agent surfaced it explicitly, the workaround took an extra turn, the gap is now logged for later authoring. This is the system working as designed — gaps don't block the work, they accumulate as future improvement targets.

### Turn 5 — Top-down highlight dampening, composition tension surfaces

```
agent: "Now the top-down highlight dampening for the sun. But before I
        apply it — quick composition note: the bright top of frame is
        currently helping separate the iguana from the background. If
        we dampen too aggressively, we lose some of that contrast.
        We'd need to compensate with structure on the iguana to maintain
        separation.

        Two options:
        (a) Subtle dampen — pulls back just the brightest spots without
            killing the overall light gradient.
        (b) Stronger dampen — more dramatic, but we'll need to push
            the iguana structure harder to compensate.

        The brief mentioned 'gradually toward down' which I read as 'just
        the very top, falling off quickly' — that's option (a). Want
        to start there?"

photographer: "Yes (a), good catch on the contrast"
```

Discipline 6 in action. The agent caught a tension the brief glossed over and surfaced it before committing. The photographer benefits — they're now thinking about the contrast tradeoff instead of discovering it after the fact.

```
agent: apply_primitive(image_id, "gradient_top_dampen_highlights")
agent: render_preview(image_id)

[ photographer sees: top of frame slightly cooler/darker, iguana still
  reads against the background ]

photographer: "Looks right"

agent: snapshot(label="highlights dampened, subtle")
```

### Turn 6 — Eye work, masking gets harder

```
agent: "Now the eye work — 'more clear, more attention.' This is fine-grained
        and I want to be honest about uncertainty here.

        Standard subject mask covers the whole iguana. For eye-level
        work I'd need to use prompted segmentation to isolate just the
        eyes. Quality varies — sometimes great, sometimes catches one eye
        and not the other.

        Three options:
        (a) Try prompted eye mask. If it works cleanly, apply clarity
            there. If not, fall back.
        (b) Apply subtle clarity to the whole iguana. Eyes get lifted
            along with the rest, but consistently. Less precise but
            reliable.
        (c) Skip eye work this session, revisit when masking tools
            improve.

        I'd try (a) first, fall back to (b) if needed. Fine?"

photographer: "(a)"

agent: generate_mask(image_id, target="custom", prompt="iguana eyes",
                     name="iguana_eyes")
agent: render_preview(image_id, with_mask_overlay=True, mask="iguana_eyes")

[ photographer sees: mask shows both eyes + a small region of scales
  near the right eye that got picked up incorrectly ]

agent: "Mask got both eyes but caught a few scales near the right eye.
        Imperfect. Three options now:
        (a) Accept and proceed. The extra area will get clarity too,
            slightly lifting those scales. Probably visible at 100% but
            unlikely to be objectionable.
        (b) Regenerate with a tighter prompt.
        (c) Fall back to whole-iguana clarity (option b from before)."

photographer: "Try (b), tighter prompt"

agent: regenerate_mask(image_id, target="custom",
                        prompt="iguana eye pupils only",
                        name="iguana_eyes")
agent: render_preview(image_id, with_mask_overlay=True, mask="iguana_eyes")

[ photographer sees: tighter mask, just the dark center of each eye ]

photographer: "Better"

agent: apply_primitive(image_id, "clarity_strong_masked",
                        mask_override="iguana_eyes")
agent: render_preview(image_id)

[ photographer sees: eyes pop slightly more — subtle but noticeable ]

photographer: "Good"

agent: snapshot(label="eyes lifted with clarity")
```

The eye work is the hardest part of the session and the agent handled it well: surfaced uncertainty, offered options, demonstrated the mask, accepted refinement, applied the move. Two extra turns vs. perfect tooling, but no surprises and the photographer stayed in control.

### Turn 7 — Subject crispness for separation

```
agent: "Last brief item: crispness on the iguana for separation. Subject
        mask is still active. From your taste notes you bias toward
        subtle structure — should I start there or push harder given
        we softened the top contrast?"

photographer: "Subtle is fine, the eye work and color work are doing
                most of the separation already"

agent: apply_primitive(image_id, "structure_subject_subtle")
agent: render_preview(image_id)

[ photographer sees: iguana slightly more dimensional, fine detail
  on scales emerging without crunchy halos ]

photographer: "That works"

agent: snapshot(label="subject structure subtle")
```

Quick and clean because the previous turns had set the right context. Taste.md said "bias toward subtle"; the agent honored it without needing a discussion.

### Turn 8 — Final review, end-of-session synthesis

```
agent: render_preview(image_id, size=2048)  [ larger render for review ]

agent: "Here's where we landed. Quick summary of what we did:
        - Baseline: lens correction, denoise, underwater_pelagic_blue
        - Subject mask: clean isolation of iguana
        - Water work: blue recovery + subject warmth protection (two
          steps because the composite-mask vocabulary entry didn't exist)
        - Highlights: subtle top-down dampen (subtle to preserve
          background contrast — your call)
        - Eyes: prompted mask + strong clarity, second attempt cleaner
        - Subject: subtle structure for separation

        Anything to adjust before tagging this for export?"

photographer: "Looks good, tag it"

agent: tag(image_id, name="iguana_galapagos_v1")
agent: export_final(image_id, ref="iguana_galapagos_v1", size=4096)

agent: "Exported. End-of-session synthesis:

        Proposed updates to taste.md:
        1. 'For Galápagos / similar coastal subjects: blue cast is
           strong; standard pattern is global blue recovery + subject
           warmth protection.' Accept?
        2. 'Bias to ask about composition tradeoffs before applying
           strong gradient/dampening moves.' Accept?

        Proposed addition to vocabulary_gaps.jsonl (already logged
        in-session, just confirming):
        - colorcal_underwater_recover_blue_water_only (composite mask)

        Proposed addition to image notes.md:
        - 'Subject color target: warm dark gray, photographer's visual
           memory.' Already added in-session.

        Tooling observation worth noting: prompted eye mask required
        a refinement turn. If 'iguana eyes' is a recurring need,
        worth either authoring a tighter system prompt or training
        a small specialist masker."

photographer: "Accept 1 and 2 for taste.md. Accept the gap note.
                Note the tooling observation in this image's notes."

agent: [ updates ~/.chemigram/taste.md with two new notes ]
agent: [ confirms vocabulary_gaps.jsonl entry ]
agent: [ updates <image_id>/notes.md with the masking observation ]

agent: "Done. Session log written. See you next time."
```

End-of-session synthesis is where the compounding happens. Two new entries in `taste.md` that didn't exist before. One vocabulary gap waiting for the photographer to spend an evening authoring it. One image note that future sessions on this image will read.

## Session metrics

- **Wall time:** roughly 50 minutes
- **Conversational turns:** about 25
- **Snapshots created:** 8 (each meaningful state)
- **Branches:** 0 (no exploration this session, just main)
- **Vocabulary entries used:** 8 distinct entries
- **Vocabulary gaps surfaced:** 1
- **Mask generations:** 2 (subject + eye, with one regeneration)
- **`taste.md` additions accepted:** 2
- **`notes.md` additions:** 2
- **Final result:** tagged snapshot, full-resolution JPEG exported

## What this session demonstrates

### About the loop working as designed

- Agent read context at session start, oriented correctly, didn't restart from zero
- Brief was honored even where it had tensions (composition tradeoff caught)
- Background research informed color decisions appropriately
- Vocabulary gap was worked around without blocking, then logged for later
- Mask quality variance was surfaced honestly, photographer kept in control
- End-of-session synthesis updated taste.md with patterns from this session

### About friction points

- The composite-mask vocabulary gap added one extra turn (acceptable cost, future sessions benefit)
- Eye masking required a refinement turn (cost of imperfect tooling)
- Some of the agent's surfacing was verbose (could be tuned with prompt iteration)

### About what compounds

- `taste.md` now contains two notes that will inform every future session
- `vocabulary_gaps.jsonl` has one entry that, when authored, makes the underwater workflow one turn shorter
- This image's `notes.md` carries forward the color target and tooling observation
- The session transcript itself is reviewable later — "how did we land on the iguana color?" → just read the session

## What this session reveals about gaps

Concrete to-do items the session surfaced:

**Vocabulary gaps to author:**
- `colorcal_underwater_recover_blue_water_only` (composite parametric + raster mask)
- Possibly `colorcal_warm_protect_subject_strong` if the strength variants don't ladder well
- `structure_subject_with_warmth` if the combined move comes up again

**Tooling observations:**
- Prompted segmentation for fine features ("eyes", "fins", "specific patterns") would benefit from caching successful prompts per species/subject
- A `mask_overlay_render` mode that shows both the rendered preview and the active masks would speed up mask verification

**Process observations:**
- End-of-session synthesis is valuable but verbose — worth tuning prompt for terser proposals
- The composition tension catch (Discipline 6) felt natural in this session; worth instrumenting how often the agent catches vs. misses these

These observations would feed into the next iteration of the agent prompt, the vocabulary, and the engine. That's the compounding loop at the project level.

## What you should take away

If you're reading this for the first time:

1. **A session is a structured engagement, not a series of slider tweaks.** It begins with context-reading, ends with synthesis. The middle is the work.

2. **The agent is an apprentice, not a tool.** It surfaces uncertainty, catches tensions, asks before committing, learns across sessions.

3. **Compounding is the point.** Session 5 will be faster than session 1 because `taste.md` has captured patterns, the vocabulary has been extended, and the agent has more context.

4. **Friction is information.** Vocabulary gaps and tooling limits aren't failures — they're surfaced to a backlog and addressed when the photographer chooses to.

5. **The photographer is still the photographer.** The agent makes the work tractable and the loop fast, but every meaningful decision goes through the photographer. The compounding is real but bounded.

This is the project's promise: an agent that learns *your* photo work, with you, over time. Not a tool that automates editing. A relationship that compounds craft.
