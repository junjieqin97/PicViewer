"""Source image color profile models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


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
