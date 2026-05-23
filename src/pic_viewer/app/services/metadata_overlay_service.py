"""Metadata overlay summary formatting for image previews."""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection

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

    general = _section_dict(metadata.general)
    exif = _section_dict(metadata.exif)
    camera_name = _camera_name(exif)
    lens_model = _first_value(exif, ("LensModel", "Lens", "LensInfo"))
    aperture = _format_aperture(_first_value(exif, ("FNumber", "ApertureValue")))
    exposure = _format_exposure_time(_first_value(exif, ("ExposureTime", "ShutterSpeedValue")))
    iso = _first_value(
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
        _join_parts(camera_name, lens_model),
        _join_parts(_prefix_value("f/", aperture), _suffix_value(exposure, "s"), _prefix_value("ISO ", iso)),
        resolution,
    )
    return tuple(line for line in lines if line)


def _section_dict(entries: MetadataSection) -> dict[str, str]:
    return {key: value for key, value in entries}


def _first_value(entries: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = entries.get(key)
        if value:
            return value.strip()
    return ""


def _camera_name(exif: dict[str, str]) -> str:
    make = _first_value(exif, ("Make", "Camera Make"))
    model = _first_value(exif, ("Model", "Camera Model Name"))
    if make and model.lower().startswith(make.lower()):
        return model
    return _join_parts(make, model)


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


def _join_parts(*parts: str) -> str:
    return " ".join(part.strip() for part in parts if part and part.strip())


def _prefix_value(prefix: str, value: str) -> str:
    if not value:
        return ""
    return f"{prefix}{value}"


def _suffix_value(value: str, suffix: str) -> str:
    if not value:
        return ""
    return f"{value}{suffix}"
