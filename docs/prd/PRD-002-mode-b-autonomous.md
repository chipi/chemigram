# PRD-002 — Mode B: autonomous fine-tuning

> Status · Draft v0.1 · 2026-04-27
> Sources · 01/The work, 02/Mode B
> Audiences · photographer (PA/audiences/photographer) — specifically the taste-articulator and exploratory editor sub-shapes
> Promises · agent-as-apprentice, inspectable-state, vocabulary-as-voice, photographer-controls-everything (PA/promises)
> Principles · agent-is-the-only-writer, restraint-before-push, compounding-over-throughput, honest-about-limits (PA/principles)
> Why this is a PRD · Mode A is the conversational loop where the photographer is in every turn. Mode B is the deferred mode where the agent explores autonomously between sessions, then surfaces variants for judgment. The user-value argument is real but distinct from Mode A's: it's about expanding what one image can become, not about the back-and-forth conversation. Wanting it built is not enough — the case has to be made.

It's Saturday morning. The iguana is at v1 — yesterday you got it to "this is good." But there's a thread you didn't pull. The brief said "subtle"; you stayed conservative. You wonder what the image looks like if it's pushed harder — not abandoned to a different look, but explored along the same vector. You don't have time to do the exploration yourself. You leave a note: "explore three variants, all within the spirit of v1, each pushing one axis: tone (more dramatic shadow lift), color (warmer subject), structure (more clarity on the rock texture). Cap at 30 minutes. Show me when you're done." You close the laptop. Two hours later, you come back to three branches: `branch_b_tone`, `branch_b_color`, `branch_b_structure`. Each is rendered, tagged, and has a one-paragraph note from the agent explaining what it tried and what it judged. You compare. Two are not what you wanted. One — the structure variant — is genuinely better than v1. You tag it `v2`. The iguana is done.

## The problem

Every photographer has the same experience: an image that's "good" but unfinished. The work that would push it from good to memorable requires *time the photographer doesn't have* and *exploration the photographer can't always do consciously*. You know there's more in the image; you don't have the bandwidth to find it.

Existing tools don't help. Lightroom's "auto" buttons suggest defaults, not exploration. Preset packs offer borrowed looks, not extensions of the photographer's own direction. What's missing is a collaborator who can *do work while you're not at the keyboard* — who knows your taste well enough to explore within it (not outside it), who reports back honestly, and whose work is fully inspectable so you can audit what they tried.

This is harder than it sounds. Autonomy has to be bounded — the agent that "experiments freely" produces a hundred variants you don't want. The agent's exploration has to be guided by the photographer's actual taste (`taste.md`, vocabulary, this image's brief) rather than generic "make it look good." Reports back have to be honest — "I tried X, it was worse, I abandoned it" matters as much as "I tried Y, it was better." The branching and tagging from Mode A gives Mode B somewhere to put the variants without polluting main. The vocabulary system gives the agent named, finite moves rather than continuous slider-flailing. Mode B is built on top of Mode A's substrate; it's not a separate product.

But it's not Mode A either. The relationship is different — the photographer hands off, the agent works alone, the photographer judges later. The pacing is different (hours, not minutes). The trust is different (more autonomy, hence more careful constraints). PRDing it separately makes the difference visible.

## The experience

The photographer ends a Mode A session with a state they like — call it `v1`. They want exploration along specific axes, but not now. They open Mode B with an instruction:

> "Starting from v1, explore variants that push the image along these vectors:
>  - tone: more dramatic shadow lift
>  - color: warmer subject
>  - structure: more clarity on the rock texture
> Stay within the spirit of v1 — don't introduce new looks. Cap effort at 30 minutes. Show me three branches, each judged with a short note. Snapshots tagged `branch_b_tone`, `branch_b_color`, `branch_b_structure`."

The agent confirms the instruction (propose-and-confirm: "Here's what I'm about to do; OK?"), the photographer says yes, the agent begins.

The agent runs. It branches from v1. On `branch_b_tone`, it tries `tone_lifted_shadows_subject` at higher intensity — too much, abandons. Tries combining with `tone_eq_zone_specific_shadows` — keeps. Renders, judges its own output ("subject feels present without breaking the brief's 'subtle'"). Snapshots, tags. Same on `branch_b_color`. Same on `branch_b_structure`. For each branch, the agent maintains a transcript and writes a paragraph-sized note explaining its path.

When the agent's exploration converges, it stops. It hasn't tried every combination — that wasn't asked. It surfaces the three branches.

The photographer comes back. Calls `compare(v1, branch_b_structure)`. Sees the variants side by side. Reads the agent's note. Decides: this one is genuinely better. Tags it `v2`. Discards the other two branches (or leaves them for later reference; gc happens manually). The iguana is done.

The session transcript captures everything the agent did — every primitive applied, every render judged, every dead-end abandoned. The audit trail is complete. The photographer can replay the agent's reasoning at any time.

## Why now

Mode B is genuinely v2 work — Mode A has to land first, the vocabulary has to be rich enough that exploration produces diverse variants, the agent has to be reliable enough that 30-minute autonomous work doesn't drift into nonsense. Today, none of those preconditions are met.

But the case for designing it now (in PRD form, with deliberation captured) is real:

1. **Branching and tagging exist for Mode B.** The versioning model in ADR-018 / ADR-019 has branches as a first-class concept partly because Mode B will use them. Designing the versioning without Mode B in mind would have produced a linear-undo model.

2. **Vocabulary scope is informed by Mode B.** A vocabulary that's just enough for Mode A is not enough for Mode B's exploration. Knowing Mode B is coming pushes vocabulary breadth.

3. **The agent's behavioral disciplines** (02/6) include autonomy bounding and honest reporting precisely because Mode B will exercise them. Without Mode B as a horizon, the disciplines would over-emphasize Mode A's conversational pacing.

4. **The research thesis depends on it.** A photographer using Chemigram for a year on Mode A alone would still produce a vocabulary and a `taste.md`, but Mode B is what tests whether the artifact has acquired enough of the photographer's craft for autonomous work. If Mode B can produce variants the photographer judges as "yes, that's me" — the thesis is confirmed. If it produces variants that feel generic — the thesis needs revisiting.

So: building Mode B is deferred. Designing for it is now.

## Success looks like

- A Mode B session with a 30-minute cap produces 3 variants, of which the photographer picks at least one as "yes, this is meaningfully better than v1, and within my voice." Across many images, the hit rate is high enough that the photographer trusts the mode.

- The agent's per-branch notes accurately describe what was tried and what was judged. When the photographer replays the transcript, no surprises ("you said you tried X but actually you did Y").

- The agent stops when asked. The 30-minute cap is honored. No "I went deeper because it seemed worth it" without the photographer having approved that.

- Mode B's exploration surfaces vocabulary gaps the photographer didn't realize they had. ("I kept reaching for X but you don't have it; I improvised.") These gaps feed back into vocabulary expansion.

## Out of scope

- **Real-time autonomous editing.** Mode B is deferred — the photographer hands off, comes back later. "Watch the agent work in real time" is not the experience.

- **Multi-image autonomous work.** Mode B is per-image, like Mode A. "Process my last 30 raws while I sleep" is bulk-edit (not an audience per PA/audiences/not-an-audience/bulk-edit-users).

- **Generative imagery.** Mode B explores within the existing image. It doesn't generate or composite new content.

- **Cross-photographer style transfer.** Mode B works within the photographer's own taste. "Make this look like Annie Leibovitz" or "apply Steve McCurry's color" is a different product entirely.

- **Indefinite autonomy.** Every Mode B session has an explicit cap (time, depth, branches). The agent never runs unbounded. "Just keep exploring until you're satisfied" is not a valid Mode B instruction.

- **Self-evaluating without photographer review.** The agent's judgment is its own work; the photographer always reviews variants before any of them become the canonical state. Mode B never autonomously updates `main` or removes branches.

## The sharpest threat

Mode B's value depends on the agent's *autonomous taste judgment* matching the photographer's *retrospective taste judgment* enough of the time. The agent says "this variant is better"; the photographer needs to agree often enough that the work isn't wasted exploration.

This is harder than Mode A because the photographer isn't in the loop — they can't redirect mid-stream. If the agent's taste calibration is off, an entire 30-minute session might produce three variants the photographer rejects. After two such sessions, trust collapses; Mode B becomes a feature people don't use.

The frame that breaks: that a `taste.md` accumulated through Mode A sessions is sufficient input for the agent to make autonomous taste judgments well. It might not be. Mode A's `taste.md` is shaped by what's *in conversation* — the bits the photographer found articulable. The bits they didn't articulate (because they were obvious, because they're hard to verbalize, because no session surfaced them) are missing. Mode B asks the agent to use what it has, which might not be enough.

Mitigation directions if this proves a problem:
- **Tighter constraints.** Mode B starts with extreme guardrails (1 variant, 10-minute cap) and earns more autonomy over time as the photographer's trust grows.
- **Mode-B-specific taste tier.** A `taste_for_mode_b.md` written explicitly by the photographer, not extracted from sessions. Captures the things that don't surface naturally in Mode A.
- **Supervised first variant.** Before exploring autonomously, the agent generates the first variant in a Mode A session, gets reviewed, and only then continues autonomously with that variant as a calibration anchor.

We won't know which mitigation matters until Mode B ships. The PRD captures the threat so we have a starting position when the time comes.

## Open threads

- **Mode B agent prompt template.** Needs to be written. Bounded autonomy, honest reporting, vocabulary-respecting exploration.
- **Mode B's evaluator.** Does the agent self-evaluate ("this variant is better"), or does a separate evaluator (a different LLM, configured per BYOA) judge? Architectural question; affects RFC for evaluator protocol.
- **RFC-005** — pipeline stage protocol. Mode B's autonomous exploration may need different pipeline stages (e.g., fast preview-only stages) than Mode A.
- **RFC-014** — end-of-session synthesis flow. Mode B has its own end-of-session: variant surfacing, comparison, photographer decision. Distinct flow from Mode A.

## Links

- PA/audiences/photographer
- PA/promises/agent-as-apprentice
- PA/promises/inspectable-state
- PA/principles/honest-about-limits
- 01/The work
- 02/Mode B
- Related: PRD-001 (Mode A), PRD-003 (Vocabulary as voice), PRD-004 (Local adjustments)
- ADR-018 (per-image DAG; branches enable Mode B)
- ADR-019 (git-like ref structure)
