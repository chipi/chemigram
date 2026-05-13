# Mask architecture trilogy

> Source: `docs/diagrams/mask-trilogy.md`. The mask system after v1.9.0 +
> v1.10.0. Four input sources flow into one wire (`mask_spec`) that
> serializes to darktable's XMP `masks_history` block.

v1.9.0 closed the mask + retouch architecture trilogy (RFC-024 + RFC-025
+ RFC-026 + RFC-029 → ADR-084..087); v1.10.0 added named-mask
references (RFC-032) on top. Before this trilogy chemigram had a
PNG-mask path that turned out to be a silent no-op (ADR-076 retired
it). The current architecture: every mask, regardless of source, ends
up as `masks_history` XML inside the XMP.

```mermaid
flowchart TB
    subgraph SOURCES["Four mask sources (the trilogy + named refs)"]
        direction LR
        DRAWN["**Drawn geometry**<br/>RFC-029 / ADR-084<br/>gradient / ellipse / rectangle / path<br/>4-N vertex closed polygons"]
        PARAMETRIC["**Parametric range filter**<br/>RFC-024 / ADR-085<br/>luminance / color_h / color_s / color_l<br/>blendif bytes"]
        VISION["**LLM-vision derived**<br/>RFC-026 / ADR-086<br/>chat client sees render_preview<br/>constructs mask_spec from spatial reasoning"]
        RETOUCH["**Spot retouch**<br/>RFC-025 / ADR-087<br/>heal + clone via apply_spot<br/>CIRCLE geometry, single-form per call"]
    end

    NAMED["**Named maskdef references**<br/>RFC-032<br/>{kind: 'named', name: 'mask_sky'}<br/>resolves to drawn or parametric spec"]

    subgraph WIRE["The mask_spec wire (apply-time)"]
        direction TB
        SPEC["mask_spec dict<br/>{dt_form, dt_params} ∪ {range_filter} ∪ {kind: 'named', ...}"]
        COMPOSE["AND composition<br/>drawn ∧ parametric"]
        RESOLVE["resolve_named_mask_spec<br/>(vocab lookup)"]
    end

    BYTES["**dt_serialize.py**<br/>encodes mask geometry as bytes<br/>+ retouch op_params"]

    XMP["**XMP**<br/>masks_history XML<br/>(darktable reads at render time)"]

    DRAWN --> SPEC
    PARAMETRIC --> SPEC
    NAMED --> RESOLVE
    RESOLVE --> SPEC
    VISION -.->|chat-client constructs| SPEC
    SPEC --> COMPOSE
    COMPOSE --> BYTES
    RETOUCH -.->|sister wire| BYTES
    BYTES --> XMP

    classDef source fill:#e8f3ff,stroke:#0366d6,stroke-width:2px
    classDef wire fill:#fff5e6,stroke:#d97706,stroke-width:2px
    classDef external fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
    class DRAWN,PARAMETRIC,VISION,RETOUCH,NAMED source
    class SPEC,COMPOSE,RESOLVE,BYTES wire
    class XMP external
```

## Reading the diagram

- **Four blue inputs** — each mask source has its own RFC + ADR pair. They look different at the photographer's surface (a JSON `dt_form` is not the same shape as a `range_filter`, an LLM prompt, or a retouch coordinate), but they converge on one wire.
- **Named-mask references** (the `RFC-032` box) — the v1.10.0 addition. A photographer writes `{"kind": "named", "name": "mask_sky"}` and the vocabulary's maskdef store resolves it to whatever spec the maskdef declares (typically a parametric range filter for sky / skin / luminance bands).
- **AND composition** — drawn masks AND parametric range filters compose multiplicatively. "Bottom third (gradient) AND luminance shadows (range_filter)" gives you the dark pixels in the bottom third.
- **Retouch** uses the same byte-encoder but doesn't go through the mask_spec wire — `apply_spot` is a sister verb. The reason: retouch carries op_params that reference a mask via `mask_id`, not via the `mask_spec` field.
- **darktable reads `masks_history`** at render time; the engine never reads it back. The XMP is the contract.

## What's NOT in this diagram

- The v0.3.0–v1.4.0 PNG-mask path (retired in v1.5.0 per ADR-076). darktable doesn't actually read external PNG files for raster masks; the entire system was a silent no-op.
- AI auto-spot-detection (find ALL the dust spots, not heal at one coord) — deferred to RFC-030 / deployed sibling-provider precision tier.

See also: `docs/guides/mask-applicable-controls.md` (per-module compatibility), `docs/guides/mask-shapes-from-words.md` (drawn-form recipes), `docs/guides/llm-vision-for-masks.md` (Pattern 7 — vision construction).
