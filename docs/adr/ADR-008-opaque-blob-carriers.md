# ADR-008 — XMP and `.dtstyle` as opaque-blob carriers

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/constraints/opaque-hex-blobs ·/contracts/dtstyle-schema ·/contracts/xmp-darktable-history
> Related RFC · None (foundational; underlies vocabulary approach)

## Context

darktable encodes module parameters in two binary formats:
- **`op_params`** — raw hex of a C struct, modversion-pinned. Each module has its own struct with its own field layout.
- **`blendop_params`** — gzip-compressed, base64-encoded blob of a C struct holding blend operation and mask data.

Programmatically generating these requires per-module struct definitions, version pinning, and a custom encoder/decoder per module. There are 60+ modules; the engineering cost is large.

## Decision

Chemigram treats `op_params` and `blendop_params` as **opaque blobs** in v1. The synthesizer copies them verbatim from `.dtstyle` files into synthesized XMPs. No decoding, no encoding, no modification. The vocabulary primitive is the abstraction; the underlying bytes are darktable's concern.

## Rationale

- **Avoids per-module engineering.** Adding a new module to the vocabulary costs zero engineering work; the photographer authors a `.dtstyle` in the GUI and the synthesizer can compose it.
- **Avoids modversion drift maintenance.** When darktable bumps a module's modversion, only that module's vocabulary needs re-authoring. The engine code is unaffected.
- **Aligns with the vocabulary research thesis.** The vocabulary is the photographer's articulated craft; treating module bytes as primitives at the right abstraction level keeps focus on vocabulary, not parameter encoding.
- Phase 0 confirmed end-to-end that opaque-blob copying produces correct renders.

## Alternatives considered

- **Decode/encode all modules' op_params:** rejected — see ADR-001's Architecture A. Per-module engineering cost dominates Phase 1.
- **Decode/encode a few high-value modules (Path C):** deferred to RFC-012 / future work. Phase 0 demonstrated that exposure's op_params can be programmatically edited (changing `0000003f` → `00000040` produced the expected render). When vocabulary gaps surface a real bottleneck for a specific module, Path C can address that module without abandoning this ADR's general policy.

## Consequences

Positive:
- Synthesizer code is small and modversion-agnostic
- Vocabulary expansion is photographer work, not engineering work
- New darktable releases mostly don't break Chemigram (vocabulary may need re-authoring, engine doesn't)

Negative:
- Continuous parameter control requires Path C (programmatic generation per module). Most users won't need this; some will.
- Vocabulary granularity is whatever the photographer authored. "Apply +0.42 EV" is not directly expressible — the agent picks from `expo_+0.3`, `expo_+0.5`, etc.
- Diff/inspection of `op_params` (e.g., "what does this entry actually do?") requires running darktable to render and observe, not reading the bytes.

## Implementation notes

`src/chemigram_core/dtstyle.py` reads `<plugin>` elements as records of strings; `op_params` and `blendop_params` are kept as strings throughout. `src/chemigram_core/xmp.py` writes them as XML attribute values verbatim. No parsing of the hex content occurs anywhere in `chemigram_core`.
