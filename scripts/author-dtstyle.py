#!/usr/bin/env python3
"""Programmatic .dtstyle authoring tool — RFC-012 / Path C technique formalized.

For each darktable iop module we want to author vocabulary entries for, this
tool maps the C struct ``dt_iop_<module>_params_t`` (from
``src/iop/<module>.c`` in the darktable source tree) to a Python encoder
that produces a binary blob compatible with what darktable's
``DT_MODULE_INTROSPECTION(N, ...)`` decoder expects.

The encoders below are the canonical reference for how each module's
op_params bytes are laid out. When authoring a vocabulary entry by hand
in darktable's GUI and saving as a style, the resulting file's
``<op_params>`` should byte-match the output of the corresponding encoder
when the same parameter values are passed.

That byte-match is the validation test the user runs after authoring
manually: ``diff hand_authored.dtstyle programmatic.dtstyle`` should
show only metadata differences (timestamps, names, descriptions) — never
``<op_params>`` differences.

This file is a reference + test helper, not the runtime authoring tool
the agent uses (the agent reads this, generates entries, and writes
``.dtstyle`` files into ``vocabulary/packs/<pack>/layers/...``).

darktable version: 5.4.1.
"""

from __future__ import annotations

import struct

# Default blendop_params blob — the standard "default blend mode, no
# mask, fully opaque" gz-compressed value seen across many existing
# saved styles. Same blob used in the starter pack.
DEFAULT_BLENDOP = "gz08eJxjYGBgYAFiCQYYOOHEgAZY0QWAgBGLGANDgz0Ej1Q+dlAx68oBEMbFxwX+AwGIBgCbGCeh"


# ---------------------------------------------------------------------------
# grain — DT_MODULE_INTROSPECTION(2, dt_iop_grain_params_t)  [16 bytes]
# Source: darktable 5.4.1 src/iop/grain.c:62-71
# ---------------------------------------------------------------------------

# Channel enum (src/iop/grain.c:54-60):
GRAIN_CHANNEL_HUE = 0
GRAIN_CHANNEL_SATURATION = 1
GRAIN_CHANNEL_LIGHTNESS = 2  # default
GRAIN_CHANNEL_RGB = 3

GRAIN_SCALE_FACTOR = 213.2  # src/iop/grain.c:44


def grain_blob(
    *,
    channel: int = GRAIN_CHANNEL_LIGHTNESS,
    scale_um: float = 1600.0,
    strength: float = 25.0,
    midtones_bias: float = 100.0,
) -> str:
    """Encode a grain v2 op_params blob.

    Args:
        channel: 0=HUE, 1=SAT, 2=LIGHTNESS (default), 3=RGB.
        scale_um: coarseness in micrometers (UI-displayed value).
            Internally divided by GRAIN_SCALE_FACTOR. Default 1600 µm.
            Range: 20 µm (very fine) to 6400 µm (very coarse).
        strength: 0-100, default 25.
        midtones_bias: 0-100, default 100. Lower values bias grain
            toward shadows.
    """
    return struct.pack(
        "<ifff",
        channel,
        scale_um / GRAIN_SCALE_FACTOR,
        strength,
        midtones_bias,
    ).hex()


# ---------------------------------------------------------------------------
# vignette — DT_MODULE_INTROSPECTION(4, dt_iop_vignette_params_t)  [44 bytes]
# Source: darktable 5.4.1 src/iop/vignette.c:61-73
# ---------------------------------------------------------------------------


def vignette_blob(
    *,
    scale: float = 80.0,
    falloff_scale: float = 50.0,
    brightness: float = -0.5,
    saturation: float = -0.5,
    center_x: float = 0.0,
    center_y: float = 0.0,
    autoratio: bool = False,
    whratio: float = 1.0,
    shape: float = 1.0,
    dithering: int = 0,  # 0=off, 1=8-bit, 2=16-bit
    unbound: bool = True,
) -> str:
    """Encode a vignette v4 op_params blob.

    Args (all calibrated to darktable's UI ranges):
        scale: fall-off start, percent of largest image dim. 0-200, default 80.
        falloff_scale: fall-off radius. 0-200, default 50.
        brightness: -1 to 1, default -0.5 (more negative = darker corners).
        saturation: -1 to 1, default -0.5.
        center_x, center_y: -1 to 1, default 0 (center).
        autoratio: when True, vignette uses image aspect ratio.
        whratio: 0-2, default 1.0.
        shape: 0-5, default 1.0 (circular).
        dithering: 0=off (default), 1=8-bit, 2=16-bit.
        unbound: True (default) = clip values to [0,1].
    """
    # Layout: 6 floats + 1 int (autoratio) + 2 floats + 1 uint (dithering) + 1 int (unbound)
    return struct.pack(
        "<ffffffiffIi",
        scale,
        falloff_scale,
        brightness,
        saturation,
        center_x,
        center_y,
        1 if autoratio else 0,
        whratio,
        shape,
        dithering,
        1 if unbound else 0,
    ).hex()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_dtstyle(
    *,
    name: str,
    description: str,
    operation: str,
    modversion: int,
    op_params: str,
    blendop_params: str = DEFAULT_BLENDOP,
    blendop_version: int = 14,
    multi_priority: int = 0,
    multi_name: str = "",
) -> str:
    """Render a single-plugin .dtstyle file as a string.

    The agent calls this and writes the output to
    ``vocabulary/packs/<pack>/layers/.../entry.dtstyle``.
    """
    multi_name_xml = f"<multi_name>{multi_name}</multi_name>"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<darktable_style version="1.0">'
        f"<info><name>{name}</name><description>{description}</description></info>"
        "<style>"
        "<plugin>"
        f"<num>0</num><module>{modversion}</module><operation>{operation}</operation>"
        f"<op_params>{op_params}</op_params>"
        "<enabled>1</enabled>"
        f"<blendop_params>{blendop_params}</blendop_params>"
        f"<blendop_version>{blendop_version}</blendop_version>"
        f"<multi_priority>{multi_priority}</multi_priority>"
        f"{multi_name_xml}"
        "<multi_name_hand_edited>0</multi_name_hand_edited>"
        "</plugin>"
        "</style></darktable_style>\n"
    )


if __name__ == "__main__":
    # Smoke test — print known blobs against expected sizes.
    print("grain default:", grain_blob())
    print("  size:", len(bytes.fromhex(grain_blob())), "bytes (expect 16)")
    print()
    print("vignette default:", vignette_blob())
    print("  size:", len(bytes.fromhex(vignette_blob())), "bytes (expect 44)")
