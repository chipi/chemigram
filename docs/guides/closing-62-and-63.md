# Closing the v1.4.0 carry — issues #62 and #63

> A step-by-step you can follow tomorrow without re-reading the threads.
> Both issues are on milestone **v1.5.1** (see https://github.com/chipi/chemigram/milestone/11).

## What's in front of you

| | What | Time | Where |
|-|-|-|-|
| **#62** | Close as resolved-by-retirement (one comment + close) | ~5 min | terminal |
| **#63 part A** | darktable session: configure channelmixerrgb for B&W → export `.dtstyle` to `_seeds/` | ~10–15 min | darktable GUI |
| **#63 part B** | New Claude session decodes the seed + authors 3 variants + closes the issue | ~30 min wall, you sip coffee | Claude Code |

After both: open issues drops 2 → 0, v1.5.1 closes, Phase 1.4 fully done.

---

## Issue #62 — `tone_lifted_shadows_subject` content bug

### Why this is a 5-minute close

The original "Resolution path" in the issue tells you to author a tone_equalizer + raster-mask `.dtstyle`. That whole architecture is gone — v1.5.0 retired the PNG-mask path entirely (ADR-076) because darktable doesn't read external PNGs for raster masks. The broken entry was *deleted* from the starter pack as part of that cleanup. The bug doesn't exist anymore because the file doesn't exist anymore.

Just close the issue with a comment explaining.

### Step 1 — close it

```bash
cd ~/Projects/chemigram
gh issue close 62 --comment "Resolved by retirement in v1.5.0. The PNG-mask architecture this entry depended on (\`mask_kind: raster\` + \`mask_ref\`) was a silent no-op — darktable never reads external PNGs for raster masks (verified against darktable 5.4.1 source). Per ADR-076, the mask architecture is now drawn-form only, and the broken \`tone_lifted_shadows_subject\` was dropped from the starter pack along with the dead path. If we want a 'lift shadows on subject area' starter primitive in the future, it would be authored as a drawn-mask entry (e.g., radial ellipse) — separate ticket if/when motivated by Phase 2 evidence."
```

### Step 2 — verify

```bash
gh issue view 62 --json state -q .state    # expect: CLOSED
```

That's it for #62.

### Optional — author a replacement (skip unless you want one)

If you decide a "lift shadows on a subject area" starter primitive is worth having, that's a *new* drawn-mask entry, not a fix to #62. Recipe: open darktable → enable `tone equalizer` (or just exposure) → set up a *radial drawn mask* in the blend tab (not a raster mask) → save the style → export → add a manifest entry with `mask_spec: {dt_form: ellipse, dt_params: {...}}`. Follow the pattern of `vocabulary/packs/expressive-baseline/layers/L3/masked/radial_subject_lift.dtstyle`. **Don't do this tomorrow unless you specifically want to** — it's a new ticket, not part of closing #62.

---

## Issue #63 — `channelmixerrgb` B&W trio

### What you're doing

Producing one seed `.dtstyle` from a real darktable session that captures the channelmixerrgb v3 binary struct. The struct is ~160 bytes (matrix-style fields) and gz-compressed in the wild — too risky to reverse-engineer cold. Once we have one working seed, the three variants (`bw_convert` neutral, `bw_sky_drama` blue-emphasis, `bw_foliage` green-emphasis) are extrapolatable by varying the `grey[4]` floats.

### Step 1 — pre-flight

```bash
cd ~/Projects/chemigram
mkdir -p vocabulary/packs/expressive-baseline/_seeds/
which darktable                              # confirm darktable installed
ls tests/e2e/expressive/test_path_a_bw.py    # verify test scaffold exists
```

### Step 2 — author the seed in darktable

1. Open **darktable** (the GUI, not `darktable-cli`).
2. Open **any photo** — the specific image doesn't matter; we just need one to drive the module against.
3. In the right panel, find **`channel mixer rgb`** under the *color* group. **Enable it.**
4. Open its settings:
   - Set **Destination:** `grey`
   - Pick a reasonable **B&W mix** — the "monochrome" preset, or hand-tune the R/G/B sliders to give a neutral B&W. Exact values don't matter for this seed; we just need a non-default working struct.
5. Look at the preview — image should now be black and white. If it's not, the destination didn't take effect.
6. **Right-click on the history stack** (left panel, near the bottom) → **compress history**. This collapses your edits to a single clean state.
7. **Right-click the styles panel** (left panel) → **create style**.
   - **Name:** `bw_convert_seed`
   - **Description:** `Seed for #63 — channelmixerrgb v3 reverse-engineering`
   - When asked which modules to include: select **only** `channel mixer rgb`.
8. **Right-click the new style** → **export**. Save to:
   ```
   ~/Projects/chemigram/vocabulary/packs/expressive-baseline/_seeds/bw_convert_seed.dtstyle
   ```

### Step 3 — verify the seed

```bash
cd ~/Projects/chemigram
ls -la vocabulary/packs/expressive-baseline/_seeds/bw_convert_seed.dtstyle
# expect: file exists, non-empty (a few hundred bytes)

head -c 500 vocabulary/packs/expressive-baseline/_seeds/bw_convert_seed.dtstyle
# expect: <darktable_style ...> with <plugin>...<operation>channelmixerrgb</operation>... in it

grep -c '<operation>channelmixerrgb</operation>' \
  vocabulary/packs/expressive-baseline/_seeds/bw_convert_seed.dtstyle
# expect: 1
```

If `grep` returns `0`, the style didn't capture channelmixerrgb. Go back to step 2.6 and make sure the module is **enabled with non-default values** *before* you compress history. Default-state modules don't get included in styles.

### Step 4 — hand off to a Claude session

Start a new Claude Code session in this repo. Paste this prompt:

```
Pick up GH issue #63 (milestone v1.5.1). The seed dtstyle is at
vocabulary/packs/expressive-baseline/_seeds/bw_convert_seed.dtstyle.

Decode the channelmixerrgb v3 struct against scripts/author-dtstyle.py
(add a channelmixerrgb section if it doesn't have one). Author three
variants by varying the grey[4] floats:

  - bw_convert     (neutral B&W mix)
  - bw_sky_drama   (blue-channel emphasis — darkens skies)
  - bw_foliage     (green-channel emphasis — lifts foliage)

Add manifest entries in vocabulary/packs/expressive-baseline/manifest.json
(layer L3, subtype channelmixerrgb, modversion 3, source expressive-baseline,
license MIT). Place the dtstyle files at
vocabulary/packs/expressive-baseline/layers/L3/channelmixerrgb/<name>.dtstyle.

Run tests/e2e/expressive/test_path_a_bw.py until all three variants pass
the channel_spread direction-of-change assertion. Then close #63 in the
closing commit and update CHANGELOG.md with a v1.5.1 entry.
```

That session needs real darktable on the path (for the e2e tests). You don't need to babysit it — it'll either succeed or come back with a clear blocker.

### Step 5 — when the Claude session is done, sanity-check

```bash
ls vocabulary/packs/expressive-baseline/layers/L3/channelmixerrgb/
# expect: bw_convert.dtstyle, bw_sky_drama.dtstyle, bw_foliage.dtstyle

uv run pytest tests/e2e/expressive/test_path_a_bw.py -v
# expect: 3 passed

gh issue view 63 --json state -q .state
# expect: CLOSED

gh issue list --milestone "v1.5.1"
# expect: empty (both #62 and #63 closed)
```

### Step 6 — close v1.5.1 milestone + tag + release

If everything passes, close the milestone and ship v1.5.1:

```bash
# Close the milestone (replace 11 if the URL above showed a different number)
gh api -X PATCH repos/chipi/chemigram/milestones/11 -f state=closed

# Tag and push
git tag v1.5.1 -m "v1.5.1 — channelmixerrgb B&W trio + #62 close-as-retired"
git push origin v1.5.1

# GH release
gh release create v1.5.1 --title "v1.5.1 — channelmixerrgb B&W trio" \
  --notes-from-tag
# (or paste a longer notes body — the Claude session that ships #63 will
# already have updated CHANGELOG.md with the right summary)
```

You can also let the Claude session do these — just say "tag and release v1.5.1 when the trio passes" in the handoff prompt.

---

## What if something goes wrong

**The seed dtstyle doesn't contain channelmixerrgb.** Module wasn't enabled or had default values when you compressed history. Re-do step 2 — make sure the preview *visibly* changes (image goes B&W) before compressing.

**`darktable` not on path.** It's installed but not symlinked. On macOS the binary is usually inside the app bundle: `/Applications/darktable.app/Contents/MacOS/darktable`. You can either symlink it (`ln -s ... /usr/local/bin/darktable`) or just open the .app from Finder for the GUI part — only step 5 needs the binary on path, and you can set `CHEMIGRAM_DT_CONFIGDIR` + `PATH` for that step alone.

**The Claude session's struct decode fails.** The seed is your insurance. The session can show you the hex bytes and you can use darktable to verify the layout against known-good values. Worst case: log it as a follow-up and ship v1.5.1 with #62 closed only.

**Tests pass but the visuals look wrong.** That's vocabulary judgment, not architecture. The test asserts direction-of-change; the *aesthetic* result is yours to judge. If `bw_sky_drama` doesn't actually darken the sky enough, tweak the grey[blue] float and re-run.

---

*This guide ships in the repo at `docs/guides/closing-62-and-63.md` so you can re-read it anytime. Once v1.5.1 is shipped it can be deleted.*
