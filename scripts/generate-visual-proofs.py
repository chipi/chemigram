#!/usr/bin/env python3
"""Generate visual before/after proofs for every vocabulary entry.

For each entry in ``starter`` + ``expressive-baseline``: render the
synthetic ColorChecker PNG and the synthetic grayscale ramp through the
entry's dtstyle, save as small JPEGs under ``docs/visual-proofs/``, and
regenerate ``docs/guides/visual-proofs.md`` with a side-by-side gallery.

Mask-bound entries (``mask_spec`` set) route through the drawn-mask apply
path per ADR-076, so the gallery shows the spatial effect of each mask
form on the chart inputs.

Usage::

    uv run python scripts/generate-visual-proofs.py

Requires ``CHEMIGRAM_DT_CONFIGDIR`` set (or ``~/chemigram-phase0/dt-config``
exists). Render time: ~1-2 sec per output for 2 inputs across ~39 entries,
roughly 2 minutes total.

Output:

- ``docs/visual-proofs/baseline-{colorchecker,grayscale}.jpg`` - the
  reference targets rendered through the baseline XMP only.
- ``docs/visual-proofs/<pack>/<entry-name>-{colorchecker,grayscale}.jpg`` -
  one render per entry per input.
- ``docs/guides/visual-proofs.md`` - the gallery page, regenerated.

CI is intentionally **not** wired to regenerate this - darktable-cli isn't
on CI runners. The gallery lives in-repo and gets refreshed by hand when
vocabulary changes (typical cadence: vocabulary-authoring evenings).
"""

from __future__ import annotations

import dataclasses
import os
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from chemigram.core.helpers import apply_with_drawn_mask  # noqa: E402
from chemigram.core.pipeline import render  # noqa: E402
from chemigram.core.vocab import load_packs  # noqa: E402
from chemigram.core.xmp import parse_xmp, synthesize_xmp, write_xmp  # noqa: E402

# We deliberately use an EMPTY baseline (zero history entries) for the
# gallery. The shipped baseline XMP (`_baseline_v1.xmp`) has 11 history
# entries including sigmoid + colorbalancergb defaults that mangle
# display-referred sRGB chart input through scene-referred tone mapping -
# producing a magenta cast on the rendered baseline. Combined with
# darktable-cli's `--apply-custom-presets false` (which chemigram's
# DarktableCliStage already passes), an empty baseline gives a faithful
# chart render: input color profile + output color profile only, no
# scene-referred transforms.
#
# The trade-off: this baseline is intended ONLY for the chart-input
# fixture path. Production raw renders use the regular `_baseline_v1.xmp`
# because raws DO require the full scene-referred pipeline to render
# correctly. The gallery's job is per-primitive isolation visualization,
# not production-render simulation.
_BASELINE_TEMPLATE_XMP = REPO / "src/chemigram/core/_baseline_v1.xmp"
COLORCHECKER = REPO / "tests/fixtures/reference-targets/colorchecker_synthetic_srgb.png"
GRAYSCALE = REPO / "tests/fixtures/reference-targets/grayscale_synthetic_linear.png"
PROOFS_DIR = REPO / "docs/visual-proofs"
GALLERY_PAGE = REPO / "docs/guides/visual-proofs.md"

# Render at modest size — enough to see the effect, small enough to keep
# the committed footprint tight.
RENDER_WIDTH = 400
RENDER_HEIGHT = 400


@dataclass(frozen=True)
class RenderTarget:
    """One reference input + display name + output filename slug."""

    path: Path
    label: str
    slug: str


TARGETS = (
    RenderTarget(COLORCHECKER, "ColorChecker", "colorchecker"),
    RenderTarget(GRAYSCALE, "Grayscale ramp", "grayscale"),
)


def _resolve_configdir() -> Path:
    raw = os.environ.get("CHEMIGRAM_DT_CONFIGDIR")
    if raw:
        return Path(raw).expanduser()
    fallback = Path.home() / "chemigram-phase0" / "dt-config"
    if fallback.exists():
        return fallback
    raise RuntimeError(
        "CHEMIGRAM_DT_CONFIGDIR not set and ~/chemigram-phase0/dt-config "
        "doesn't exist. Set CHEMIGRAM_DT_CONFIGDIR to a pre-bootstrapped "
        "darktable configdir (open the GUI once, quit, that bootstraps it)."
    )


def _render_one(input_path: Path, xmp_path: Path, output_path: Path, configdir: Path) -> bool:
    """Render one input through one xmp; True on success."""
    result = render(
        raw_path=input_path,
        xmp_path=xmp_path,
        output_path=output_path,
        width=RENDER_WIDTH,
        height=RENDER_HEIGHT,
        high_quality=False,
        configdir=configdir,
    )
    if not result.success:
        print(f"  ✗ render failed: {result.error_message}", file=sys.stderr)
    return result.success


def _synthesize_for_entry(baseline, entry):
    """Build the XMP that applies entry to baseline.

    Mask-bound entries (`mask_spec` set) route through `apply_with_drawn_mask`;
    others go through the plain `synthesize_xmp` path.
    """
    if entry.mask_spec is not None:
        return apply_with_drawn_mask(baseline, entry.dtstyle, entry.mask_spec)
    return synthesize_xmp(baseline, [entry.dtstyle])


def render_all(configdir: Path) -> dict[str, dict[str, Path]]:
    """Render baseline + every entry against every target. Returns
    ``{entry_name: {target_slug: output_path}}`` plus a special
    ``"baseline"`` key for the unmodified-baseline renders.
    """
    PROOFS_DIR.mkdir(parents=True, exist_ok=True)
    # Empty-history baseline — see _BASELINE_TEMPLATE_XMP comment above
    template = parse_xmp(_BASELINE_TEMPLATE_XMP)
    baseline = dataclasses.replace(template, history=())

    rendered: dict[str, dict[str, Path]] = {"baseline": {}}

    # 1) Baseline (no primitive applied) — the "before" reference for all rows
    print("rendering baseline (no primitive applied)…")
    baseline_xmp_path = PROOFS_DIR / "_baseline.xmp"
    write_xmp(baseline, baseline_xmp_path)
    for target in TARGETS:
        out = PROOFS_DIR / f"baseline-{target.slug}.jpg"
        if not _render_one(target.path, baseline_xmp_path, out, configdir):
            raise RuntimeError(f"baseline render failed for {target.slug}")
        rendered["baseline"][target.slug] = out
    baseline_xmp_path.unlink()
    print("  ✓ baseline done")

    # 2) Every vocabulary entry against both targets
    vocab = load_packs(["starter", "expressive-baseline"])
    for entry in vocab.list_all():
        # Pack root for output organization
        pack_root = vocab.pack_for(entry.name)
        pack_name = pack_root.name if pack_root else "unknown"
        entry_dir = PROOFS_DIR / pack_name
        entry_dir.mkdir(parents=True, exist_ok=True)

        print(f"rendering {pack_name}/{entry.name}…")
        try:
            applied_xmp = _synthesize_for_entry(baseline, entry)
        except Exception as exc:
            print(f"  ✗ synthesize failed: {exc}", file=sys.stderr)
            continue

        xmp_path = entry_dir / f"_{entry.name}.xmp"
        write_xmp(applied_xmp, xmp_path)

        rendered.setdefault(entry.name, {})
        for target in TARGETS:
            out = entry_dir / f"{entry.name}-{target.slug}.jpg"
            if _render_one(target.path, xmp_path, out, configdir):
                rendered[entry.name][target.slug] = out
        xmp_path.unlink(missing_ok=True)

    return rendered


def render_gallery_md(rendered: dict[str, dict[str, Path]]) -> str:
    """Build the markdown gallery page from rendered outputs."""
    vocab = load_packs(["starter", "expressive-baseline"])

    # Group entries by pack for the gallery
    by_pack: dict[str, list] = {}
    for entry in vocab.list_all():
        if entry.name not in rendered:
            continue
        pack_root = vocab.pack_for(entry.name)
        pack_name = pack_root.name if pack_root else "unknown"
        by_pack.setdefault(pack_name, []).append(entry)

    lines: list[str] = []

    # Header + baseline reference at top
    lines.append("# Visual proofs — vocabulary-entry before/after gallery\n")
    lines.append(
        "> Side-by-side renders of the synthetic ColorChecker chart and the "
        "synthetic grayscale ramp, before and after each vocabulary entry. "
        "For human visual validation: does each primitive *visibly* do what "
        "its description claims?\n"
    )
    lines.append(
        "> Renders use an **empty-history baseline** + "
        "``--apply-custom-presets false`` so the chart passes through the "
        "darktable pipeline cleanly (input profile → output profile only, "
        "no scene-referred tone mapping). Each primitive is then applied "
        "in isolation — the only difference between baseline and per-entry "
        "renders is *that primitive's effect*. This lets you eyeball each "
        "primitive against the reference chart and verify it does what "
        "its description claims.\n"
    )
    lines.append(
        "> Production raw renders use the full ``_baseline_v1.xmp`` "
        "with sigmoid + colorbalancergb defaults — that path is correct "
        "for raws. The empty-baseline trick is specifically for chart-input "
        "isolation testing; it would not be appropriate for editing real "
        "photographs.\n"
    )
    lines.append(
        "> **Auto-generated.** Regenerate via "
        "``uv run python scripts/generate-visual-proofs.py`` "
        "after vocabulary changes. Commit the regenerated images "
        "alongside any vocabulary commit so the gallery and the "
        "manifest stay in sync.\n"
    )
    lines.append(
        f"> Render size: {RENDER_WIDTH}x{RENDER_HEIGHT}, JPEG quality default. "
        f"Inputs: synthetic targets from "
        f"[`tests/fixtures/reference-targets/`]"
        f"(../../tests/fixtures/reference-targets/README.md).\n"
    )

    lines.append("---\n")
    lines.append("## Baseline reference\n")
    lines.append(
        "These are the reference targets rendered through the baseline XMP "
        "with no primitive applied — the *before* state every row below "
        "compares against.\n"
    )
    lines.append("| ColorChecker | Grayscale ramp |")
    lines.append("|-|-|")
    base = rendered["baseline"]
    cc_rel = base["colorchecker"].relative_to(GALLERY_PAGE.parent.parent)
    gs_rel = base["grayscale"].relative_to(GALLERY_PAGE.parent.parent)
    lines.append(f"| ![baseline ColorChecker](../{cc_rel}) | ![baseline grayscale](../{gs_rel}) |")
    lines.append("")
    lines.append("---\n")

    # One section per pack, then per entry
    for pack_name in ("starter", "expressive-baseline"):
        if pack_name not in by_pack:
            continue
        entries = by_pack[pack_name]
        lines.append(f"## `{pack_name}` pack ({len(entries)} entries)\n")

        for entry in entries:
            outs = rendered[entry.name]
            cc = outs.get("colorchecker")
            gs = outs.get("grayscale")
            if cc is None and gs is None:
                continue

            mask_marker = " 🟦 mask-bound" if entry.mask_spec is not None else ""
            lines.append(f"### `{entry.name}`{mask_marker}\n")
            lines.append(f"_{entry.description}_\n")

            cc_rel = cc.relative_to(GALLERY_PAGE.parent.parent) if cc else None
            gs_rel = gs.relative_to(GALLERY_PAGE.parent.parent) if gs else None
            lines.append("| ColorChecker | Grayscale ramp |")
            lines.append("|-|-|")
            cc_md = f"![{entry.name} ColorChecker](../{cc_rel})" if cc_rel else "_(render failed)_"
            gs_md = f"![{entry.name} grayscale](../{gs_rel})" if gs_rel else "_(render failed)_"
            lines.append(f"| {cc_md} | {gs_md} |")
            lines.append("")

        lines.append("---\n")

    # Footer
    lines.append("## Notes\n")
    lines.append(
        "- **Inputs are sRGB PNGs**, not raw files. darktable processes "
        "them through its non-raw path — input color profile applies, "
        "demosaic does not. Some primitives (e.g., raw-aware white-balance "
        "moves) behave differently from how they would on a real raw. The "
        "gallery is for *visual response validation*, not pipeline "
        "calibration; for raw-pipeline direction-of-change validation see "
        "the e2e suite in [`tests/e2e/`](../../tests/e2e/).\n"
    )
    lines.append(
        "- **Mask-bound entries** (gradient/ellipse/rectangle, marked "
        "🟦 above) route through the drawn-mask apply path per ADR-076. "
        "The mask geometry encodes into the XMP's `masks_history`; you "
        "see the spatial shaping in the rendered chart.\n"
    )
    lines.append(
        "- **Out-of-gamut patches** on the ColorChecker (notably patch #18 "
        "Cyan) clip to nearest in-gamut sRGB; that clipping is in the input, "
        "not the primitive. See "
        "[`reference-targets/README.md`](../../tests/fixtures/reference-targets/README.md).\n"
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    print("Generating visual proofs gallery…")
    print("Inputs:")
    print(f"  ColorChecker: {COLORCHECKER}")
    print(f"  Grayscale:    {GRAYSCALE}")
    print(f"Output dir:   {PROOFS_DIR}")
    print(f"Gallery page: {GALLERY_PAGE}")
    print()

    if not COLORCHECKER.exists() or not GRAYSCALE.exists():
        print("ERROR: reference-target inputs missing.", file=sys.stderr)
        return 2

    configdir = _resolve_configdir()
    print(f"darktable configdir: {configdir}")
    print()

    rendered = render_all(configdir)
    page = render_gallery_md(rendered)
    GALLERY_PAGE.write_text(page, encoding="utf-8")

    n_entries = len(rendered) - 1  # subtract baseline
    n_renders = sum(len(v) for v in rendered.values())
    print()
    print(f"Done. {n_entries} entries by ~2 targets = {n_renders} renders + baseline.")
    print(f"Gallery page: {GALLERY_PAGE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
