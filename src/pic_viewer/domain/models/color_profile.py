"""Source image color profile models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pic_viewer.domain.models.color_space import WorkingColorSpace


class ImageColorProfileStatus(Enum):
    """ICC profile status detected while loading an image."""

    EMBEDDED = "embedded"
    MISSING = "missing"
    INVALID = "invalid"
    CONVERSION_FAILED = "conversion_failed"


@dataclass(frozen=True)
class ImageColorProfileInfo:
    """User-visible source color profile status for an image."""

    display_name: str
    status: ImageColorProfileStatus
    uses_srgb_fallback: bool
    assumed_color_space: WorkingColorSpace | None = None
