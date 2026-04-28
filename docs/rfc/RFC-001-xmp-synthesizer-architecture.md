# RFC-001 — XMP synthesizer architecture

> Status · Draft v0.1
> TA anchor ·/components/synthesizer ·/contracts/dtstyle-schema ·/contracts/xmp-darktable-history
> Related · ADR-001, ADR-002, ADR-008, ADR-009, ADR-010
> Closes into · ADR-009 (already closed), additional ADRs for parser API and error contracts (pending)
> Why this is an RFC · The high-level synthesis approach is settled (vocabulary-via-`.dtstyle`, SET semantics, opaque-blob copying). What's open: the concrete parser API, the synthesizer's function signatures, error handling contracts, and edge cases like malformed `.dtstyle`, stale `multi_priority` collisions, and locale-dependent decimal separators in `iop_order`.

## The question

Phase 0 settled the architectural critical path: parse `.dtstyle`, identify user entries by empty `<multi_name>`, replace by `(operation, multi_priority)` (Path A) or append with explicit iop_order (Path B), write XMP, render. What's still open is the concrete code surface: function signatures, error types, what gets logged vs raised, how the pack/manifest layer composes with the parser.

This RFC specifies the synthesizer's API at the level the agent (and any human readers) will actually interact with it. It closes into ADRs locking the API and error contract.

## Use cases

- Agent calls `apply_primitive(image_id, "expo_+0.5")` — synthesizer must compose the entry into the current XMP and write a new one.
- Vocabulary CI runs render-tests on each PR — synthesizer must work standalone (without a full image pipeline running).
- Path B add of a new module (drawn-mask gradient that wasn't in baseline) — synthesizer must handle missing entries gracefully and supply iop_order from the dtstyle.
- Malformed `.dtstyle` (missing `<plugin>`, malformed XML) — synthesizer must error clearly, not produce a corrupted XMP.

## Goals

- A small, testable parser-and-synthesizer API
- Error reporting that surfaces specific dtstyle/XMP issues (not generic "parsing failed")
- Locale-independent handling of `iop_order` decimal separators
- Predictable behavior on edge cases (multiple plugins in one dtstyle; same operation in dtstyle that already exists in XMP at different multi_priority)

## Constraints

- TA/constraints/opaque-hex-blobs — the synthesizer doesn't decode op_params or blendop_params
- TA/components/synthesizer — module decomposition is `xmp.py` + `dtstyle.py`
- TA/contracts/xmp-darktable-history — output XMP must conform

## Proposed approach

**API surface in `chemigram_core/dtstyle.py`:**

```python
@dataclass
class PluginEntry:
    """A user-authored module entry parsed from a .dtstyle file."""
    operation: str
    modversion: int
    op_params: str            # opaque hex
    blendop_params: str       # opaque base64
    blendop_version: int
    multi_priority: int
    multi_name: str           # always "" for user entries (filtered by parser)
    iop_order: float          # locale-corrected on parse


def parse_dtstyle(path: Path, touches: list[str]) -> list[PluginEntry]:
    """
    Parse a .dtstyle file and return user-authored plugin entries
    matching the manifest's `touches` declaration.

    Filters: drops entries whose <multi_name> starts with "_builtin_".
    Filters: drops entries whose <operation> is not in `touches`.
    Locale: converts comma decimal separator in <iop_order> to period.

    Raises:
        DtstyleParseError: if XML is malformed
        DtstyleSchemaError: if required fields are missing
        DtstyleValidationError: if `touches` contains entries not present
    """
```

**API surface in `chemigram_core/xmp.py`:**

```python
@dataclass
class HistoryEntry:
    """A history entry parsed from an XMP file's <darktable:history>."""
    num: int
    operation: str
    enabled: bool
    modversion: int
    params: str
    multi_name: str
    multi_priority: int
    blendop_version: int
    blendop_params: str
    iop_order: float | None   # may be absent from XMP


@dataclass
class XMP:
    """An XMP sidecar's parsed state."""
    raw: str                  # full XMP source
    history: list[HistoryEntry]
    history_end: int
    iop_order_version: int
    raw_xml_attrs: dict[str, str]   # for round-trip preservation


def parse_xmp(path: Path) -> XMP:
    """Parse an XMP file, returning the structured representation."""


def synthesize_xmp(
    baseline: XMP,
    entries: list[PluginEntry],
) -> XMP:
    """
    Apply the given plugin entries to the baseline XMP.

    For each entry:
        - If a HistoryEntry exists in baseline.history with matching
          (operation, multi_priority): replace its content (Path A).
        - Otherwise: append a new HistoryEntry (Path B), supplying
          iop_order from the entry.

    Returns a new XMP with updated history and history_end.
    Does not mutate the baseline argument.
    """


def write_xmp(xmp: XMP, path: Path) -> None:
    """Serialize the XMP to disk."""
```

**Error hierarchy:**

```python
class SynthesizerError(Exception): pass
class DtstyleParseError(SynthesizerError): pass
class DtstyleSchemaError(SynthesizerError): pass
class DtstyleValidationError(SynthesizerError): pass
class XmpParseError(SynthesizerError): pass
class XmpSchemaError(SynthesizerError): pass
class XmpSynthesizeError(SynthesizerError): pass
```

Each carries the offending file path and a specific diagnostic message.

## Alternatives considered

- **Single `apply_dtstyle_to_xmp(dtstyle_path, xmp_path) -> xmp_path` function:** rejected — couples parsing and writing, hard to test in isolation, hard to compose multiple primitives in one synthesis pass.

- **Mutate the XMP argument in-place:** rejected — copy-and-return is safer, easier to test, and synthesis is fast enough that the copy cost is irrelevant.

- **Return errors as result objects instead of exceptions:** considered. Exceptions match Python's idiomatic error handling here; the call sites (MCP server, vocabulary CI) need to log specific failures, which is what exceptions enable cleanly.

- **Embed the manifest's `touches` filter inside `parse_dtstyle`:** done in proposed API. Alternative would be to return all entries and filter at the call site; but bundling the filter at parse time prevents callers from accidentally getting `_builtin_*` entries.

## Trade-offs

- The two-step parse (`parse_dtstyle` + `parse_xmp` separate from `synthesize_xmp`) means synthesis can't take shortcuts even when the dtstyle and XMP are simple. Acceptable: synthesis is a coarse operation, not a hot loop.
- Returning a new XMP object instead of editing the file directly means the caller is responsible for `write_xmp`. Acceptable: separation of concerns; tests can avoid I/O.

## Open questions

- **Round-trip preservation.** Does `parse_xmp` → `synthesize_xmp` → `write_xmp` preserve every XML attribute outside the `<darktable:history>` element verbatim? RFC-002 (canonical XMP serialization) is downstream of this — we need round-trip stability before we can hash XMPs deterministically.
- **Multiple-plugin dtstyles.** When a `.dtstyle` has multiple `<plugin>` entries (e.g., the coupled WB + color cal case from ADR-025), does the synthesizer apply them as a set (all-or-nothing) or independently? Proposed: as a set — atomic application of the entry.
- **Stale `multi_priority` collisions.** What if the XMP has an exposure entry at `multi_priority=0` AND `multi_priority=1`, and the agent applies an entry at `multi_priority=0`? Path A (replace at 0) is the answer per ADR-009; should we warn about the unrelated entry at `multi_priority=1`? Proposed: no warning; SET is per-priority by design.
- **Validation strictness.** Should synthesis error on a `.dtstyle` whose plugin's `<modversion>` doesn't match the running darktable's reported modversion, or just warn? RFC-007 deliberates this.

## How this closes

- **ADR-009** — already closed (Path A vs Path B).
- **ADR for parser/synthesizer API** — closes when the proposed API stabilizes after first implementation pass. Captures the function signatures, error hierarchy, and round-trip preservation guarantees.
- **ADR for synthesizer error handling** — possibly merged into the API ADR; or split if error handling has its own deliberation surface.

## Links

- TA/components/synthesizer
- TA/contracts/dtstyle-schema
- TA/contracts/xmp-darktable-history
- ADR-001, ADR-002, ADR-008, ADR-009, ADR-010
- `examples/phase-0-notebook.md` (architectural critical path validation)
