# Reference targets

Synthetic reference images and ground-truth values for color-accuracy
and tonal-response assertions. Per RFC-019 v0.2.

## Files

- `colorchecker24_lab_d50.json` — 24-patch L\*a\*b\* D50 ground truth
  (post-Nov 2014 X-Rite formulation). Hand-curated from
  `docs/guides/standardized-testing.md`. Tiny (<3 KB).
- `colorchecker_synthetic_srgb.png` — 600x400 synthetic CC24 generated
  from the JSON's L\*a\*b\* values via `chemigram.core.assertions.lab_to_srgb`.
  Each patch is 100x100 px; patches are in row-major order matching
  ``patches[*].index``. PNG (~1.5 KB; solid-color regions compress
  efficiently — well under the 500 KB pre-commit large-file limit).
- `grayscale_synthetic_linear.png` — synthetic 24-step linear grayscale
  ramp (sRGB 0..255 in equal increments). Used for tonal-response checks.
- `generate_synthetic.py` — re-generation script. Run from repo root:
  ``uv run python tests/fixtures/reference-targets/generate_synthetic.py``.

## Why synthetic

Per RFC-019 v0.2: the project doesn't ship physical chart shoots, and CI
must run end-to-end without one. Synthetic fixtures derived from
published colorimetric references are sufficient to validate the
*software pipeline* (sRGB ↔ L\*a\*b\* math, the synthesizer, the
assertion library) without depending on a Nikon and a sunny afternoon.

The trade-off: this does NOT validate darktable's RAW path against
reference-target ground truth. The existing direction-of-change e2e
suite (`tests/e2e/`) covers darktable-RAW for direction-of-change.
If full-pipeline reference-target validation becomes important, a
follow-on RFC reopens the discussion (likely once a community-
contributed downloadable RAW pack appears).

## Out-of-gamut patches

Patch #18 ("Cyan") sits outside the sRGB gamut. The synthetic CC24
clips it to the nearest in-gamut sRGB; assertions exclude it from the
strict mean/max Delta E thresholds via the ``out_of_gamut_indices``
field in the reference JSON.

## Versioning

The reference set is **immutable** within a version. The current version
is ``reference_v1``. When future work needs a different formulation
(e.g., pre-Nov 2014 chart, or a different illuminant), it ships as
``reference_v2`` — the v1 files stay untouched for reproducibility.
