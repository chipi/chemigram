# Phase 2 Playbook

> Your guide to actually using Chemigram in the use-phase. What to do this week, what to do this month, what signals to watch for. Phase 2 is open-ended — this guide gets richer as your use does.

## The shape of Phase 2

Phase 1 (build-phase) is done. The engine works. Phase 2 is where Chemigram becomes *yours* — not by adding features, but by accumulating use. Every session leaves something behind: a snapshot, a taste-file line, a logged gap, a personal vocabulary entry. After six months you don't have "the same tool, used a lot." You have a portrait of how you edit, externalized through the project.

That's the bet of the entire project. Phase 2 is where the bet plays out.

There are no slices, no gates, no PRs to ship. The work is intermittent — concentrated when you want to edit a photo or work on a project, dormant otherwise.

## Daily / weekly — running sessions

### Pre-session

A 90-second ritual that pays off:

- [ ] Have a real reason to edit this photo. Don't run sessions to "test the system" — that breeds shallow use. Edit photos you actually want to edit.
- [ ] Drop the raw somewhere accessible (e.g., `/tmp/photo.NEF` or in `~/Pictures/raw-archive/`). Chemigram will symlink it into its workspace.
- [ ] Open a fresh conversation in your MCP client (Claude Code, Cursor, etc.). Don't reuse a coding session — context bleeds.
- [ ] Optionally: pre-write a short `brief.md` in your workspace if the image deserves it. Or just describe the brief verbally — the agent can offer to capture it later.

### During the session

A few things to remember:

- **Don't over-direct.** "Apply expo_+0.5 then wb_warm_subtle" works but you've turned the agent into a slider panel. Better: "the water feels too cyan, can we warm it up?" Let the agent reach for what it has.
- **Trust the rendering loop.** A render takes 1–3 seconds. Use it. Ask for a preview after every 2–3 moves. The judgment is in the visual feedback, not in the description.
- **Watch what the agent reaches for.** If it says "I'd want to apply tone_lift_shadows_subject here but we don't have it" — that's a gap signal. Note it.
- **Watch what the agent *doesn't* reach for.** Sometimes the agent will skip a move you'd have made. Either ask why or recognize that you have an unexpressed preference. Both worth knowing.
- **Branch when curious.** `branch experimental` is free. Use it for exploring "what if we went warmer" without commitment.
- **Snapshot before significant moves.** The agent does this automatically, but if you're about to do something destructive, ask explicitly.

### End of session

The agent will offer two propose-and-confirms. Take them seriously:

- **Taste-file proposals.** Read the proposed line *carefully*. Does it actually reflect a preference you'd want to inherit in future sessions? If it's surface-level ("the photographer prefers warm tones") — decline. If it's specific ("for pelagic shots, slate-blue water beats cyan-pop") — accept.
- **Notes proposals.** These go into the per-image `notes.md`. Good notes are reasoning ("I lifted shadows on the manta belly because the bottom-up angle made it read too dark against the surface"); bad notes are summary ("applied 7 primitives"). Decline summary; accept reasoning.

If the agent didn't propose anything but you noticed something worth capturing, ask: "I think we landed on a useful preference about [X]. Can you propose it as a taste update?"

### Post-session (optional)

If you have 5 minutes:

- [ ] `cat ~/Pictures/Chemigram/<image_id>/sessions/*.jsonl | jq -r 'select(.kind == "tool_call") | .tool' | uniq -c` — what tools did the agent reach for?
- [ ] `cat ~/Pictures/Chemigram/<image_id>/vocabulary_gaps.jsonl | jq` — what gaps did it log?

You don't have to do this every session. Once a week is plenty.

## Monthly — vocabulary authoring evening

The most important Phase 2 ritual. Without it, the gap log just grows.

### When to do it

- ~once a month, or whenever the gap log hits ~10 recurring gaps
- A single evening — 90 minutes, not a weekend project
- Keep it light; treat it as a craft exercise, not a chore

### Step by step

1. **Aggregate gaps across all images.**

   ```bash
   cat ~/Pictures/Chemigram/*/vocabulary_gaps.jsonl | jq
   ```

   Or, if you want to cluster by missing capability:

   ```bash
   cat ~/Pictures/Chemigram/*/vocabulary_gaps.jsonl | \
     jq -r '.missing_capability // "uncategorized"' | sort | uniq -c | sort -rn
   ```

   The recurring missing_capability values are your signal.

2. **Pick 3–5 gaps that recurred.** One-off gaps are noise; recurring ones are the vocabulary you actually need. If a gap shows up across multiple images and multiple sessions, it's real.

3. **Open darktable's GUI.** Load a representative photo for each gap. Build the move you wanted: tone curve, color calibration, parametric mask, whatever it takes. Adjust until the move feels right.

4. **Export as a `.dtstyle`.** In darktable: select the module(s) for this move only (per ADR-010, single-module is cleaner than multi-module), Styles → Create New Style. Export. The file is the captured move.

5. **Drop into your personal pack.** The pack lives at `~/.chemigram/vocabulary/personal/`:

   ```
   ~/.chemigram/vocabulary/personal/
     manifest.json
     layers/
       L3/
         tone/
           tone_lift_shadows_subject_subtle.dtstyle  ← your new entry
   ```

   Add a manifest entry following the format in `vocabulary/starter/manifest.json` (per `docs/adr/TA.md` `contracts/vocabulary-manifest`). Keep names following the `module_intention_context` convention (see `docs/concept/02-project-concept.md` § Vocabulary primitives).

6. **Validate.**

   ```bash
   ./scripts/verify-vocab.sh ~/.chemigram/vocabulary/personal
   # → verify-vocab: OK (N entries)
   ```

   Fix any reported errors before continuing.

7. **Run another session.** The agent now has those primitives. Notice if it reaches for them.

### What to author vs what to skip

| Author | Skip |
|-|-|
| Recurring gaps with a clear missing_capability | One-off gaps from a single weird photo |
| Moves that compose well with existing vocabulary | Multi-module "look" entries that bundle 6 things into one (compose them in the agent instead) |
| Moves with stable parameters across photos | Moves so photo-specific they'd never apply twice |
| Single-module entries when possible | Multi-module entries when single-module would do |
| Genre-specific moves (with the genre tag) | Generic "everything in 1" entries |

### Naming convention reminder

`module_intention_context` — three or two parts. Examples:

- `expo_+0.5` (action, quality)
- `wb_warming_pelagic` (module, intention, context)
- `colorcal_underwater_recover_blue` (module, intention, context)
- `tone_lifted_shadows_subject` (module, intention, target)

Avoid generic names (`look_warm`, `style_dramatic`) — they don't compose.

## Quarterly — taste file review

Sessions accumulate proposals; over time your taste files grow. Once a quarter, audit them.

### Why this matters

The agent will propose taste updates. You confirmed them in the moment. Three months in, are they still true? Has the agent talked you into a preference you don't actually believe? Are some lines redundant?

### Step by step

1. **Read your tastes:**

   ```bash
   cat ~/.chemigram/tastes/_default.md
   for f in ~/.chemigram/tastes/*.md; do echo "=== $f ==="; cat "$f"; done
   ```

2. **Read each line and ask:** Do I still believe this? Is it specific enough to be useful? Does it conflict with other lines?

3. **Edit directly.** You own these files; the propose-and-confirm protocol is for *agent-initiated* updates. Manual edits are always allowed. Add, remove, refine.

4. **Optionally: rename or split.** If `_default.md` got too generic, split out genre-specific files. If two genre files overlap heavily, merge them.

5. **Look at the conflicts.** When `read_context` reports `tastes.conflicts` (same line in two genre files), you can either resolve them by editing or accept that both apply situationally.

## Signals to watch for

Phase 2 may eventually surface needs that the architecture itself can't satisfy. When that happens, you transition to Phase 3, 4, or 5.

| If you keep reaching for... | Signal | Phase response |
|-|-|-|
| Specific masked moves like `expo_+0.5_subject_only`, `wb_warm_water_only` | Parametric masks in vocabulary needed | **Phase 3** — usually dissolves into Phase 2 (just author parametric-masked entries; see [Phase 3 preview](phase-3-preview.md)) |
| Subject-aware masks for things parametric masks can't isolate ("the manta", "the bird's eye") | Need pixel-precise AI masking | **Phase 4** — install `chemigram-masker-sam` (sibling project) |
| Continuous control on one specific module — `expo_+0.42` not `+0.3` or `+0.5` | Discrete vocabulary granularity insufficient | **Phase 5** — Path C hex encoders for that module |
| Cross-session reflection ("across the last 3 sessions you reached for X") | Not yet supported | Future tool work; log it as a TODO |
| Different agent persona for autonomous editing | Mode B | Phase 5+ scope (eval harness exists at design level) |

## Tracking your progress

A few quick metrics to keep in your head:

- **Personal vocabulary count.** `cat ~/.chemigram/vocabulary/personal/manifest.json | jq '.entries | length'` — markers: 30–60 after 3 months, 80–120 after 6 months, 150–200 after 12 months.
- **Average session turn count.** Open a few session transcripts (`cat ~/Pictures/Chemigram/*/sessions/*.jsonl | jq -r 'select(.kind == "tool_call")' | wc -l` divided by session count) — should trend downward as context accumulates.
- **Taste file lines.** `wc -l ~/.chemigram/tastes/*.md` — watch them grow. If they're not growing, you're not confirming proposals (or the agent isn't proposing — sign that something's stale).
- **Snapshot ratio per image.** A 10-snapshot image has been worked on; a 2-snapshot image is shallow. Aim for *some* depth.

## Common mistakes

- **Treating sessions as benchmark runs.** "Let me edit 5 photos to test if the agent works" — produces shallow gaps and shallow tastes. Edit photos you'd actually edit anyway.
- **Authoring 30 vocabulary entries in one weekend.** Pre-authoring guesses produces dead vocabulary. Wait for real evidence; let gaps recur.
- **Not reading session transcripts.** They're full of signal. A 2-minute scan once a week is enough.
- **Confirming every proposed taste update without thinking.** You inherit them forever. A bad line poisons all future sessions.
- **Editing taste files only via propose-and-confirm.** Direct edits are always allowed; sometimes you know what you want better than the agent.
- **Letting the gap log get stale.** Three months of unprocessed gaps means three months of Phase 2 stalled. The monthly authoring evening is the antidote.

## Resources

- [Getting started](getting-started.md) — install + first session
- [Phase 3 preview](phase-3-preview.md) — what to watch for as you do Phase 2
- `vocabulary/starter/README.md` — what ships, what's intentionally absent
- `docs/CONTRIBUTING.md` § Vocabulary contributions — full authoring procedure
