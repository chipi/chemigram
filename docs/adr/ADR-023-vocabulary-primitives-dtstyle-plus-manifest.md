# ADR-023 — Vocabulary primitives are `.dtstyle` files + manifest entries

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/contracts/dtstyle-schema ·/contracts/vocabulary-manifest
> Related RFC · None (concept-package decision)

## Context

A vocabulary primitive is the unit the agent applies — `expo_+0.5`, `tone_lifted_shadows_subject`, `fuji_acros`. Each primitive needs both the operational data (op_params, blendop_params, modversion — what darktable applies) and the structural metadata (which layer, which modules touched, mask reference, license, version, source, etc.).

Different file formats could hold these: a single combined JSON, two separate files, an embedded structure inside a custom format. The choice affects authoring ergonomics, parsing complexity, distribution, and how vocabulary is reviewed.

## Decision

A vocabulary primitive consists of two files:

1. **The `.dtstyle` file** — the darktable-native XML, capturing the actual edit operations. Authored in darktable's GUI by the photographer.
2. **A manifest entry** — JSON metadata in the pack's `manifest.json`. Declares layer, subtype, modules touched, mask kind, version pinning, source, license, etc.

A pack (the unit of distribution) contains many `.dtstyle` files plus one `manifest.json` listing all of them.

```
chemigram-vocabulary/
  layers/
    L1/...
    L2/
      neutralizing/
      film_sims/
        fuji_acros.dtstyle
    L3/
      tone_lifted_shadows_subject.dtstyle
      ...
  manifest.json     <- declares all entries with metadata
```

## Rationale

- **`.dtstyle` is darktable's native format.** Photographers author primitives in darktable's GUI and export to `.dtstyle`; we use the format darktable produces, no transformation needed.
- **Separation of concerns.** Operational data lives in `.dtstyle` (darktable's domain); metadata lives in the manifest (Chemigram's domain). Each is the right tool for its job.
- **Distribution is natural.** A vocabulary pack is a directory of `.dtstyle` files plus a manifest — it ships as a tarball or git repo without special packaging.
- **Inspection is straightforward.** `cat fuji_acros.dtstyle` shows the XML; `jq '.' manifest.json` shows the metadata. No proprietary container.

## Alternatives considered

- **Single combined JSON per primitive (embed darktable's XML inside a JSON wrapper):** rejected — couples manifest schema to darktable's evolving XML format; loses the property that `.dtstyle` files are darktable-readable in their native form.
- **Manifest embedded inside `.dtstyle`'s `<description>`:** rejected — pollutes the description field, fragile if darktable changes XML schema, hard to validate.
- **Single manifest combining all primitives' operational data and metadata in one big JSON:** rejected — defeats the photographer's natural workflow (export `.dtstyle` from darktable, drop in directory). Forces a transform step that adds friction.

## Consequences

Positive:
- Authoring stays close to darktable's natural workflow
- Manifest is clean JSON with predictable schema
- Vocabulary inspection works with standard tools
- Distribution is "directory + manifest"

Negative:
- Two files per primitive (`.dtstyle` + manifest entry) instead of one. Mitigated: the manifest has all entries together, so it's not "two files per primitive" but "all-entries-in-one-file plus per-primitive `.dtstyle`."
- Schema validation must check both files plus their consistency (touches in manifest matches operations in dtstyle). Done in CI.

## Implementation notes

`src/chemigram_core/vocab.py` loads packs by reading `manifest.json` first, then loading each entry's `.dtstyle` from the declared path. Vocabulary CI checks (per CONTRIBUTING.md) validate both schemas plus their consistency.
