# expressive-baseline

The comprehensive baseline vocabulary pack for expressive taste articulation.

35 entries covering the parameter dimensions identified in the taste-library research (Van Gogh, Rembrandt, Picasso, Adams, Capa, Leiter). Calibrated to darktable 5.4.1.

## Composition with `starter`

This pack is **opt-in** and complements the minimal `starter` pack rather than replacing it. Photographers typically load both:

```python
from chemigram.core.vocab import load_packs
vocab = load_packs(["starter", "expressive-baseline"])
```

The starter pack stays minimal (5 entries — exposure + WB only) as a teaching artifact. The expressive-baseline pack ships the comprehensive set needed for actual artist-profile work.

## Path A vs Path B entries

- **Path A** (16 entries) — modules already in the baseline XMP. No engine prerequisites.
  - `highlights`, `sigmoid`, `channelmixerrgb`, `temperature`, `exposure`
- **Path B** (19 entries) — modules NOT in the baseline; require the synthesizer's Path B (new-instance addition) plus an `iop_order` value populated by `scripts/probe-iop-order.py` per ADR-063.
  - `colorbalancergb`, `localcontrast`, `grain`, `vignette`

Each Path B entry carries `iop_order`, `iop_order_source`, and `iop_order_darktable_version` in the manifest. If darktable bumps a module's modversion or pipeline order, RFC-007's drift detection flags the entry for re-validation.

## Provenance

All entries authored against darktable 5.4.1 by the project maintainers per the discipline in `docs/CONTRIBUTING.md` § Vocabulary contributions. Entries derived from external research projects (e.g., taste-library POC) are credited in their manifest entry's `source` field.

## Adding to this pack

See `docs/CONTRIBUTING.md` § Vocabulary authoring for the procedure. Path B entries additionally require the probe-iop-order workflow (per ADR-064).
