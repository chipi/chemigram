# Vocabulary Packs

Comprehensive and community-contributed vocabulary packs. Each pack is a self-contained subdirectory with its own manifest, `.dtstyle` files, and (for borrowed packs) `ATTRIBUTION.md`.

## Currently shipped

- **[`expressive-baseline/`](expressive-baseline/README.md)** — 35-entry comprehensive baseline calibrated to artist profiles (Van Gogh, Rembrandt, Picasso, Adams, Capa, Leiter). Authored programmatically via Path C reverse-engineering (ADR-073) plus 4 drawn-mask-bound entries via path 4a (ADR-076). Loads with `load_packs(["starter", "expressive-baseline"])`. Calibrated to darktable 5.4.1.

## Planned packs

- **`fuji-sims/`** — Fuji film simulations (Provia, Velvia, Astia, Classic Chrome, Acros, Classic Neg, etc.) borrowed from existing community work (likely `bastibe/Darktable-Film-Simulation-Panel` and/or `t3mujinpack`). Calibrated to Fuji X-Trans color science; usable on other sensors with the spirit-not-pixel-identical caveat.

## Pack structure

```
packs/
  <pack-name>/
    manifest.json           # pack metadata, entries list
    ATTRIBUTION.md          # credits and upstream license (borrowed packs)
    layers/                 # entries organized by L1/L2/L3
    profiles/               # optional ICC / LUT assets
    README.md               # pack-specific documentation
```

## Contributing a pack

See `docs/CONTRIBUTING.md` § "Vocabulary contributions". For borrowed packs:

1. Verify upstream license is compatible (typically MIT or CC variants).
2. Vendor the content under `packs/<pack-name>/` with version pin to upstream commit.
3. Write `ATTRIBUTION.md` with full credits.
4. Open a PR following the vocabulary contribution flow (before/after renders required).

For programmatic authoring (the path used for `expressive-baseline`), see [`docs/guides/expressive-baseline-authoring.md`](../../docs/guides/expressive-baseline-authoring.md). For the daily-use authoring flow (open darktable, capture move, drop into personal pack), see [`docs/guides/authoring-vocabulary-entries.md`](../../docs/guides/authoring-vocabulary-entries.md).
