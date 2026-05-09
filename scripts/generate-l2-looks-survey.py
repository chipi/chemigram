#!/usr/bin/env python3
# ruff: noqa: C901
"""Generate 14 L2 composite looks from the photographer-workflows survey.

Per RFC-031 / RFC-032 / RFC-033 follow-up: the survey identified 14
recurring composition patterns (5 portrait + 9 landscape) that recur
across 4-6 photographers per genre. This script authors each as a
multi-plugin .dtstyle file by patching baseline op_params from existing
shipped primitive entries through ``chemigram.core.parameterize``.

Re-runnable: rewrites the .dtstyle files and the manifest entries each
run. Idempotent — each run produces the same bytes for the same input.

Inputs (read-only): existing primitive .dtstyle baselines in
``vocabulary/packs/expressive-baseline/layers/L3/``.

Outputs (overwritten):
- ``vocabulary/packs/expressive-baseline/layers/L2/look/look_*.dtstyle``
  (14 new files)
- The 14 manifest entries appended to
  ``vocabulary/packs/expressive-baseline/manifest.json``

Validation: each look loads via ``chemigram.core.vocab.load_packs`` and
applies via ``chemigram.core.helpers.apply_entry`` against an empty
baseline. Unit tests in ``tests/unit/core/test_l2_looks_survey.py``
verify schema correctness.

Visual quality (does the rendered image actually look like the named
intent?) requires a darktable-session sign-off — see
``docs/guides/visual-review-survey-l2-looks.md`` for the checklist.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "vocabulary" / "packs" / "expressive-baseline"
L2_DIR = PACK / "layers" / "L2" / "look"
MANIFEST_PATH = PACK / "manifest.json"
L3_DIR = PACK / "layers" / "L3"

DEFAULT_BLENDOP = "gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh"


def read_op_params(rel: str) -> str:
    """Read the first <op_params> blob from a primitive .dtstyle file."""
    text = (PACK / rel).read_text(encoding="utf-8")
    m = re.search(r"<op_params>([^<]+)</op_params>", text)
    if not m:
        raise SystemExit(f"no <op_params> in {rel}")
    return m.group(1)


# ---------------------------------------------------------------------------
# Baseline op_params blobs (read once from shipped primitives)
# ---------------------------------------------------------------------------

BASE_EXPOSURE = read_op_params("layers/L3/exposure/exposure.dtstyle")
BASE_SIGMOID = read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
BASE_TEMPERATURE = read_op_params("layers/L3/temperature/temperature.dtstyle")
BASE_COLORBALANCE = read_op_params("layers/L3/colorbalancergb/brilliance_global.dtstyle")
BASE_BILAT = read_op_params("layers/L3/localcontrast/bilat_clarity_strength.dtstyle")
BASE_HAZE = read_op_params("layers/L3/hazeremoval/dehaze.dtstyle")
BASE_COLOREQUAL = read_op_params("layers/L3/colorequal/hsl_saturation.dtstyle")


# ---------------------------------------------------------------------------
# Plugin specs (operation, modversion, module-id used in <module> tag)
# ---------------------------------------------------------------------------

# The <module> tag in dtstyle XML is the *module ID* darktable assigns at
# load time. Reading from existing looks: temperature=2, exposure=7,
# colorbalancergb=5, sigmoid=3, bilat=4, hazeremoval=6, colorequal=8 (from
# darktable's enum). Verified against shipped looks (look_portrait etc.).
MODULE_IDS: dict[str, int] = {
    "temperature": 2,
    "exposure": 7,
    "colorbalancergb": 5,
    "sigmoid": 3,
    "bilat": 4,
    "hazeremoval": 6,
    "colorequal": 8,
    "toneequalizer": 9,
}

# Plugin order in the <iop_list> declaration. Existing looks use a fixed
# baseline pipeline order. New looks may touch ops outside that order
# (e.g., colorequal, hazeremoval); they get appended to preserve readability.
# darktable resolves actual pipeline position from iop_order_version, so
# this declaration is informational, not load-bearing — but matching the
# existing convention reduces XMP diff noise (item #8 of the retro).
_BASELINE_IOP_ORDER = (
    "colorin,demosaic,temperature,exposure,colorbalancergb,bilat,grain,sigmoid,colorout"
)


def derive_iop_list(touches: list[str]) -> str:
    """Build the <iop_list> string for the new look. Modules in the
    baseline order keep their position; modules outside it are appended
    after (preserving readability vs. injecting at unknown positions)."""
    base = _BASELINE_IOP_ORDER.split(",")
    extra = [op for op in touches if op not in base]
    if not extra:
        return _BASELINE_IOP_ORDER
    return ",".join(base + extra)


def make_plugin(
    *,
    num: int,
    operation: str,
    op_params: str,
    enabled: bool = True,
    multi_priority: int = 0,
    multi_name: str = "",
) -> str:
    module_id = MODULE_IDS.get(operation, 0)
    return (
        "<plugin>"
        f"<num>{num}</num>"
        f"<module>{module_id}</module>"
        f"<operation>{operation}</operation>"
        f"<op_params>{op_params}</op_params>"
        f"<enabled>{1 if enabled else 0}</enabled>"
        f"<blendop_params>{DEFAULT_BLENDOP}</blendop_params>"
        "<blendop_version>14</blendop_version>"
        f"<multi_priority>{multi_priority}</multi_priority>"
        f"<multi_name>{multi_name}</multi_name>"
        "<multi_name_hand_edited>0</multi_name_hand_edited>"
        "</plugin>"
    )


def make_dtstyle(*, name: str, description: str, plugins: list[str], touches: list[str]) -> str:
    plugins_xml = "".join(plugins)
    iop_list = derive_iop_list(touches)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<darktable_style version="1.0">'
        f"<info><name>{name}</name>"
        f"<description>{_escape_xml(description)}</description>"
        f"<iop_list>{iop_list}</iop_list></info>"
        f"<style>{plugins_xml}</style>"
        "</darktable_style>\n"
    )


def _escape_xml(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# ---------------------------------------------------------------------------
# Look definitions — 14 new + 2 description refinements
# ---------------------------------------------------------------------------


def _patch_temperature_warm(amount: float = 0.05) -> str:
    """Slight warm shift via red_coeff bump. ``amount`` is fractional bump."""
    from chemigram.core.parameterize import temperature

    return temperature.patch(
        BASE_TEMPERATURE,
        red_coeff=1.0 + amount,
        blue_coeff=1.0 - amount * 0.5,
        green_coeff=1.0,
    )


def _patch_temperature_cool(amount: float = 0.05) -> str:
    from chemigram.core.parameterize import temperature

    return temperature.patch(
        BASE_TEMPERATURE,
        red_coeff=1.0 - amount * 0.5,
        blue_coeff=1.0 + amount,
        green_coeff=1.0,
    )


def look_portrait_natural_skin() -> tuple[str, str, dict]:
    """Restraint-first portrait foundation (Tucker / Marino voice)."""
    from chemigram.core.parameterize import colorbalancergb, exposure, sigmoid

    plugins = [
        make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.03)),
        make_plugin(num=11, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=0.1)),
        make_plugin(
            num=12, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.2)
        ),
        make_plugin(
            num=13,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE, saturation_global=-0.05, vibrance=0.1
            ),
        ),
    ]
    name = "look_portrait_natural_skin"
    desc = (
        "Restraint-first portrait foundation — Tucker/Marino-aligned. "
        "Slight warm temperature (+0.03 red), exposure +0.1 EV, "
        "sigmoid contrast 1.2 (gentle s-curve), saturation_global -0.05 + "
        "vibrance +0.1 (mild chroma shaping that protects skin tones). "
        "The starting point for portrait work that doesn't push contrast or "
        "saturation as a stylistic choice."
    )
    return (
        name,
        desc,
        _manifest(name, desc, ["temperature", "exposure", "sigmoid", "colorbalancergb"], plugins),
    )


def look_portrait_editorial() -> tuple[str, str, dict]:
    """Magazine punch — split-tone fashion grade."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    plugins = [
        make_plugin(
            num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.6)
        ),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                saturation_global=-0.10,
                hue_shadows=210.0,
                saturation_shadows=0.15,
                hue_highlights=45.0,
                saturation_highlights=0.10,
            ),
        ),
    ]
    name = "look_portrait_editorial"
    desc = (
        "Magazine / fashion editorial grade. Punchier sigmoid contrast (1.6), "
        "global saturation pull-back (-0.10) — counterintuitive but the move "
        "Adler/Woloszynowicz reach for; reduced overall sat lets the split-tone "
        "read. Cool-shadows + warm-highlights split (hue_shadows=210, "
        "hue_highlights=45). Compose with skin_uniformity if skin patches "
        "fight the grade."
    )
    return name, desc, _manifest(name, desc, ["sigmoid", "colorbalancergb"], plugins)


def look_portrait_skin_warm_lift() -> tuple[str, str, dict]:
    """Brighten + warm skin tones — pre-baked with mask_skin_region."""
    from chemigram.core.parameterize import exposure

    plugins = [
        make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.04)),
        make_plugin(num=11, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=0.2)),
    ]
    name = "look_portrait_skin_warm_lift"
    desc = (
        "Subject-region warm + brighten. Slight warm temperature (+0.04 red) + "
        "exposure +0.2 EV. Pre-baked with mask_skin_region so the lift scopes "
        "to skin without affecting clothing or background. Pairs with "
        "skin_uniformity for a complete portrait skin pass."
    )
    return (
        name,
        desc,
        _manifest(
            name,
            desc,
            ["temperature", "exposure"],
            plugins,
            mask_spec={"kind": "named", "name": "mask_skin_region"},
        ),
    )


def look_portrait_background_dim() -> tuple[str, str, dict]:
    """Dim + desaturate background — pre-baked with inverted mask_subject (RFC-034)."""
    from chemigram.core.parameterize import colorbalancergb, exposure

    plugins = [
        make_plugin(num=10, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=-0.4)),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(BASE_COLORBALANCE, saturation_global=-0.15),
        ),
    ]
    name = "look_portrait_background_dim"
    desc = (
        "Dim and de-saturate the background to push the subject forward. "
        "Exposure -0.4 EV + saturation_global -0.15. Pre-baked with "
        "mask_subject + invert: true (RFC-034) — the photographer doesn't "
        "have to construct an inverse-subject mask manually. The parametric "
        "fallback for mask_subject is coarse (midtone luminance + center-"
        "bias); for clean subject vs. background separation override the "
        "mask_spec at apply time with a manually-drawn inverted ellipse, "
        "or escalate via render_preview + LLM-vision construction "
        "(llm-vision-for-masks.md Pattern 7) for a path-form subject mask."
    )
    return (
        name,
        desc,
        _manifest(
            name,
            desc,
            ["exposure", "colorbalancergb"],
            plugins,
            mask_spec={"kind": "named", "name": "mask_subject", "invert": True},
        ),
    )


def look_portrait_split_tone_moody() -> tuple[str, str, dict]:
    """Cinematic split-tone — borderline candidate (recurrence 3)."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    plugins = [
        make_plugin(
            num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.4)
        ),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=210.0,
                saturation_shadows=0.30,
                hue_highlights=45.0,
                saturation_highlights=0.20,
            ),
        ),
    ]
    name = "look_portrait_split_tone_moody"
    desc = (
        "Cinematic split-tone portrait — cool blue shadows (hue 210, sat 0.30) + "
        "warm orange highlights (hue 45, sat 0.20), sigmoid contrast 1.4. "
        "Stronger split than look_portrait_editorial; some photographers "
        "(Adler) consider this 'fashion-only' rather than a general portrait "
        "move. Borderline survey candidate — ships, but exercise judgment."
    )
    return name, desc, _manifest(name, desc, ["sigmoid", "colorbalancergb"], plugins)


# --- Landscape looks ---------------------------------------------------------


def look_landscape_grand_vista() -> tuple[str, str, dict]:
    """Wide-scene work — sky + foreground balance, mild clarity."""
    from chemigram.core.parameterize import bilat, colorbalancergb, sigmoid

    plugins = [
        make_plugin(
            num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.4)
        ),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=30.0,
                saturation_shadows=0.10,
                vibrance=0.10,
            ),
        ),
        make_plugin(
            num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.5)
        ),
    ]
    name = "look_landscape_grand_vista"
    desc = (
        "Heaton/PureRAW-style grand vista. Sigmoid contrast 1.4, mildly warm "
        "shadows (hue 30, sat 0.10), vibrance +0.10, bilat clarity_strength 0.5. "
        "The chemigram shape of LR's adaptive sky + foreground lift workflow "
        "rendered globally; for sky-specific work compose with "
        "look_landscape_sky_enhance instead."
    )
    return name, desc, _manifest(name, desc, ["sigmoid", "colorbalancergb", "bilat"], plugins)


def look_landscape_intimate_quiet() -> tuple[str, str, dict]:
    """Marino restraint — small-scene / forest-interior."""
    from chemigram.core.parameterize import bilat, colorbalancergb, sigmoid

    plugins = [
        make_plugin(
            num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.05)
        ),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(BASE_COLORBALANCE, saturation_global=-0.10),
        ),
        make_plugin(
            num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=-0.3)
        ),
    ]
    name = "look_landscape_intimate_quiet"
    desc = (
        "Marino-style intimate / small-scene restraint. Very gentle sigmoid "
        "contrast (1.05), saturation pulled back (-0.10), bilat softened "
        "(clarity_strength -0.3 — opposite of clarity boost). The defining "
        "stylistic choice for forest interiors, abstract details, and any "
        "scene where drama would betray the subject. Applies LESS than the "
        "baseline does, deliberately."
    )
    return name, desc, _manifest(name, desc, ["sigmoid", "colorbalancergb", "bilat"], plugins)


def look_landscape_golden_hour() -> tuple[str, str, dict]:
    """Sunset / sunrise mood — warm shift + amber highlights."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    plugins = [
        make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.07)),
        make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.3)
        ),
        make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=30.0,
                saturation_shadows=0.20,
                hue_highlights=50.0,
                saturation_highlights=0.15,
                vibrance=0.10,
            ),
        ),
    ]
    name = "look_landscape_golden_hour"
    desc = (
        "Sunset / sunrise mood. Warm temperature shift (+0.07 red), sigmoid "
        "contrast 1.3, warm shadows (hue 30, sat 0.20) + amber highlights "
        "(hue 50, sat 0.15), vibrance +0.10. Pushes the warmth that golden-"
        "hour light almost has and amplifies it without breaking color "
        "credibility. For scenes already on the warm side, apply at lower "
        "strength via opacity — not authored as parametric (look-not-primitive)."
    )
    return name, desc, _manifest(name, desc, ["temperature", "sigmoid", "colorbalancergb"], plugins)


def look_landscape_blue_hour_cool() -> tuple[str, str, dict]:
    """Twilight / pre-dawn — cool shift, opposite of golden-hour."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    plugins = [
        make_plugin(num=10, operation="temperature", op_params=_patch_temperature_cool(0.07)),
        make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.3)
        ),
        make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=210.0,
                saturation_shadows=0.20,
                hue_highlights=200.0,
                saturation_highlights=0.10,
                saturation_global=-0.05,
            ),
        ),
    ]
    name = "look_landscape_blue_hour_cool"
    desc = (
        "Twilight / pre-dawn / blue-hour mood. Cool temperature shift (+0.07 "
        "blue), sigmoid contrast 1.3, cool shadows (hue 210, sat 0.20) + "
        "neutral-cool highlights (hue 200, sat 0.10), saturation_global -0.05. "
        "Opposite mood from golden_hour; equally valid genre signature. "
        "Composes with sigmoid_contrast for stronger drama if needed."
    )
    return name, desc, _manifest(name, desc, ["temperature", "sigmoid", "colorbalancergb"], plugins)


def look_landscape_atmospheric_haze() -> tuple[str, str, dict]:
    """Misty / hazy conditions — atmosphere as the subject."""
    from chemigram.core.parameterize import bilat, colorbalancergb, hazeremoval

    plugins = [
        make_plugin(
            num=10, operation="hazeremoval", op_params=hazeremoval.patch(BASE_HAZE, strength=0.5)
        ),
        make_plugin(
            num=11, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.3)
        ),
        make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=30.0,
                saturation_shadows=0.10,
                vibrance=0.05,
            ),
        ),
    ]
    name = "look_landscape_atmospheric_haze"
    desc = (
        "Misty / hazy / fog-as-subject mood. Hazeremoval strength 0.5 (lift "
        "visibility while preserving the moody atmosphere), bilat clarity 0.3, "
        "warm shadows (hue 30, sat 0.10) + vibrance +0.05. The trick: lift "
        "JUST enough to read details, not enough to flatten the atmosphere. "
        "Strong hazeremoval values (>1.0) produce 'no atmosphere' results "
        "that defeat the intent — keep restrained."
    )
    return name, desc, _manifest(name, desc, ["hazeremoval", "bilat", "colorbalancergb"], plugins)


def look_landscape_dramatic_moody() -> tuple[str, str, dict]:
    """Page/Adamus moody — stormy skies, rugged terrain."""
    from chemigram.core.parameterize import bilat, colorbalancergb, sigmoid

    plugins = [
        make_plugin(
            num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.7)
        ),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=210.0,
                saturation_shadows=0.20,
                hue_highlights=30.0,
                saturation_highlights=0.15,
                vibrance=0.10,
            ),
        ),
        make_plugin(
            num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.6)
        ),
    ]
    name = "look_landscape_dramatic_moody"
    desc = (
        "Page/Adamus-style dramatic atmospheric. Sigmoid contrast 1.7 "
        "(strong), cool shadows (hue 210, sat 0.20) + warm highlights "
        "(hue 30, sat 0.15), bilat clarity_strength 0.6. The dramatic "
        "counterpart to intimate_quiet — for stormy skies, rugged terrain, "
        "and weather drama. Pair with mask_luminosity_brightest_quartile "
        "darkening for stormy-cloud emphasis."
    )
    return name, desc, _manifest(name, desc, ["sigmoid", "colorbalancergb", "bilat"], plugins)


def look_landscape_autumn_pop() -> tuple[str, str, dict]:
    """Autumn foliage — orange/red lift, blue compensation."""
    from chemigram.core.parameterize import bilat, colorequal

    plugins = [
        make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.04)),
        make_plugin(
            num=11,
            operation="colorequal",
            op_params=colorequal.patch(
                BASE_COLOREQUAL,
                sat_orange=0.30,
                sat_red=0.20,
                sat_blue=-0.10,
            ),
        ),
        make_plugin(
            num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.4)
        ),
    ]
    name = "look_landscape_autumn_pop"
    desc = (
        "Autumn foliage / fall color. Slight warm temperature (+0.04 red), "
        "colorequal sat_orange +0.30 + sat_red +0.20 (lift autumn colors) + "
        "sat_blue -0.10 (compensating to keep skies natural — without this, "
        "skies turn cartoonish). Bilat clarity_strength 0.4 for foliage "
        "definition. A targeted seasonal grade; not for non-foliage scenes."
    )
    return name, desc, _manifest(name, desc, ["temperature", "colorequal", "bilat"], plugins)


def look_landscape_sky_enhance() -> tuple[str, str, dict]:
    """Sky-targeted move — pre-baked with mask_sky."""
    from chemigram.core.parameterize import colorbalancergb

    plugins = [
        make_plugin(
            num=10,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_highlights=200.0,
                saturation_highlights=0.15,
                vibrance=0.05,
            ),
        ),
    ]
    name = "look_landscape_sky_enhance"
    desc = (
        "Sky-targeted enhancement (Heaton 'adaptive sky' shape). "
        "Cool-tone highlights shift (hue 200, sat 0.15) + slight vibrance "
        "(+0.05). Pre-baked with mask_sky (RFC-032) so the move scopes to "
        "the sky region automatically. **Compose, don't replace** — this is "
        "a focused enhancement to stack on top of any landscape look. For "
        "complex skies (sunsets, partial clouds, trees protruding into sky), "
        "override mask_spec with a constructed path mask via render_preview "
        "+ LLM-vision (llm-vision-for-masks.md Pattern 7)."
    )
    return (
        name,
        desc,
        _manifest(
            name,
            desc,
            ["colorbalancergb"],
            plugins,
            mask_spec={"kind": "named", "name": "mask_sky"},
        ),
    )


def look_landscape_water_silk() -> tuple[str, str, dict]:
    """Water surfaces — smooth, opposite of clarity."""
    from chemigram.core.parameterize import bilat, colorbalancergb

    plugins = [
        make_plugin(
            num=10, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=-0.4)
        ),
        make_plugin(
            num=11,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE,
                hue_shadows=200.0,
                saturation_shadows=0.10,
                vibrance=0.05,
            ),
        ),
    ]
    name = "look_landscape_water_silk"
    desc = (
        "Water surfaces — silky water in long-exposure work, glassy lakes. "
        "Bilat clarity_strength -0.4 (smooths the texture, OPPOSITE of "
        "clarity), cool-tone shadows (hue 200, sat 0.10), vibrance +0.05. "
        "Pre-baked with mask_water_blue_cyan so the smoothing scopes to "
        "water without affecting rocks, foliage, or sky. Reduces clarity "
        "selectively to enhance the smoothness photographers spent shutter-"
        "time creating."
    )
    return (
        name,
        desc,
        _manifest(
            name,
            desc,
            ["bilat", "colorbalancergb"],
            plugins,
            mask_spec={"kind": "named", "name": "mask_water_blue_cyan"},
        ),
    )


# ---------------------------------------------------------------------------
# Manifest entry assembler
# ---------------------------------------------------------------------------


def _manifest(
    name: str,
    description: str,
    touches: list[str],
    plugins: list[str],  # ignored; this function returns the manifest entry
    *,
    mask_spec: dict | None = None,
) -> dict:
    entry = {
        "name": name,
        "layer": "L2",
        "subtype": "look",
        "path": f"layers/L2/look/{name}.dtstyle",
        "touches": touches,
        "tags": _tags_for(name, mask_spec is not None),
        "description": description,
        "modversions": _modversions_for(touches),
        "darktable_version": "5.4",
        "source": "expressive-baseline",
        "license": "MIT",
    }
    if mask_spec is not None:
        entry["mask_spec"] = mask_spec
    return entry


_TAG_KEYWORDS = (
    ("portrait", "portrait"),
    ("landscape", "landscape"),
    ("skin", "skin"),
    ("sky", "sky"),
    ("water", "water"),
    ("autumn", "autumn"),
    ("golden", "golden-hour"),
    ("background_dim", "background"),
)
_TAG_COMPOUND = (
    (("blue", "hour"), "blue-hour"),
    (("haze",), "atmospheric"),
    (("atmospheric",), "atmospheric"),
    (("dramatic",), "dramatic"),
    (("moody",), "dramatic"),
    (("intimate",), "restrained"),
    (("quiet",), "restrained"),
    (("natural",), "restraint-discipline"),
    (("intimate",), "restraint-discipline"),
)


def _tags_for(name: str, has_mask: bool) -> list[str]:
    tags = ["look", "composite"]
    for keyword, tag in _TAG_KEYWORDS:
        if keyword in name and tag not in tags:
            tags.append(tag)
    for keywords, tag in _TAG_COMPOUND:
        if all(k in name for k in keywords) and tag not in tags:
            tags.append(tag)
    if has_mask:
        tags.append("masked")
    return tags


def _modversions_for(touches: list[str]) -> dict[str, int]:
    """Modversions canonical to the parameterize decoders. Single source of
    truth: ``known_pinned_modversions()`` from the modversion-drift module —
    no manual duplicate map. Drift warnings at vocab-load time already
    enforce this on the read side; this enforces it on the write side
    (item #6 of the post-batch retro)."""
    from chemigram.core.vocab._modversion_drift import known_pinned_modversions

    pinned = known_pinned_modversions()
    out: dict[str, int] = {}
    for op in touches:
        # Note: existing entries declare exposure mv7, but the parameterize
        # decoder pins to a different number (existing manifests use the
        # higher number from the dtstyle's <module> tag, not the decoder
        # pin). Fall back to the existing-manifest convention for entries
        # the registry doesn't recognize.
        if op in pinned:
            out[op] = pinned[op]
        else:
            # Fallbacks for ops not in the parameterize registry — match
            # the values shipped on existing L2 looks.
            fallbacks = {"exposure": 7}
            out[op] = fallbacks.get(op, 1)
    return out


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


LOOK_BUILDERS = [
    look_portrait_natural_skin,
    look_portrait_editorial,
    look_portrait_skin_warm_lift,
    look_portrait_background_dim,
    look_portrait_split_tone_moody,
    look_landscape_grand_vista,
    look_landscape_intimate_quiet,
    look_landscape_golden_hour,
    look_landscape_blue_hour_cool,
    look_landscape_atmospheric_haze,
    look_landscape_dramatic_moody,
    look_landscape_autumn_pop,
    look_landscape_sky_enhance,
    look_landscape_water_silk,
]


def main() -> None:
    L2_DIR.mkdir(parents=True, exist_ok=True)
    new_entries: list[dict] = []
    for builder in LOOK_BUILDERS:
        name, desc, entry = builder()
        plugins = _build_plugins_for(name)
        dtstyle_xml = make_dtstyle(
            name=name, description=desc, plugins=plugins, touches=entry["touches"]
        )
        dtstyle_path = L2_DIR / f"{name}.dtstyle"
        dtstyle_path.write_text(dtstyle_xml, encoding="utf-8")
        new_entries.append(entry)
        print(f"  wrote {dtstyle_path.relative_to(REPO)}")

    # Append entries to manifest (replacing any existing entries with same names)
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    new_names = {e["name"] for e in new_entries}
    manifest["entries"] = [e for e in manifest["entries"] if e["name"] not in new_names]
    manifest["entries"].extend(new_entries)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  appended {len(new_entries)} entries to {MANIFEST_PATH.relative_to(REPO)}")


def _build_plugins_for(name: str) -> list[str]:
    """Re-derive the plugin list for a given look name. Mirrors the body of
    each builder but returns just the plugin XML list.

    **Known duplication** (item #7 of the post-batch retro): each builder
    constructs plugins inline (for the manifest entry's touches list) and
    this function re-constructs them. A cleaner design has builders return
    ``(name, desc, touches, plugins, mask_spec)`` and main() builds the
    entry dict + dtstyle XML. Refactor deferred — this script ships and is
    re-runnable; the duplication is contained to this file. Address before
    the next genre's L2-look batch (Wedding/Event, B&W, Nature/Wildlife,
    Food/Product) for cleaner authoring across all 6 genres."""
    from chemigram.core.parameterize import (
        bilat,
        colorbalancergb,
        colorequal,
        exposure,
        hazeremoval,
        sigmoid,
    )

    if name == "look_portrait_natural_skin":
        return [
            make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.03)),
            make_plugin(
                num=11, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=0.1)
            ),
            make_plugin(
                num=12, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.2)
            ),
            make_plugin(
                num=13,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE, saturation_global=-0.05, vibrance=0.1
                ),
            ),
        ]
    if name == "look_portrait_editorial":
        return [
            make_plugin(
                num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.6)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    saturation_global=-0.10,
                    hue_shadows=210.0,
                    saturation_shadows=0.15,
                    hue_highlights=45.0,
                    saturation_highlights=0.10,
                ),
            ),
        ]
    if name == "look_portrait_skin_warm_lift":
        return [
            make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.04)),
            make_plugin(
                num=11, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=0.2)
            ),
        ]
    if name == "look_portrait_background_dim":
        return [
            make_plugin(
                num=10, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=-0.4)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(BASE_COLORBALANCE, saturation_global=-0.15),
            ),
        ]
    if name == "look_portrait_split_tone_moody":
        return [
            make_plugin(
                num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.4)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=210.0,
                    saturation_shadows=0.30,
                    hue_highlights=45.0,
                    saturation_highlights=0.20,
                ),
            ),
        ]
    if name == "look_landscape_grand_vista":
        return [
            make_plugin(
                num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.4)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=30.0,
                    saturation_shadows=0.10,
                    vibrance=0.10,
                ),
            ),
            make_plugin(
                num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.5)
            ),
        ]
    if name == "look_landscape_intimate_quiet":
        return [
            make_plugin(
                num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.05)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(BASE_COLORBALANCE, saturation_global=-0.10),
            ),
            make_plugin(
                num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=-0.3)
            ),
        ]
    if name == "look_landscape_golden_hour":
        return [
            make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.07)),
            make_plugin(
                num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.3)
            ),
            make_plugin(
                num=12,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=30.0,
                    saturation_shadows=0.20,
                    hue_highlights=50.0,
                    saturation_highlights=0.15,
                    vibrance=0.10,
                ),
            ),
        ]
    if name == "look_landscape_blue_hour_cool":
        return [
            make_plugin(num=10, operation="temperature", op_params=_patch_temperature_cool(0.07)),
            make_plugin(
                num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.3)
            ),
            make_plugin(
                num=12,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=210.0,
                    saturation_shadows=0.20,
                    hue_highlights=200.0,
                    saturation_highlights=0.10,
                    saturation_global=-0.05,
                ),
            ),
        ]
    if name == "look_landscape_atmospheric_haze":
        return [
            make_plugin(
                num=10,
                operation="hazeremoval",
                op_params=hazeremoval.patch(BASE_HAZE, strength=0.5),
            ),
            make_plugin(
                num=11, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.3)
            ),
            make_plugin(
                num=12,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=30.0,
                    saturation_shadows=0.10,
                    vibrance=0.05,
                ),
            ),
        ]
    if name == "look_landscape_dramatic_moody":
        return [
            make_plugin(
                num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.7)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=210.0,
                    saturation_shadows=0.20,
                    hue_highlights=30.0,
                    saturation_highlights=0.15,
                    vibrance=0.10,
                ),
            ),
            make_plugin(
                num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.6)
            ),
        ]
    if name == "look_landscape_autumn_pop":
        return [
            make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.04)),
            make_plugin(
                num=11,
                operation="colorequal",
                op_params=colorequal.patch(
                    BASE_COLOREQUAL,
                    sat_orange=0.30,
                    sat_red=0.20,
                    sat_blue=-0.10,
                ),
            ),
            make_plugin(
                num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.4)
            ),
        ]
    if name == "look_landscape_sky_enhance":
        return [
            make_plugin(
                num=10,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_highlights=200.0,
                    saturation_highlights=0.15,
                    vibrance=0.05,
                ),
            ),
        ]
    if name == "look_landscape_water_silk":
        return [
            make_plugin(
                num=10, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=-0.4)
            ),
            make_plugin(
                num=11,
                operation="colorbalancergb",
                op_params=colorbalancergb.patch(
                    BASE_COLORBALANCE,
                    hue_shadows=200.0,
                    saturation_shadows=0.10,
                    vibrance=0.05,
                ),
            ),
        ]
    raise SystemExit(f"unknown look: {name}")


if __name__ == "__main__":
    main()
