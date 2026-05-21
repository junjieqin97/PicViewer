"""Third-party dependency license metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata

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
class _DependencyLicenseSpec:
    display_name: str
    package_name: str
    fallback_license: str
    notes: str = ""


_RUNTIME_DEPENDENCIES: tuple[_DependencyLicenseSpec, ...] = (
    _DependencyLicenseSpec(
        display_name="PySide2",
        package_name="PySide2",
        fallback_license="LGPL-3.0-only / GPL-2.0-only / Commercial",
        notes="LGPL v3, GPL v2, or commercial license depending on distribution.",
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
        display_name="Pillow",
        package_name="Pillow",
        fallback_license="MIT-CMU",
    ),
    _DependencyLicenseSpec(
        display_name="rawpy",
        package_name="rawpy",
        fallback_license="MIT",
        notes="Optional RAW image support.",
    ),
)


def load_third_party_licenses() -> list[ThirdPartyLicenseInfo]:
    """Load license metadata for PicViewer runtime dependencies."""

    return [_load_license_info(spec) for spec in _RUNTIME_DEPENDENCIES]


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
        return license_expression

    license_text = _clean_metadata_value(package_metadata.get("License"))
    if license_text:
        return license_text

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
            return classifier_parts[-1]
    return None


def _clean_metadata_value(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned or cleaned.upper() == "UNKNOWN":
        return None
    return cleaned
