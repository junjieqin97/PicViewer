"""Color-space models used by image loading and analysis."""

from __future__ import annotations

from enum import Enum


class WorkingColorSpace(Enum):
    """Supported internal RGB working color spaces."""

    SRGB = "srgb"
    DISPLAY_P3 = "display_p3"
    ADOBE_RGB_1998 = "adobe_rgb_1998"
    PROPHOTO_RGB = "prophoto_rgb"

    @property
    def display_name(self) -> str:
        """Return the stable user-facing English label."""

        labels = {
            WorkingColorSpace.SRGB: "sRGB",
            WorkingColorSpace.DISPLAY_P3: "Display P3",
            WorkingColorSpace.ADOBE_RGB_1998: "Adobe RGB (1998)",
            WorkingColorSpace.PROPHOTO_RGB: "ProPhoto RGB",
        }
        return labels[self]


WORKING_COLOR_SPACE_ORDER: tuple[WorkingColorSpace, ...] = (
    WorkingColorSpace.SRGB,
    WorkingColorSpace.DISPLAY_P3,
    WorkingColorSpace.ADOBE_RGB_1998,
    WorkingColorSpace.PROPHOTO_RGB,
)

DEFAULT_WORKING_COLOR_SPACE = WorkingColorSpace.PROPHOTO_RGB
DEFAULT_ASSUMED_IMAGE_COLOR_SPACE = WorkingColorSpace.SRGB
