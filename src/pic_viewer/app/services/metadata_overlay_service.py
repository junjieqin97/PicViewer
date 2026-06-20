"""Metadata overlay summary formatting for image previews."""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from pic_viewer.app.dto.metadata import ImageMetadata
from pic_viewer.app.services.metadata_summary_service import (
    camera_display_name,
    first_metadata_value,
    join_metadata_parts,
    lens_display_name,
    metadata_section_dict,
)

def build_metadata_overlay_lines(
    metadata: ImageMetadata,
    source_size: Optional[tuple[int, int]],
) -> tuple[str, ...]:
    """Build the fixed three-line metadata overlay shown over an image preview.

    Args:
        metadata: Structured metadata collected during full image loading.
        source_size: Original image size as ``(height, width)`` used when
            metadata does not include a General/Resolution entry.

    Returns:
        Available display lines: camera/lens, exposure settings, and resolution.
        Missing metadata fields are omitted instead of shown as placeholders.
    """

    general = metadata_section_dict(metadata.general)
    exif = metadata_section_dict(metadata.exif)
    camera_name = camera_display_name(metadata)
    lens_model = lens_display_name(metadata)
    aperture = _format_aperture(first_metadata_value(exif, ("FNumber", "ApertureValue")))
    exposure = _format_exposure_time(first_metadata_value(exif, ("ExposureTime", "ShutterSpeedValue")))
    iso = first_metadata_value(
        exif,
        (
            "ISOSpeedRatings",
            "PhotographicSensitivity",
            "ISO",
            "ISOSpeed",
        ),
    )
    resolution = _resolution_text(general, source_size)
    lines = (
        join_metadata_parts(camera_name, lens_model),
        join_metadata_parts(
            _prefix_value("f/", aperture),
            _suffix_value(exposure, "s"),
            _prefix_value("ISO ", iso),
        ),
        resolution,
    )
    return tuple(line for line in lines if line)


def _format_aperture(value: str) -> str:
    if not value:
        return ""
    normalized = value.strip()
    if normalized.lower().startswith("f/"):
        normalized = normalized[2:].strip()
    return _format_numeric_metadata_value(normalized)


def _format_exposure_time(value: str) -> str:
    if not value:
        return ""
    normalized = value.strip()
    if normalized.lower().endswith("s"):
        normalized = normalized[:-1].strip()
    fraction = _parse_fraction(normalized)
    if fraction is None:
        return normalized
    if 0 < fraction < 1:
        fraction = fraction.limit_denominator(8000)
        if fraction.numerator == 1:
            return f"1/{fraction.denominator}"
    return _format_fraction(fraction)


def _format_numeric_metadata_value(value: str) -> str:
    fraction = _parse_fraction(value)
    if fraction is None:
        return value
    return _format_fraction(fraction)


def _parse_fraction(value: str) -> Fraction | None:
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None


def _format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    as_float = value.numerator / value.denominator
    formatted = f"{as_float:.2f}".rstrip("0").rstrip(".")
    return formatted


def _resolution_text(general: dict[str, str], source_size: Optional[tuple[int, int]]) -> str:
    resolution = general.get("Resolution")
    if resolution:
        return resolution
    if source_size is None:
        return ""
    try:
        height, width = source_size
    except (TypeError, ValueError):
        return ""
    return f"{width} x {height}"


def _prefix_value(prefix: str, value: str) -> str:
    if not value:
        return ""
    return f"{prefix}{value}"


def _suffix_value(value: str, suffix: str) -> str:
    if not value:
        return ""
    return f"{value}{suffix}"
