# Starter Vocabulary

The vocabulary pack that ships with `pip install chemigram`. **Deliberately small** — five entries, generic by design — so the agent loop works out of the box. Phase 2 grows the vocabulary from real session evidence, not from imagined upfront completeness; the gaps surfaced via `log_vocabulary_gap` are the seed for new entries.

See `docs/concept/04-architecture.md` § 5 (layer model) for the L1/L2/L3 architecture, and `docs/prd/PRD-003-vocabulary-as-voice.md` for the design rationale.

## Currently shipped

| Name | Layer | Touches | Mask | Description |
|-|-|-|-|-|
| `expo_+0.5` | L3 | exposure | — | Lift exposure +0.5 EV (global) |
| `expo_-0.5` | L3 | exposure | — | Lower exposure -0.5 EV (global) |
| `wb_warm_subtle` | L3 | temperature | — | Subtle warm white balance shift |
| `look_neutral` | L2 | exposure + temperature | — | Neutral L2 baseline (exposure + warm-subtle WB) |
| `tone_lifted_shadows_subject` | L3 | exposure | raster (subject) | Shadow lift restricted to the subject mask |

The mask-bound entry references `current_subject_mask` — the agent generates this via `generate_mask(image_id, target="subject")` before applying.

## What's not shipped

- **L1 entries (camera+lens templates)** — empty by default per ADR-016. Photographers add entries keyed to their actual gear; fuzzy matching would silently introduce ambiguity.
- **Color calibration**, **view transform**, **detail**, **local-other-than-subject** entries — Phase 2 evidence-driven.
- **Genre-specific packs** (underwater, wildlife, portrait, etc.) — these belong in `vocabulary/packs/` (community packs) once those exist.

## Adding to the starter pack

See `docs/CONTRIBUTING.md` § Vocabulary contributions for the authoring procedure (export styles from darktable, add manifest entries, validate via `scripts/verify-vocab.sh`).

## Adding personal vocabulary (Phase 2 pattern)

The starter pack is upstream-shipped and small. Your *personal* vocabulary lives at `~/.chemigram/vocabulary/personal/` (per ADR-049) and grows organically:

1. Run real Mode A sessions; the agent calls `log_vocabulary_gap` when it reaches for primitives that don't exist
2. Periodically (a vocabulary-authoring evening per month, roughly): open darktable, capture missing primitives as `.dtstyle` files, drop them into your personal pack
3. Watch which primitives get used heavily, which never get used; refine over time
4. When a personal entry is generic enough to be useful to others, contribute it upstream via the CONTRIBUTING.md flow

Markers of maturation: ~30–60 personal entries after 3 months; ~80–120 after 6 months. The vocabulary becomes an articulation of your craft.
