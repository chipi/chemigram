# ADR-016 — L1 empty by default; opt-in per camera+lens

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer
> Related RFC · RFC-015 (EXIF auto-binding rules)

## Context

L1 (technical correction) covers lens correction, profiled denoise, hot pixel removal, and similar fixes that depend on camera + lens combination. A fisheye lens shouldn't be lens-corrected (the projection is the point). A clean low-ISO image doesn't need denoise. Defaulting L1 on for all images would over-process; defaulting it off for all images would force every photographer to opt in repeatedly.

## Decision

L1 is empty by default for any image. Photographers opt in via per-camera+lens bindings declared in `~/.chemigram/config.toml`:

```toml
[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Nikkor 24-70mm f/2.8E ED VR"
template = "lens_correct_full + denoise_auto"

[[layers.L1.bindings]]
camera = "NIKON D850"
lens = "AF-S Fisheye Nikkor 8-15mm f/3.5-4.5E ED"
template = "denoise_auto"   # NO lens correction — preserve fisheye projection
```

Auto-resolution by EXIF picks the right binding per image: exact match (camera + lens), then camera-only fallback, then nothing.

## Rationale

- **Safety.** A surprised photographer (e.g., fisheye over-corrected by default) is worse than a mildly inconvenienced one (had to add a binding once).
- **Per-camera+lens granularity.** Lens correction has to be lens-specific; embedding the granularity in the binding pattern matches the actual problem shape.
- **Templates.** The starter vocabulary provides a small set of templates (`lens_correct_full`, `lens_correct_distortion_only`, `denoise_auto`, `chromatic_aberration_only`); the photographer composes bindings from these.
- **One-time setup.** Once the photographer's gear list is bound in `config.toml`, they don't think about L1 again.

## Alternatives considered

- **Always-on L1 with per-image override:** rejected — produces surprising over-processing for edge cases (fisheye, low-ISO, intentional lens character).
- **Camera-only bindings (ignore lens):** rejected — loses the fisheye exception case and similar lens-specific decisions.
- **GUI-based binding management:** out of scope (Chemigram has no UI). TOML is hand-edited; this is acceptable for a per-photographer one-time setup.

## Consequences

Positive:
- No surprising default processing applied to images
- Per-lens granularity supports edge cases naturally
- Setup cost is one-time per camera+lens combination
- EXIF auto-resolution removes per-image decisions once bindings exist

Negative:
- Photographers without bindings get no L1 (they must notice this and configure)
- TOML editing is a setup friction (mitigated: small file, well-documented)

## Implementation notes

`src/chemigram_core/bind.py` implements EXIF reading and binding resolution. Resolution rules: exact (camera+lens) → camera-only → nothing. Resolution result is stored in the per-image `metadata.json` as `auto_binding.l1`. RFC-015 specifies the resolution algorithm in detail.
