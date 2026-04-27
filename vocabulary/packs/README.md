# Vocabulary Packs

Borrowed and community-contributed vocabulary packs. Each pack is a self-contained subdirectory with its own manifest, `.dtstyle` files, and `ATTRIBUTION.md`.

**Status:** empty. Populated as packs are vetted and integrated.

## Planned early packs

- **`fuji-sims/`** — Fuji film simulations (Provia, Velvia, Astia, Classic Chrome, Acros, Classic Neg, etc.) borrowed from existing community work (likely `bastibe/Darktable-Film-Simulation-Panel` and/or `t3mujinpack`). Calibrated to Fuji X-Trans color science; usable on other sensors with the spirit-not-pixel-identical caveat.

## Pack structure

```
packs/
  <pack-name>/
    manifest.json           # pack metadata, entries list
    ATTRIBUTION.md          # credits and upstream license
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
