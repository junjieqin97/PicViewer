"""DTOs for structured image metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

MetadataEntry = Tuple[str, str]
MetadataSection = Tuple[MetadataEntry, ...]


@dataclass(frozen=True)
class ImageMetadata:
    """Image metadata grouped by category."""

    general: MetadataSection
    exif: MetadataSection
    iptc: MetadataSection
    tiff: MetadataSection
