# Real-raw fixtures for visual-proof rendering

Drop real photographic raws (or JPEG exports) here for use by
`scripts/generate-visual-proofs.py`. The script's synthetic
ColorChecker / grayscale targets work for primitive isolation, but a
handful of vocabulary entries (notably HSL via `colorequal`) need a
working color-management chain that the synthetic chart pipeline
doesn't provide. Those entries render against the real raws here.

## Convention

The script looks for files at well-known paths:

| Filename | Used by | Subject characteristics needed |
|---|---|---|
| `iguana_galapagos.jpg` | HSL entries (`hsl_hue` / `hsl_saturation` / `hsl_luminance`) | Identifiable per-color content (skin tones, sky, foliage); EXIF (camera, lens, ISO); reasonable size (~5-10 MB committed, larger OK if license-free) |

When a fixture file is missing, the script falls back to the
synthetic-chart placeholder (gallery shows the documented placeholder
row from v1.8.0).

## License notes

Each fixture should be either:
- **CC0 / public-domain test raw** from a free-test-raws collection (e.g.
  www.signatureedits.com/free-raw-photos/), OR
- **Photographer-owned** image the project has explicit license to redistribute.

Add a license comment in this README per fixture as they're added.

## Size

A Sony A1 raw is ~50-80 MB. For repo footprint sanity, prefer:
- A high-quality JPEG export (1200-2000 px on the long edge) for the
  visual-proof gallery use case, OR
- A downsized 16-bit TIFF if RAW-pipeline behaviour matters and the
  fixture is small (< 20 MB)

The visual-proof renders cap at 400x400 anyway; large fixtures are
overkill.
