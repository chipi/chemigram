# ADR-053 — EXIF auto-binding by exact-match identity

> Status · Accepted
> Date · 2026-04-28
> TA anchor ·/components/exif-binding
> Related RFC · RFC-015 (closes here)
> Related ADR · ADR-007 (BYOA), ADR-013 (Python 3.11+), ADR-015 (three-layer model), ADR-016 (L1 empty by default)

## Context

RFC-015 framed L1 vocabulary auto-binding: when a photographer drops a raw into chemigram, which L1 entries apply based on camera/lens identity? Three options were considered — exact match, fuzzy normalization, focal-length-aware lookup. ADR-016 already said L1 is empty by default; the binding question is "given the photographer authors L1 entries, how does the engine pick which apply?"

Slice 1 Issue #5 implemented the simplest rule (exact match) and tested it against the Phase 0 Nikon D850 NEF plus a synthetic `exifread` surface.

## Decision

`chemigram.core.binding.bind_l1(exif, vocabulary) -> list[DtstyleEntry]` is a thin delegating wrapper around the vocabulary layer's lookup:

```python
return vocabulary.lookup_l1(exif.make, exif.model, exif.lens_model)
```

The match logic lives in :class:`VocabularyIndex.lookup_l1`. `bind_l1` is the typed boundary between `chemigram.core.exif` and the vocabulary system.

**Resolution rules:**

1. **Exact match** on the full tuple `(make, model, lens_model)`. Case-sensitive. No normalization. No whitespace tolerance beyond what `read_exif` strips on extraction (trailing whitespace + trailing NUL bytes from C-string EXIF encoding).
2. **No fuzzy matching.** `"Nikkor Z 24-70"` does not match `"NIKKOR Z 24-70mm f/2.8 S"`.
3. **No focal-length awareness.** A 24-70 zoom shooting at 24mm matches the same L1 entry as the same lens at 70mm. `focal_length_mm` is captured in `ExifData` for future use but does not participate in v1 binding.
4. **No-match returns `[]`** (empty list). Not an error. ADR-016 explicitly says L1 is empty by default; "no entries match" is the dominant case during Phase 1.

**EXIF extraction** (`chemigram.core.exif.read_exif`) uses `exifread` (pure-Python). Tags consumed: `Image Make`, `Image Model`, `EXIF LensModel` (with fallback to `MakerNote LensModel`), `EXIF FocalLength`. String fields are stripped of whitespace and trailing NUL bytes; missing string fields become `""` (not `None`); missing `focal_length_mm` becomes `None`. `FileNotFoundError` propagates; other failures wrap into `ExifReadError`.

## Rationale

- **Exact match is the predictable rule.** Photographers author L1 entries against their actual gear; fuzzy matching would silently introduce ambiguity into a curated, intentionally narrow space. The cost of "your entry didn't match because of a space" is once-per-author; the cost of fuzzy false-positives is forever.
- **Fuzzy matching is weak in practice.** EXIF strings are produced by camera firmware and stable across captures from the same body. Spelling variants come from manual editing, which is rare.
- **Focal-length awareness was rejected** because lens corrections in `.dtstyle` are typically full-zoom-range parametric profiles. A focal-length-keyed lookup would multiply the L1 entry count without architectural payoff.
- **`exifread` chosen** over `PyExifTool` (requires the `exiftool` binary as external dep), `Pillow.ExifTags` (weaker NEF coverage), and stdlib (no EXIF support). Pure Python, no native deps, fits BYOA + minimal-core.
- **`bind_l1` as a thin delegating wrapper** preserves the type-checked boundary while letting the vocabulary layer own the actual lookup. If the vocabulary index later gains case-insensitive aliases or normalization features, `bind_l1`'s contract stays the same.

## Alternatives considered

- **Fuzzy / normalized matching** (case-insensitive, whitespace-tolerant): rejected per the rationale above. Predictability beats convenience.
- **Focal-length-aware lookup**: rejected as overkill for v1; lens profiles are typically full-range.
- **Embedded XMP extraction from raw files**: deferred. Sidecar XMPs are sufficient for Slice 1; embedded XMP arrives if a real workflow demands it.
- **PyExifTool**: rejected because it requires the `exiftool` binary as an external dep — violates the "minimal core" stance.
- **Pillow.ExifTags**: rejected because NEF support is weaker than `exifread`.
- **Composite key including focal length range** (e.g., `(make, model, lens, "wide" | "tele")`): rejected — adds complexity for theoretical correctness; real-world lens profiles are typically zoom-range parametric.

## Consequences

Positive:
- Predictable binding behavior; no silent fuzzy fallbacks
- Empty L1 is the default and matches photographer expectation under ADR-016
- Pure-Python dependency tree; no native install steps for contributors
- `bind_l1` is pure (no I/O, no mutation); easy to test with a fake `VocabularyIndex`
- `focal_length_mm` is captured in `ExifData` so a future binding rule that uses it doesn't require re-parsing the raw

Negative:
- Photographer-authored L1 entries must use exact EXIF strings (e.g., `"NIKON CORPORATION"` not `"Nikon"`). Mitigation: `docs/CONTRIBUTING.md` (Slice 6 vocabulary contribution guidance) will call this out; an `exiftool` snippet in the docs lets contributors discover their gear's exact EXIF strings.
- Manual lenses (no `LensModel` in EXIF) bind against `(make, model, "")` — coarse but correct. Photographers who want a generic manual-lens default can author one `(make, model, "")` entry per body.

## Implementation notes

- `src/chemigram/core/exif.py` — `ExifData`, `ExifReadError`, `read_exif`
- `src/chemigram/core/binding.py` — `VocabularyIndex` Protocol, `bind_l1`
- Runtime dep: `exifread>=3.0` added to `pyproject.toml`
- Tests:
  - `tests/unit/core/test_exif.py` — 8 unit cases (dataclass shape, missing-lens fallback, whitespace/null stripping, MakerNote fallback, focal-length parse, invalid-file handling, file-not-found)
  - `tests/unit/core/test_binding.py` — 6 unit cases (exact match, no-match empty list, case-sensitivity, string passthrough, manual lens, Protocol structural typing)
  - `tests/integration/core/test_exif_integration.py` — 1 case reading the Phase 0 D850 NEF via `CHEMIGRAM_TEST_RAW`
- RFC-015 status moves to `Decided`; remains as historical record
- Future work: a richer L1 binding rule (genre-aware, focal-length-aware) lives behind a future RFC and amends this ADR's rule set
