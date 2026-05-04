# Tastes quickstart

> Your first taste file in 5 minutes.
>
> The taste system is what makes Chemigram *yours* over time. The agent reads your tastes at every session start and lets them shape every move it suggests. Without a taste file, the agent has no opinion to defer to — it picks generic, safe moves. Even an imperfect first-draft taste file is dramatically more useful than none.

This guide gets you from zero to a working `_default.md` that the agent will actually use. Everything else (genre-specific files, propose-and-confirm cycles for additions, taste growth over months) builds from here.

---

## What is a taste file?

A markdown document at `~/.chemigram/tastes/_default.md` that captures your photographic preferences in prose. Specific, opinionated, undated-but-could-be-dated entries. Read by the agent at session start via `read_context`. Written by you, refined by you (the agent proposes additions; you confirm or decline).

Three rules:

1. **Specific, not generic.** "Crush deep shadows to true black" beats "I like contrast."
2. **Opinionated, not balanced.** "Never `structure_strong` — it reads aggressive" is more useful than "use sharpening judgment."
3. **Yours, not borrowed.** Don't copy a stock taste file as if it described you. The point is articulating what *you* actually prefer.

---

## Step 1 — Make the directory

```bash
mkdir -p ~/.chemigram/tastes
```

That's it for setup. No other files are required.

---

## Step 2 — Copy a starting template

The repo ships a real-feeling sample at [`examples/templates/tastes/_default.md`](../../examples/templates/tastes/_default.md). Open it and read it through to see the shape of a working taste file. Don't copy it verbatim — it's not yours. But the structure (sections by concern, dated entries, specific opinions) is the right shape to imitate.

Then create your own:

```bash
$EDITOR ~/.chemigram/tastes/_default.md
```

Fill in five to ten entries you can actually defend. **Imperfect is fine.** The agent will read whatever you write; you'll refine it over months.

---

## Step 3 — A starter scaffold

If staring at a blank file is paralyzing, here's a minimal scaffold to fill in. Think of these as prompts, not prescriptions — leave out sections that don't fit your work.

```markdown
# _default.md — universal preferences

*Curated over time. Last revised: <today's date>.*

This file always loads at session start. For genre-specific preferences,
add sibling files (e.g. underwater.md, wildlife.md, portrait.md) and
declare them in each image's brief.md.

## Color

- <a thing you do reach for, with a reason or context>
- <a thing you don't reach for, with a reason>

## Tone

- <where you stand on shadows: lift / crush / preserve>
- <where you stand on highlights: protect / open / let-clip>

## Sharpening / structure

- <how aggressive you let local contrast / clarity get>
- <when you'd reach for a softer painterly look vs sharp>

## Aesthetic / mood

- <one or two sentences on the overall feel you reach for>

## What I avoid

- <styles you don't want the agent suggesting>
- <moves that consistently feel wrong to you>

## Workflow notes

- <how you like the agent to behave: branch often? few suggestions? quiet?>
- <known biases: "the agent tends to estimate cool, bias warmer">
```

Five to ten lines under these headings is plenty for v0.1.

---

## Step 4 — Verify the agent reads it

In your next Mode A session, the agent's first move is `read_context`. The response should mention "tastes loaded" with a count or summary. If the agent says tastes are empty after you've created the file, check:

- File path: `~/.chemigram/tastes/_default.md` (lowercase, with the leading underscore)
- Or set `CHEMIGRAM_TASTES_DIR` to a non-standard location (see [`cli-env-vars.md`](cli-env-vars.md))

You can also verify from the CLI:

```bash
chemigram --json read-context <some-image-id> | jq '.tastes.default'
```

This prints the parsed `_default.md` content.

---

## Step 5 — Let it grow

Don't try to write a complete taste file in one sitting. The system grows over weeks and months, not minutes:

1. **In sessions:** the agent proposes additions (`propose_taste_update`) when it notices a recurring pattern. You confirm the good ones, decline the rest.
2. **Outside sessions:** add entries directly when something occurs to you. Don't wait for the agent.
3. **Genre files:** when you notice a preference applies only to *some* work — underwater shots specifically, say — move it to a sibling file (`underwater.md`, `wildlife.md`) and declare it in the image's brief.

After 3–6 months of regular use, a taste file becomes recognizably *yours* — someone reading it could anticipate moves you'd reach for on an unfamiliar image. That's the artifact this system is trying to produce.

---

## Genre-specific files

Sibling templates ship at [`examples/templates/tastes/underwater.md`](../../examples/templates/tastes/underwater.md) and [`examples/templates/tastes/wildlife.md`](../../examples/templates/tastes/wildlife.md). The shape:

```markdown
# underwater.md — underwater-specific preferences

*Loads when an image's brief.md declares `Tastes: underwater`.*

## <section>

- <preference specific to underwater work>
```

Genre files compose with `_default.md`: both load when the brief calls for the genre, and the agent honors both. When `_default.md` and a genre file disagree on a specific point, the genre file wins (most-specific rule). When two genre files disagree with each other, `read_context` surfaces the conflict and the agent asks you to mediate.

---

## What goes in a taste file (and what doesn't)

**Goes in:**

- Cross-image preferences ("I always crush deep shadows")
- Aversions ("Heavy clarity reads aggressive to me")
- Workflow preferences ("Show 2–3 candidates before committing")
- Color biases ("You tend to estimate cool — bias warmer")

**Doesn't go in:**

- Per-image notes (those go in that image's `brief.md` and `notes.md`)
- Hard rules the agent should never violate (those would be `principles` in PA, not taste — though if you really need this, a phrasing like "never X — last 3 times you tried I rejected" works)
- Commentary on the project itself (irrelevant to editing decisions)

---

## See also

- [`examples/templates/tastes/_default.md`](../../examples/templates/tastes/_default.md) — full sample showing the shape of a real taste file (~25 entries)
- [`examples/templates/brief.md`](../../examples/templates/brief.md) — per-image brief format (where you declare which tastes apply)
- [`docs/getting-started.md#your-first-session`](../getting-started.md#your-first-session) — full onboarding walkthrough
- [`docs/concept/03-data-catalog.md`](../concept/03-data-catalog.md) — the broader context system (tastes / briefs / notes / sessions / gaps)
- [`docs/adr/ADR-048-multi-scope-tastes.md`](../adr/ADR-048-multi-scope-tastes.md) — multi-scope taste resolution semantics
