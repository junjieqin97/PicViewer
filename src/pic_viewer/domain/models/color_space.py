"""Color-space models used by image loading and analysis."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from pathlib import Path


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


ColorProfileSpec = WorkingColorSpace | LocalColorProfile
LOCAL_COLOR_PROFILE_CHOICE_DATA = "__picviewer_choose_local_icc__"


WORKING_COLOR_SPACE_ORDER: tuple[WorkingColorSpace, ...] = (
    WorkingColorSpace.SRGB,
    WorkingColorSpace.DISPLAY_P3,
    WorkingColorSpace.ADOBE_RGB_1998,
    WorkingColorSpace.PROPHOTO_RGB,
)

DEFAULT_WORKING_COLOR_SPACE = WorkingColorSpace.PROPHOTO_RGB
DEFAULT_ASSUMED_IMAGE_COLOR_SPACE = WorkingColorSpace.SRGB
