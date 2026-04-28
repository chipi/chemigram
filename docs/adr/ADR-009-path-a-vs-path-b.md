# ADR-009 — Path A vs Path B for synthesis

> Status · Accepted
> Date · 2026-04-27
> TA anchor ·/components/synthesizer ·/contracts/xmp-darktable-history
> Related RFC · RFC-001

## Context

The synthesizer applies a vocabulary entry to an XMP either by replacing an existing history entry (the common case — most user moves replace darktable's auto-applied `_builtin_*` defaults) or by adding a new entry (the less-common case — adding a module not in the baseline pipeline, or adding a second instance of a module at a different `multi_priority`).

Phase 0 experiment 4 surfaced that these two paths have different requirements regarding `iop_order` (the float that determines pipeline position).

## Decision

The synthesizer has two paths, dispatched on whether the vocabulary entry's `(operation, multi_priority)` matches an existing XMP entry:

**Path A — Replace.** When `(operation, multi_priority)` matches an existing entry:
- Replace `op_params`, `enabled`, `blendop_params`, `blendop_version`, `multi_name` (set to empty string for user-authored entries)
- **Keep the existing `darktable:num` and do NOT supply iop_order** — the replacement inherits the pipeline position of the entry it replaces
- Update `<darktable:history_end>` only if the entry count changes (it doesn't, in Path A)

**Path B — Add new instance.** When `(operation, multi_priority)` does NOT match any existing entry:
- Append a new `<rdf:li>` with the next available `darktable:num`
- **Must supply `darktable:iop_order`** — copied from the source `.dtstyle` file's `<iop_order>` element (note: locale-dependent comma → period conversion may be needed: `47,474747` → `47.474747`)
- If iop_order is omitted, darktable emits "cannot get iop-order for `<operation>` instance N" and silently drops the entry
- Increment `<darktable:history_end>`

## Rationale

- Path A is the dominant case (replacing `_builtin_*` defaults with user vocabulary). Keeping it simple — no iop_order math — matches its frequency.
- Path B is needed for additive moves (multi-instance modules, drawn-mask gradients added on top, etc.). Requiring explicit iop_order matches darktable's actual requirement.
- Phase 0 testing established this empirically: experiment 4 iteration 1 added a new instance without iop_order and the entry was silently dropped; iteration 2 used Path A (replacement) and the render was correct; iteration 3 confirmed by changing op_params alone and observing visible effect.

## Alternatives considered

- **Always use Path B (always add, never replace):** rejected — produces unintended layering, conflicts with SET semantics (ADR-002), accumulates history forever.
- **Always use Path A, error on no-match:** rejected — would prevent legitimate Path B use cases like adding a drawn-mask gradient on top of the baseline.
- **Compute iop_order ourselves rather than copying from .dtstyle:** rejected — darktable's pipeline ordering is internal and version-specific. Copying from `.dtstyle` (where darktable already wrote a valid value) is reliable.

## Consequences

Positive:
- Most vocabulary applications go through the simpler Path A
- Path B is available when needed (multi-instance, additive moves)
- `iop_order` source-of-truth is the `.dtstyle` file, not engine logic

Negative:
- The synthesizer must implement two paths and dispatch correctly between them
- A vocabulary entry's `multi_priority` value affects whether application is a replace or an add — authors must understand this when their entry should layer rather than replace

## Implementation notes

`src/chemigram_core/xmp.py.synthesize_xmp()` looks up `(operation, multi_priority)` in the existing history; dispatches to `_replace_entry()` or `_append_entry()` accordingly. Locale-related decimal-separator handling for iop_order lives in `dtstyle.py.parse_dtstyle()`. See RFC-001 for the full synthesizer architecture.
