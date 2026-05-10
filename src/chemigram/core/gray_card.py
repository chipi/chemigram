"""Gray-card-pick white-balance correction (RFC-postponed; survey Gap #20).

Sample a region of a rendered image at user-specified coordinates,
compute the RGB coefficients that would correct the sampled pixels to
neutral gray (R=G=B). Returns coefficients suitable for the
``temperature`` parameterized primitive (red_coeff / blue_coeff /
green_coeff).

The agent workflow:

1. ``render_preview(image_id)`` → JPEG path
2. Agent (or photographer) examines the JPEG and identifies a gray-card
   region at pixel coordinates ``(x, y)``.
3. ``wb_from_gray_card(jpeg_path, x, y)`` → ``{red_coeff, blue_coeff,
   green_coeff}``.
4. ``apply_primitive(image_id, "temperature", parameter_values=<coeffs>)``.

The math:

- Pixel sample = average RGB over a square region around ``(x, y)``.
- For a true gray card, the sampled RGB should be ``(g, g, g)`` for some g.
- The correction-to-neutral coefficients satisfy::

      sampled_R * red_coeff == sampled_G * green_coeff == sampled_B * blue_coeff

- Convention: pin ``green_coeff = 1.0`` (matches darktable's temperature
  module convention); compute ``red_coeff = G/R`` and ``blue_coeff = G/B``.
- A perfectly-neutral starting point sampled from a true gray card returns
  ``(1.0, 1.0, 1.0)`` — no correction needed.

Surfaced by R3 Food/Product genre — commercial color accuracy demands a
gray-card-anchored workflow (Zoe Noble, Karl Taylor, Darina Kopcok all
ship gray-card discipline as their Step 1). Cross-references R1 Portrait
(Woloszynowicz gray-card pick), R2 Wedding (mixed-light WB
reconciliation), R3 Wildlife (subject-based WB picker on bird's white
patch — same algorithm).

Per ADR-007 (BYOA), this is a chemigram-native primitive — no AI involved,
just pixel sampling + inverse arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class GrayCardError(Exception):
    """Raised when gray-card sampling fails (out-of-bounds, unreadable, etc.)."""


@dataclass(frozen=True)
class GrayCardCoefficients:
    """The RGB correction coefficients suitable for the ``temperature``
    primitive's ``red_coeff`` / ``blue_coeff`` / ``green_coeff`` parameters.

    Convention: ``green_coeff`` is pinned to 1.0 (the reference channel);
    ``red_coeff`` and ``blue_coeff`` express how much the red and blue
    channels need to be multiplied to bring the sample to neutral.
    """

    red_coeff: float
    blue_coeff: float
    green_coeff: float = 1.0
    sampled_r: float = 0.0
    sampled_g: float = 0.0
    sampled_b: float = 0.0
    sample_radius: int = 0

    def as_parameter_values(self) -> dict[str, float]:
        """Return a dict suitable for ``apply_primitive(..., parameter_values=...)``
        when the primitive is ``temperature``."""
        return {
            "red_coeff": self.red_coeff,
            "green_coeff": self.green_coeff,
            "blue_coeff": self.blue_coeff,
        }


def wb_from_gray_card(
    image_path: Path,
    x: int,
    y: int,
    *,
    sample_radius: int = 5,
) -> GrayCardCoefficients:
    """Sample a gray-card region of ``image_path`` and compute white-balance
    correction coefficients.

    Args:
        image_path: Path to a rendered JPEG / PNG / TIFF (typically from
            ``render_preview``).
        x: Pixel x coordinate of the center of the sample region (0-based,
            from left edge).
        y: Pixel y coordinate of the center (0-based, from top edge).
        sample_radius: Half-side of the square sample region (default 5 →
            11x11 pixel region). Larger values average more noise but risk
            sampling non-gray-card pixels.

    Returns:
        :class:`GrayCardCoefficients` with red_coeff, blue_coeff, green_coeff,
        plus the sampled R/G/B for diagnostics.

    Raises:
        GrayCardError: image can't be read, coordinates are out of bounds,
            or the sampled region is entirely black (would produce
            divide-by-zero coefficients).
    """
    from PIL import Image

    if sample_radius < 0:
        raise GrayCardError(f"sample_radius must be ≥ 0; got {sample_radius}")

    try:
        img = Image.open(image_path).convert("RGB")
    except (OSError, ValueError) as exc:
        raise GrayCardError(f"failed to read image at {image_path}: {exc}") from exc

    width, height = img.size
    if not (0 <= x < width):
        raise GrayCardError(f"x={x} out of bounds for {image_path} (width={width})")
    if not (0 <= y < height):
        raise GrayCardError(f"y={y} out of bounds for {image_path} (height={height})")

    # Clamp the sample box to image bounds.
    x0 = max(0, x - sample_radius)
    x1 = min(width, x + sample_radius + 1)
    y0 = max(0, y - sample_radius)
    y1 = min(height, y + sample_radius + 1)

    region = img.crop((x0, y0, x1, y1))
    r_band, g_band, b_band = region.split()
    sampled_r = _band_mean(r_band)
    sampled_g = _band_mean(g_band)
    sampled_b = _band_mean(b_band)

    # All-black region or fully-clipped sample is a hard error — no useful
    # WB info there. Use a small floor to avoid spurious divide-by-zero on
    # near-black gray cards (rare but possible if photographer sampled
    # shadow under the card).
    floor = 1.0  # 8-bit luminance units
    if sampled_r < floor or sampled_g < floor or sampled_b < floor:
        raise GrayCardError(
            f"sampled region is too dark for reliable WB derivation "
            f"(R={sampled_r:.2f}, G={sampled_g:.2f}, B={sampled_b:.2f}); "
            f"sample a brighter mid-gray region of the gray card"
        )

    # Convention: pin green = 1.0; red and blue scale to bring the sample
    # to neutral. This matches darktable's temperature module convention.
    red_coeff = sampled_g / sampled_r
    blue_coeff = sampled_g / sampled_b

    # Clamp to the temperature primitive's accepted range. The parameter
    # ranges are typically [0.1, 4.0] per the manifest declaration; values
    # outside suggest the gray card pick was bad (e.g. sampled a pure red
    # pixel produces a tiny red_coeff). Surface as an error rather than
    # silently clamp.
    for coeff_name, coeff_value in (("red_coeff", red_coeff), ("blue_coeff", blue_coeff)):
        if not (0.1 <= coeff_value <= 4.0):
            raise GrayCardError(
                f"derived {coeff_name}={coeff_value:.3f} outside reasonable "
                f"WB range [0.1, 4.0]; the sampled region (R={sampled_r:.1f}, "
                f"G={sampled_g:.1f}, B={sampled_b:.1f}) likely isn't a gray card"
            )

    return GrayCardCoefficients(
        red_coeff=red_coeff,
        blue_coeff=blue_coeff,
        green_coeff=1.0,
        sampled_r=sampled_r,
        sampled_g=sampled_g,
        sampled_b=sampled_b,
        sample_radius=sample_radius,
    )


def _band_mean(band) -> float:  # type: ignore[no-untyped-def]
    """Mean intensity of a single 8-bit band via its histogram (cheap)."""
    hist = band.histogram()
    total: int = sum(i * count for i, count in enumerate(hist))
    n: int = sum(hist)
    return total / max(n, 1)
