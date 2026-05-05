# ADR-078 — Vocabulary manifest `parameters` schema (multi-parameter from day one)

> Status · Accepted
> Date · 2026-05-05
> TA anchor ·/contracts/vocabulary-manifest
> Related RFC · RFC-021 (closes); paired with ADR-077, ADR-079, ADR-080

## Context

ADR-077 makes Path C the default for explicitly-declared parameterizable modules. The manifest needs to carry the declaration: which fields of the module's `op_params` blob are parameterized, what types, what ranges, what defaults, what byte locations.

RFC-021 §Open Q1 deliberated single-parameter vs multi-parameter schema. Some modules are single-axis (`exposure` is one float); others are natively multi-axis (`temperature` carries temp + tint + WB strength as separate fields). Single-parameter is simpler to ship; multi-parameter is forward-compatible.

## Decision

The vocabulary manifest schema gains an optional **`parameters`** field on entry objects. It is a JSON array of parameter declarations (always an array, even for single-parameter entries — no "single-parameter only" shortcut shape). Each declaration carries:

```json
{
  "name": "ev",
  "type": "float",
  "range": [-3.0, 3.0],
  "default": 0.0,
  "field": {
    "module": "exposure",
    "modversion": 7,
    "offset": 4,
    "encoding": "le_f32"
  }
}
```

Fields:
- **`name`** — parameter identifier; user-facing in CLI `--param NAME=V` and MCP `value: {NAME: V}`. Must be a valid Python identifier and unique within the entry.
- **`type`** — currently `"float"` only (matches all v1.6.0 priority modules); reserved for `"int"`, `"bool"`, `"enum"` extensions later.
- **`range`** — `[min, max]` inclusive; values outside fail with `INVALID_INPUT` per ADR-079.
- **`default`** — value applied when the caller doesn't supply this parameter; must be inside the declared range.
- **`field`** — byte-level location in the module's `op_params` blob. `module` is the darktable iop name; `modversion` is the pinned struct version; `offset` is the byte offset (0-based) into the decoded struct; `encoding` declares the on-wire encoding (`"le_f32"`, `"le_i32"`, `"le_u32"` — little-endian per darktable convention).

Multi-parameter entries list multiple declarations:

```json
"parameters": [
  {"name": "temp", "type": "float", "range": [-2.0, 2.0], "default": 0.0, "field": {...}},
  {"name": "tint", "type": "float", "range": [-1.0, 1.0], "default": 0.0, "field": {...}}
]
```

Entries without a `parameters` field are non-parameterized and behave as before (ADR-008 opacity).

## Rationale

- **Multi-parameter from day one** avoids the forced schema migration when `temperature` (the first natively multi-axis priority module) joins the parameterized set. Cost is small: array-of-one is identical at the schema level to scalar-or-array; the apply logic iterates regardless.
- **Byte-level field declaration** keeps the decoder thin. The manifest carries the per-modversion struct knowledge; the `chemigram.core.parameterize.<module>` decoder reads from the manifest declaration rather than hardcoding it. Adding a new modversion = manifest edit + decoder modversion-bump.
- **Pinned modversions** propagate ADR-008's modversion-drift discipline. A parameterized entry refuses to apply against a mismatched modversion; the agent / user gets a clear error rather than a silently-wrong render.

## Decision: removal of existing magnitude-ladder entries (no deprecation overlap)

The existing discrete magnitude-ladder entries are **deleted in the same PR** that introduces the parameterized form. Specifically:

- `expo_+0.3`, `expo_-0.3`, `expo_+0.5`, `expo_-0.5`, `shadows_global_+`, `shadows_global_-` → removed; replaced by parameterized `exposure` entry.
- `vignette_subtle`, `vignette_medium`, `vignette_heavy` → removed; replaced by parameterized `vignette` entry.
- (Future migrations follow the same pattern as their parameterized forms ship.)

No deprecation aliases. No backwards-compatibility shims. The product has no users yet whose scripts depend on these names; carrying the old names buys nothing and adds maintenance burden. Manifest, vocabulary tests, visual-proofs gallery, and documentation updates land atomically with the parameterized entries.

The four shipped *mask-bound* exposure entries (`gradient_top_dampen_highlights`, `gradient_bottom_lift_shadows`, `radial_subject_lift`, `rectangle_subject_band_dim`) are **kept** — they're not magnitude-ladder entries; they're discrete photographic moves with specific geometry baked in. ADR-076 governs them.

## Alternatives considered

- **Single-parameter schema (scalar `parameter` field) for v1.6.0; extend to multi-parameter later.** Rejected — forces schema migration when `temperature` lands; the marginal cost of starting with array-of-one is negligible.
- **Keep magnitude-ladder entries as deprecated aliases for one minor version.** Rejected — RFC-021 §Q4: no users, no migration burden. Aliases are dead code from day one.
- **Encode field offsets in the decoder source rather than the manifest.** Rejected — would force a code change for every modversion bump; manifest-declared offsets keep modversion knowledge in data, not code.

## Consequences

Positive:

- Multi-axis modules (`temperature`) can ship without schema break.
- Manifest is self-documenting: a contributor reading `vocabulary/packs/expressive-baseline/manifest.json` sees the parameterized contract without reading code.
- Vocabulary collapses cleanly: 39 → ~30 entries with the same photographic coverage, plus parameterization.

Negative:

- Manifest schema is more complex (mitigated: backwards-compatible; non-parameterized entries unchanged).
- Manual modversion bookkeeping per parameterized entry (mitigated: pinned + clear failure on mismatch; same discipline as the rest of the project).

## Implementation notes

The parser at `src/chemigram/core/vocab.py` reads the optional `parameters` array; `VocabEntry` gains a `parameters: tuple[ParameterSpec, ...] | None` attribute. Schema validation lives alongside the existing manifest validation. Range/type/default consistency is checked at vocabulary-load time (early failure beats apply-time surprise).

The first ship (v1.6.0) carries two parameterized entries: `exposure` and `vignette`, both single-parameter (`parameters: [{name: "ev", ...}]` and `parameters: [{name: "brightness", ...}]` respectively). The discrete `expo_*` and `vignette_*` entries are removed in the same commit.
