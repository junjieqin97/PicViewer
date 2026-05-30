"""Third-party dependency license metadata helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import metadata, resources

logger = logging.getLogger(__name__)

NOT_INSTALLED_VERSION = "Not installed"
UNKNOWN_LICENSE = "Unknown"


@dataclass(frozen=True)
class ThirdPartyLicenseInfo:
    """License details for one third-party runtime dependency."""

    display_name: str
    package_name: str
    version: str
    license_text: str
    notes: str


@dataclass(frozen=True)
class LicenseTextPart:
    """A display fragment from a license expression.

    Args:
        text: Literal text to render in the dependency license row.
        document_key: Local license document key when the fragment is clickable.
    """

    text: str
    document_key: str | None


@dataclass(frozen=True)
class LicenseDocument:
    """Full text for a bundled third-party license document."""

    key: str
    title: str
    body: str


@dataclass(frozen=True)
class _DependencyLicenseSpec:
    display_name: str
    package_name: str
    fallback_license: str
    notes: str = ""


_RUNTIME_DEPENDENCIES: tuple[_DependencyLicenseSpec, ...] = (
    _DependencyLicenseSpec(
        display_name="PySide6",
        package_name="PySide6",
        fallback_license="LGPL-3.0-only / GPL-2.0-only / GPL-3.0-only / Commercial",
        notes="LGPL v3, GPL v2, GPL v3, or commercial license depending on distribution.",
    ),
    _DependencyLicenseSpec(
        display_name="opencv-python",
        package_name="opencv-python",
        fallback_license="Apache-2.0",
        notes="Includes OpenCV and bundled third-party components.",
    ),
    _DependencyLicenseSpec(
        display_name="NumPy",
        package_name="numpy",
        fallback_license="BSD-3-Clause",
    ),
    _DependencyLicenseSpec(
        display_name="pyexiv2",
        package_name="pyexiv2",
        fallback_license="GPL-3.0-only",
        notes="Runtime metadata backend based on Exiv2.",
    ),
    _DependencyLicenseSpec(
        display_name="Pillow",
        package_name="Pillow",
        fallback_license="MIT-CMU",
        notes="Runtime color management backend based on ImageCms.",
    ),
    _DependencyLicenseSpec(
        display_name="rawpy",
        package_name="rawpy",
        fallback_license="MIT",
        notes="Optional RAW image support.",
    ),
)

_LICENSE_DOCUMENT_TITLES: dict[str, str] = {
    "LGPL-3.0-only": "GNU Lesser General Public License v3.0 only",
    "GPL-3.0-only": "GNU General Public License v3.0 only",
    "GPL-2.0-only": "GNU General Public License v2.0 only",
    "Apache-2.0": "Apache License 2.0",
    "BSD-3-Clause": 'BSD 3-Clause "New" or "Revised" License',
    "MIT": "MIT License",
    "MIT-CMU": "CMU License",
}
_LICENSE_DOCUMENT_KEYS = tuple(sorted(_LICENSE_DOCUMENT_TITLES, key=len, reverse=True))
_LICENSE_ALIASES: dict[str, str] = {
    "apache 2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0",
    "apache software license": "Apache-2.0",
    "bsd license": "BSD-3-Clause",
    "cmu license": "MIT-CMU",
    "gpl v3": "GPL-3.0-only",
    "gplv3": "GPL-3.0-only",
    "gnu general public license v3": "GPL-3.0-only",
    "gnu general public license v3 (gplv3)": "GPL-3.0-only",
    "gnu library or lesser general public license (lgpl)": "LGPL-3.0-only",
    "lgpl": "LGPL-3.0-only",
    "mit license": "MIT",
}


def load_third_party_licenses() -> list[ThirdPartyLicenseInfo]:
    """Load license metadata for PicViewer runtime dependencies."""

    return [_load_license_info(spec) for spec in _RUNTIME_DEPENDENCIES]


def split_license_text(license_text: str) -> tuple[LicenseTextPart, ...]:
    """Split a license expression into literal and clickable fragments."""

    parts: list[LicenseTextPart] = []
    index = 0
    plain_start = 0
    while index < len(license_text):
        document_key = _matching_document_key(license_text, index)
        if document_key is None:
            index += 1
            continue

        if plain_start < index:
            parts.append(LicenseTextPart(license_text[plain_start:index], None))
        parts.append(LicenseTextPart(document_key, document_key))
        index += len(document_key)
        plain_start = index

    if plain_start < len(license_text):
        parts.append(LicenseTextPart(license_text[plain_start:], None))
    return tuple(parts)


def load_license_document(document_key: str) -> LicenseDocument | None:
    """Load a bundled license document by key.

    Args:
        document_key: SPDX-like local document identifier.

    Returns:
        The license document, or None when the key/resource is unavailable.
    """

    title = _LICENSE_DOCUMENT_TITLES.get(document_key)
    if title is None:
        logger.info("Unknown license document key: %s", document_key)
        return None

    try:
        resource = resources.files("pic_viewer").joinpath(
            "assets",
            "licenses",
            f"{document_key}.txt",
        )
        body = resource.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        logger.exception("Failed to load license document: %s", document_key)
        return None
    return LicenseDocument(key=document_key, title=title, body=body)


def _matching_document_key(license_text: str, index: int) -> str | None:
    for document_key in _LICENSE_DOCUMENT_KEYS:
        if license_text.startswith(document_key, index) and _has_license_key_boundaries(
            license_text,
            index,
            index + len(document_key),
        ):
            return document_key
    return None


def _has_license_key_boundaries(license_text: str, start: int, end: int) -> bool:
    before = license_text[start - 1] if start > 0 else ""
    after = license_text[end] if end < len(license_text) else ""
    return not _is_identifier_boundary_char(before) and not _is_identifier_boundary_char(after)


def _is_identifier_boundary_char(char: str) -> bool:
    return bool(char) and (char.isalnum() or char in {"-", "_"})


def _load_license_info(spec: _DependencyLicenseSpec) -> ThirdPartyLicenseInfo:
    try:
        package_version = metadata.version(spec.package_name)
        package_metadata = metadata.metadata(spec.package_name)
    except metadata.PackageNotFoundError:
        return ThirdPartyLicenseInfo(
            display_name=spec.display_name,
            package_name=spec.package_name,
            version=NOT_INSTALLED_VERSION,
            license_text=spec.fallback_license,
            notes=spec.notes,
        )

    return ThirdPartyLicenseInfo(
        display_name=spec.display_name,
        package_name=spec.package_name,
        version=package_version,
        license_text=_resolve_license_text(package_metadata, spec.fallback_license),
        notes=spec.notes,
    )


def _resolve_license_text(package_metadata: metadata.PackageMetadata, fallback_license: str) -> str:
    license_expression = _clean_metadata_value(package_metadata.get("License-Expression"))
    if license_expression:
        return _canonicalize_license_text(license_expression)

    license_text = _clean_metadata_value(package_metadata.get("License"))
    if license_text and not _is_embedded_license_body(license_text):
        return _canonicalize_license_text(license_text)

    classifier_license = _resolve_classifier_license(package_metadata)
    if classifier_license:
        return classifier_license

    return fallback_license or UNKNOWN_LICENSE


def _resolve_classifier_license(package_metadata: metadata.PackageMetadata) -> str | None:
    for classifier in package_metadata.get_all("Classifier", []):
        if not classifier.startswith("License ::"):
            continue
        classifier_parts = [part.strip() for part in classifier.split("::") if part.strip()]
        if classifier_parts:
            return _canonicalize_license_text(classifier_parts[-1])
    return None


def _canonicalize_license_text(license_text: str) -> str:
    if license_text in _LICENSE_DOCUMENT_TITLES:
        return license_text
    return _LICENSE_ALIASES.get(license_text.strip().lower(), license_text)


def _is_embedded_license_body(license_text: str) -> bool:
    if "\n" in license_text:
        return True
    return len(license_text) > 160 and "copyright" in license_text.lower()


def _clean_metadata_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "UNKNOWN":
        return None
    return cleaned
