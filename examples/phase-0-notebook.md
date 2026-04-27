# Phase 0 — Lab Notebook

*Capability verification and ecosystem check. Hands-on validation of architecture assumptions before writing any Chemigram code.*

**Goal:** confirm the vocabulary-composition story works end-to-end on this machine with real raws, before committing ~600 lines of Python to architectural assumptions.

**Time budget:** one focused evening. 3-4 hours if smooth, 5-6 hours if surprises.

**Cost of running this:** very low.
**Cost of skipping this:** building Phase 1 on assumptions that may be wrong.

---

## Setup checklist

Before starting:

- [ ] darktable 5.x installed (Apple Silicon native build from darktable.org)
- [ ] Note the exact version: ____________________________
- [ ] At least one La Ventana raw available (or any raw — Sony A1 ARW, Nikon NEF, Fuji RAF, doesn't matter for these tests)
- [ ] Note which raw(s) you'll use: ____________________________
- [ ] Text editor that handles XML cleanly (VS Code, Sublime, BBEdit, vim — anything but TextEdit)
- [ ] Terminal access
- [ ] ~30GB free disk space (overkill, but you'll be making temp files)

---

## Experiment 1 — Isolated configdir launch

**Validates:** the isolation principle that everything else depends on. Chemigram's darktable subprocess runs against a separate configdir; the user's everyday `~/.config/darktable/` stays untouched.

### What I tried

```bash
mkdir -p ~/chemigram-phase0/dt-config
mkdir -p ~/chemigram-phase0/workspace
mkdir -p ~/chemigram-phase0/styles
mkdir -p ~/chemigram-phase0/raws

# Launch darktable with isolated configdir
/Applications/darktable.app/Contents/MacOS/darktable \
  --core --configdir ~/chemigram-phase0/dt-config
```

### What I expected

- darktable launches with empty library (no images, no presets)
- `~/chemigram-phase0/dt-config/` populates with `library.db`, `data.db`, `darktablerc`
- Quitting and relaunching shows same empty state (stable, not regenerated)
- Real `~/.config/darktable/` untouched

### What I actually saw

*(fill in during the experiment)*

```
Files appearing in dt-config:
  -
  -
  -

Lighttable state on first launch:

Lighttable state on second launch (verifies stability):

Real ~/.config/darktable/ modified? (yes/no):

Surprises:
```

### Verdict

- [ ] ✅ Works as expected — proceed
- [ ] ⚠️ Works with caveats — note them: ____________________________
- [ ] ❌ Doesn't work — investigate before continuing

### Notes

*(anything worth remembering)*

---

## Experiment 2 — Author three primitive styles

**Validates:** that `.dtstyle` files capture single-module styles cleanly and have the schema we documented in `architecture.md`.

### What I tried

1. In the isolated darktable, copy a raw into `~/chemigram-phase0/raws/` and import it.
2. Open in darkroom. **Right-click on the history stack → "compress history" or "discard history"** to get to a known minimal state.
3. **Style 1 — `expo_+0.5`:**
   - Set exposure to +0.5 EV. Nothing else.
   - Styles panel → Create new style → name `expo_+0.5` → save.
   - Right-click the style → Export → save to `~/chemigram-phase0/styles/`.
4. Reset history. **Style 2 — `expo_+0.0`:**
   - Leave exposure at default 0.0 EV (or set explicitly to 0.0).
   - Capture as style `expo_+0.0`. Export.
5. Reset history. **Style 3 — `wb_warm_subtle`:**
   - Touch only the color calibration module. Pull the white balance slightly warm (towards yellow/red).
   - Capture as style `wb_warm_subtle`. Export.

### What I expected

- Three `.dtstyle` files in `~/chemigram-phase0/styles/`
- Each is XML matching the schema in `architecture.md`:
  - Root `<darktable_style>` with `<info>` and `<style>` children
  - One `<plugin>` element per captured module
  - `<operation>`, `<op_params>`, `<enabled>`, `<blendop_params>`, `<modversion>`, `<multi_priority>=0`, `<iop_order>`
- For `expo_+0.5`: a single `<plugin>` with `<operation>exposure</operation>`
- For `wb_warm_subtle`: a single `<plugin>` with `<operation>channelmixerrgb</operation>` (color calibration's internal name)

### What I actually saw

*(fill in)*

```
expo_+0.5.dtstyle:
  Number of <plugin> elements: ___
  Operations included: ___________________________
  modversion: ___
  iop_order: ___

expo_+0.0.dtstyle:
  Number of <plugin> elements: ___
  Operations included: ___________________________

wb_warm_subtle.dtstyle:
  Number of <plugin> elements: ___
  Operations included: ___________________________
  modversion: ___
  iop_order: ___

Did any style include modules I didn't touch? (yes/no, which):

Surprises in the XML schema vs documented:
```

### Verdict

- [ ] ✅ Clean single-module capture — proceed
- [ ] ⚠️ Capture is contaminated by auto-applied modules — investigate: do we need to disable auto-apply presets in the darktable instance first? Or filter on extraction?
- [ ] ❌ `.dtstyle` schema differs significantly from docs — update the architecture spec before continuing

### Notes

*Save copies of the three `.dtstyle` files; they'll be referenced in later experiments.*

---

## Experiment 3 — Single-style render via darktable-cli

**Validates:** that `darktable-cli` can render a JPEG given a raw and a style, headless, on this machine, in the time we predicted.

### What I tried

```bash
/Applications/darktable.app/Contents/MacOS/darktable-cli \
  ~/chemigram-phase0/raws/<raw_filename> \
  --style expo_+0.5 \
  ~/chemigram-phase0/workspace/test1_expo.jpg \
  --width 1024 \
  --apply-custom-presets false \
  --core --configdir ~/chemigram-phase0/dt-config
```

If `--style` doesn't find the style by name, try `--style-overwrite` and/or specify the path explicitly via `--style ~/chemigram-phase0/styles/expo_+0.5.dtstyle`. Note exactly which form worked.

### What I expected

- Command runs without errors
- JPEG appears at `~/chemigram-phase0/workspace/test1_expo.jpg`
- JPEG visually shows +0.5 EV brighter than a no-edit render
- Render time: 1-3 seconds (note actual time)

### What I actually saw

*(fill in)*

```
Command form that worked:
  darktable-cli ...

Render time (wall clock): ___ seconds

JPEG dimensions: ___ x ___

Visual check (compared to no-style render):
  ☐ Visibly brighter as expected
  ☐ Same brightness (style didn't apply)
  ☐ Different effect than expected

stdout/stderr observations:
```

Repeat the same render with `--style expo_+0.0` and `--style wb_warm_subtle`. Note any differences in behavior.

### Verdict

- [ ] ✅ Render works, time within expected range — proceed
- [ ] ⚠️ Render works but slower than expected (5-10s) — note for Mode B planning, may impact iteration budgets
- [ ] ⚠️ Render works but `--apply-custom-presets false` strips something visible — investigate which modules are essential
- [ ] ❌ Render fails — investigate before any composition test

### Notes

---

## Experiment 4 — Manual XMP composition (the critical one)

**Validates:** *the* core architectural test. Compose two `.dtstyle` entries into one XMP by hand, render it, confirm both effects apply.

### What I tried

#### Step 4a: Get a baseline XMP

Take any raw and develop it briefly in darktable to write its `.raw.xmp` sidecar. Find this file (it should be next to the raw). Open it in your text editor and study the structure — this is your template.

Identify:
- The `<darktable:history>` block
- The current `<darktable:history_end>` value
- How `<rdf:li>` entries are formatted
- The XMP namespace declarations at the top

#### Step 4b: Hand-compose

In a copy of the baseline XMP (named `composed.xmp`):

1. From `expo_+0.5.dtstyle`, locate the `<plugin>` element. Note these values:
   - `operation` = ________________
   - `enabled` = ________________
   - `modversion` (`<module>` in dtstyle) = ________________
   - `op_params` = ________________
   - `blendop_params` = ________________
   - `blendop_version` = ________________
   - `multi_priority` = ________________
   - `multi_name` = ________________
   - `iop_order` = ________________

2. From `wb_warm_subtle.dtstyle`, locate the same fields.

3. In `composed.xmp`, replace the `<darktable:history>` block with two `<rdf:li>` entries, mapping per the table in `architecture.md`:

```xml
<darktable:history>
  <rdf:Seq>
    <rdf:li
      darktable:num="0"
      darktable:operation="exposure"
      darktable:enabled="1"
      darktable:modversion="..."
      darktable:params="..."
      darktable:multi_name=""
      darktable:multi_priority="0"
      darktable:blendop_version="..."
      darktable:blendop_params="..."
      darktable:iop_order="..."/>
    <rdf:li
      darktable:num="1"
      darktable:operation="channelmixerrgb"
      ... etc ...
      />
  </rdf:Seq>
</darktable:history>
```

4. Set `<darktable:history_end>2</darktable:history_end>`.
5. Save `composed.xmp`.

#### Step 4c: Render

```bash
/Applications/darktable.app/Contents/MacOS/darktable-cli \
  ~/chemigram-phase0/raws/<raw_filename> \
  ~/chemigram-phase0/workspace/composed.xmp \
  ~/chemigram-phase0/workspace/test_composed.jpg \
  --width 1024 \
  --apply-custom-presets false \
  --core --configdir ~/chemigram-phase0/dt-config
```

### What I expected

- Render succeeds
- Output JPEG shows *both* effects: brighter than baseline AND warmer than baseline
- Comparing to single-style renders from Experiment 3 confirms it's the union, not just one of the two

### What I actually saw

*(fill in — this is the most important section in the entire notebook)*

```
Did the render succeed? (yes/no):

If yes, visual inspection:
  ☐ Both effects visible (the architecture works!)
  ☐ Only exposure effect visible (WB entry was ignored)
  ☐ Only WB effect visible (exposure entry was ignored)
  ☐ Neither effect visible (something fundamentally wrong)
  ☐ Some other unexpected result: ___________________________

If no, error message:

XMP attribute mappings that turned out to be wrong:

Surprises:
```

### Verdict

- [ ] ✅ Composition works — Phase 1 architecture is validated
- [ ] ⚠️ Works but with caveats — document them and adjust architecture: ____________________________
- [ ] ❌ Doesn't work — investigate. Possible causes:
  - Missing required XMP attribute
  - `iop_order` formatting issue
  - `darktable:num` ordering matters more than expected
  - Namespace declaration missing
  - `<darktable:history_end>` integer wrong

If broken, run darktable in debug mode to see what it doesn't like:

```bash
/Applications/darktable.app/Contents/MacOS/darktable-cli \
  ... \
  -d common -d xmp 2>&1 | tee debug.log
```

### Notes

---

## Experiment 5 — Same-module collision (SET semantics test)

**Validates:** the SET-semantics assumption. What happens when two `.dtstyle` entries touch the same module with the same `multi_priority`? This decides whether we trust darktable's append behavior or need to dedupe ourselves.

### What I tried

1. Author a third style `expo_+1.0` (exposure +1.0 EV, single module). Export.
2. Compose an XMP with **both** `expo_+0.5` and `expo_+1.0` in the history — same `operation: exposure`, same `multi_priority: 0`, different `darktable:num` (0 and 1, then 1 and 0 to test order independence).

**Test 5a:** `expo_+0.5` first (num=0), then `expo_+1.0` (num=1).
**Test 5b:** `expo_+1.0` first (num=0), then `expo_+0.5` (num=1).

Render both. Compare visually to single-style renders of `expo_+0.5` and `expo_+1.0`.

### What I expected

One of three behaviors:

- **Last-num wins (cleanest):** Test 5a renders as +1.0 EV, Test 5b renders as +0.5 EV. Our SET implementation is "remove existing, append new with next num". Done.
- **First-num wins:** Test 5a renders as +0.5 EV, Test 5b renders as +1.0 EV. We adapt our SET implementation accordingly.
- **Additive:** Both render as +1.5 EV (or some other combined effect). We must explicitly dedupe in our XMP synthesis layer before write.

### What I actually saw

*(fill in)*

```
Test 5a (expo_+0.5 then expo_+1.0):
  Render brightness compared to known +0.5 render: ☐ same  ☐ brighter  ☐ same as +1.0  ☐ other
  Render brightness compared to known +1.0 render: ☐ same  ☐ darker  ☐ other

Test 5b (expo_+1.0 then expo_+0.5):
  Render brightness compared to known +0.5 render: ☐ same  ☐ brighter  ☐ other
  Render brightness compared to known +1.0 render: ☐ same  ☐ darker  ☐ other

Conclusion (which behavior matches):
  ☐ Last-num wins
  ☐ First-num wins
  ☐ Additive
  ☐ Something else: ___________________________

Did darktable error or warn about the collision? (yes/no, what):
```

### Verdict and implementation implication

Based on what you saw:

- **If last-num wins:** SET implementation in `xmp.py` synthesis layer is "remove any existing entries matching `(operation, multi_priority)`, then append new entry with `num = max(existing_nums) + 1`". Simple.
- **If first-num wins:** Same logic but renumber the kept entry to be last. Slightly trickier but cheap.
- **If additive:** SET is "remove any existing entries matching `(operation, multi_priority)`, then insert new". Must dedupe before write or accumulation breaks our agent's mental model.
- **If darktable errors:** investigate further. Possibly we need explicit deduping with a single entry per module.

### Notes

---

## Experiment 6 (optional but valuable) — Reproduce a real edit

**Validates:** the vibe check. Can ~5 vocabulary primitives produce a result that's headed in the right direction for a real photo? This isn't an architectural test — it's a reality check on whether the vocabulary thesis holds.

### What I tried

1. Pick one La Ventana raw you've already developed somewhere (LR, darktable, anywhere). Export your final edit as a JPEG for reference.
2. Look at your final edit. Identify ~5 moves that mattered most. Probably some combination of:
   - exposure adjustment
   - white balance / color cast recovery
   - shadow lift or highlight recovery
   - contrast or tone curve move
   - clarity or local contrast
3. Author a `.dtstyle` for each (single module each, name them descriptively).
4. Compose an XMP with all 5 entries.
5. Render at the same dimensions as your reference.
6. Compare side-by-side.

### What I expected

The vocabulary render should be:
- *Visibly headed in the same direction* as your real edit
- *Coarser* — discrete steps can't match continuous slider tuning
- *Probably 70-80% there* — the broad strokes match, the fine-tuning is missing

### What I actually saw

*(fill in — this is subjective but informative)*

```
The 5 vocabulary entries I authored:
  1.
  2.
  3.
  4.
  5.

Comparison to my real edit:
  Overall direction: ☐ same  ☐ different
  Tonal balance: ☐ similar  ☐ noticeably different
  Color cast: ☐ similar  ☐ noticeably different
  Detail / sharpness: ☐ similar  ☐ noticeably different

Roughly what fraction of "the way there" did 5 primitives get?
  ☐ 90%+   ☐ 70-80%   ☐ 50-60%   ☐ less than 50%

Where was the vocabulary obviously inadequate?

Did this exercise feel like it'll be enjoyable to work with, or frustrating?
```

### What this tells me

- If 5 primitives get to 70%+, the vocabulary approach is viable. Expanding the vocabulary or adding more primitives gets the rest.
- If 5 primitives get to 50% or less, the vocabulary needs to be much larger or more granular than estimated. Either author finer increments (`expo_+0.1`, `expo_+0.2` ...) or accept that some L3 primitives need to be parameterized after all (which means revisiting the hex-encoder approach for a small set of modules).

### Notes

---

## Synthesis — what Phase 0 told me

*(fill in at the end of the session)*

### Architectural assumptions confirmed

- [ ] Isolated configdir works on Apple Silicon
- [ ] `.dtstyle` files capture cleanly (or: capture with caveat ___)
- [ ] `darktable-cli` renders headless in expected time (___s for 1024px)
- [ ] Hand-composed XMPs render correctly with multiple modules
- [ ] Same-module collisions resolve to: ___________________________

### Architectural assumptions corrected

*(things we believed that turned out to be wrong)*

- ___________________________
- ___________________________

### Surprises worth remembering for Phase 1

- ___________________________
- ___________________________

### Updates needed in the docs

- [ ] `architecture.md` — section _____ needs updating because _____
- [ ] `layers.md` — section _____ needs updating because _____
- [ ] None — docs match reality

### Phase 1 readiness

Pick one:

- [ ] **Green light.** Architecture validated. Start Phase 1 (Python engine).
- [ ] **Yellow light.** Architecture mostly works but [specific concern] needs design adjustment first.
- [ ] **Red light.** Phase 0 surfaced a fundamental issue. Redesign before any code.

### Artifacts to keep from this session

- [ ] The `.dtstyle` files (seed of the vocabulary)
- [ ] The working hand-composed XMP (reference template for the synthesis layer)
- [ ] The working `darktable-cli` invocation (reference for the render stage)
- [ ] This notebook itself (commits to the project)

---

## Appendix — useful commands and references

```bash
# Inspect a raw's EXIF (useful for manual binding tests later)
exiftool ~/chemigram-phase0/raws/<file>

# Pretty-print a .dtstyle file
xmllint --format ~/chemigram-phase0/styles/expo_+0.5.dtstyle

# Pretty-print an XMP
xmllint --format ~/chemigram-phase0/workspace/composed.xmp

# Render with debug output
darktable-cli ... -d common -d xmp -d perf 2>&1 | tee debug.log

# List installed styles in your isolated configdir
darktable-cli --list-styles --core --configdir ~/chemigram-phase0/dt-config
```

**Key references during this session:**

- `architecture.md` § "Concrete data formats" — the `.dtstyle` schema and dtstyle→XMP attribute mapping
- `architecture.md` § "Concrete `darktable-cli` invocation" — the canonical CLI form
- `architecture.md` § "Resolved questions" — what we expected to find
- darktable user manual — for any module behavior questions
