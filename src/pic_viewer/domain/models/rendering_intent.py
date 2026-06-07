"""ICC rendering intent models used by color conversion."""

from __future__ import annotations

from enum import Enum


class RenderingIntent(Enum):
    """Supported ICC rendering intents."""

    PERCEPTUAL = "perceptual"
    RELATIVE_COLORIMETRIC = "relative_colorimetric"
    SATURATION = "saturation"
    ABSOLUTE_COLORIMETRIC = "absolute_colorimetric"

    @property
    def display_name(self) -> str:
        """Return the stable user-facing English label."""

        labels = {
            RenderingIntent.PERCEPTUAL: "Perceptual",
            RenderingIntent.RELATIVE_COLORIMETRIC: "Relative Colorimetric",
            RenderingIntent.SATURATION: "Saturation",
            RenderingIntent.ABSOLUTE_COLORIMETRIC: "Absolute Colorimetric",
        }
        return labels[self]


RENDERING_INTENT_ORDER: tuple[RenderingIntent, ...] = (
    RenderingIntent.PERCEPTUAL,
    RenderingIntent.RELATIVE_COLORIMETRIC,
    RenderingIntent.SATURATION,
    RenderingIntent.ABSOLUTE_COLORIMETRIC,
)

DEFAULT_RENDERING_INTENT = RenderingIntent.PERCEPTUAL
