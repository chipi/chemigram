# Worked Example: Galápagos Iguana, Session 1

*A concrete Mode A walkthrough demonstrating the agent loop, its frictions, and what the session produces.*

> **Note on capabilities:** this example shows a session against the **v1.5.0** capability surface — drawn-form geometric masks (gradient/ellipse/rectangle) baked into vocabulary entries' `mask_spec`, plus the photographer's accumulated personal vocabulary (~80 entries). Pixel-precise content-aware masking ("mask the iguana exactly," "mask just the eyes") is Phase 4 work via a sibling project (`chemigram-masker-sam`) producing darktable drawn-form geometry; per ADR-076 the v1.4-and-earlier PNG-mask path was retired (it was a silent no-op). The session honors that honestly — surfacing where v1.5.0 can't satisfy a brief and what compounds toward Phase 4.

This example shows the agent loop in action. It's intended as an onramp for new readers — read this and you understand what Chemigram actually does, before diving into architecture or layer-model docs.

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
agent: "Noted in notes.md. About subject isolation: pixel-precise
        content-aware masking ('mask the iguana exactly') is Phase 4
        work — the sibling project producing darktable drawn-form
        geometry isn't shipped yet. For today, two paths:

        (a) Use radial_subject_lift_marine from your personal vocab —
            a centered ellipse you authored for animal-on-rock
            compositions. Approximates the subject area; not pixel-
            precise, but the iguana sits roughly center-frame here so
            the approximation should be acceptable.
        (b) Apply effects globally and accept they touch the
            background too.

        I'd lean (a). Your taste notes say you accept this kind of
        geometric approximation when the subject is centered."

photographer: "(a) is fine"

agent: snapshot(label="color target captured, drawn-form mask plan set")
```

This turn took several exchanges but did real work: established the color target, captured it in `notes.md`, and made an honest call about masking. The agent named the v1.5.0 limit (no pixel-precise masking yet) without dressing it up — and proposed a workable approximation grounded in the photographer's taste.

### Turn 4 — Water blue work + a real Phase 2 gap

```
agent: "Now the water-blue work. Ideal would be your hypothetical
        wb_warm_water_only — a parametric mask in blendop_params
        restricting WB warmth to cyan-blue hues only. You haven't
        authored that one yet.

        Three paths:
        (a) Apply wb_warm_subtle (starter) globally; the warmth
            touches the iguana too but at this strength it's mild
            and your taste notes say you bias warmer on subjects
            with natural warmth, so it might be fine.
        (b) Apply your radial_subject_lift_marine (centered ellipse,
            +0.6 EV) which we already planned for and stack a
            subtle warm WB over it. The radial mask shapes the
            warmth toward the subject area.
        (c) Skip for now and log the gap; come back to it after
            you've authored wb_warm_water_only this weekend.

        I'd lean (b) — does double duty (subject lift + warmth)
        and uses what we have."

photographer: "(b) — and log the gap, I'll author the parametric
                version next vocabulary evening"

agent: [ appends to vocabulary_gaps.jsonl:
         "wb_warm_water_only — parametric WB restricted to cyan-blue
         hue range via blendop_params. Workaround: radial_subject_lift_marine
         + global wb_warm_subtle. Session 1, image iguana_galapagos.
         intent_category: wb. Recurring across underwater work." ]

agent: apply_primitive(image_id, "radial_subject_lift_marine")
        # personal-pack entry, mask_spec: ellipse centered on frame
agent: apply_primitive(image_id, "wb_warm_subtle")
agent: render_preview(image_id)

[ photographer sees: subject area lifted and warmed, water still reads
  cool but the subject pulls forward against it ]

photographer: "Iguana's still a little gray. Push the warm a touch more"

agent: "I can stack grade_shadows_warm — it'll add an orange tint to
        the shadow zones. Since the iguana is the dominant shadow
        region in the frame, it lands mostly on him."

agent: apply_primitive(image_id, "grade_shadows_warm")
agent: render_preview(image_id)

photographer: "Yes that's it"

agent: snapshot(label="subject lifted + warm + shadow grade")
```

The vocabulary gap was real and got worked around. The agent surfaced it explicitly (a parametric `wb_warm_water_only` entry the photographer can author from a single darktable evening — see [`docs/guides/authoring-vocabulary-entries.md`](../docs/guides/authoring-vocabulary-entries.md)), the workaround stacked three existing primitives, the gap is now logged. This is the Phase 2 loop working — gaps don't block the work; they accumulate as concrete authoring targets that take 15 minutes each in darktable's GUI.

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

### Turn 6 — Eye work, the v1.5.0 → Phase 4 honesty moment

```
agent: "Now the eye work — 'more clear, more attention.' I want to be
        honest about what's available today.

        Eye-precise masking — isolating just the iguana's eyes —
        requires content-aware AI masking. That's Phase 4 work via
        the chemigram-masker-sam sibling project (will produce
        darktable drawn-form geometry per ADR-076). Not shipped yet.

        Three options today:

        (a) Apply clarity_painterly globally. Soft local-contrast,
            touches everything. Eyes pop a bit but so does the
            background — your taste notes say you accept this on
            quiet animal portraits where the subject is the story.
        (b) Skip eye work this session. The radial subject lift +
            warmth + structure work we have planned will pull the
            eye toward the iguana naturally; that may be enough.
        (c) Author a personal radial-eye drawn-form mask later
            (ellipse centered on the eye region) and revisit.
            Not great for a moving subject but works for static
            portraits where the eyes are predictable.

        Honestly? (b) — your previous moves are doing most of the
        separation work already. Fine-grain eye clarity is the
        kind of thing Phase 4 will fix; for today, the brief is
        substantially satisfied without it."

photographer: "Yes (b), we'll come back when chemigram-masker-sam
                ships. Log it as a gap."

agent: [ appends to vocabulary_gaps.jsonl:
         "eye-precise local clarity on animal portraits — content-aware
         masking, Phase 4 sibling project. Not a vocabulary-authoring
         gap, an architecture gap. Workaround: skipped this session;
         radial subject lift + structure handle most of the visual
         separation. Session 1, image iguana_galapagos." ]

agent: snapshot(label="eye work deferred, brief substantially satisfied")
```

The eye work is the v1.5.0 → Phase 4 honesty moment. The agent didn't fake a workaround, didn't overpromise; it named the architectural limit, proposed honest options, and the photographer chose to skip. The gap log differentiates "vocabulary-authoring gap" (the photographer can fix tonight in darktable) from "architecture gap" (Phase 4 sibling project is the answer) — both are valid observations, but the response shapes are different.

### Turn 7 — Subject crispness for separation

```
agent: "Last brief item: crispness on the iguana for separation. From
        your taste notes you bias toward subtle structure. Two
        candidates:

        (a) clarity_painterly globally — soft local contrast, touches
            the whole frame. Works for animal portraits where the
            subject is the story.
        (b) clarity_strong — sharper, but you've flagged it as
            'reads aggressive' in your taste.

        I'd default to (a)."

photographer: "(a), and the previous moves are doing most of the
                separation work already"

agent: apply_primitive(image_id, "clarity_painterly")
        # expressive-baseline; soft local contrast (detail 0.4)
agent: render_preview(image_id)

[ photographer sees: iguana slightly more dimensional, fine detail
  on scales emerging without crunchy halos ]

photographer: "That works"

agent: snapshot(label="clarity_painterly applied")
```

Quick and clean because the previous turns had set the right context. Taste.md said "bias toward subtle"; the agent honored it without needing a discussion. `clarity_painterly` is a global move (touches the whole frame) — in v1.5.0 there's no shipped subject-only structure entry, but the iguana is dominant enough in the composition that a soft global clarity reads as subject-emphasis. A future personal entry like `clarity_painterly_radial_subject` (drawn-form ellipse) could refine this if the photographer wants tighter localization.

### Turn 8 — Final review, end-of-session synthesis

```
agent: render_preview(image_id, size=2048)  [ larger render for review ]

agent: "Here's where we landed. Quick summary of what we did:
        - Baseline: lens correction, denoise, underwater_pelagic_blue
        - Subject area: radial_subject_lift_marine (centered ellipse,
          drawn-form mask in blendop_params per ADR-076)
        - Water/warmth work: wb_warm_subtle + grade_shadows_warm,
          stacked over the radial. Worked around the missing
          wb_warm_water_only entry.
        - Highlights: gradient_top_dampen_highlights (drawn-form
          gradient mask), subtle to preserve background contrast
        - Eye work: deferred to Phase 4 (chemigram-masker-sam)
        - Subject crispness: clarity_painterly globally (subject
          area + background; your taste says fine for animal portraits)

        Anything to adjust before tagging this for export?"

photographer: "Looks good, tag it"

agent: tag(image_id, name="iguana_galapagos_v1")
agent: export_final(image_id, ref="iguana_galapagos_v1", size=4096)

agent: "Exported. End-of-session synthesis:

        Proposed updates to taste.md:
        1. 'For Galápagos / similar coastal underwater subjects: stack
           radial_subject_lift_marine + wb_warm_subtle + grade_shadows_warm
           as a default. Iguana-on-rock pattern.' Accept?
        2. 'Bias to ask about composition tradeoffs before applying
           strong gradient/dampening moves.' Accept?

        Proposed additions to vocabulary_gaps.jsonl (already logged
        in-session, just confirming):
        - wb_warm_water_only — parametric WB by hue range. Authorable
          this weekend in darktable (vocabulary gap, not architecture).
        - eye-precise local clarity — Phase 4 sibling project work
          (architecture gap, not vocabulary).

        Proposed addition to image notes.md:
        - 'Subject color target: warm dark gray, photographer's visual
           memory.' Already added in-session.
        - 'Eye work deferred to Phase 4. radial + structure carried
           the visual separation.'

        Architecture observation worth tracking: this session shows
        the v1.5.0 → Phase 4 boundary cleanly. Drawn-form masks
        carry placement-driven moves; subject-precise moves wait on
        the sibling project."

photographer: "Accept 1 and 2 for taste.md. Accept both gap notes.
                Add both observations to this image's notes."

agent: [ updates ~/.chemigram/taste.md with two new notes ]
agent: [ confirms vocabulary_gaps.jsonl entry ]
agent: [ updates <image_id>/notes.md with the masking observation ]

agent: "Done. Session log written. See you next time."
```

End-of-session synthesis is where the compounding happens. Two new entries in `taste.md` that didn't exist before. One vocabulary gap waiting for the photographer to spend an evening authoring it. One image note that future sessions on this image will read.

## Session metrics

- **Wall time:** roughly 45 minutes
- **Conversational turns:** about 22
- **Snapshots created:** 7 (each meaningful state)
- **Branches:** 0 (no exploration this session, just main)
- **Vocabulary entries applied:** 6 distinct (4 personal-pack including 1 mask-bound, 2 expressive-baseline including 1 mask-bound)
- **Drawn-form masks bound:** 2 (radial_subject_lift_marine + gradient_top_dampen_highlights — both via `mask_spec`, encoded into `masks_history` per ADR-076)
- **Vocabulary gaps surfaced:** 2 (one authorable in darktable, one Phase 4 architecture)
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

- The missing `wb_warm_water_only` entry added one extra turn (acceptable cost; future sessions benefit once the photographer authors it)
- Eye work was deferred to Phase 4 — honest acknowledgment, not a workaround
- Some of the agent's surfacing was verbose (could be tuned with prompt iteration)

### About what compounds

- `taste.md` now contains two notes that will inform every future session
- `vocabulary_gaps.jsonl` has one entry that, when authored, makes the underwater workflow one turn shorter
- This image's `notes.md` carries forward the color target and tooling observation
- The session transcript itself is reviewable later — "how did we land on the iguana color?" → just read the session

## What this session reveals about gaps

Concrete to-do items the session surfaced:

**Vocabulary gaps to author** (Phase 2 work — open darktable, capture, drop into personal pack):
- `wb_warm_water_only` — parametric WB restricted to cyan-blue hue range via `blendop_params`. ~15 minutes in darktable's GUI; see [`docs/guides/authoring-vocabulary-entries.md`](../docs/guides/authoring-vocabulary-entries.md).
- Possibly `radial_subject_lift_marine_strong` if the existing radial doesn't push hard enough on darker subjects.

**Architecture gaps** (Phase 4 sibling project):
- Eye-precise / pixel-precise content-aware masking → `chemigram-masker-sam` will produce darktable drawn-form geometry from natural-language prompts; the apply path stays unchanged when it lands. ADR-076 documents the seam.
- A potential `radial_subject_lift_offcenter` family if many of the photographer's compositions don't land the subject mid-frame; could ship as an expressive-baseline addition or stay personal.

**Process observations:**
- End-of-session synthesis is valuable but verbose — worth tuning prompt for terser proposals
- The composition tension catch (Discipline 6) felt natural in this session; worth instrumenting how often the agent catches vs. misses these
- The vocabulary-gap-vs-architecture-gap distinction (made in this session) is genuinely useful for triaging the backlog — different gap types have different response shapes

These observations would feed into the next iteration of the agent prompt, the vocabulary, and the engine. That's the compounding loop at the project level.

## What you should take away

If you're reading this for the first time:

1. **A session is a structured engagement, not a series of slider tweaks.** It begins with context-reading, ends with synthesis. The middle is the work.

2. **The agent is an apprentice, not a tool.** It surfaces uncertainty, catches tensions, asks before committing, learns across sessions.

3. **Compounding is the point.** Session 5 will be faster than session 1 because `taste.md` has captured patterns, the vocabulary has been extended, and the agent has more context.

4. **Friction is information.** Vocabulary gaps and tooling limits aren't failures — they're surfaced to a backlog and addressed when the photographer chooses to.

5. **The photographer is still the photographer.** The agent makes the work tractable and the loop fast, but every meaningful decision goes through the photographer. The compounding is real but bounded.

This is the project's promise: an agent that learns *your* photo work, with you, over time. Not a tool that automates editing. A relationship that compounds craft.
