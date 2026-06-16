"""Image file support policy shared by import entry points."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

RAW_IMAGE_SUFFIXES = frozenset(
    {
        ".dng",
        ".nef",
        ".cr2",
        ".arw",
        ".raf",
    }
)

RASTER_IMAGE_SUFFIXES = frozenset(
    {
        ".jpg",
        ".jpeg",
        ".png",
        ".tif",
        ".tiff",
        ".bmp",
        ".webp",
        ".avif",
        ".heif",
        ".heic",
    }
)

SUPPORTED_IMAGE_SUFFIXES = RASTER_IMAGE_SUFFIXES | RAW_IMAGE_SUFFIXES


def is_supported_image_path(path: Path) -> bool:
    """Return True when a path points to a supported local image file."""

    try:
        return path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    except OSError:
        return False


def filter_supported_image_paths(paths: Iterable[Path]) -> list[Path]:
    """Filter paths to supported local image files while preserving order."""

    return [path for path in paths if is_supported_image_path(path)]
