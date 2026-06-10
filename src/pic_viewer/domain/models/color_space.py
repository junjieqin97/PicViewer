"""Color-space models used by image loading and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from pathlib import Path


class ColorSpacePreset(Enum):
    """Supported RGB color-space presets."""

    SRGB = "srgb"
    DISPLAY_P3 = "display_p3"
    ADOBE_RGB_1998 = "adobe_rgb_1998"
    PROPHOTO_RGB = "prophoto_rgb"

    @property
    def display_name(self) -> str:
        """Return the stable user-facing English label."""

        labels = {
            ColorSpacePreset.SRGB: "sRGB",
            ColorSpacePreset.DISPLAY_P3: "Display P3",
            ColorSpacePreset.ADOBE_RGB_1998: "Adobe RGB (1998)",
            ColorSpacePreset.PROPHOTO_RGB: "ProPhoto RGB",
        }
        return labels[self]


@dataclass(frozen=True)
class LocalColorProfile:
    """A user-selected local ICC profile for the current session."""

    display_name: str
    path: Path
    profile_bytes: bytes

    @property
    def stable_key(self) -> str:
        """Return a stable key for cache and async result comparisons."""

        digest = hashlib.sha1(self.profile_bytes).hexdigest()
        return f"local:{digest}:{self.path.expanduser()}"


ColorProfileSpec = ColorSpacePreset | LocalColorProfile
LOCAL_COLOR_PROFILE_CHOICE_DATA = "__picviewer_choose_local_icc__"


COLOR_SPACE_PRESET_ORDER: tuple[ColorSpacePreset, ...] = (
    ColorSpacePreset.SRGB,
    ColorSpacePreset.DISPLAY_P3,
    ColorSpacePreset.ADOBE_RGB_1998,
    ColorSpacePreset.PROPHOTO_RGB,
)

DEFAULT_DISPLAY_COLOR_SPACE = ColorSpacePreset.SRGB
DEFAULT_ASSUMED_IMAGE_COLOR_SPACE = ColorSpacePreset.SRGB
