# 05 — Design System

*The visual and behavioral language of the project. Intentionally minimal for v1.*

A traditional Design System document covers visual tokens, typography, color systems, and per-surface visual contracts. Chemigram has none of these in v1 — **it is an MCP server, not a UI app**. There are no surfaces to design; the photographer interacts with Chemigram through an MCP-capable agent (Claude, GPT, etc.) running in the photographer's chosen interface, and through file-system artifacts (taste.md, brief.md, notes.md, vocabulary entries).

This document is therefore deliberately thin. It covers the two areas where Chemigram does establish design conventions:

1. **The agent's prompt template** — the design system for how the agent *behaves*
2. **Vocabulary naming conventions** — the design system for the agent's *action space*

Both shape the experience even without a visual UI.

---

## 1. Why this is intentionally minimal

The Phase 1 process guide names this slot — the design system doc — as the document where visual language, typography, and per-surface screenshots live. For projects with a user-facing UI, this is irreducible — surfaces need visual contracts, and the package can't be complete without them.

Chemigram has no such surfaces. The photographer's interface is whichever agent they choose to drive the MCP server. Claude.ai, Claude Code, a desktop chat client, a terminal-based MCP client — all are valid. Designing visual language for a GUI Chemigram doesn't have would be premature work that would constrain future product decisions if Chemigram ever sprouts a GUI.

**The honest answer: Chemigram v1 is plumbing under whichever agent the photographer wants to use. It has no surfaces, no chrome, no visual identity to maintain.**

This is a deliberate scope choice, not a gap. See `04`/1.3 (BYOA) for the principle this reflects: Chemigram orchestrates AI capabilities chosen by the photographer rather than shipping its own.

If a future Chemigram phase introduces a dedicated UI (a desktop tool, a web client, a custom session viewer), this document would expand substantially. Until then, the design surface is two things: how the agent talks, and how vocabulary is named.

---

## 2. The agent's prompt template

The agent's system prompt is the closest Chemigram has to a "voice" — the persona, behavioral patterns, and conversational style the photographer experiences.

`02`/9 sketches the prompt structure. This section names the conventions that prompt should follow.

### 2.1 Voice principles

The agent's voice should be:

- **Apprentice, not assistant.** Engaged, curious, opinionated when warranted. Not subservient. Not constantly asking permission for trivial things.
- **Specific, not generic.** "Marine iguanas are typically dark gray to black" not "iguanas have various colorations."
- **Honest about uncertainty.** "The eye mask caught one eye well but the other is partially obscured" not "Done." (See `02`/6.2.)
- **Concise in routine, expansive when reasoning matters.** A simple apply doesn't need narration. A composition tension surfaced before applying needs a couple of sentences.
- **Present-tense, declarative.** "I'm generating the subject mask now" not "I will now proceed to generate the subject mask."

### 2.2 Standard response shapes

Recurring conversational shapes the agent should produce:

**Session-start orientation** (`02`/5.1):

> "I've read your context. This is [image description], shot on [camera], [purpose from brief]. From your taste notes, [relevant patterns]. Last session [recent state]. Want to [option A] or [option B]?"

**Pre-action surfacing**:

> "I'm going to [action]. Quality may vary because [reason]. Here's what I tried — does this match your intent?"

**Vocabulary gap acknowledgment**:

> "I don't have a single entry for [need]. I'm composing it from [entry A] + [entry B]. Result should be similar; logging this as a gap for future authoring."

**Composition tension catch**:

> "Quick note: [observation about how moves interact]. We can [mitigation], but this is a tradeoff. Worth flagging before I proceed."

**End-of-session synthesis**:

> "Proposed addition to your taste.md: '[note]'. Accept (Y/N)?"

These shapes aren't templates to be filled in mechanically — they're patterns that emerge from the disciplines in `02`/6. Documented here so prompt engineering iterations can converge on consistent voice.

### 2.3 What the agent doesn't do

To preserve the apprentice persona:

- **No SaaS-speak filler.** Skip "It is worth noting that," "In order to," "At this point in time."
- **No hedging by default.** "I think this looks better" not "It seems like this might possibly be better."
- **No empty validation.** "Great choice!" after every photographer decision is annoying. Reserve enthusiasm for genuinely surprising or interesting moves.
- **No emoji** (unless the photographer's previous message has them).
- **No apologetic preamble.** "Sorry, before I do that, I should mention..." → just say what you need to say.

These are voice rules, not behavioral rules. They affect how things are said, not what gets said.

---

## 3. Vocabulary naming conventions

The vocabulary is the agent's action space. Naming conventions matter because the agent reasons over names — when scanning vocabulary, predicting which entry fits an intent, recognizing patterns.

### 3.1 The naming pattern

```
<category>_<modifier>[_<scope>][_<intensity>]
```

Examples broken down:

| Entry | Category | Modifier | Scope | Intensity |
|-|-|-|-|-|
| `expo_+0.5` | exposure | +0.5 | (global) | (none) |
| `colorcal_underwater_recover_blue` | colorcal | underwater_recover_blue | (global) | (none) |
| `tone_lifted_shadows_subject` | tone | lifted_shadows | subject | (none) |
| `tone_lifted_shadows_subject_strong` | tone | lifted_shadows | subject | strong |
| `gradient_top_dampen_highlights` | gradient | top_dampen_highlights | (drawn-mask) | (none) |
| `structure_subject_subtle` | structure | (none) | subject | subtle |

Underscores between segments. Lowercase. No spaces, no special characters except `+` and `-` for signed values.

### 3.2 Category prefixes

Common category prefixes establish the vocabulary's spine:

| Prefix | What it touches |
|-|-|
| `expo_` | exposure module |
| `wb_` | white balance (legacy) or color calibration in WB mode |
| `colorcal_` | color calibration (channel mixer + WB combined) |
| `tone_` | tone equalizer or tone curve |
| `filmic_` | filmic view transform |
| `sigmoid_` | sigmoid view transform |
| `colorbalance_` | color balance rgb (grading) |
| `clarity_` | diffuse-or-sharpen in clarity mode |
| `structure_` | diffuse-or-sharpen in structure mode |
| `denoise_` | profiled denoise |
| `dehaze_` | haze removal |
| `gradient_` | drawn-mask gradient with effect |
| `vignette_` | drawn-mask vignette with effect |
| `parametric_` | parametric-mask entry where the parametric scope is integral to the move |
| `lens_correct_` | lens correction (L1) |

Categories follow modules, not effects. A "lift the shadows" move could be `tone_lifted_shadows` (tone equalizer) or `colorbalance_lifted_shadows` (color balance rgb). The category name disambiguates which module's parameters are doing the work.

### 3.3 Scope suffixes

Scope suffixes indicate spatial restriction:

| Suffix | Meaning |
|-|-|
| (no suffix) | Global — applies to whole frame |
| `_subject` | Restricted to current subject mask (raster, AI-generated) |
| `_sky` | Restricted to current sky mask |
| `_background` | Restricted to inverse subject |
| `_only` | Parametric restriction integral to the move (e.g. `warm_highlights_only` = warm restricted to luminance highlights via parametric mask) |

When a vocabulary entry exists in both global and subject-masked variants, the suffix tells the agent which is which. Pattern recognition is reliable enough that the agent can navigate by name alone.

### 3.4 Intensity suffixes

Where intensity matters and isn't captured in the modifier itself:

| Suffix | Meaning |
|-|-|
| (no suffix) | Default intensity |
| `_subtle` | Reduced intensity |
| `_strong` | Increased intensity |
| `_steep` | (For gradient-mask entries) steeper falloff |
| `_extra` | Composes with the default-intensity entry (different `multi_priority`) |

Three rungs (subtle / default / strong) is usually enough. Five rungs is overkill — the photographer can always express "halfway between subtle and default" verbally and the agent can reason about it.

### 3.5 Layer prefixes (optional, when ambiguous)

L1 entries are sometimes prefixed `lens_correct_` or `denoise_` which are unambiguously L1. No explicit prefix needed.

L2 entries that are looks (Fuji sims, etc.) follow their own naming (`fuji_acros`, `fuji_classic_chrome`). L2 entries that are neutralizing scenes (`underwater_pelagic_blue`, `topside_neutral`) are also unprefixed.

L3 entries are everything else — the bulk of vocabulary. No L3 prefix is used; L3 is the default.

If a layer is ambiguous from the name alone, manifest metadata resolves it (`layer: "L3"` field). The naming conventions are for agent recognition; the manifest is for engine correctness.

### 3.6 Reserved patterns

Some name patterns are reserved for the engine:

| Pattern | Reserved for |
|-|-|
| `current_*_mask` | Mask registry symbolic names (e.g. `current_subject_mask`) |
| `*_test_*` | Test fixtures only — not for production vocabulary |
| `_internal_*` | Engine-internal entries that the agent shouldn't surface |

---

## 4. The session transcript format

Sessions are captured as JSONL — one entry per turn — in `<image_id>/sessions/<date>-<purpose>.jsonl`. While not visual, the transcript format is a kind of design choice — it determines what's recoverable later.

### 4.1 Per-turn entry shape

```json
{
  "turn": 7,
  "timestamp": "2026-04-27T15:23:11Z",
  "role": "agent" | "photographer" | "system",
  "type": "message" | "tool_call" | "tool_result" | "snapshot" | "context_update",
  "content": "...",
  "metadata": {
    "snapshot_hash": "a3f291...",
    "tool_name": "apply_primitive",
    "tool_input": {...},
    "tool_output": {...}
  }
}
```

### 4.2 Session header (first entry of file)

```json
{
  "session_id": "2026-04-27-iguana-correction",
  "image_id": "iguana_galapagos_DSC4321",
  "started_at": "2026-04-27T14:45:00Z",
  "ended_at": "2026-04-27T15:35:22Z",
  "mode": "A",
  "brief_snapshot": "...full brief.md content at session start...",
  "taste_snapshot_ref": "sha256-of-taste.md-at-session-start",
  "outcome": "tagged_export" | "abandoned" | "branched_for_later",
  "tags_created": ["iguana_galapagos_v1"],
  "snapshots_produced": ["a3f291...", "b71204...", ...],
  "vocabulary_gaps_logged": 1,
  "context_proposals_accepted": 2,
  "context_proposals_rejected": 0
}
```

The header is the searchable, summary-level entry. The body is the full transcript.

### 4.3 Why this format matters

A session is a research artifact. The format determines what future-photographer (or research analysis) can reconstruct from it. The shape above supports:

- **Replay** — given the snapshots produced, the photographer can revisit any state
- **Review** — the message stream can be re-read end-to-end
- **Aggregation** — sessions can be analyzed across many images for patterns
- **Reference** — `taste.md` additions reference session IDs, so the provenance of any taste note is traceable

This is the JSONL equivalent of a well-formatted git commit history: not glamorous, but irreplaceable when you want to understand later why something is the way it is.

---

## 5. What's not here (and what would be if Chemigram had a GUI)

For completeness, the design-system content this document would contain if Chemigram had user-facing surfaces:

- Visual tokens — colors, typography scales, spacing, radii
- Component states — default, hover, active, focus, disabled, loading, empty, error
- Per-surface visual contracts — dashboard, image viewer, session browser, vocabulary inspector
- Navigation patterns — how surfaces connect
- Accessibility targets — contrast ratios, keyboard navigation, screen reader behavior
- Animation and motion language

None of this exists in v1 because none of these surfaces exist. If Chemigram ever gains a dedicated UI, this document expands at that time.

---

*05 · Design System · v1.0 · Intentionally minimal — Chemigram v1 is an MCP server with no UI surfaces*
