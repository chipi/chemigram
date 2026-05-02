"""Pixel-level assertion library for reference-image validation (RFC-019).

A small toolkit for color-accuracy and tonal-response assertions against
synthetic reference targets (CC24 patches, grayscale ramps). Hand-rolled
sRGB ↔ CIE L\\*a\\*b\\* D50 conversion + Delta E 2000 — no ``colour-science``
or ``numpy`` dependency, only Pillow.

Public API
----------

- :func:`srgb_to_lab` — convert an sRGB triple to CIE L\\*a\\*b\\* D50
- :func:`lab_to_srgb` — inverse, with sRGB gamut clipping
- :func:`delta_e_2000` — CIE DE2000 perceptual color difference
- :func:`extract_patch_values` — sample mean L\\*a\\*b\\* per patch from an image
- :func:`assert_color_accuracy` — mean / max Delta E vs reference patches
- :func:`assert_tonal_response` — gamma fit + linearity R² for a grayscale
- :func:`assert_exposure_shift` — directional L\\* shift between two patch sets
- :func:`assert_wb_shift` — directional b\\*-axis shift on neutral patches

Reference colour-math sources
-----------------------------

- Lindbloom XYZ ↔ Lab conversion: https://www.brucelindbloom.com/index.html?Eqn_Lab_to_XYZ.html
- Lindbloom sRGB ↔ XYZ matrix (D50 RGB → XYZ): https://www.brucelindbloom.com/Eqn_RGB_XYZ_Matrix.html
- Sharma, Wu & Dalal (2005) "The CIEDE2000 color-difference formula" —
  the canonical DE2000 algorithm; this module follows the
  Lindbloom DE2000 reference implementation
  https://www.brucelindbloom.com/Eqn_DeltaE_CIE2000.html
- X-Rite ColorChecker24 published L\\*a\\*b\\* D50 values (post-Nov 2014) —
  see ``docs/guides/standardized-testing.md`` for the table.

Design notes
------------

The decision to hand-roll DE2000 + sRGB↔Lab (rather than depend on
``colour-science``) is documented in RFC-019 v0.2. Rationale: the
``colour-science`` package brings in numpy and ~50 MB of transitive
deps; the project's existing pixel work uses Pillow only. Hand-rolled
is ~150 lines of pure Python and trivial to audit. If we ever ship a
hot path that needs vectorized colour math, swap in ``colour-science``
behind this module's interface.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

# ----- Reference values -----------------------------------------------------

# D50 reference white (CIE 1931 2° observer), normalized so Y=1.0.
# Used for Lab ↔ XYZ conversion. Source: CIE 15:2004.
_D50_XYZ = (0.96422, 1.00000, 0.82521)

# sRGB → XYZ D50 matrix (Bradford-adapted from D65 to D50). Source: Lindbloom.
# https://www.brucelindbloom.com/Eqn_RGB_XYZ_Matrix.html (sRGB row, D50 column)
_M_SRGB_TO_XYZ_D50 = (
    (0.4360747, 0.3850649, 0.1430804),
    (0.2225045, 0.7168786, 0.0606169),
    (0.0139322, 0.0971045, 0.7141733),
)

# Inverse — XYZ D50 → sRGB.
_M_XYZ_D50_TO_SRGB = (
    (3.1338561, -1.6168667, -0.4906146),
    (-0.9787684, 1.9161415, 0.0334540),
    (0.0719453, -0.2289914, 1.4052427),
)


# ----- sRGB ↔ Linear -------------------------------------------------------


def _srgb_to_linear(c: float) -> float:
    """sRGB gamma decode. Input in [0, 1]."""
    if c <= 0.04045:
        return c / 12.92
    return float(((c + 0.055) / 1.055) ** 2.4)


def _linear_to_srgb(c: float) -> float:
    """sRGB gamma encode. Input in [0, 1]; output clipped to [0, 1]."""
    if c <= 0.0031308:
        v = 12.92 * c
    else:
        v = 1.055 * (c ** (1.0 / 2.4)) - 0.055
    return max(0.0, min(1.0, v))


# ----- Lab ↔ XYZ (D50 illuminant) -----------------------------------------

_LAB_EPSILON = 216.0 / 24389.0  # 0.008856
_LAB_KAPPA = 24389.0 / 27.0  # 903.296...


def _lab_f(t: float) -> float:
    if t > _LAB_EPSILON:
        return float(t ** (1.0 / 3.0))
    return (_LAB_KAPPA * t + 16.0) / 116.0


def _lab_f_inv(t: float) -> float:
    t3 = t * t * t
    if t3 > _LAB_EPSILON:
        return t3
    return (116.0 * t - 16.0) / _LAB_KAPPA


def _xyz_to_lab(x: float, y: float, z: float) -> tuple[float, float, float]:
    fx = _lab_f(x / _D50_XYZ[0])
    fy = _lab_f(y / _D50_XYZ[1])
    fz = _lab_f(z / _D50_XYZ[2])
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return L, a, b


def _lab_to_xyz(L: float, a: float, b: float) -> tuple[float, float, float]:
    fy = (L + 16.0) / 116.0
    fx = fy + a / 500.0
    fz = fy - b / 200.0
    x = _D50_XYZ[0] * _lab_f_inv(fx)
    y = _D50_XYZ[1] * _lab_f_inv(fy)
    z = _D50_XYZ[2] * _lab_f_inv(fz)
    return x, y, z


def _matmul3(
    m: tuple[tuple[float, ...], ...],
    v: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


# ----- sRGB → Lab D50 (public) --------------------------------------------


def srgb_to_lab(
    srgb: tuple[int, int, int] | tuple[float, float, float],
) -> tuple[float, float, float]:
    """Convert an sRGB triple to CIE L\\*a\\*b\\* D50.

    Accepts either 0..255 ints or 0.0..1.0 floats. Output (L, a, b)
    where L is in [0, 100] and a, b are in roughly [-128, 128].
    """
    r, g, b = srgb
    if isinstance(r, int) or r > 1.0:
        r, g, b = r / 255.0, g / 255.0, b / 255.0
    rl, gl, bl = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    x, y, z = _matmul3(_M_SRGB_TO_XYZ_D50, (rl, gl, bl))
    return _xyz_to_lab(x, y, z)


def lab_to_srgb(lab: tuple[float, float, float]) -> tuple[int, int, int]:
    """Convert CIE L\\*a\\*b\\* D50 to sRGB (0..255 ints, gamut-clipped)."""
    L, a, b = lab
    x, y, z = _lab_to_xyz(L, a, b)
    rl, gl, bl = _matmul3(_M_XYZ_D50_TO_SRGB, (x, y, z))
    r = round(_linear_to_srgb(rl) * 255)
    g = round(_linear_to_srgb(gl) * 255)
    bb = round(_linear_to_srgb(bl) * 255)
    return r, g, bb


# ----- Delta E 2000 -------------------------------------------------------


def delta_e_2000(
    lab1: tuple[float, float, float],
    lab2: tuple[float, float, float],
    *,
    kL: float = 1.0,
    kC: float = 1.0,
    kH: float = 1.0,
) -> float:
    """CIE DE2000 perceptual color difference.

    Pure-Python, no numpy. Follows the Lindbloom reference implementation
    of the Sharma/Wu/Dalal 2005 formulation. Returns Delta E in the same
    units as ``lab*`` inputs (Δ E ≈ 1 ≈ just-noticeable difference).
    """
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    avg_L = (L1 + L2) / 2.0
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    avg_C = (C1 + C2) / 2.0

    G = 0.5 * (1.0 - math.sqrt((avg_C**7) / (avg_C**7 + 25.0**7)))
    a1p = a1 * (1.0 + G)
    a2p = a2 * (1.0 + G)

    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)
    avg_Cp = (C1p + C2p) / 2.0

    h1p = math.degrees(math.atan2(b1, a1p)) % 360.0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360.0

    if abs(h1p - h2p) > 180.0:
        avg_Hp = (h1p + h2p + 360.0) / 2.0
    else:
        avg_Hp = (h1p + h2p) / 2.0

    T = (
        1.0
        - 0.17 * math.cos(math.radians(avg_Hp - 30.0))
        + 0.24 * math.cos(math.radians(2 * avg_Hp))
        + 0.32 * math.cos(math.radians(3 * avg_Hp + 6.0))
        - 0.20 * math.cos(math.radians(4 * avg_Hp - 63.0))
    )

    delta_hp = h2p - h1p
    if abs(delta_hp) > 180.0:
        if h2p <= h1p:
            delta_hp += 360.0
        else:
            delta_hp -= 360.0

    delta_Lp = L2 - L1
    delta_Cp = C2p - C1p
    delta_Hp = 2.0 * math.sqrt(C1p * C2p) * math.sin(math.radians(delta_hp / 2.0))

    SL = 1.0 + (0.015 * (avg_L - 50.0) ** 2) / math.sqrt(20.0 + (avg_L - 50.0) ** 2)
    SC = 1.0 + 0.045 * avg_Cp
    SH = 1.0 + 0.015 * avg_Cp * T

    delta_theta = 30.0 * math.exp(-(((avg_Hp - 275.0) / 25.0) ** 2))
    RC = 2.0 * math.sqrt((avg_Cp**7) / (avg_Cp**7 + 25.0**7))
    RT = -RC * math.sin(2.0 * math.radians(delta_theta))

    return math.sqrt(
        (delta_Lp / (kL * SL)) ** 2
        + (delta_Cp / (kC * SC)) ** 2
        + (delta_Hp / (kH * SH)) ** 2
        + RT * (delta_Cp / (kC * SC)) * (delta_Hp / (kH * SH))
    )


# ----- Patch extraction ----------------------------------------------------


@dataclass(frozen=True)
class PatchCoord:
    """A rectangular sample region in pixel coordinates: (x, y, width, height)."""

    x: int
    y: int
    w: int
    h: int


def _mean_rgb_in_box(
    img: Image.Image, box: tuple[int, int, int, int]
) -> tuple[float, float, float]:
    region = img.crop(box).convert("RGB")
    r_band, g_band, b_band = region.split()

    def _band_mean(band: Image.Image) -> float:
        hist = band.histogram()
        n = sum(hist)
        if n == 0:
            return 0.0
        return float(sum(i * c for i, c in enumerate(hist)) / n)

    return _band_mean(r_band), _band_mean(g_band), _band_mean(b_band)


def extract_patch_values(
    image: Path | Image.Image,
    coords: Sequence[PatchCoord],
) -> list[tuple[float, float, float]]:
    """Sample mean sRGB → Lab D50 per patch.

    Returns one (L, a, b) tuple per coordinate, in input order.
    """
    img = image if isinstance(image, Image.Image) else Image.open(image).convert("RGB")
    out: list[tuple[float, float, float]] = []
    for c in coords:
        box = (c.x, c.y, c.x + c.w, c.y + c.h)
        r, g, b = _mean_rgb_in_box(img, box)
        out.append(srgb_to_lab((r, g, b)))
    return out


# ----- Assertion result types ---------------------------------------------


@dataclass(frozen=True)
class ColorAccuracyResult:
    """Outcome of :func:`assert_color_accuracy`."""

    passed: bool
    mean_de: float
    max_de: float
    per_patch: tuple[float, ...]
    threshold_mean: float
    threshold_max: float


@dataclass(frozen=True)
class TonalResponseResult:
    """Outcome of :func:`assert_tonal_response`."""

    passed: bool
    r_squared: float
    threshold_r_squared: float


# ----- Public assertions ---------------------------------------------------


def assert_color_accuracy(
    measured: Sequence[tuple[float, float, float]],
    reference: Sequence[tuple[float, float, float]],
    *,
    max_mean_de: float = 3.0,
    max_max_de: float = 6.0,
    skip_indices: Sequence[int] = (),
) -> ColorAccuracyResult:
    """Compare measured Lab patches to a reference, report Delta E 2000.

    ``skip_indices`` excludes specific patches from mean/max thresholds —
    e.g., out-of-gamut patches that synthetic CC24 clips. The Delta E is
    still computed and reported; just not enforced.
    """
    if len(measured) != len(reference):
        raise ValueError(
            f"measured ({len(measured)}) and reference ({len(reference)}) must have the same length"
        )
    skip = set(skip_indices)
    de_per: list[float] = [delta_e_2000(m, r) for m, r in zip(measured, reference, strict=True)]
    enforced = [d for i, d in enumerate(de_per) if i not in skip]
    if not enforced:
        raise ValueError("all patches skipped; no enforcement possible")
    mean_de = sum(enforced) / len(enforced)
    max_de = max(enforced)
    return ColorAccuracyResult(
        passed=mean_de <= max_mean_de and max_de <= max_max_de,
        mean_de=mean_de,
        max_de=max_de,
        per_patch=tuple(de_per),
        threshold_mean=max_mean_de,
        threshold_max=max_max_de,
    )


def assert_tonal_response(
    measured_L: Sequence[float],
    reference_L: Sequence[float],
    *,
    min_r_squared: float = 0.98,
) -> TonalResponseResult:
    """Linear regression R² of measured L\\* against reference L\\*.

    Used for grayscale tonal-response checks. R² ≈ 1.0 means the rendered
    grayscale ramp tracks the reference linearly; lower means the tone
    curve has been bent.
    """
    if len(measured_L) != len(reference_L):
        raise ValueError("measured and reference must have the same length")
    n = len(measured_L)
    if n < 2:
        raise ValueError("need at least 2 points for tonal-response R²")
    mean_x = sum(reference_L) / n
    mean_y = sum(measured_L) / n
    ss_tot = sum((y - mean_y) ** 2 for y in measured_L)
    if ss_tot == 0:
        # Degenerate — measured is constant. Treat as failed unless reference also constant.
        return TonalResponseResult(passed=False, r_squared=0.0, threshold_r_squared=min_r_squared)
    sxx = sum((x - mean_x) ** 2 for x in reference_L)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(reference_L, measured_L, strict=True))
    if sxx == 0:
        return TonalResponseResult(passed=False, r_squared=0.0, threshold_r_squared=min_r_squared)
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    ss_res = sum(
        (y - (slope * x + intercept)) ** 2 for x, y in zip(reference_L, measured_L, strict=True)
    )
    r_squared = 1.0 - ss_res / ss_tot
    return TonalResponseResult(
        passed=r_squared >= min_r_squared,
        r_squared=r_squared,
        threshold_r_squared=min_r_squared,
    )


def assert_exposure_shift(
    baseline_lab: Sequence[tuple[float, float, float]],
    shifted_lab: Sequence[tuple[float, float, float]],
    *,
    direction: int,
    min_magnitude: float = 1.0,
) -> bool:
    """``direction`` is +1 for "expected to brighten", -1 for "expected to darken".

    Returns True if the mean L\\* shift is in the expected direction with
    magnitude ≥ ``min_magnitude``.
    """
    if direction not in (-1, 1):
        raise ValueError(f"direction must be +1 or -1, got {direction}")
    base_L = sum(p[0] for p in baseline_lab) / len(baseline_lab)
    shift_L = sum(p[0] for p in shifted_lab) / len(shifted_lab)
    delta = shift_L - base_L
    return (delta * direction) >= min_magnitude


def assert_wb_shift(
    baseline_lab: Sequence[tuple[float, float, float]],
    shifted_lab: Sequence[tuple[float, float, float]],
    *,
    axis: str = "b",
    direction: int,
    min_magnitude: float = 0.5,
) -> bool:
    """Direction-of-change on the ``a*`` (red↔green) or ``b*`` (yellow↔blue)
    axis. ``direction`` +1 = positive shift expected (warmer for b*, redder
    for a*); -1 = negative.
    """
    if axis not in ("a", "b"):
        raise ValueError(f"axis must be 'a' or 'b', got {axis!r}")
    if direction not in (-1, 1):
        raise ValueError(f"direction must be +1 or -1, got {direction}")
    idx = 1 if axis == "a" else 2
    base = sum(p[idx] for p in baseline_lab) / len(baseline_lab)
    shifted = sum(p[idx] for p in shifted_lab) / len(shifted_lab)
    delta = shifted - base
    return (delta * direction) >= min_magnitude
