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

from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from chemigram.core.helpers import apply_entry, apply_with_drawn_mask  # noqa: E402
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
CLIPPED_GRADIENT = REPO / "tests/fixtures/reference-targets/clipped_gradient_synthetic.png"
# Real-raw fixture for entries that need a working color-management
# chain (e.g. HSL via colorequal). When the file is missing, those
# entries fall back to the documented placeholder row in the gallery
# md (#103 mechanism). See tests/fixtures/raws/README.md for fixture
# conventions + license expectations.
REAL_RAW_FIXTURE = REPO / "tests/fixtures/raws/iguana_galapagos.jpg"
PROOFS_DIR = REPO / "docs/visual-proofs"
GALLERY_PAGE = REPO / "docs/guides/visual-proofs.md"

# Render at modest size — enough to see the effect, small enough to keep
# the committed footprint tight.
RENDER_WIDTH = 400
RENDER_HEIGHT = 400

# Centered ellipse used to demonstrate "any global primitive can be
# applied through a mask." Renders alongside the global version for
# every non-mask-bound entry so the gallery shows mask localization
# visually. Same geometry as `tests/e2e/test_lab_grade_masked_universality`.
DEMO_MASK_SPEC = {
    "dt_form": "ellipse",
    "dt_params": {
        "center_x": 0.5,
        "center_y": 0.5,
        "radius_x": 0.2,
        "radius_y": 0.2,
        "border": 0.05,
    },
}

# Mean per-pixel diff (0..255 scale) below which we consider a render
# "near baseline" (= no visible change). Annotated inline with a
# reason from `_NEAR_BASELINE_NOTES`.
_NEAR_BASELINE_DIFF_THRESHOLD = 2.0

# Subtypes whose drawn-mask binding doesn't render usefully — suppress
# the masked column entirely. Value is the anchor in
# `mask-applicable-controls.md` the inline note links back to.
#
# - `wb` (temperature module): empirically `global == masked`
#   (0.000 mean diff between them, ~32 from baseline). darktable
#   processes temperature before colorin in the pipeline; the drawn-
#   mask binding doesn't apply to pre-input-profile data.
# - `vignette`: vignette intensity is ~0 at frame center where the
#   demo mask = 1, and ~1 at edges where mask = 0. The two geometries
#   cancel; result ≈ baseline. The matrix in mask-applicable-controls
#   already flags this as a "don't" combo.
_SUPPRESS_MASKED_SUBTYPES: dict[str, str] = {
    "wb": "temperature",
    "vignette": "vignette",
}

# Tags meaning "pure color / chroma move." Gray patches have zero
# chroma; multiplying or shifting zero is still zero. Suppress the
# grayscale column (both global and masked) for entries with any of
# these tags.
_SKIP_GRAYSCALE_TAGS: set[str] = {"saturation", "chroma", "vibrance"}

# Entries whose photographic effect requires real-raw input (working-
# profile RGB after a real input profile + EXIF + camera-aware color
# management). On the synthetic ColorChecker / grayscale fixtures, the
# darktable pipeline produces degenerate output for these — not because
# the apply path is wrong (the byte-level patches and the 5-layer test
# coverage per ADR-080 verify correctness), but because the underlying
# darktable module's algorithm is incompatible with the chart's
# already-baked-sRGB-as-input shape.
#
# These entries DO work on real raw photographs; their visual proofs
# need to be captured on real fixtures (a v1.9.0+ work item — possibly
# an extension to the visual-proofs script that swaps in a real raw
# fixture for these). Until then, the entries are skipped from the
# synthetic-chart gallery to avoid publishing broken output as if it
# were correct.
_SKIP_VISUAL_PROOF_ENTRIES: set[str] = {
    # HSL Color Mixer — colorequal mv4 needs the full input-profile +
    # working-profile chain that the synthetic chart doesn't provide.
    # The pipeline produces degenerate dark output on flat patches
    # regardless of axis values or global tuning. Verified by
    # experimenting with use_filter / param_size / chroma_size
    # adjustments — none recover the chart pipeline. (RFC-023 / ADR-083
    # entries; commit 1b5db21 ship.)
    "hsl_saturation",
    "hsl_hue",
    "hsl_luminance",
}

# Subtypes that render against the **clipped-gradient** fixture in
# addition to the default cc + grayscale targets. The colorchecker24
# and grayscale-ramp fixtures don't carry the signal these modules
# operate on (no blown highlights to recover; no continuous tone for
# grain texture to ride on). The clipped fixture has both: a vertical
# 0..255 gradient in the top half + a 60% clipped band on the bottom.
# See tests/fixtures/reference-targets/README.md for the layout.
_EXTRA_CLIPPED_FIXTURE_SUBTYPES: set[str] = {"highlights", "grain"}

# Per-parameter sweep values for the parameter-sweep gallery rows. Maps
# a parameter name to the list of values to render. The first value
# is treated as the "baseline" of the sweep (typically 0 / default).
# When an entry's ``parameters`` block declares a parameter we know
# how to sweep, the gallery emits one row PER axis showing the entry
# rendered at each value side-by-side. For multi-parameter entries
# (RFC-022 Tier 2: temperature, crop, toneequalizer), each parameter
# gets its own sweep row; the swept axis varies, others held at the
# dtstyle's encoded defaults via the parameterized apply path's
# partial-update semantics. Closes #84.
_PARAMETER_SWEEP_VALUES: dict[str, list[float]] = {
    # ----- Single-axis Phase 4 entries -----
    "ev": [-1.0, -0.5, 0.0, 0.5, 1.0],
    "brightness": [-0.8, -0.5, -0.25, 0.0],
    "saturation_global": [-1.0, -0.5, 0.0, 0.25, 0.5],
    "contrast": [0.5, 1.0, 1.5, 2.0, 2.5],
    "clarity_strength": [-0.5, 0.0, 0.5, 1.5, 2.5],
    "grain_strength": [0.0, 8.0, 25.0, 50.0, 100.0],
    "clip_threshold": [0.5, 0.85, 0.95, 1.0, 1.5],
    # ----- dehaze (hazeremoval): 2 axes (#90 Bucket A.2) -----
    "strength": [-0.4, 0.0, 0.2, 0.6, 1.0],
    "distance": [0.0, 0.2, 0.5, 0.8, 1.0],
    # ----- texture (diffuse-or-sharpen): 3 axes (#92 Bucket A.6) -----
    "first": [-0.5, -0.2, 0.0, 0.3, 0.7],
    "second": [-0.3, 0.0, 0.3, 0.6, 1.0],
    "sharpness": [-0.5, 0.0, 0.3, 0.6, 1.0],
    # ----- HSL Color Mixer (colorequal): 24 axes total, RFC-023 -----
    # Per the closing RFC's open question (visual-proof sweep coverage scope),
    # ship one representative axis per HSL channel at v1.8.0; the remaining
    # 21 axes can be added as gaps surface. Saturation is the most-used HSL
    # axis so sat_blue gets a sweep; hue_green covers foliage warmth; bright_blue
    # covers sky-deepening — three of the most common Lightroom HSL moves.
    "sat_blue": [-0.5, -0.2, 0.0, 0.3, 0.6],
    "hue_green": [-30.0, -10.0, 0.0, 15.0, 30.0],
    "bright_blue": [-0.6, -0.3, 0.0, 0.2, 0.5],
    # ----- filmic v6 (filmicrgb mv6): 8 axes (#97) -----
    # `contrast` is shared with sigmoid (different default but compatible
    # range); other axes are filmic-specific.
    "grey_point_source": [10.0, 18.45, 25.0, 35.0],
    "black_point_source": [-12.0, -10.0, -8.0, -5.0],
    "white_point_source": [2.0, 4.0, 6.0, 8.0],
    "output_power": [1.0, 2.0, 4.0, 6.0],
    "latitude": [0.0, 10.0, 25.0, 50.0],
    "saturation": [-50.0, 0.0, 25.0, 50.0],
    "balance": [-25.0, -10.0, 0.0, 10.0, 25.0],
    # ----- denoise (denoiseprofile mv12): 4 axes (#96) -----
    # Axis names use the denoise_ prefix to disambiguate from dehaze.strength etc.
    "denoise_strength": [0.5, 1.0, 2.0, 5.0, 20.0],
    "denoise_shadows": [0.0, 0.5, 1.0, 1.4, 1.8],
    "denoise_radius": [0.0, 1.0, 3.0, 6.0, 10.0],
    "denoise_scattering": [0.0, 1.0, 5.0, 10.0, 20.0],
    # ----- lens correction (lens mv10): 10 axes (#95) -----
    # Axis names use lens_ prefix for disambiguation. Photographic effect
    # depends on lensfun camera/lens identifier strings being populated
    # (EXIF auto-binding follow-up); sweeps still verify the apply path
    # bytes-correctness.
    "lens_scale": [0.0, 1.0, 1.5, 2.0],
    # TCA values use 0.02 spacing so 2-decimal slugs stay distinct
    # (0.995 and 1.005 both round to "+1.00" in the slugger).
    "lens_tca_r": [0.98, 0.99, 1.0, 1.01, 1.02],
    "lens_tca_b": [0.98, 0.99, 1.0, 1.01, 1.02],
    "lens_cor_distortion": [0.0, 0.3, 0.6, 1.0],
    "lens_cor_vignette": [0.0, 0.3, 0.6, 1.0],
    "lens_cor_ca_r": [-1.0, 0.0, 1.0],
    "lens_cor_ca_b": [-1.0, 0.0, 1.0],
    "lens_v_strength": [-0.5, 0.0, 0.5, 1.0],
    "lens_v_radius": [0.5, 1.0, 2.0],
    "lens_v_steepness": [0.5, 1.0, 2.5, 5.0],
    # ----- transform (ashift mv5): 5 axes (#101) -----
    "transform_rotation": [-15.0, -5.0, 0.0, 5.0, 15.0],
    "transform_lensshift_v": [-0.5, -0.2, 0.0, 0.2, 0.5],
    "transform_lensshift_h": [-0.5, -0.2, 0.0, 0.2, 0.5],
    "transform_shear": [-0.3, 0.0, 0.3],
    "transform_aspect": [0.7, 0.9, 1.0, 1.2, 1.5],
    # ----- wb_kelvin_delta (#102): UX wrapper on temperature -----
    "kelvin_delta": [-3000.0, -1500.0, 0.0, 1500.0, 3000.0],
    "tint_delta": [-200.0, -100.0, 0.0, 100.0, 200.0],
    # ----- temperature: 3 axes (RFC-022 Tier 2 + #90 Bucket A.3 tint) -----
    "red_coeff": [0.5, 1.0, 1.5, 2.148],
    "green_coeff": [0.85, 0.95, 1.0, 1.15, 1.3],
    "blue_coeff": [0.5, 1.0, 1.5, 2.137],
    # ----- crop: 4 axes (RFC-022 Tier 2) -----
    "cx": [0.0, 0.1, 0.2, 0.3],
    "cy": [0.0, 0.1, 0.2, 0.3],
    "cw": [0.7, 0.8, 0.9, 1.0],
    "ch": [0.7, 0.8, 0.9, 1.0],
    # ----- single-axis Tier 2 entries -----
    "amount": [0.0, 0.5, 1.0, 1.5, 2.0],
    "vibrance": [-0.5, 0.0, 0.3, 0.6, 1.0],
    "chroma_global": [-0.5, 0.0, 0.3, 0.6, 1.0],
    "hue_angle": [-90.0, -30.0, 0.0, 30.0, 90.0],
    # ----- #91 Bucket A.5: colorbalancergb per-zone hue/sat + blending/balance -----
    "hue_shadows": [0.0, 90.0, 180.0, 270.0, 350.0],
    "hue_midtones": [0.0, 90.0, 180.0, 270.0, 350.0],
    "hue_highlights": [0.0, 90.0, 180.0, 270.0, 350.0],
    "saturation_shadows": [-0.5, 0.0, 0.3, 0.5, 1.0],
    "saturation_midtones": [-0.5, 0.0, 0.3, 0.5, 1.0],
    "saturation_highlights": [-0.5, 0.0, 0.3, 0.5, 1.0],
    "shadows_weight": [0.0, 0.5, 1.0, 2.0, 4.0],
    "highlights_weight": [0.0, 0.5, 1.0, 2.0, 4.0],
    "white_fulcrum": [-1.0, -0.5, 0.0, 0.5, 1.0],
    # ----- toneequalizer: 9 axes (RFC-022 Tier 2; deepest stress test) -----
    # Each band gets a row spanning EV ± 1.5; the 5-value sweep covers the
    # photographically meaningful range for that band's typical use.
    "noise": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "ultra_deep_blacks": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "deep_blacks": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "blacks": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "shadows": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "midtones": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "highlights": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "whites": [-1.5, -0.5, 0.0, 0.5, 1.5],
    "speculars": [-1.5, -0.5, 0.0, 0.5, 1.5],
    # ----- colorbalancergb brilliance axes (#86) -----
    "brilliance_global": [-0.5, 0.0, 0.3, 0.6, 1.0],
    "brilliance_highlights": [-0.5, 0.0, 0.3, 0.6, 1.0],
    "brilliance_midtones": [-0.5, 0.0, 0.3, 0.6, 1.0],
    "brilliance_shadows": [-0.5, 0.0, 0.3, 0.6, 1.0],
}

# Subtypes / contexts where the engine renders correctly but the chart
# is a poor signal medium. We render but annotate inline. Keys are
# `entry.subtype` first, then the special key `_masked_sigmoid` for
# masked sigmoid entries (small mask area x tone curve = small visible
# delta, expected behavior).
_NEAR_BASELINE_NOTES: dict[str, str] = {
    "highlights": (
        "this chart has no blown highlights to recover — "
        "see the **clipped-gradient row below** for the visible effect, "
        "or [mask-applicable-controls](mask-applicable-controls.md#highlights)"
    ),
    "grain": (
        "grain texture is hard to see on flat chart patches — "
        "see the **clipped-gradient row below** for visible texture, "
        "or [mask-applicable-controls](mask-applicable-controls.md#grain)"
    ),
    "vignette": (
        "subtle vignette is small at the modest gallery render size; "
        "effect is concentrated at the very corners of the frame"
    ),
    "_masked_sigmoid": (
        "16% mask area x tone curve = small visible effect "
        "(engine works correctly; chart just shows a faint signal)"
    ),
}


def _should_skip_masked(entry) -> str | None:
    """Return the anchor in mask-applicable-controls.md if the masked
    column should be suppressed for this entry, else None."""
    return _SUPPRESS_MASKED_SUBTYPES.get(entry.subtype)


def _should_skip_target(entry, target_slug: str) -> bool:
    """True if a particular target render should be suppressed for this
    entry (e.g., color-only entries on the grayscale chart)."""
    if target_slug == "grayscale" and (set(entry.tags) & _SKIP_GRAYSCALE_TAGS):
        return True
    return False


def _mean_pixel_diff(a: Path, b: Path) -> float:
    """Mean per-pixel absolute RGB difference (0..255 scale).

    Used to detect renders that are visually indistinguishable from
    baseline so the gallery can annotate them inline with a reason
    rather than silently presenting an unchanged image.
    """
    img_a = Image.open(a).convert("RGB")
    img_b = Image.open(b).convert("RGB")
    diff = ImageChops.difference(img_a, img_b)
    hist = diff.histogram()
    n = sum(hist)
    if n == 0:
        return 0.0
    total = 0.0
    for ch in range(3):
        for v in range(256):
            total += v * hist[ch * 256 + v]
    return total / n


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

# Real-raw target for entries that fail on the synthetic chart pipeline
# (e.g. HSL via colorequal — see _SKIP_VISUAL_PROOF_ENTRIES). Used as a
# replacement for TARGETS, not in addition: skip-listed entries render
# against the real raw INSTEAD of the synthetic chart.
REAL_RAW_TARGET = RenderTarget(REAL_RAW_FIXTURE, "Real raw", "realraw")


def _real_raw_fixture_available() -> bool:
    """True when the real-raw fixture file exists on disk; the script
    falls back to the placeholder text when it's missing so the gallery
    still builds without the fixture committed."""
    return REAL_RAW_FIXTURE.exists()


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


def _synthesize_for_entry_demo_masked(baseline, entry):
    """Build the XMP that applies entry to baseline through a centered
    ellipse mask. Used to demonstrate "any global primitive can be
    masked"; only meaningful for non-mask-bound entries (the 4 already-
    mask-bound entries don't get a demo render since their own
    ``mask_spec`` is the demonstration).
    """
    return apply_with_drawn_mask(baseline, entry.dtstyle, DEMO_MASK_SPEC)


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
        _render_entry(entry, vocab, baseline, configdir, rendered)

    return rendered


def _render_entry(entry, vocab, baseline, configdir, rendered: dict) -> None:
    """Render one vocab entry against every target plus the demo-masked
    variant (when applicable). Mutates ``rendered`` in place. Errors are
    logged and skipped so a single broken entry doesn't fail the whole run.

    Honors routing decisions from :data:`_SUPPRESS_MASKED_SUBTYPES` and
    :func:`_should_skip_target`: skipped renders store a sentinel
    ``"skipped"`` (target) or set ``_masked_skip_reason`` (whole masked
    column) so the markdown emit can render the right layout. Pixel
    diff vs baseline is computed for every emitted JPEG and stored as
    ``{slug}_diff`` for inline near-baseline annotation.
    """
    pack_root = vocab.pack_for(entry.name)
    pack_name = pack_root.name if pack_root else "unknown"
    entry_dir = PROOFS_DIR / pack_name
    entry_dir.mkdir(parents=True, exist_ok=True)

    if entry.name in _SKIP_VISUAL_PROOF_ENTRIES:
        if _real_raw_fixture_available():
            # Render this entry against the real raw fixture instead of
            # the synthetic chart targets. The byte-level apply path is
            # the same; only the input differs.
            print(f"rendering {pack_name}/{entry.name} against real raw…")
            try:
                applied_xmp = _synthesize_for_entry(baseline, entry)
            except Exception as exc:
                print(f"  ✗ synthesize failed: {exc}", file=sys.stderr)
                return
            xmp_path = entry_dir / f"_{entry.name}.xmp"
            write_xmp(applied_xmp, xmp_path)
            rendered.setdefault(entry.name, {})
            out = entry_dir / f"{entry.name}-{REAL_RAW_TARGET.slug}.jpg"
            if _render_one(REAL_RAW_TARGET.path, xmp_path, out, configdir):
                rendered[entry.name][REAL_RAW_TARGET.slug] = out
                rendered[entry.name]["__real_raw_only"] = True
            xmp_path.unlink(missing_ok=True)
            # Also produce parameter sweeps against the real raw if the
            # entry is parameterized — the sweep emit will pick up the
            # __real_raw_only flag and render against REAL_RAW_TARGET.
            _render_parameter_sweep(entry, baseline, entry_dir, configdir, rendered, {})
            return
        # No fixture: documented placeholder row instead of broken render.
        rendered.setdefault(entry.name, {})
        rendered[entry.name]["__visual_proof_skip"] = True
        print(
            f"skipping {pack_name}/{entry.name} "
            f"(real-raw fixture missing; see tests/fixtures/raws/README.md)"
        )
        return

    print(f"rendering {pack_name}/{entry.name}…")
    try:
        applied_xmp = _synthesize_for_entry(baseline, entry)
    except Exception as exc:
        print(f"  ✗ synthesize failed: {exc}", file=sys.stderr)
        return

    xmp_path = entry_dir / f"_{entry.name}.xmp"
    write_xmp(applied_xmp, xmp_path)
    rendered.setdefault(entry.name, {})
    baseline_paths = rendered["baseline"]
    for target in TARGETS:
        if _should_skip_target(entry, target.slug):
            rendered[entry.name][target.slug] = "skipped"
            continue
        out = entry_dir / f"{entry.name}-{target.slug}.jpg"
        if _render_one(target.path, xmp_path, out, configdir):
            rendered[entry.name][target.slug] = out
            rendered[entry.name][f"{target.slug}_diff"] = _mean_pixel_diff(
                out, baseline_paths[target.slug]
            )
    xmp_path.unlink(missing_ok=True)

    _render_masked_variant(entry, baseline, entry_dir, configdir, rendered, baseline_paths)
    _render_clipped_fixture(entry, baseline, entry_dir, configdir, rendered)
    _render_parameter_sweep(entry, baseline, entry_dir, configdir, rendered, baseline_paths)


def _render_parameter_sweep(
    entry, baseline, entry_dir: Path, configdir: Path, rendered: dict, baseline_paths: dict
) -> None:
    """For parameterized entries (RFC-021/RFC-022), render the entry at
    multiple parameter values side-by-side as "parameter sweep" rows in
    the gallery. The values come from :data:`_PARAMETER_SWEEP_VALUES`
    keyed by parameter name.

    Single-parameter entries get a one-axis sweep across the declared
    range. Multi-parameter entries (RFC-022 Tier 2: temperature, crop,
    toneequalizer) get one sweep row PER axis — the swept axis varies
    across its sweep recipe; the other axes are held at their dtstyle
    defaults via the parameterized apply path's partial-update semantics.

    Renders against the colorchecker target (the cleanest signal medium
    for tone deltas; vignette + grain etc. need different targets but
    those modules' sweep visualizations work fine on colorchecker).

    Each rendered axis writes a separate ``_sweep`` record under
    ``rendered[entry.name]["_sweeps"]`` (note: list, not dict). The
    markdown emit walks the list and emits one block per axis.
    """
    if entry.parameters is None:
        return

    # Real-raw-only entries (skip-listed; #103) sweep against the real
    # raw target instead of the synthetic colorchecker — colorequal etc.
    # need a working color-management chain.
    if rendered.get(entry.name, {}).get("__real_raw_only"):
        target_slug = REAL_RAW_TARGET.slug
        target_path = REAL_RAW_TARGET.path
    else:
        # Render against colorchecker only — tone deltas read cleanly there.
        target_slug = "colorchecker"
        target_path = COLORCHECKER

    rendered[entry.name].setdefault("_sweeps", [])
    sweeps: list[dict] = rendered[entry.name]["_sweeps"]

    for spec in entry.parameters:
        sweep_values = _PARAMETER_SWEEP_VALUES.get(spec.name)
        if sweep_values is None:
            # No sweep recipe for this parameter name; the entry still
            # renders at its default in the main row.
            continue

        axis_records: list[dict] = []
        for v in sweep_values:
            # Synthesize via the engine's parameterized apply path so we
            # exercise the same code the user/agent calls at apply time.
            # Multi-parameter entries: only this axis is patched; the
            # others stay at the dtstyle's encoded defaults.
            try:
                applied = apply_entry(baseline, entry, parameter_values={spec.name: v})
            except Exception as exc:
                print(f"  x sweep synthesize failed at {spec.name}={v}: {exc}", file=sys.stderr)
                continue
            v_label = f"{v:+.2f}" if v != 0 else "0.00"
            v_slug = v_label.replace("+", "p").replace("-", "n").replace(".", "_")
            # Include the axis name in the file slug so multi-parameter
            # entries don't collide (same value across different axes).
            xmp_path = entry_dir / f"_{entry.name}_sweep_{spec.name}_{v_slug}.xmp"
            out = entry_dir / f"{entry.name}-sweep-{spec.name}-{v_slug}.jpg"
            write_xmp(applied, xmp_path)
            if _render_one(target_path, xmp_path, out, configdir):
                axis_records.append(
                    {
                        "value": v,
                        "label": v_label,
                        "path": out,
                        "diff": _mean_pixel_diff(out, baseline_paths[target_slug]),
                    }
                )
            xmp_path.unlink(missing_ok=True)

        if axis_records:
            sweeps.append({"param": spec.name, "renders": axis_records})


def _render_clipped_fixture(
    entry, baseline, entry_dir: Path, configdir: Path, rendered: dict
) -> None:
    """Render the clipped-gradient fixture for entries whose subtype
    benefits from continuous-tone or blown-highlights signal that the
    colorchecker / grayscale-ramp fixtures don't carry.

    Writes a baseline render of the clipped fixture (once per script run)
    plus per-entry global + demo-masked variants. Stored under the slugs
    ``clipped``, ``clipped_masked``, and ``clipped_baseline`` so the
    markdown emit can render an extra row beneath the main 4-column block.
    """
    if entry.subtype not in _EXTRA_CLIPPED_FIXTURE_SUBTYPES:
        return

    # Render the clipped fixture's baseline once per script run.
    baseline_clipped = PROOFS_DIR / "baseline-clipped.jpg"
    if not baseline_clipped.exists():
        baseline_xmp_path = PROOFS_DIR / "_baseline_clipped.xmp"
        write_xmp(baseline, baseline_xmp_path)
        if not _render_one(CLIPPED_GRADIENT, baseline_xmp_path, baseline_clipped, configdir):
            print("  x baseline-clipped render failed; skipping clipped fixture", file=sys.stderr)
            baseline_xmp_path.unlink(missing_ok=True)
            return
        baseline_xmp_path.unlink(missing_ok=True)
    rendered["baseline"]["clipped"] = baseline_clipped

    # Global render against the clipped fixture.
    global_xmp_path = entry_dir / f"_{entry.name}_clipped.xmp"
    write_xmp(_synthesize_for_entry(baseline, entry), global_xmp_path)
    out = entry_dir / f"{entry.name}-clipped.jpg"
    if _render_one(CLIPPED_GRADIENT, global_xmp_path, out, configdir):
        rendered[entry.name]["clipped"] = out
        rendered[entry.name]["clipped_diff"] = _mean_pixel_diff(out, baseline_clipped)
    global_xmp_path.unlink(missing_ok=True)

    # Demo-masked variant against the clipped fixture (same ellipse as
    # the cc/grayscale demo masks).
    if entry.mask_spec is not None:
        return  # mask-bound entries don't get a demo-mask variant
    masked_xmp_path = entry_dir / f"_{entry.name}_clipped_masked.xmp"
    write_xmp(_synthesize_for_entry_demo_masked(baseline, entry), masked_xmp_path)
    out = entry_dir / f"{entry.name}-clipped-masked.jpg"
    if _render_one(CLIPPED_GRADIENT, masked_xmp_path, out, configdir):
        rendered[entry.name]["clipped_masked"] = out
        rendered[entry.name]["clipped_masked_diff"] = _mean_pixel_diff(out, baseline_clipped)
    masked_xmp_path.unlink(missing_ok=True)


def _render_masked_variant(
    entry, baseline, entry_dir: Path, configdir: Path, rendered: dict, baseline_paths: dict
) -> None:
    """Render the demo-mask variant for one entry, if applicable.

    Skipped when entry is already mask-bound (its own mask_spec is the
    demonstration) or when the entry's subtype is in the suppress list
    (modules whose mask binding doesn't render usefully).
    """
    if entry.mask_spec is not None:
        return
    suppress_reason = _should_skip_masked(entry)
    if suppress_reason is not None:
        rendered[entry.name]["_masked_skip_reason"] = suppress_reason
        return
    try:
        masked_xmp = _synthesize_for_entry_demo_masked(baseline, entry)
    except Exception as exc:
        print(f"  x demo-mask synthesize failed: {exc}", file=sys.stderr)
        return
    masked_xmp_path = entry_dir / f"_{entry.name}_masked.xmp"
    write_xmp(masked_xmp, masked_xmp_path)
    for target in TARGETS:
        if _should_skip_target(entry, target.slug):
            rendered[entry.name][f"{target.slug}_masked"] = "skipped"
            continue
        out = entry_dir / f"{entry.name}-{target.slug}-masked.jpg"
        if _render_one(target.path, masked_xmp_path, out, configdir):
            rendered[entry.name][f"{target.slug}_masked"] = out
            rendered[entry.name][f"{target.slug}_masked_diff"] = _mean_pixel_diff(
                out, baseline_paths[target.slug]
            )
    masked_xmp_path.unlink(missing_ok=True)


def _img_md(p, alt: str) -> str:
    """Render an image cell as inline HTML so we can size it tight."""
    if p is None:
        return "_(n/a)_"
    rel = p.relative_to(GALLERY_PAGE.parent.parent)
    return f'<img src="../{rel}" alt="{alt}" width="180">'


def _near_baseline_reason(entry, *, masked: bool) -> str:
    """Pick the most-specific near-baseline reason for an entry+context.

    Priority: subtype-keyed reason -> masked-sigmoid generic -> default.
    """
    if entry.subtype in _NEAR_BASELINE_NOTES:
        return _NEAR_BASELINE_NOTES[entry.subtype]
    if masked and entry.subtype == "sigmoid":
        return _NEAR_BASELINE_NOTES["_masked_sigmoid"]
    return "below visible threshold on this chart input"


def _diff_annotations(entry, outs: dict) -> list[str]:
    """One inline note per render cell whose diff signals it's worth flagging.

    Different signal for global vs masked cells:

    - **Global cells**: flag if mean-pixel-diff vs baseline is below
      threshold — the entry effectively did nothing visible to the
      whole image.
    - **Masked cells**: a small whole-image diff is *expected and correct*
      (the mask only affects ~16% of pixels, so 84% of the image stays
      at baseline by design). We only flag a masked cell as
      "near-baseline" when the *paired global* cell was also near-
      baseline — i.e., the move is small everywhere, not just inside
      the mask.
    """
    notes: list[str] = []
    for slug, label in (
        ("colorchecker", "ColorChecker (global)"),
        ("grayscale", "grayscale (global)"),
    ):
        diff = outs.get(f"{slug}_diff")
        if diff is None:
            continue
        if diff < _NEAR_BASELINE_DIFF_THRESHOLD:
            reason = _near_baseline_reason(entry, masked=False)
            notes.append(f"_(near-baseline diff in {label}: {reason})_")

    for slug, label, paired_global in (
        ("colorchecker_masked", "ColorChecker (masked)", "colorchecker"),
        ("grayscale_masked", "grayscale (masked)", "grayscale"),
    ):
        diff = outs.get(f"{slug}_diff")
        global_diff = outs.get(f"{paired_global}_diff")
        if diff is None or global_diff is None:
            continue
        # Only annotate if BOTH global and masked are near-baseline (move
        # is small everywhere). If global is visibly different but masked
        # is near-baseline, the mask is correctly excluding most pixels —
        # that's the expected behavior, not a problem to flag.
        if diff < _NEAR_BASELINE_DIFF_THRESHOLD and global_diff < _NEAR_BASELINE_DIFF_THRESHOLD:
            reason = _near_baseline_reason(entry, masked=True)
            notes.append(f"_(near-baseline diff in {label}: {reason})_")
    return notes


def _render_entry_md(entry, rendered: dict[str, dict[str, Path]]) -> list[str]:
    """Markdown lines for one entry's row in the gallery.

    Layout selection priority:
      1. Mask-bound entry (entry.mask_spec set) -> 2-col global only
      2. Suppressed-masked entry (_masked_skip_reason set) -> 2-col global
         + a "🚫 Masked variant suppressed" note
      3. Skip-grayscale entry (gs slug == "skipped") -> CC-only columns
         + a "Grayscale column omitted" note
      4. Default 4-col (CC global, gs global, CC masked, gs masked)

    Plus: for any rendered cell whose diff vs baseline is below the
    near-baseline threshold, append an italicized one-liner reason
    referencing the most-specific entry in :data:`_NEAR_BASELINE_NOTES`.
    """
    outs = rendered[entry.name]
    cc = outs.get("colorchecker")
    gs = outs.get("grayscale")
    cc_masked = outs.get("colorchecker_masked")
    gs_masked = outs.get("grayscale_masked")

    # Skip-listed entries (#103): delegate to one of two helpers — either
    # the placeholder (fixture missing) or the real-raw render layout.
    # Done as a single branch so this function's complexity stays under C901.
    skip_md = _maybe_render_skip_listed_md(entry, outs)
    if skip_md is not None:
        return skip_md

    if (cc in (None, "skipped")) and (gs in (None, "skipped")):
        return []

    is_mask_bound = entry.mask_spec is not None
    masked_skip = outs.get("_masked_skip_reason")
    gs_skipped = gs == "skipped"

    out: list[str] = []
    mask_marker = " 🟦 mask-bound" if is_mask_bound else ""
    out.append(f"### `{entry.name}`{mask_marker}\n")
    out.append(f"_{entry.description}_\n")

    if is_mask_bound:
        # Layout 1: mask-bound — 2-col global; demo-masked column omitted.
        out.append("| ColorChecker | Grayscale ramp |")
        out.append("|-|-|")
        out.append(
            f"| {_img_md(cc, f'{entry.name} ColorChecker')} "
            f"| {_img_md(gs, f'{entry.name} grayscale')} |"
        )
    elif masked_skip is not None:
        # Layout 2: masked column suppressed for this subtype (wb / vignette).
        if gs_skipped:
            # No grayscale either -> CC global only.
            out.append("| ColorChecker (global) |")
            out.append("|-|")
            out.append(f"| {_img_md(cc, f'{entry.name} ColorChecker global')} |")
        else:
            out.append("| ColorChecker (global) | Grayscale (global) |")
            out.append("|-|-|")
            out.append(
                f"| {_img_md(cc, f'{entry.name} ColorChecker global')} "
                f"| {_img_md(gs, f'{entry.name} grayscale global')} |"
            )
        out.append("")
        out.append(
            f"> 🚫 **Masked variant suppressed**: "
            f"see [mask-applicable-controls](mask-applicable-controls.md#{masked_skip}) "
            f"for why drawn-mask binding doesn't render usefully for this module."
        )
    elif gs_skipped:
        # Layout 3: chroma-only entry — CC columns only (global + masked).
        out.append("| ColorChecker (global) | ColorChecker (centered ellipse mask) |")
        out.append("|-|-|")
        out.append(
            f"| {_img_md(cc, f'{entry.name} ColorChecker global')} "
            f"| {_img_md(cc_masked, f'{entry.name} ColorChecker masked')} |"
        )
        out.append("")
        out.append(
            "> **Grayscale column omitted**: this primitive moves chroma only; "
            "gray patches have no chroma to affect."
        )
    else:
        # Layout 4: default 4-column (CC + grayscale, global + masked).
        out.append(
            "| ColorChecker (global) | Grayscale (global) "
            "| ColorChecker (centered ellipse mask) "
            "| Grayscale (centered ellipse mask) |"
        )
        out.append("|-|-|-|-|")
        out.append(
            f"| {_img_md(cc, f'{entry.name} ColorChecker global')} "
            f"| {_img_md(gs, f'{entry.name} grayscale global')} "
            f"| {_img_md(cc_masked, f'{entry.name} ColorChecker masked')} "
            f"| {_img_md(gs_masked, f'{entry.name} grayscale masked')} |"
        )

    # Inline near-baseline annotations for any cell with diff < threshold.
    for note in _diff_annotations(entry, outs):
        out.append("")
        out.append(note)

    # Extra row: clipped-gradient fixture for highlights / grain entries.
    clipped = outs.get("clipped")
    clipped_masked = outs.get("clipped_masked")
    if clipped not in (None, "skipped"):
        out.append("")
        out.append(
            "**On the clipped-gradient fixture** (continuous tone + blown "
            "highlights — chart designed to show this module's effect; "
            "see [`reference-targets/README.md`]"
            "(https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md)):"
        )
        if is_mask_bound or clipped_masked in (None, "skipped"):
            out.append("")
            out.append("| Clipped gradient (global) |")
            out.append("|-|")
            out.append(f"| {_img_md(clipped, f'{entry.name} clipped-gradient global')} |")
        else:
            out.append("")
            out.append("| Clipped gradient (global) | Clipped gradient (centered ellipse mask) |")
            out.append("|-|-|")
            out.append(
                f"| {_img_md(clipped, f'{entry.name} clipped-gradient global')} "
                f"| {_img_md(clipped_masked, f'{entry.name} clipped-gradient masked')} |"
            )

    # Parameter sweep rows (RFC-021/RFC-022): for parameterized entries,
    # show the entry rendered at multiple parameter values side-by-side.
    # Multi-parameter entries get one sweep row per axis.
    out.extend(_render_sweep_rows_md(entry, outs.get("_sweeps") or []))

    out.append("")
    return out


def _maybe_render_skip_listed_md(entry, outs: dict) -> list[str] | None:
    """Dispatcher for #103 skip-listed entries. Returns the rendered
    markdown when the entry is in _SKIP_VISUAL_PROOF_ENTRIES (either
    placeholder or real-raw layout), or None if the caller should
    proceed with the regular synthetic-chart layout."""
    if outs.get("__visual_proof_skip"):
        return _render_skip_placeholder_md(entry)
    if outs.get("__real_raw_only"):
        return _render_real_raw_entry_md(entry, outs)
    return None


def _render_skip_placeholder_md(entry) -> list[str]:
    """Markdown for an entry skipped from visual proofs (#103) when the
    real-raw fixture isn't available."""
    skip_url = "https://github.com/chipi/chemigram/blob/main/scripts/generate-visual-proofs.py#L120"
    return [
        f"### `{entry.name}`\n",
        f"_{entry.description}_\n",
        "> 🚫 **Visual-proof rendering skipped.** This entry's "
        "photographic effect requires real-raw input — its underlying "
        "darktable module produces degenerate output on the synthetic "
        "ColorChecker / grayscale fixtures (verified experimentally by "
        "varying the module's global tuning; chart pipeline doesn't "
        "recover). The byte-level apply path is verified by the 5-layer "
        "test coverage (per ADR-080). Visual proof on real raws is a "
        "v1.9.0+ work item — see "
        f"[`_SKIP_VISUAL_PROOF_ENTRIES`]({skip_url}) in the gallery "
        "script for the list and reasoning. To enable real-raw "
        "rendering, drop a fixture file at the path defined by "
        "`REAL_RAW_FIXTURE` (see `tests/fixtures/raws/README.md`).\n",
        "",
    ]


def _render_real_raw_entry_md(entry, outs: dict) -> list[str]:
    """Markdown for a real-raw-only entry (#103): rendered against the
    iguana fixture instead of the synthetic chart targets. Emits a
    1-col global view followed by parameter-sweep rows if applicable."""
    out: list[str] = []
    out.append(f"### `{entry.name}` 🦎 real-raw\n")
    out.append(f"_{entry.description}_\n")
    out.append(
        "> 🦎 **Real-raw rendering.** This entry's photographic effect "
        "needs a working color-management chain that the synthetic "
        "chart pipeline doesn't provide; rendered against the iguana "
        "fixture instead. Apply-path correctness is independently "
        "verified by the 5-layer test coverage (per ADR-080).\n"
    )
    realraw = outs.get(REAL_RAW_TARGET.slug)
    if realraw not in (None, "skipped"):
        out.append("| Real raw |")
        out.append("|-|")
        out.append(f"| {_img_md(realraw, f'{entry.name} real raw')} |")
        out.append("")
    out.extend(_render_sweep_rows_md(entry, outs.get("_sweeps") or []))
    out.append("")
    return out


def _render_sweep_rows_md(entry, sweeps: list[dict]) -> list[str]:
    """Markdown lines for one entry's parameter-sweep rows. Each sweep
    in the list emits one block (header + table); multi-parameter
    entries thus emit one block per axis. The swept axis varies across
    the recipe; other parameterized axes (if any) are held at the
    dtstyle's encoded defaults via the parameterized apply path's
    partial-update semantics."""
    out: list[str] = []
    for sweep in sweeps:
        if not sweep.get("renders"):
            continue
        out.append("")
        out.append(
            f"**Parameter sweep** (`{sweep['param']}`): "
            "rendered at multiple values via the parameterized apply path "
            "(`--value V` / `--param NAME=V`); other parameterized axes "
            "(if any) held at their dtstyle defaults."
        )
        out.append("")
        records = sweep["renders"]
        header = "| " + " | ".join(f"`{r['label']}`" for r in records) + " |"
        sep = "|" + "|".join(["-"] * len(records)) + "|"
        cells = (
            "| "
            + " | ".join(
                _img_md(r["path"], f"{entry.name} {sweep['param']}={r['label']}") for r in records
            )
            + " |"
        )
        out.append(header)
        out.append(sep)
        out.append(cells)
    return out


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
        "> **Masked columns**: every non-mask-bound primitive renders "
        "additionally through a centered ellipse mask "
        "(``radius=0.2``, ``border=0.05``) so you can see the spatial "
        "shaping in action. The mask covers the middle 16% of the frame; "
        "anything outside it should remain at baseline. This visually "
        "demonstrates that **any** primitive can be applied through a "
        "mask — see [`mask-applicable-controls.md`](mask-applicable-controls.md) "
        "for the per-module compatibility matrix.\n"
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
        f"(https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md).\n"
    )
    if _real_raw_fixture_available():
        lines.append(
            "> **🦎 Real-raw fixture path (#103).** A small set of entries "
            "(currently the HSL row via `colorequal`) need a working "
            "color-management chain that the synthetic chart pipeline "
            "doesn't provide. Those entries render against the real-raw "
            "fixture at "
            "[`tests/fixtures/raws/`]"
            "(https://github.com/chipi/chemigram/blob/main/tests/fixtures/raws/README.md) "
            "instead. Look for the 🦎 marker in the entry header.\n"
        )
    else:
        lines.append(
            "> **🚫 Real-raw fixture missing (#103).** A small set of "
            "entries (currently HSL via `colorequal`) need a real raw "
            "for visual proof — the synthetic chart pipeline produces "
            "degenerate output. Those entries currently show a documented "
            "placeholder row; drop a fixture file at the path defined by "
            "`REAL_RAW_FIXTURE` in this script (see "
            "[`tests/fixtures/raws/README.md`]"
            "(https://github.com/chipi/chemigram/blob/main/tests/fixtures/raws/README.md)) "
            "to enable real-raw rendering.\n"
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
            lines.extend(_render_entry_md(entry, rendered))

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
        "the e2e suite in [`tests/e2e/`](https://github.com/chipi/chemigram/blob/main/tests/e2e/).\n"
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
        "[`reference-targets/README.md`](https://github.com/chipi/chemigram/blob/main/tests/fixtures/reference-targets/README.md).\n"
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
