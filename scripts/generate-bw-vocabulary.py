#!/usr/bin/env python3
"""Generate the B&W conversion vocabulary — bw_convert primitive + look_bw_* L2 family.

Closes Gap #1 of the photographer-workflows survey (6/6 universal in B&W;
3/6 in Wedding for the B&W-as-parallel-deliverable pattern). Authors:

- ``bw_convert`` — parameterized L3 primitive. Single colorequal plugin
  with all 8 sat axes saturation-killed (sat_X = -1.0); exposes 8
  bright_X parameters that emulate Adams-school color-filter strength
  per hue band (bright_red lightens reds; bright_blue darkens skies;
  etc.).
- ``look_bw_*`` — 5 L2 composite looks built on top: classic neutral,
  high-contrast chiaroscuro, dramatic landscape, split-tone warm-
  shadows, Silver-Efex zone-balanced.

Re-runnable; idempotent.

Inputs (read-only): existing primitive .dtstyle baselines.
Outputs (overwritten):
- ``vocabulary/packs/expressive-baseline/layers/L3/colorequal/bw_convert.dtstyle``
- ``vocabulary/packs/expressive-baseline/layers/L2/look/look_bw_*.dtstyle`` (5)
- 6 manifest entries appended to the pack manifest.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PACK = REPO / "vocabulary" / "packs" / "expressive-baseline"
L2_DIR = PACK / "layers" / "L2" / "look"
L3_COLOREQUAL_DIR = PACK / "layers" / "L3" / "colorequal"
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
}


def _read_op_params(rel: str) -> str:
    text = (PACK / rel).read_text(encoding="utf-8")
    m = re.search(r"<op_params>([^<]+)</op_params>", text)
    if not m:
        raise SystemExit(f"no <op_params> in {rel}")
    return m.group(1)


# ---------------------------------------------------------------------------
# Build the bw_convert baseline op_params
# ---------------------------------------------------------------------------


def _bw_convert_op_params() -> str:
    """The bw_convert baseline: hsl_saturation.dtstyle blob with all 8
    sat_X axes set to -1.0 (full saturation kill = grayscale)."""
    from chemigram.core.parameterize import colorequal

    base = _read_op_params("layers/L3/colorequal/hsl_saturation.dtstyle")
    return colorequal.patch(
        base,
        sat_red=-1.0,
        sat_orange=-1.0,
        sat_yellow=-1.0,
        sat_green=-1.0,
        sat_cyan=-1.0,
        sat_blue=-1.0,
        sat_lavender=-1.0,
        sat_magenta=-1.0,
    )


# ---------------------------------------------------------------------------
# .dtstyle XML builders
# ---------------------------------------------------------------------------


_IOP_LIST = "colorin,demosaic,temperature,exposure,colorbalancergb,bilat,grain,sigmoid,colorout"


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


# ---------------------------------------------------------------------------
# bw_convert primitive
# ---------------------------------------------------------------------------


def _author_bw_convert() -> dict:
    """Author bw_convert.dtstyle + return its manifest entry."""
    L3_COLOREQUAL_DIR.mkdir(parents=True, exist_ok=True)
    op_params = _bw_convert_op_params()
    plugin = _make_plugin(num=0, operation="colorequal", op_params=op_params)
    desc = (
        "B&W conversion (RFC-033 follow-up; survey Gap #1). Single colorequal "
        "plugin with all 8 sat axes set to -1.0 (full saturation kill = "
        "grayscale). Exposes 8 bright_X parameters emulating Adams-school "
        "color-filter strength: bright_red +0.3 lightens skin / red flowers / "
        "darkens skies in B&W; bright_blue -0.2 darkens skies; bright_green "
        "+0.3 lightens foliage; etc. The chemigram analog of Photoshop "
        "Channel Mixer (Monochrome) and Silver Efex Color Filters. "
        "Universal Step 1 of any B&W workflow per the photographer survey "
        "(6/6 photographers reach for color-filter-driven conversion as "
        "their foundational B&W move)."
    )
    dtstyle_path = L3_COLOREQUAL_DIR / "bw_convert.dtstyle"
    dtstyle_path.write_text(
        _make_dtstyle(name="bw_convert", description=desc, plugins=[plugin]),
        encoding="utf-8",
    )
    print(f"  wrote {dtstyle_path.relative_to(REPO)}")

    # Parameter declarations: 8 brightness axes (the channel-filter mental
    # model). Range [-1.0, 1.0] matching colorequal's brightness convention.
    # Default 0.0 (neutral conversion). Field offsets per colorequal struct
    # — bright_X axes start at field index 23 (offset 92).
    params = []
    for axis_idx, axis_name in enumerate(
        [
            "bright_red",
            "bright_orange",
            "bright_yellow",
            "bright_green",
            "bright_cyan",
            "bright_blue",
            "bright_lavender",
            "bright_magenta",
        ]
    ):
        offset = (23 + axis_idx) * 4
        params.append(
            {
                "name": axis_name,
                "type": "float",
                "range": [-1.0, 1.0],
                "default": 0.0,
                "field": {
                    "module": "colorequal",
                    "modversion": 4,
                    "offset": offset,
                    "encoding": "le_f32",
                },
            }
        )

    return {
        "name": "bw_convert",
        "layer": "L3",
        "subtype": "colorequal",
        "path": "layers/L3/colorequal/bw_convert.dtstyle",
        "touches": ["colorequal"],
        "_test_coverage_exempt": (
            "Survey Gap #1 (6/6 B&W universal). Lab-grade global / lab-grade "
            "masked / visual proof tiers require human review of channel-"
            "filter rendering against representative B&W test images — "
            "natural skin tone in B&W vs. red-filter-darkened sky vs. "
            "green-filter-lightened foliage are visual judgments per ADR-080. "
            "Unit + integration coverage ships; lab-grade lands alongside the "
            "darkroom-session sign-off."
        ),
        "tags": [
            "bw",
            "monochrome",
            "channel-mixer",
            "color-filter",
            "fundamental",
            "global",
            "parameterized",
            "multi-axis",
        ],
        "description": desc,
        "modversions": {"colorequal": 4},
        "darktable_version": "5.4",
        "source": "expressive-baseline",
        "license": "MIT",
        "parameters": params,
    }


# ---------------------------------------------------------------------------
# look_bw_* L2 entries
# ---------------------------------------------------------------------------


def _author_look_bw_classic_neutral() -> dict:
    """Default B&W conversion — neutral channel weighting, mid contrast,
    mild structure."""
    from chemigram.core.parameterize import bilat, sigmoid

    base_sigmoid = _read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
    base_bilat = _read_op_params("layers/L3/localcontrast/bilat_clarity_strength.dtstyle")
    plugins = [
        _make_plugin(num=10, operation="colorequal", op_params=_bw_convert_op_params()),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(base_sigmoid, contrast=1.3)
        ),
        _make_plugin(
            num=12,
            operation="bilat",
            op_params=bilat.patch(base_bilat, clarity_strength=0.3),
        ),
    ]
    name = "look_bw_classic_neutral"
    desc = (
        "Classic B&W foundation — neutral channel weighting (no filter), "
        "mid contrast (sigmoid 1.3), mild structure (clarity 0.3). The "
        "starting point for any B&W work; compose with split-tone or "
        "chiaroscuro variants for stylistic direction. Per RFC-033 / "
        "survey Gap #1."
    )
    return _l2_manifest(name, desc, ["colorequal", "sigmoid", "bilat"], plugins)


def _author_look_bw_high_contrast_chiaroscuro() -> dict:
    """Tucker/Thompson-style chiaroscuro — strong contrast, deep shadows."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    base_sigmoid = _read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
    base_cb = _read_op_params("layers/L3/colorbalancergb/brilliance_global.dtstyle")
    plugins = [
        _make_plugin(num=10, operation="colorequal", op_params=_bw_convert_op_params()),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(base_sigmoid, contrast=1.7)
        ),
        _make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                base_cb, brilliance_shadows=-0.20, brilliance_highlights=0.10
            ),
        ),
    ]
    name = "look_bw_high_contrast_chiaroscuro"
    desc = (
        "Tucker/Thompson-style chiaroscuro B&W — strong sigmoid contrast "
        "(1.7), deep shadow brilliance (-0.20), lifted highlight brilliance "
        "(+0.10). For street/portrait B&W where dramatic light-shadow "
        "interplay defines the image. Compose with mask_subject for "
        "directional facial sculpting (Tucker portrait discipline)."
    )
    return _l2_manifest(name, desc, ["colorequal", "sigmoid", "colorbalancergb"], plugins)


def _author_look_bw_landscape_dramatic() -> dict:
    """Page/Adamus B&W landscape — storm clouds, deep shadows, sky pop."""
    from chemigram.core.parameterize import bilat, colorequal, sigmoid

    base_sigmoid = _read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
    base_bilat = _read_op_params("layers/L3/localcontrast/bilat_clarity_strength.dtstyle")
    base_colorequal = _read_op_params("layers/L3/colorequal/hsl_saturation.dtstyle")

    # Apply red-filter conversion: sat all -1.0 + bright_red +0.2 (lightens
    # warm tones / land) + bright_blue -0.3 (darkens skies for drama)
    bw_with_red_filter = colorequal.patch(
        base_colorequal,
        sat_red=-1.0,
        sat_orange=-1.0,
        sat_yellow=-1.0,
        sat_green=-1.0,
        sat_cyan=-1.0,
        sat_blue=-1.0,
        sat_lavender=-1.0,
        sat_magenta=-1.0,
        bright_red=0.20,
        bright_blue=-0.30,
    )

    plugins = [
        _make_plugin(num=10, operation="colorequal", op_params=bw_with_red_filter),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(base_sigmoid, contrast=1.6)
        ),
        _make_plugin(
            num=12,
            operation="bilat",
            op_params=bilat.patch(base_bilat, clarity_strength=0.5),
        ),
    ]
    name = "look_bw_landscape_dramatic"
    desc = (
        "Page/Adamus dramatic B&W landscape — red-filter-emulated "
        "conversion (bright_red +0.20 lightens land; bright_blue -0.30 "
        "darkens skies — the classic Adams-school red filter for storm-"
        "cloud drama). Sigmoid contrast 1.6 + clarity 0.5. For stormy "
        "skies, rugged terrain, weather drama. The B&W counterpart of "
        "look_landscape_dramatic_moody."
    )
    return _l2_manifest(name, desc, ["colorequal", "sigmoid", "bilat"], plugins)


def _author_look_bw_split_tone_warm_shadows() -> dict:
    """Sepia/selenium evocation — warm shadows + cool highlights."""
    from chemigram.core.parameterize import colorbalancergb, sigmoid

    base_sigmoid = _read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
    base_cb = _read_op_params("layers/L3/colorbalancergb/brilliance_global.dtstyle")
    plugins = [
        _make_plugin(num=10, operation="colorequal", op_params=_bw_convert_op_params()),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(base_sigmoid, contrast=1.35)
        ),
        _make_plugin(
            num=12,
            operation="colorbalancergb",
            op_params=colorbalancergb.patch(
                base_cb,
                hue_shadows=30.0,
                saturation_shadows=0.05,
                hue_highlights=210.0,
                saturation_highlights=0.03,
            ),
        ),
    ]
    name = "look_bw_split_tone_warm_shadows"
    desc = (
        "Subtle warm-shadows toned B&W — sepia / selenium print evocation. "
        "Neutral B&W conversion + mid-strong sigmoid contrast (1.35) + "
        "warm-tone shadows (hue 30, sat 0.05) + cool-tone highlights "
        "(hue 210, sat 0.03). The split-tone tinting reads as 'toned print' "
        "rather than pure neutral B&W."
    )
    return _l2_manifest(name, desc, ["colorequal", "sigmoid", "colorbalancergb"], plugins)


def _author_look_bw_silver_efex_zone_balanced() -> dict:
    """Whalley/Boutwell zone-system-aware balanced B&W — restraint discipline."""
    from chemigram.core.parameterize import bilat, sigmoid

    base_sigmoid = _read_op_params("layers/L3/sigmoid/sigmoid_contrast.dtstyle")
    base_bilat = _read_op_params("layers/L3/localcontrast/bilat_clarity_strength.dtstyle")
    plugins = [
        _make_plugin(num=10, operation="colorequal", op_params=_bw_convert_op_params()),
        _make_plugin(
            num=11, operation="sigmoid", op_params=sigmoid.patch(base_sigmoid, contrast=1.15)
        ),
        _make_plugin(
            num=12,
            operation="bilat",
            op_params=bilat.patch(base_bilat, clarity_strength=0.15),
        ),
    ]
    name = "look_bw_silver_efex_zone_balanced"
    desc = (
        "Whalley/Boutwell zone-system-aware balanced B&W — the restraint "
        "discipline applied to monochrome. Neutral conversion + gentle "
        "sigmoid contrast (1.15) + subtle clarity (0.15). The defining "
        "stylistic position for B&W work that doesn't push contrast or "
        "structure as a dramatic move; reads as 'measured tonal "
        "development' (Adams-school)."
    )
    return _l2_manifest(name, desc, ["colorequal", "sigmoid", "bilat"], plugins)


# ---------------------------------------------------------------------------
# manifest assembler
# ---------------------------------------------------------------------------


def _l2_manifest(name: str, description: str, touches: list[str], plugins: list[str]) -> dict:
    iop_extras = [op for op in touches if op not in _IOP_LIST.split(",")]
    iop_list = _IOP_LIST + ("," + ",".join(iop_extras) if iop_extras else "")
    dtstyle_path = L2_DIR / f"{name}.dtstyle"
    L2_DIR.mkdir(parents=True, exist_ok=True)
    dtstyle_path.write_text(
        _make_dtstyle(name=name, description=description, plugins=plugins, iop_list=iop_list),
        encoding="utf-8",
    )
    print(f"  wrote {dtstyle_path.relative_to(REPO)}")

    return {
        "name": name,
        "layer": "L2",
        "subtype": "look",
        "path": f"layers/L2/look/{name}.dtstyle",
        "touches": touches,
        "tags": ["look", "composite", "bw", "monochrome"]
        + (["dramatic"] if "dramatic" in name or "chiaroscuro" in name else [])
        + (["restrained"] if "balanced" in name else [])
        + (["landscape"] if "landscape" in name else [])
        + (["split-tone"] if "split_tone" in name else []),
        "description": description,
        "modversions": _modversions_for(touches),
        "darktable_version": "5.4",
        "source": "expressive-baseline",
        "license": "MIT",
    }


def _modversions_for(touches: list[str]) -> dict[str, int]:
    from chemigram.core.vocab._modversion_drift import known_pinned_modversions

    pinned = known_pinned_modversions()
    fallbacks = {"exposure": 7}
    return {op: pinned.get(op, fallbacks.get(op, 1)) for op in touches}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


L2_BUILDERS = [
    _author_look_bw_classic_neutral,
    _author_look_bw_high_contrast_chiaroscuro,
    _author_look_bw_landscape_dramatic,
    _author_look_bw_split_tone_warm_shadows,
    _author_look_bw_silver_efex_zone_balanced,
]


def main() -> None:
    new_entries: list[dict] = []
    new_entries.append(_author_bw_convert())
    for builder in L2_BUILDERS:
        new_entries.append(builder())

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
