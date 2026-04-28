# RFC-006 — Same-module collision behavior

> Status · Draft v0.1
> TA anchor ·/components/synthesizer
> Related · ADR-002, ADR-009, RFC-001
> Closes into · ADR (pending) — specifies behavior for under-tested edge cases
> Why this is an RFC · ADR-002 commits to SET semantics by `(operation, multi_priority)`. ADR-009 specifies Path A vs Path B. But Phase 0 experiment 5 (same-module collision testing) was deferred — we don't have direct empirical evidence for what happens when two `.dtstyle` entries touch the same `(operation, multi_priority)` in a single synthesis pass. Specifying the resolution rule (and validating it) is a real open question.

## The question

When the agent applies multiple primitives in a single conceptual move (or applies primitive B onto a state that already includes primitive A's effect), and the primitives touch the same `(operation, multi_priority)`, what's the resolution rule?

Three concrete scenarios:

1. **Sequential application.** Agent applies `expo_+0.5` (becomes head). Agent then applies `expo_+0.8` to current state. ADR-002 SET semantics says: replacement, last-wins. Net effect: `expo_+0.8` is the final state.

2. **Composite primitive.** A vocabulary entry contains multiple `<plugin>` records that touch the same `(operation, multi_priority)` (e.g., a misauthored entry, or a deliberate entry that intends a specific kind of cumulative effect — though "cumulative" doesn't apply at the SET-semantics level).

3. **Cross-pack conflicts.** Photographer has both `expo_+0.5` from starter pack and `expo_+0.5_alt` from a community pack — both touch exposure at multi_priority=0. The agent applies `expo_+0.5_alt`. SET semantics → replace.

Each scenario has a clear rule per ADR-002 (last-wins on (operation, multi_priority)), but: are there weird edge cases? Is "last-wins" correct for the composite-primitive case? What about entries where the same operation appears multiple times within a single `.dtstyle` (multi-priority slots)?

## Use cases

- Sequential vocabulary application — most common case; SET semantics is correct
- Composite primitives with multiple plugins — rare but legitimate (e.g., the WB+color-cal coupling from ADR-025)
- Pack conflicts — multiple packs declaring entries with overlapping coverage

## Goals

- Explicit, predictable resolution rules
- Validation that catches misauthored entries before they cause runtime confusion
- No silent bad-outcome modes (e.g., the synthesizer applies both, last one wins, but no diagnostic surfaces)

## Constraints

- TA/components/synthesizer — the synthesizer must produce a single coherent XMP
- ADR-002 — SET semantics is the chosen approach; same-module entries don't accumulate

## Proposed approach

**Resolution rules, in order:**

1. **Within a single `.dtstyle` file**, two `<plugin>` records with the same `(operation, multi_priority)` are a **schema error**. The parser raises `DtstyleSchemaError` with the offending file and operation. This catches misauthored entries early.

2. **Within a single `synthesize_xmp()` call** (multiple `PluginEntry` objects passed in), two entries with the same `(operation, multi_priority)` are a **synthesizer error**. Raise `XmpSynthesizeError`. The caller (probably the agent's `apply_primitive` flow) shouldn't be trying to apply multiple entries to the same slot in one call.

3. **Across sequential `apply_primitive()` calls**, the SET semantics from ADR-002 applies cleanly: each call's PluginEntry replaces any existing match in the XMP. This is the dominant case; no diagnostic needed (the snapshot trail records the sequence).

4. **Cross-pack conflicts** (same name, different packs) are a **vocabulary loading concern**, not a synthesis concern. Resolved at vocabulary load time: by precedence (e.g., starter pack < community packs < personal vocabulary). If two packs at the same precedence level have entries with the same name, that's a configuration error and the photographer's responsibility to resolve (e.g., disable one pack).

5. **Same-name entries in the *same* pack** are a manifest schema error caught by CI.

## Alternatives considered

- **Allow multiple entries; later wins; warn:** rejected for cases 1 and 2. The author/caller likely intended a different semantics; a warning is too quiet.
- **Allow multiple entries; treat as accumulation in some fields:** rejected — would diverge from SET semantics, complicate reasoning, and require per-field accumulation rules that don't exist.
- **Force an ADR per case (separate ADRs for in-file collision, in-call collision, etc.):** considered. The cases are conceptually similar (all about `(op, mp)` uniqueness within a scope); one ADR covering all cases is cleaner.

## Trade-offs

- Strict schema errors at parse time can frustrate authors who hit them during exploration. Mitigated: the error message clearly explains the rule; it's a one-line fix to the dtstyle.
- The `multi_priority` slot is a real expressivity escape — authors can intentionally have two exposure entries at different priorities. Need clear documentation that "different priority is OK; same priority is a collision."

## Open questions

- **How does Phase 0 experiment 5 confirm or refute these rules?** The experiment was deferred. When implementation begins, run the experiment as a self-test. If darktable surprisingly *does* allow same-(op, mp) entries to layer, revise this RFC.
- **Are there modules where multi_priority semantics differ?** As far as Phase 0 testing went, multi_priority is universal across modules. Verify on a wider set of modules during Phase 1 self-tests.
- **Composite primitives with multi_priority slots.** A `.dtstyle` *can* include `exposure` at `multi_priority=0` AND `multi_priority=1` (different slots, both applying). This isn't a collision — they're different slots. The schema-error rule should be precise: same `operation` AND same `multi_priority` → error. Different priority → fine.

## How this closes

This RFC closes into:
- **An ADR specifying the resolution rules** as proposed.
- **A test suite** running the same-module collision scenarios (essentially Phase 0 experiment 5, deferred to Phase 1 implementation).

## Links

- TA/components/synthesizer
- ADR-002 (SET semantics)
- ADR-009 (Path A vs Path B)
- RFC-001 (synthesizer architecture)
- `examples/phase-0-notebook.md`/Experiment 5 (deferred)
