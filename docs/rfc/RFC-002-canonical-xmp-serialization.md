# RFC-002 — Canonical XMP serialization for stable hashing

> Status · Draft v0.1
> TA anchor ·/components/versioning ·/components/synthesizer
> Related · ADR-018, RFC-001
> Closes into · ADR-018-amendment (pending) — specifies the canonicalization
> Why this is an RFC · ADR-018 commits to "SHA-256 over the canonical XMP serialization" as the snapshot identifier, but doesn't specify what canonical means. Whitespace, attribute ordering, namespace prefix choice, and XML declaration form all affect the hash. Without a specification, identical-edit-state XMPs produce different hashes — defeating the content-addressing guarantee.

## The question

What XML serialization rules produce a hash that's stable across:
- Same edit state, different render runs (synthesizer non-determinism in attribute ordering)
- Same edit state, different operating systems (line-ending differences)
- Same edit state, two different photographers (anything that varies between machines)

We need a deterministic byte representation of the meaningful state. Two candidate paths exist: (a) adopt XML Canonical Form 1.1 (XML-C14N), or (b) define a custom narrow canonicalization specific to darktable XMPs.

## Use cases

- Snapshot identifier hashing (ADR-018) — same XMP must produce the same hash always.
- Identical-state detection — if the agent applies and undoes a primitive, the resulting XMP should hash to the same value as before.
- Cross-machine comparison — researchers analyzing session transcripts need stable hashes.
- Round-trip preservation — `parse_xmp → synthesize_xmp → write_xmp` should produce the same hash if no actual state changed.

## Goals

- Deterministic SHA-256 across invocations and machines
- Robust to incidental XML differences (whitespace, attribute order, line endings)
- Cheap to compute (snapshot operation runs frequently)
- Clear specification (any implementation can produce the same canonical form)

## Constraints

- TA/components/versioning — content-addressing requires deterministic hashing
- The canonical form must round-trip — `canonicalize(parse(canonicalize(x))) == canonicalize(x)`
- Cannot mutate semantic content (operation values, multi_priority, etc.)

## Proposed approach

**Custom narrow canonicalization specific to darktable XMPs.** Specifically:

1. **Parse** the XMP with a tolerant parser.
2. **Strip** non-semantic whitespace inside elements.
3. **Sort** attributes within each element alphabetically by qualified name.
4. **Normalize** namespace prefixes to a fixed set (e.g., `darktable`, `xmp`, `xmpMM`, `dc`, `lr`, `exif`, `tiff`, `aux`, `Iptc4xmpCore`).
5. **Normalize** the `<darktable:history>` `<rdf:Seq>` order: keep `darktable:num` ordering as authoritative; renumber 0..N-1 if `<darktable:history_end>` matches the count.
6. **Strip** XML declaration `<?xml ...?>` and serialize without (the declaration's encoding/standalone attributes shouldn't affect hash).
7. **Use** UTF-8 with `\n` line endings (no `\r\n`).
8. **Use** double quotes for attributes consistently.
9. **Preserve** `op_params`, `blendop_params`, and other opaque blob attributes verbatim (these are already deterministic since darktable produces them).
10. **Compute** SHA-256 over the serialized bytes.

This is implemented in a single `canonicalize_xmp(xmp: XMP) -> bytes` function that's called inside `versioning.snapshot()`.

## Alternatives considered

- **XML Canonical Form 1.1 (W3C XML-C14N):** rejected — too permissive in what it preserves (e.g., comments, processing instructions) and not specific enough about RDF/Seq ordering. We'd still need additional rules on top, defeating the "use a standard" benefit.

- **JSON-LD round-trip (parse XMP into JSON-LD, hash that):** rejected — adds a dependency, RDF-to-JSON-LD round-trip has its own canonicalization issues, and the resulting hash is divorced from what's actually written to disk.

- **Hash only the `<darktable:history>` element, ignore rest:** considered. Simpler, but loses the property that snapshot hashes capture *all* state in the XMP (e.g., custom `<dc:subject>` tags, IPTC fields). Future tooling that wants to detect "did the rating change?" would lose that capability. The narrow canonicalization is more general.

- **Hash the parsed `XMP` dataclass fields directly (not the bytes):** considered. Loses the property that canonicalization is observable on disk. Two engines could disagree on what hashes to what. Hashing serialized bytes (with a specified canonical form) is verifiable.

## Trade-offs

- Custom canonicalization means we maintain a spec. Acceptable; the spec is small (~20 rules) and is a one-time cost.
- Tighter than XML-C14N means our canonical form is narrower (e.g., we wouldn't preserve comments — which we explicitly don't want to — or processing instructions). Acceptable: we control what counts as state.
- Round-trip stability requires careful implementation (parse → canonicalize → write must equal parse → write only if no state changed). Test with property-based testing.

## Open questions

- **XML namespace prefix order.** If two parsers produce identical content but order namespace declarations differently in `<rdf:Description>`, the canonical form must produce the same output. Proposed: sort by prefix alphabetically.
- **Empty `<darktable:masks_history>`.** Should `<rdf:Seq/>` be canonicalized identically to `<rdf:Seq></rdf:Seq>`? Proposed: use the self-closing form always.
- **Attribute presence vs absence.** Some attributes are equivalent when absent vs default-valued (e.g., `darktable:enabled="1"` vs absent → defaults to 1). Should we strip default-valued attributes? Proposed: NO — stripping would diverge from darktable's natural output, defeating round-trip stability when darktable re-emits the file.
- **iop_order precision.** `47.474747` vs `47.474746999999...` — float rounding can differ across operations. Proposed: round to 6 decimal places, store as text. The 6-decimal precision matches darktable's emission.

## How this closes

This RFC closes into:
- **An amendment to ADR-018** (or a new ADR superseding the relevant section) that specifies the canonical form. Likely as ADR-034 or similar.
- A test suite (unit + property-based) demonstrating round-trip stability.

## Links

- TA/components/versioning
- TA/components/synthesizer
- ADR-018 (per-image content-addressed DAG)
- RFC-001 (synthesizer architecture; round-trip preservation is a related concern)
