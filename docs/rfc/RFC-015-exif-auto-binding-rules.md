# RFC-015 — EXIF auto-binding rules

> Status · Draft v0.1
> TA anchor ·/components/synthesizer ·/components/mcp-server
> Related · ADR-016
> Closes into · ADR (pending) — locks the resolution algorithm
> Why this is an RFC · ADR-016 commits to L1 empty by default with per-camera+lens bindings. The auto-resolution algorithm — given an image's EXIF, find the right binding template — has multiple plausible shapes. Edge cases (unknown lens, EXIF mangled, multiple matching bindings) need explicit handling. The resolution rules also affect L2 binding (chosen baseline), which has different inputs (camera, lighting context, photographer preference).

## The question

When a raw is ingested:
- Read its EXIF.
- Look up applicable L1 and L2 bindings from `config.toml`.
- Decide which template to apply.

Several questions:
- What's the resolution priority order? (exact match → camera-only fallback → ...)
- What about EXIF entries with weird formatting (lens names with extra metadata, brand+model variations)?
- L2 binding has more axes than L1 — how to resolve?
- What happens when no binding matches — silent skip or warning?

## Use cases

- Nikon D850 + Nikkor 24-70mm lens → exact match → apply `lens_correct_full + denoise_auto`.
- Nikon D850 + a lens not in bindings → camera-only fallback → apply `denoise_auto` (skip lens correction).
- Sony A1 + lens with weird EXIF spelling → name normalization → match.
- Nikon D850 + Fisheye → exact match → apply `denoise_auto` only (NO lens correction).
- Nikon D850 + lens not in bindings AND no camera-only fallback → no L1 applied; warning.

## Goals

- Predictable, predictable resolution
- Tolerant of EXIF formatting variations
- Edge cases (no binding, partial match) handled clearly
- Same machinery handles L1 and L2 (with their respective config sections)

## Constraints

- TA/components/synthesizer — bindings produce templates that the synthesizer composes
- ADR-016 — L1 default is empty; bindings opt-in
- `config.toml` is the source of truth for bindings

## Proposed approach

**Resolution algorithm (for L1; L2 follows the same shape with different config keys):**

```python
def resolve_l1_binding(exif: ExifSummary, config: Config) -> Binding | None:
    bindings = config.layers.L1.bindings  # list, in declaration order

    camera = normalize_camera_name(exif.camera_model)
    lens = normalize_lens_name(exif.lens_model) if exif.lens_model else None

    # Pass 1: exact match (camera + lens)
    if lens:
        for b in bindings:
            if normalize_camera_name(b.camera) == camera \
               and normalize_lens_name(b.lens or "") == lens:
                return b

    # Pass 2: camera-only match (binding has no lens declared)
    for b in bindings:
        if normalize_camera_name(b.camera) == camera and b.lens is None:
            return b

    # No match
    return None


def normalize_camera_name(name: str) -> str:
    """Strip whitespace, lowercase, strip 'NIKON ' / 'CAMERA' prefixes."""
    return name.strip().lower()


def normalize_lens_name(name: str) -> str:
    """Aggressive normalization: lowercase, strip whitespace,
    strip vendor prefixes (Nikkor/Sigma/Tamron),
    strip metadata in parens."""
    n = name.strip().lower()
    n = re.sub(r'^(nikkor|sigma|tamron|sony|fujifilm|canon)\s+', '', n)
    n = re.sub(r'\s*\([^)]*\)', '', n)
    return n.strip()
```

**`Binding` shape:**

```python
@dataclass
class Binding:
    camera: str
    lens: str | None    # None = camera-only fallback
    template: str       # space-separated vocabulary entry names: "lens_correct_full + denoise_auto"
```

**Edge case handling:**

- **No EXIF lens info.** Pass 1 is skipped; only Pass 2 runs. If camera-only binding exists, applied. Otherwise no L1.
- **Mangled EXIF.** Normalization is aggressive; usually catches typos and variant spellings. If still no match, fall through to "no L1."
- **Multiple matching bindings (Pass 1 or Pass 2).** First match in declaration order wins. Photographers control order in `config.toml`.
- **Binding template references unknown vocabulary.** Loud error at config load time, not at image-ingest time. Fail fast.

**L2 resolution:**

L2 has more axes than L1 — camera + lighting context + photographer preference. The resolution rules are similar but the binding shape includes additional fields:

```python
@dataclass
class L2Binding:
    camera: str
    lighting_context: Literal["topside", "underwater", "mixed", "any"]   # contextual
    template: str
```

Photographer's L2 binding declarations might look like:

```toml
[[layers.L2.bindings]]
camera = "NIKON D850"
lighting_context = "underwater"
template = "underwater_pelagic_blue"

[[layers.L2.bindings]]
camera = "NIKON D850"
lighting_context = "any"
template = "topside_neutral"
```

Resolution: camera + lighting_context (lighting_context can be inferred from depth EXIF tags if present, otherwise the photographer specifies at ingest time or it defaults to `topside`).

## Alternatives considered

- **Skip normalization (require exact EXIF match):** rejected — too brittle. EXIF formatting varies across cameras, manufacturers, even firmware versions.
- **Pattern-match bindings (regex/glob):** rejected — overkill; explicit declarations are simpler and more reviewable.
- **Bind by camera + sensor (instead of lens):** rejected — lens-specific behavior (fisheye exception) requires lens granularity.
- **Auto-detect lighting context from image (e.g., underwater detection by color cast):** considered. Defer to a future enhancement; v1 uses explicit declaration.
- **Multiple-template binding (e.g., one camera→lens→multi-template):** considered. Composition is already in the template syntax (`lens_correct_full + denoise_auto`); separate field would be redundant.

## Trade-offs

- Aggressive normalization can produce false positives (matching the wrong lens). Mitigated: photographers see binding resolution in the per-image metadata; can adjust if wrong.
- Order-dependence in `config.toml` means contributors must understand declaration order. Mitigated: documented in CONTRIBUTING.md / setup docs.
- L2's lighting context is photographer-supplied (or inferred); can be wrong. Mitigated: explicit declaration at ingest time is the canonical input.

## Open questions

- **Lens detection on Sony A1 (electronic mount).** Sony stores lens info differently than Nikon. Engine must handle both vendor variations. Test with real raws.
- **Depth-based underwater detection.** EXIF has GPS depth in some cases; could auto-classify. Defer.
- **Per-image override.** Even if EXIF-resolution finds a binding, the photographer might want to override for a specific image. Proposed: `bind_layers(image_id, l1_template?, l2_template?)` already supports this — explicit override.
- **Visualizing binding resolution.** Should `ingest()` return a "what binding was applied?" summary so the photographer can sanity-check? Proposed: yes. Already in ADR-033's `ingest` return shape: `suggested_bindings` field.

## How this closes

This RFC closes into:
- **An ADR locking the resolution algorithm** for L1 and L2 (same shape, different config sections).
- **An ADR for normalization rules** (which prefixes to strip, etc.).

## Links

- TA/components/synthesizer
- ADR-016 (L1 empty by default; opt-in)
- ADR-033 (`ingest`, `bind_layers` tools)
- 04/5 (layer model)
