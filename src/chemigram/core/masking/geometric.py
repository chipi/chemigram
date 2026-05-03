"""Built-in geometric mask providers (ADR-074).

Three deterministic, parameter-driven implementations of the
:class:`~chemigram.core.masking.MaskingProvider` Protocol that produce
masks from pure geometry — no AI, no agent sampling, no PyTorch.

- :class:`GradientMaskProvider` — angled linear gradients.
- :class:`RadialMaskProvider` — circular / elliptical area masks.
- :class:`RectangleMaskProvider` — feathered bounding-box masks.

These complement (don't replace) :class:`CoarseAgentProvider`. BYOA
(ADR-007) keeps the agent-provider first-class for content-aware
masks; the geometric providers cover the cases where the photographer
(or a vocabulary entry) knows the *shape* and just needs darktable to
have a registered PNG to read from.

Per ADR-021 the output is always 8-bit grayscale PNG sized to the
rendered preview, with peak intensity = ``int(peak * 255)`` and zero
where the geometry's falloff has reached the outside.

The :meth:`regenerate` paths delegate to :meth:`generate` — geometric
providers are deterministic and have no notion of "refining" a prior
mask.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from chemigram.core.masking import MaskGenerationError, MaskResult


def _validate_unit(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise MaskGenerationError(f"{name} must be in [0.0, 1.0], got {value!r}")


def _read_size(render_path: Path) -> tuple[int, int]:
    with Image.open(render_path) as ref:
        width, height = ref.size
        return int(width), int(height)


def _array_to_png_bytes(arr: np.ndarray) -> bytes:
    img = Image.fromarray(arr, mode="L")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _scale_to_uint8(field: np.ndarray, peak: float) -> np.ndarray:
    """Clamp a [0, 1] float field to uint8 with peak intensity scaling."""
    clipped = np.clip(field, 0.0, 1.0)
    scaled: np.ndarray = np.round(clipped * peak * 255.0).astype(np.uint8)
    return scaled


# ---------------------------------------------------------------------------
# GradientMaskProvider
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GradientMaskProvider:
    """Angled linear gradient mask.

    The gradient runs along a directional axis given in degrees; intensity
    transitions from 0 at ``start_offset`` to ``peak`` at ``end_offset``,
    measured as fractions of the image's diagonal projected onto the axis.

    Args:
        angle_degrees: Direction the bright side faces, in degrees.
            ``0`` = right, ``90`` = top, ``180`` = left, ``270`` = bottom.
        start_offset: Where the gradient begins (0..1, fraction of axis
            extent). Pixels before this point are 0.
        end_offset: Where the gradient reaches ``peak`` (0..1, > start).
        peak: Maximum intensity (0..1). The bright side will be
            ``round(peak * 255)``.

    Raises:
        MaskGenerationError: If parameters are out of range.
    """

    angle_degrees: float = 90.0
    start_offset: float = 0.0
    end_offset: float = 1.0
    peak: float = 1.0

    def __post_init__(self) -> None:
        _validate_unit("start_offset", self.start_offset)
        _validate_unit("end_offset", self.end_offset)
        _validate_unit("peak", self.peak)
        if self.end_offset <= self.start_offset:
            raise MaskGenerationError(
                f"end_offset ({self.end_offset}) must be > start_offset ({self.start_offset})"
            )

    def generate(
        self,
        *,
        target: str,
        render_path: Path,
        prompt: str | None = None,
    ) -> MaskResult:
        width, height = _read_size(render_path)
        png = _render_gradient(
            width, height, self.angle_degrees, self.start_offset, self.end_offset, self.peak
        )
        return MaskResult(png_bytes=png, generator="gradient", prompt=prompt, target=target)

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        return self.generate(target=target, render_path=render_path, prompt=prompt)


def _render_gradient(
    width: int,
    height: int,
    angle_degrees: float,
    start_offset: float,
    end_offset: float,
    peak: float,
) -> bytes:
    theta = math.radians(angle_degrees)
    dx = math.cos(theta)
    dy = -math.sin(theta)  # image y grows downward; negate so 90° = top
    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    proj = grid_x * dx + grid_y * dy
    # Normalize the projection to [0, 1] across its actual span on this image
    proj_min = float(proj.min())
    proj_max = float(proj.max())
    span = proj_max - proj_min
    if span == 0.0:
        normalized = np.zeros_like(proj)
    else:
        normalized = (proj - proj_min) / span
    # Linear ramp from start_offset → end_offset
    falloff = end_offset - start_offset
    field = (normalized - start_offset) / falloff
    return _array_to_png_bytes(_scale_to_uint8(field, peak))


# ---------------------------------------------------------------------------
# RadialMaskProvider
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RadialMaskProvider:
    """Circular / elliptical mask centered at ``(cx, cy)``.

    Pixels inside the inner radii are at full ``peak`` intensity; outside
    the outer radii are 0; the annulus between is a linear falloff.

    All coordinates and radii are in normalized image space (0..1) so the
    provider handles any preview size.

    Args:
        cx: Center x as a fraction of width.
        cy: Center y as a fraction of height.
        inner_radius: Distance (normalized to half-diagonal) to the
            full-intensity edge.
        outer_radius: Distance to the zero-intensity edge.
            Must be > ``inner_radius``.
        ellipse_ratio: Multiplier on x-axis distance (1.0 = circle,
            >1.0 = horizontally stretched, <1.0 = vertically stretched).
        peak: Maximum intensity (0..1).

    Raises:
        MaskGenerationError: If parameters are out of range.
    """

    cx: float = 0.5
    cy: float = 0.5
    inner_radius: float = 0.2
    outer_radius: float = 0.5
    ellipse_ratio: float = 1.0
    peak: float = 1.0

    def __post_init__(self) -> None:
        _validate_unit("cx", self.cx)
        _validate_unit("cy", self.cy)
        _validate_unit("inner_radius", self.inner_radius)
        _validate_unit("outer_radius", self.outer_radius)
        _validate_unit("peak", self.peak)
        if self.outer_radius <= self.inner_radius:
            raise MaskGenerationError(
                f"outer_radius ({self.outer_radius}) must be > inner_radius ({self.inner_radius})"
            )
        if self.ellipse_ratio <= 0.0:
            raise MaskGenerationError(f"ellipse_ratio must be > 0, got {self.ellipse_ratio}")

    def generate(
        self,
        *,
        target: str,
        render_path: Path,
        prompt: str | None = None,
    ) -> MaskResult:
        width, height = _read_size(render_path)
        png = _render_radial(
            width,
            height,
            self.cx,
            self.cy,
            self.inner_radius,
            self.outer_radius,
            self.ellipse_ratio,
            self.peak,
        )
        return MaskResult(png_bytes=png, generator="radial", prompt=prompt, target=target)

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        return self.generate(target=target, render_path=render_path, prompt=prompt)


def _render_radial(
    width: int,
    height: int,
    cx: float,
    cy: float,
    inner_radius: float,
    outer_radius: float,
    ellipse_ratio: float,
    peak: float,
) -> bytes:
    cx_px = cx * width
    cy_px = cy * height
    half_diag = 0.5 * math.hypot(width, height)
    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    dx = (grid_x - cx_px) / ellipse_ratio
    dy = grid_y - cy_px
    dist = np.sqrt(dx * dx + dy * dy) / half_diag
    # 1 inside inner, 0 outside outer, linear in between
    falloff = outer_radius - inner_radius
    field = 1.0 - (dist - inner_radius) / falloff
    return _array_to_png_bytes(_scale_to_uint8(field, peak))


# ---------------------------------------------------------------------------
# RectangleMaskProvider
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RectangleMaskProvider:
    """Feathered bounding-box mask.

    Pixels inside ``(x0, y0)..(x1, y1)`` (and at least ``feather`` from
    the edge) are at full ``peak`` intensity; the feathered border falls
    off linearly to 0 outside the box.

    Coordinates are normalized image fractions (0..1).

    Args:
        x0, y0, x1, y1: Bounding box corners (must satisfy
            ``x0 < x1`` and ``y0 < y1``).
        feather: Falloff distance (normalized to half the smaller image
            side; 0 = hard edge).
        peak: Maximum intensity (0..1).

    Raises:
        MaskGenerationError: If parameters are out of range or invalid.
    """

    x0: float = 0.0
    y0: float = 0.0
    x1: float = 1.0
    y1: float = 1.0
    feather: float = 0.0
    peak: float = 1.0

    def __post_init__(self) -> None:
        for name, value in (("x0", self.x0), ("y0", self.y0), ("x1", self.x1), ("y1", self.y1)):
            _validate_unit(name, value)
        _validate_unit("feather", self.feather)
        _validate_unit("peak", self.peak)
        if self.x1 <= self.x0:
            raise MaskGenerationError(f"x1 ({self.x1}) must be > x0 ({self.x0})")
        if self.y1 <= self.y0:
            raise MaskGenerationError(f"y1 ({self.y1}) must be > y0 ({self.y0})")

    def generate(
        self,
        *,
        target: str,
        render_path: Path,
        prompt: str | None = None,
    ) -> MaskResult:
        width, height = _read_size(render_path)
        png = _render_rectangle(
            width, height, self.x0, self.y0, self.x1, self.y1, self.feather, self.peak
        )
        return MaskResult(png_bytes=png, generator="rectangle", prompt=prompt, target=target)

    def regenerate(
        self,
        *,
        target: str,
        render_path: Path,
        prior_mask: bytes,
        prompt: str | None = None,
    ) -> MaskResult:
        return self.generate(target=target, render_path=render_path, prompt=prompt)


def _render_rectangle(
    width: int,
    height: int,
    x0_norm: float,
    y0_norm: float,
    x1_norm: float,
    y1_norm: float,
    feather: float,
    peak: float,
) -> bytes:
    x0 = x0_norm * width
    y0 = y0_norm * height
    x1 = x1_norm * width
    y1 = y1_norm * height
    feather_px = feather * 0.5 * min(width, height)

    xs = np.arange(width, dtype=np.float32)
    ys = np.arange(height, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)

    if feather_px <= 0.0:
        inside = (grid_x >= x0) & (grid_x <= x1) & (grid_y >= y0) & (grid_y <= y1)
        return _array_to_png_bytes(_scale_to_uint8(inside.astype(np.float32), peak))

    dx_left = grid_x - x0
    dx_right = x1 - grid_x
    dy_top = grid_y - y0
    dy_bot = y1 - grid_y
    dist_to_edge = np.minimum(np.minimum(dx_left, dx_right), np.minimum(dy_top, dy_bot))
    field = (dist_to_edge + feather_px) / (2.0 * feather_px)
    return _array_to_png_bytes(_scale_to_uint8(field, peak))


__all__ = [
    "GradientMaskProvider",
    "RadialMaskProvider",
    "RectangleMaskProvider",
]
