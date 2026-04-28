# Starter Vocabulary

A minimal, OSS, generic vocabulary intended to demonstrate Chemigram and bootstrap new users. Conservative by design — see `../README.md` for why.

**Status:** empty. Populated in Phase 1.

## Planned starter entries (~30 total in Phase 1)

- Exposure: `expo_+0.0`, `expo_+0.3`, `expo_+0.5`, `expo_+0.8`, `expo_-0.3`, `expo_-0.5`
- White balance: `wb_neutral`, `wb_warm_subtle`, `wb_cool_subtle`, `wb_underwater_warm`, `wb_underwater_neutral`
- Color calibration: `colorcal_neutral`, `colorcal_warm`, `colorcal_cool`
- Tone: `tone_lifted_shadows`, `tone_crushed_blacks`, `tone_lifted_highlights`, `tone_compressed_highlights`
- View transform: `filmic_neutral`, `sigmoid_neutral`
- Detail: `clarity_subtle`, `structure_subtle`, `denoise_auto`
- Local (Phase 1.5): `gradient_top_dampen_highlights`, `vignette_subtle`, `parametric_warm_only_highlights`

See `docs/concept/04-architecture.md` § 5 (layer model) and `docs/prd/PRD-004-local-adjustments.md` for the design rationale.

## File layout (when populated)

```
starter/
  manifest.json              # vocabulary metadata
  layers/
    L1/                      # technical correction templates
    L2/                      # look establishment templates
      neutralizing/
    L3/                      # taste / agent vocabulary
      exposure/
      wb/
      colorcal/
      tone/
      detail/
      local/
  profiles/                  # color science extensibility hook (empty)
```
