"""Reference line geometry rules for image display overlays."""

from __future__ import annotations

from dataclasses import dataclass


Point = tuple[float, float]


@dataclass(frozen=True)
class ReferenceLineSegment:
    """A reference line segment in display-local coordinates."""

    start: Point
    end: Point


@dataclass(frozen=True)
class ReferenceLineSettings:
    """Enabled reference line overlay types for the image display area."""

    cross: bool = False
    diagonal: bool = False
    thirds: bool = False


def build_reference_line_segments(
    width: int,
    height: int,
    settings: ReferenceLineSettings,
) -> tuple[ReferenceLineSegment, ...]:
    """Build reference line segments for a display rectangle.

    Args:
        width: Display rectangle width in logical pixels.
        height: Display rectangle height in logical pixels.
        settings: Enabled reference line types.

    Returns:
        Tuple of line segments in deterministic drawing order. Empty when
        width/height are invalid or no reference line type is enabled.
    """

    if width <= 0 or height <= 0:
        return ()

    w = float(width)
    h = float(height)
    lines: list[ReferenceLineSegment] = []

    if settings.cross:
        center_x = w / 2.0
        center_y = h / 2.0
        lines.extend(
            (
                ReferenceLineSegment((center_x, 0.0), (center_x, h)),
                ReferenceLineSegment((0.0, center_y), (w, center_y)),
            )
        )

    if settings.diagonal:
        lines.extend(
            (
                ReferenceLineSegment((0.0, 0.0), (w, h)),
                ReferenceLineSegment((w, 0.0), (0.0, h)),
            )
        )

    if settings.thirds:
        one_third_x = w / 3.0
        two_thirds_x = 2.0 * w / 3.0
        one_third_y = h / 3.0
        two_thirds_y = 2.0 * h / 3.0
        lines.extend(
            (
                ReferenceLineSegment((one_third_x, 0.0), (one_third_x, h)),
                ReferenceLineSegment((two_thirds_x, 0.0), (two_thirds_x, h)),
                ReferenceLineSegment((0.0, one_third_y), (w, one_third_y)),
                ReferenceLineSegment((0.0, two_thirds_y), (w, two_thirds_y)),
            )
        )

    return tuple(lines)
