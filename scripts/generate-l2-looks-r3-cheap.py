#!/usr/bin/env python3
# ruff: noqa: C901
"""Generate the 10 cheap R3 L2 looks — Wildlife (5) + Food/Product (5).

Cheap = composes existing primitives only; no new architectural work.
Wildlife looks lean on RFC-032 named masks (mask_subject, mask_eye_region);
food/product looks compose colorequal + sigmoid + colorbalancergb in
genre-specific recipes.

Re-runnable; idempotent.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "vocabulary" / "packs" / "expressive-baseline"
L2_DIR = PACK / "layers" / "L2" / "look"
MANIFEST_PATH = PACK / "manifest.json"

DEFAULT_BLENDOP = "gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh"

MODULE_IDS: dict[str, int] = {
    "temperature": 2,
    "exposure": 7,
    "colorbalancergb": 5,
    "sigmoid": 3,
    "bilat": 4,
    "hazeremoval": 6,
    "colorequal": 8,
    "toneequalizer": 9,
    "sharpen": 10,
    "denoiseprofile": 11,
    "vignette": 12,
}

_IOP_LIST = "colorin,demosaic,temperature,exposure,colorbalancergb,bilat,grain,sigmoid,colorout"


def _read_op_params(rel: str) -> str:
    text = (PACK / rel).read_text(encoding="utf-8")
    m = re.search(r"<op_params>([^<]+)</op_params>", text)
    if not m:
        raise SystemExit(f"no <op_params> in {rel}")
    return m.group(1)


BASE_TEMPERATURE = _read_op_params("layers/L3/temperature/temperature.dtstyle")
BASE_EXPOSURE = _read_op_params("layers/L3/exposure/exposure.dtstyle")
BASE_SIGMOID = _read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
BASE_COLORBALANCE = _read_op_params("layers/L3/colorbalancergb/brilliance_global.dtstyle")
BASE_BILAT = _read_op_params("layers/L3/localcontrast/bilat_clarity_strength.dtstyle")
BASE_COLOREQUAL = _read_op_params("layers/L3/colorequal/hsl_saturation.dtstyle")
BASE_VIGNETTE = _read_op_params("layers/L3/vignette/vignette.dtstyle")
BASE_SHARPEN = _read_op_params("layers/L3/sharpen/sharpen.dtstyle")
BASE_DENOISE = _read_op_params("layers/L3/denoiseprofile/denoise.dtstyle")


def _make_plugin(*, num: int, operation: str, op_params: str) -> str:
    module_id = MODULE_IDS.get(operation, 0)
    return (
        "<plugin>"
        f"<num>{num}</num><module>{module_id}</module>"
        f"<operation>{operation}</operation>"
        f"<op_params>{op_params}</op_params>"
        "<enabled>1</enabled>"
        f"<blendop_params>{DEFAULT_BLENDOP}</blendop_params>"
        "<blendop_version>14</blendop_version>"
        "<multi_priority>0</multi_priority>"
        "<multi_name></multi_name>"
        "<multi_name_hand_edited>0</multi_name_hand_edited>"
        "</plugin>"
    )


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _make_dtstyle(
    *, name: str, description: str, plugins: list[str], iop_list: str = _IOP_LIST
) -> str:
    plugins_xml = "".join(plugins)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<darktable_style version="1.0">'
        f"<info><name>{name}</name>"
        f"<description>{_escape(description)}</description>"
        f"<iop_list>{iop_list}</iop_list></info>"
        f"<style>{plugins_xml}</style>"
        "</darktable_style>\n"
    )


def _patch_temperature_warm(amount: float = 0.05) -> str:
    from chemigram.core.parameterize import temperature

    return temperature.patch(
        BASE_TEMPERATURE,
        red_coeff=1.0 + amount,
        blue_coeff=1.0 - amount * 0.5,
        green_coeff=1.0,
    )


# ---------------------------------------------------------------------------
# Wildlife looks (5)
# ---------------------------------------------------------------------------


def look_wildlife_subject_sharpen() -> tuple[str, str, dict, list[str]]:
    """Subject-isolated feather/fur sharpening with mild clarity."""
    from chemigram.core.parameterize import bilat, sharpen

    plugins = [
        _make_plugin(
            num=10, operation="sharpen", op_params=sharpen.patch(BASE_SHARPEN, amount=2.0)
        ),
        _make_plugin(
            num=11, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.3)
        ),
    ]
    name = "look_wildlife_subject_sharpen"
    desc = (
        "Subject-isolated wildlife sharpening — feather / fur / scale detail "
        "lifted ON THE SUBJECT only via mask_subject (RFC-032). Sharpen amount "
        "2.0 + bilat clarity 0.3. The chemigram realization of LR's Subject-"
        "mask + Sharpening + selective Texture pattern (Sweileh, Matiash, "
        "Dale, Gardner all reach for this). Compose with mask_subject in the "
        "manifest; pair with look_wildlife_background_blur for compositional "
        "subject emphasis."
    )
    touches = ["sharpen", "bilat"]
    return (
        name,
        desc,
        _l2_manifest(
            name, desc, touches, plugins, mask_spec={"kind": "named", "name": "mask_subject"}
        ),
        plugins,
    )


def look_wildlife_background_blur() -> tuple[str, str, dict, list[str]]:
    """Inverse-mask softening — blur background to amplify subject."""
    from chemigram.core.parameterize import bilat

    plugins = [
        _make_plugin(
            num=10, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=-0.5)
        ),
    ]
    name = "look_wildlife_background_blur"
    desc = (
        "Background softening for wildlife — bilat clarity_strength -0.5 (the "
        "softening direction; opposite of clarity boost). Pre-baked with "
        "mask_subject + invert: true (RFC-034) so the softening scopes to "
        "everything-except-subject. Mimics longer-lens / shallower-DOF "
        "rendering at edit time. Pair with look_wildlife_subject_sharpen for "
        "complete subject emphasis. Marc/Bushcrafter darktable-discipline "
        "made portable."
    )
    touches = ["bilat"]
    return (
        name,
        desc,
        _l2_manifest(
            name,
            desc,
            touches,
            plugins,
            mask_spec={"kind": "named", "name": "mask_subject", "invert": True},
        ),
        plugins,
    )


def look_wildlife_eye_lift() -> tuple[str, str, dict, list[str]]:
    """Catchlight emphasis on subject's eye."""
    from chemigram.core.parameterize import exposure, sharpen

    plugins = [
        _make_plugin(num=10, operation="exposure", op_params=exposure.patch(BASE_EXPOSURE, ev=0.3)),
        _make_plugin(
            num=11, operation="sharpen", op_params=sharpen.patch(BASE_SHARPEN, amount=1.5)
        ),
    ]
    name = "look_wildlife_eye_lift"
    desc = (
        "Catchlight emphasis on the wildlife subject's eye — exposure +0.3 EV "
        "+ sharpen amount 1.5, scoped to mask_eye_region (RFC-032). The eye "
        "becomes the brightest, sharpest point in the frame; gives the bird "
        "/ animal its 'life.' Cross-genre echo of Portrait Move 7 (eye-detail "
        "lift). For close-up wildlife where the subject's gaze is the picture."
    )
    touches = ["exposure", "sharpen"]
    return (
        name,
        desc,
        _l2_manifest(
            name, desc, touches, plugins, mask_spec={"kind": "named", "name": "mask_eye_region"}
        ),
        plugins,
    )


def look_wildlife_high_iso_recovery() -> tuple[str, str, dict, list[str]]:
    """High-ISO wildlife with NR + subject-mask compatible."""
    from chemigram.core.parameterize import bilat, denoiseprofile, sigmoid

    plugins = [
        _make_plugin(
            num=10,
            operation="denoiseprofile",
            op_params=denoiseprofile.patch(
                BASE_DENOISE, denoise_strength=1.2, denoise_scattering=2.0, denoise_radius=7.0
            ),
        ),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.25)
        ),
        _make_plugin(
            num=12, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.2)
        ),
    ]
    name = "look_wildlife_high_iso_recovery"
    desc = (
        "High-ISO wildlife recovery (low-light dance-floor, late dusk owl, "
        "early-dawn bird-burst). Manual denoiseprofile (nbhood 7, strength "
        "1.2, scattering 2.0) + gentle sigmoid 1.25 + subtle clarity 0.2. "
        "**Note:** for ISO ≥ 1600 most surveyed wildlife photographers "
        "ROUTE THROUGH a sibling AI-NR tool (Topaz DeNoise / DxO PureRAW / "
        "LR AI Denoise) BEFORE this look applies; document the BYOA pattern "
        "in vocabulary-patterns.md. This look is the chemigram-only manual "
        "fallback when sibling tooling isn't configured."
    )
    touches = ["denoiseprofile", "sigmoid", "bilat"]
    return name, desc, _l2_manifest(name, desc, touches, plugins), plugins


def look_wildlife_natural_warm() -> tuple[str, str, dict, list[str]]:
    """Warm golden-hour wildlife default."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    plugins = [
        _make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.05)),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.25)
        ),
        _make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE, vibrance=0.10, saturation_global=-0.03
            ),
        ),
    ]
    name = "look_wildlife_natural_warm"
    desc = (
        "Warm golden-hour wildlife default — temperature +0.05 red shift + "
        "sigmoid 1.25 + vibrance +0.10 with slight saturation_global pull (-0.03 "
        "to keep the warmth credible, not cartoonish). The starting point for "
        "early-morning / late-afternoon wildlife where natural warmth IS the "
        "subject. Compose with look_wildlife_subject_sharpen for full effect."
    )
    touches = ["temperature", "sigmoid", "colorbalancergb"]
    return name, desc, _l2_manifest(name, desc, touches, plugins), plugins


# ---------------------------------------------------------------------------
# Food/Product looks (5)
# ---------------------------------------------------------------------------


def look_food_appetizing_warm() -> tuple[str, str, dict, list[str]]:
    """Default food editorial — warm WB, lifted midtones, vibrant color."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    plugins = [
        _make_plugin(num=10, operation="temperature", op_params=_patch_temperature_warm(0.04)),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.25)
        ),
        _make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                BASE_COLORBALANCE, vibrance=0.15, brilliance_midtones=0.08
            ),
        ),
    ]
    name = "look_food_appetizing_warm"
    desc = (
        "Default food editorial — warm WB (+0.04 red), gentle sigmoid 1.25, "
        "vibrance +0.15 + lifted midtone brilliance +0.08. Lauren C. Short / "
        "Darina Kopcok / Joanie Simon's foundational starting point for food "
        "blog and editorial work. Pre-WB-foundation (gray card recommended); "
        "downstream HSL color shaping per look_food_orange_pop / "
        "look_food_green_natural compose orthogonally."
    )
    touches = ["temperature", "sigmoid", "colorbalancergb"]
    return name, desc, _l2_manifest(name, desc, touches, plugins), plugins


def look_food_orange_pop() -> tuple[str, str, dict, list[str]]:
    """Boost orange/red food (tomato, carrot, salmon, paprika)."""
    from chemigram.core.parameterize import colorequal

    plugins = [
        _make_plugin(
            num=10,
            operation="colorequal",
            op_params=colorequal.patch(
                BASE_COLOREQUAL,
                sat_orange=0.30,
                sat_red=0.20,
                bright_orange=0.05,
                bright_red=0.03,
            ),
        ),
    ]
    name = "look_food_orange_pop"
    desc = (
        "Lift the orange / red food band — tomato, carrot, salmon, paprika, "
        "peach. Colorequal sat_orange +0.30 + sat_red +0.20 (saturation lift "
        "on warm food colors) + slight brightness lifts. The HSL-per-color "
        "discipline that food photographers use INSTEAD of global saturation "
        "(which would destroy whites and greens). Compose on top of "
        "look_food_appetizing_warm."
    )
    touches = ["colorequal"]
    return name, desc, _l2_manifest(name, desc, touches, plugins), plugins


def look_food_green_natural() -> tuple[str, str, dict, list[str]]:
    """Lift greens (herbs, salad, parsley) without muddying."""
    from chemigram.core.parameterize import colorequal

    plugins = [
        _make_plugin(
            num=10,
            operation="colorequal",
            op_params=colorequal.patch(
                BASE_COLOREQUAL,
                sat_green=0.20,
                sat_yellow=0.10,
                bright_green=0.05,
            ),
        ),
    ]
    name = "look_food_green_natural"
    desc = (
        "Lift greens — fresh herbs, salad, parsley, basil — without crossing "
        "into the cartoonish lime-green that over-edited food photography "
        "shows. Colorequal sat_green +0.20 + sat_yellow +0.10 + bright_green "
        "+0.05. The restraint discipline applied to color shaping (Tucker / "
        "Marino voice in food work). Compose on top of look_food_appetizing_warm."
    )
    touches = ["colorequal"]
    return name, desc, _l2_manifest(name, desc, touches, plugins), plugins


def look_food_texture_subtle() -> tuple[str, str, dict, list[str]]:
    """Texture lift for bread / pastry / meat fibers without drying."""
    from chemigram.core.parameterize import bilat

    plugins = [
        _make_plugin(
            num=10, operation="bilat", op_params=bilat.patch(BASE_BILAT, clarity_strength=0.20)
        ),
    ]
    name = "look_food_texture_subtle"
    desc = (
        "Subtle texture lift for food — bread crust, pastry layers, meat "
        "fibers, fruit skin texture. Bilat clarity_strength +0.20 — explicit "
        "ceiling matching the food-photography-academy 'never overdone' "
        "discipline (Kopcok: 'overdoing clarity makes food look dry and "
        "unappealing'). Pre-baked with mask_subject so the texture lift "
        "scopes to the food, not the table / plate. Compose with "
        "look_food_appetizing_warm."
    )
    touches = ["bilat"]
    return (
        name,
        desc,
        _l2_manifest(
            name, desc, touches, plugins, mask_spec={"kind": "named", "name": "mask_subject"}
        ),
        plugins,
    )


def look_product_packshot_clean() -> tuple[str, str, dict, list[str]]:
    """Clean product on white background — neutral commercial."""
    from chemigram.core.parameterize import sigmoid, vignette

    plugins = [
        _make_plugin(
            num=10, operation="sigmoid", op_params=sigmoid.patch(BASE_SIGMOID, contrast=1.10)
        ),
        _make_plugin(
            num=11, operation="vignette", op_params=vignette.patch(BASE_VIGNETTE, brightness=-0.10)
        ),
    ]
    name = "look_product_packshot_clean"
    desc = (
        "Commercial packshot baseline — gentle sigmoid 1.10 (avoids the "
        "punch-the-product look), subtle vignette -0.10 (-10% brightness "
        "edges; pulls the eye to the centered product). Karl Taylor / Zoe "
        "Noble's commercial-product clean-on-white starting point. Assumes "
        "WB has been gray-card-corrected (use wb_from_gray_card MCP tool / "
        "CLI before this look applies)."
    )
    touches = ["sigmoid", "vignette"]
    return name, desc, _l2_manifest(name, desc, touches, plugins), plugins


# ---------------------------------------------------------------------------
# Manifest assembler
# ---------------------------------------------------------------------------


def _l2_manifest(
    name: str,
    description: str,
    touches: list[str],
    plugins: list[str],
    *,
    mask_spec: dict | None = None,
) -> dict:
    iop_extras = [op for op in touches if op not in _IOP_LIST.split(",")]
    iop_list = _IOP_LIST + ("," + ",".join(iop_extras) if iop_extras else "")
    dtstyle_path = L2_DIR / f"{name}.dtstyle"
    L2_DIR.mkdir(parents=True, exist_ok=True)
    dtstyle_path.write_text(
        _make_dtstyle(name=name, description=description, plugins=plugins, iop_list=iop_list),
        encoding="utf-8",
    )
    print(f"  wrote {dtstyle_path.relative_to(REPO)}")

    tags = ["look", "composite"]
    if "wildlife" in name:
        tags.append("wildlife")
        tags.append("nature")
    if "food" in name:
        tags.append("food")
    if "product" in name:
        tags.append("product")
    if "subject" in name:
        tags.append("subject")
    if "background" in name:
        tags.append("background")
    if "eye" in name:
        tags.append("eye")
    if "high_iso" in name:
        tags.append("high-iso")
    if "natural_warm" in name or "appetizing" in name:
        tags.append("warm")
    if "orange" in name or "green_natural" in name:
        tags.append("color-shaping")
    if "texture" in name:
        tags.append("texture")
    if "packshot" in name:
        tags.append("commercial")
    if mask_spec is not None:
        tags.append("masked")

    entry: dict = {
        "name": name,
        "layer": "L2",
        "subtype": "look",
        "path": f"layers/L2/look/{name}.dtstyle",
        "touches": touches,
        "tags": tags,
        "description": description,
        "modversions": _modversions_for(touches),
        "darktable_version": "5.4",
        "source": "expressive-baseline",
        "license": "MIT",
    }
    if mask_spec is not None:
        entry["mask_spec"] = mask_spec
    return entry


def _modversions_for(touches: list[str]) -> dict[str, int]:
    from chemigram.core.vocab._modversion_drift import known_pinned_modversions

    pinned = known_pinned_modversions()
    fallbacks = {"exposure": 7, "vignette": 4}
    return {op: pinned.get(op, fallbacks.get(op, 1)) for op in touches}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


BUILDERS = [
    look_wildlife_subject_sharpen,
    look_wildlife_background_blur,
    look_wildlife_eye_lift,
    look_wildlife_high_iso_recovery,
    look_wildlife_natural_warm,
    look_food_appetizing_warm,
    look_food_orange_pop,
    look_food_green_natural,
    look_food_texture_subtle,
    look_product_packshot_clean,
]


def main() -> None:
    new_entries: list[dict] = []
    for builder in BUILDERS:
        _name, _desc, entry, _plugins = builder()
        new_entries.append(entry)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    new_names = {e["name"] for e in new_entries}
    manifest["entries"] = [e for e in manifest["entries"] if e["name"] not in new_names]
    manifest["entries"].extend(new_entries)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  appended {len(new_entries)} entries to {MANIFEST_PATH.relative_to(REPO)}")


if __name__ == "__main__":
    main()
