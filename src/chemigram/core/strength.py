# ruff: noqa: C901
"""Parametric L2 strength via per-parameter interpolation (RFC-035 Path B).

L2 looks ship with fixed-value plugins. RFC-035 Path B introduces a
``strength`` parameter that interpolates each plugin's parameterized
fields between the module's identity value and the authored value:

    interpolated = identity + strength * (authored - identity)

- ``strength = 1.0`` → identity preserves authored values (current behavior).
- ``strength = 0.0`` → all fields at identity (no-op equivalent).
- ``strength = 0.5`` → halfway between identity and authored.

Only parameterized fields interpolate (sigmoid_contrast.contrast,
colorequal sat_X / hue_X / bright_X axes, exposure.ev, etc.).
Non-parameterized fields preserve the L2 look's authored values
(structural choices like sigmoid's mode, vignette's shape, etc.).

For modules without a registered parameterize decoder, plugins are
preserved at authored values regardless of strength — the strength
parameter only scales what's parameterizable. Document this in the
agent prompt template; visual-review checkpoint validates whether
this behavior is intuitive.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from chemigram.core.dtstyle import DtstyleEntry, PluginEntry

# Per-(module, axis) identity values (RFC-035 Path B).
# These are the "no-op" values for each parameterized axis — what the
# axis takes when the module's effect is null. Sourced from the
# parameterize module's documented conventions.
#
# Convention: identity for a relative parameter (shifts, deltas, gains)
# is 0.0; identity for a multiplicative parameter (scaling factors) is 1.0.
IDENTITY_VALUES: dict[str, dict[str, float]] = {
    "exposure": {
        "ev": 0.0,
    },
    "sigmoid": {
        "contrast": 1.0,
    },
    "temperature": {
        "red_coeff": 1.0,
        "green_coeff": 1.0,
        "blue_coeff": 1.0,
    },
    "bilat": {
        "clarity_strength": 0.0,
    },
    "vignette": {
        "brightness": 0.0,
    },
    "hazeremoval": {
        "strength": 0.0,
    },
    "sharpen": {
        # Sharpen amount has no clean "identity" — amount=0 still applies the
        # default radius/threshold. For strength interpolation, treat 0.5
        # as the rough "half-applied" identity (matches darktable's default).
        "amount": 0.5,
    },
    "colorbalancergb": {
        # Most axes shift around 0 (no-op = no shift)
        "saturation_global": 0.0,
        "chroma_global": 0.0,
        "vibrance": 0.0,
        "brilliance_global": 0.0,
        "brilliance_highlights": 0.0,
        "brilliance_midtones": 0.0,
        "brilliance_shadows": 0.0,
        "saturation_shadows": 0.0,
        "saturation_midtones": 0.0,
        "saturation_highlights": 0.0,
        # Hue axes have identity 0 too (no rotation)
        "hue_shadows": 0.0,
        "hue_midtones": 0.0,
        "hue_highlights": 0.0,
        "hue_angle": 0.0,
        # Weight axes stay at the module's defaults (preserved via authored values)
        "shadows_weight": 1.0,
        "highlights_weight": 1.0,
        "white_fulcrum": 0.0,
    },
    "colorequal": {
        # Saturation axes: identity = 0 (no saturation change per-band)
        "sat_red": 0.0,
        "sat_orange": 0.0,
        "sat_yellow": 0.0,
        "sat_green": 0.0,
        "sat_cyan": 0.0,
        "sat_blue": 0.0,
        "sat_lavender": 0.0,
        "sat_magenta": 0.0,
        # Hue axes: identity = 0 (no hue rotation per-band)
        "hue_red": 0.0,
        "hue_orange": 0.0,
        "hue_yellow": 0.0,
        "hue_green": 0.0,
        "hue_cyan": 0.0,
        "hue_blue": 0.0,
        "hue_lavender": 0.0,
        "hue_magenta": 0.0,
        # Brightness axes: identity = 0 (no brightness change per-band)
        "bright_red": 0.0,
        "bright_orange": 0.0,
        "bright_yellow": 0.0,
        "bright_green": 0.0,
        "bright_cyan": 0.0,
        "bright_blue": 0.0,
        "bright_lavender": 0.0,
        "bright_magenta": 0.0,
    },
    "denoiseprofile": {
        "denoise_strength": 1.0,  # default; identity per docs
        "denoise_radius": 1.0,
        "denoise_scattering": 0.0,
        "denoise_shadows": 1.0,
    },
    "grain": {
        "grain_strength": 0.0,
    },
}


def interpolate_plugin_strength(
    plugin: PluginEntry,
    strength: float,
) -> PluginEntry:
    """Return a new PluginEntry with parameterized fields interpolated
    between identity and the plugin's authored values by ``strength``.

    Args:
        plugin: A PluginEntry from an L2 look's dtstyle.
        strength: 1.0 = preserve authored; 0.0 = identity (no-op);
            0.5 = halfway. Outside [0, 1] is clamped at the boundaries
            (the manifest range validation typically prevents this anyway).

    Returns:
        A new PluginEntry with interpolated op_params. If the plugin's
        operation isn't in IDENTITY_VALUES (no parameterize decoder),
        returns the plugin unchanged.
    """
    strength = max(0.0, min(1.0, strength))
    if strength == 1.0:
        return plugin

    operation = plugin.operation
    if operation not in IDENTITY_VALUES:
        # No parameterize decoder for this module; preserve authored.
        return plugin

    # Decode authored op_params → tuple of field values
    decoded = _decode_op_params(operation, plugin.op_params)
    if decoded is None:
        return plugin

    # For each axis with a known identity, interpolate
    axis_identities = IDENTITY_VALUES[operation]
    interpolated_values = _interpolate_axes(operation, decoded, axis_identities, strength)

    # Re-encode with the interpolated values via the module's patch()
    new_op_params = _patch_with_values(operation, plugin.op_params, interpolated_values)
    if new_op_params is None:
        return plugin

    return dataclasses.replace(plugin, op_params=new_op_params)


def apply_strength_to_dtstyle(dtstyle: DtstyleEntry, strength: float) -> DtstyleEntry:
    """Return a new DtstyleEntry with each plugin's parameterized fields
    interpolated by ``strength``. RFC-035 Path B."""
    if strength == 1.0:
        return dtstyle
    new_plugins = tuple(interpolate_plugin_strength(p, strength) for p in dtstyle.plugins)
    return dataclasses.replace(dtstyle, plugins=new_plugins)


# ---------------------------------------------------------------------------
# Per-module decode + patch helpers
# ---------------------------------------------------------------------------


def _decode_op_params(operation: str, op_params: str) -> tuple[Any, ...] | None:
    """Dispatch decode to the right parameterize module."""
    try:
        if operation == "exposure":
            from chemigram.core.parameterize import exposure

            return exposure.decode(op_params)
        if operation == "sigmoid":
            from chemigram.core.parameterize import sigmoid

            return sigmoid.decode(op_params)
        if operation == "temperature":
            from chemigram.core.parameterize import temperature

            return temperature.decode(op_params)
        if operation == "bilat":
            from chemigram.core.parameterize import bilat

            return bilat.decode(op_params)
        if operation == "vignette":
            from chemigram.core.parameterize import vignette

            return vignette.decode(op_params)
        if operation == "hazeremoval":
            from chemigram.core.parameterize import hazeremoval

            return hazeremoval.decode(op_params)
        if operation == "sharpen":
            from chemigram.core.parameterize import sharpen

            return sharpen.decode(op_params)
        if operation == "colorbalancergb":
            from chemigram.core.parameterize import colorbalancergb

            return colorbalancergb.decode(op_params)
        if operation == "colorequal":
            from chemigram.core.parameterize import colorequal

            return colorequal.decode(op_params)
        if operation == "denoiseprofile":
            from chemigram.core.parameterize import denoiseprofile

            return denoiseprofile.decode(op_params)
        if operation == "grain":
            from chemigram.core.parameterize import grain

            return grain.decode(op_params)
    except (ValueError, ImportError, AttributeError):
        return None
    return None


def _interpolate_axes(
    operation: str,
    decoded: tuple[Any, ...],
    axis_identities: dict[str, float],
    strength: float,
) -> dict[str, float]:
    """Compute per-axis interpolated values: identity + strength * (authored - identity).

    Returns {axis_name: interpolated_value} for axes that have known
    identities and field-index mappings in the parameterize module.
    """
    result: dict[str, float] = {}
    field_map = _axis_field_map(operation)
    if field_map is None:
        return result
    for axis_name, identity in axis_identities.items():
        field_idx = field_map.get(axis_name)
        if field_idx is None:
            continue
        if field_idx >= len(decoded):
            continue
        authored = float(decoded[field_idx])
        result[axis_name] = identity + strength * (authored - identity)
    return result


def _axis_field_map(operation: str) -> dict[str, int] | None:
    """Return the {axis_name: field_index} mapping for a parameterize module."""
    try:
        if operation == "exposure":
            return {"ev": 2}
        if operation == "sigmoid":
            return {"contrast": 0}
        if operation == "temperature":
            return {"red_coeff": 0, "green_coeff": 1, "blue_coeff": 2}
        if operation == "bilat":
            return {"clarity_strength": 3}
        if operation == "vignette":
            return {"brightness": 1}
        if operation == "hazeremoval":
            return {"strength": 0}
        if operation == "sharpen":
            return {"amount": 0}
        if operation == "colorbalancergb":
            from chemigram.core.parameterize import colorbalancergb

            return colorbalancergb._AXIS_FIELD_INDICES
        if operation == "colorequal":
            from chemigram.core.parameterize import colorequal

            return colorequal._AXIS_FIELD_INDICES
        if operation == "denoiseprofile":
            from chemigram.core.parameterize import denoiseprofile

            return denoiseprofile._AXIS_FIELD_INDICES
        if operation == "grain":
            return {"grain_strength": 2}
    except (ImportError, AttributeError):
        return None
    return None


def _patch_with_values(
    operation: str,
    op_params: str,
    values: dict[str, float],
) -> str | None:
    """Dispatch patch() to the right parameterize module."""
    try:
        if operation == "exposure":
            from chemigram.core.parameterize import exposure

            if "ev" in values:
                return exposure.patch(op_params, ev=values["ev"])
        if operation == "sigmoid":
            from chemigram.core.parameterize import sigmoid

            if "contrast" in values:
                return sigmoid.patch(op_params, contrast=values["contrast"])
        if operation == "temperature":
            from chemigram.core.parameterize import temperature

            return temperature.patch(
                op_params,
                red_coeff=values.get("red_coeff"),
                green_coeff=values.get("green_coeff"),
                blue_coeff=values.get("blue_coeff"),
            )
        if operation == "bilat":
            from chemigram.core.parameterize import bilat

            if "clarity_strength" in values:
                return bilat.patch(op_params, clarity_strength=values["clarity_strength"])
        if operation == "vignette":
            from chemigram.core.parameterize import vignette

            if "brightness" in values:
                return vignette.patch(op_params, brightness=values["brightness"])
        if operation == "hazeremoval":
            from chemigram.core.parameterize import hazeremoval

            if "strength" in values:
                return hazeremoval.patch(op_params, strength=values["strength"])
        if operation == "sharpen":
            from chemigram.core.parameterize import sharpen

            if "amount" in values:
                return sharpen.patch(op_params, amount=values["amount"])
        if operation == "colorbalancergb":
            from chemigram.core.parameterize import colorbalancergb

            return colorbalancergb.patch(op_params, **values)
        if operation == "colorequal":
            from chemigram.core.parameterize import colorequal

            return colorequal.patch(op_params, **values)
        if operation == "denoiseprofile":
            from chemigram.core.parameterize import denoiseprofile

            return denoiseprofile.patch(op_params, **values)
        if operation == "grain":
            from chemigram.core.parameterize import grain

            if "grain_strength" in values:
                return grain.patch(op_params, grain_strength=values["grain_strength"])
    except (ValueError, TypeError, ImportError, AttributeError):
        return None
    return None
