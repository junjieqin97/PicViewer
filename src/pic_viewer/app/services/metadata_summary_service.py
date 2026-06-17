"""Shared image metadata summary helpers."""

from __future__ import annotations

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection


def metadata_section_dict(entries: MetadataSection) -> dict[str, str]:
    """Return a key/value mapping for a metadata section."""

    return {key: value for key, value in entries}


def first_metadata_value(entries: dict[str, str], keys: tuple[str, ...]) -> str:
    """Return the first non-empty metadata value from ordered candidate keys."""

    for key in keys:
        value = entries.get(key)
        if value:
            return value.strip()
    return ""


def camera_display_name(metadata: ImageMetadata) -> str:
    """Return the display camera name derived from Exif make/model fields."""

    exif = metadata_section_dict(metadata.exif)
    make = first_metadata_value(exif, ("Make", "Camera Make"))
    model = first_metadata_value(exif, ("Model", "Camera Model Name"))
    if make and model.lower().startswith(make.lower()):
        return model
    return join_metadata_parts(make, model)


def lens_display_name(metadata: ImageMetadata) -> str:
    """Return the display lens name derived from common Exif lens fields."""

    exif = metadata_section_dict(metadata.exif)
    return first_metadata_value(exif, ("LensModel", "Lens", "LensInfo"))


def join_metadata_parts(*parts: str) -> str:
    """Join non-empty metadata fragments with single spaces."""

    return " ".join(part.strip() for part in parts if part and part.strip())
