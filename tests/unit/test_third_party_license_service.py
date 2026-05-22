from __future__ import annotations

from email.message import Message
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.third_party_license_service import (  # noqa: E402
    LicenseTextPart,
    NOT_INSTALLED_VERSION,
    load_license_document,
    load_third_party_licenses,
    metadata,
    split_license_text,
)


class ThirdPartyLicenseServiceTests(unittest.TestCase):
    """Validate third-party dependency license metadata resolution."""

    def test_split_license_text_links_known_licenses_in_compound_expression(self) -> None:
        parts = split_license_text("LGPL-3.0-only / GPL-2.0-only / Commercial")

        self.assertEqual(
            (
                LicenseTextPart("LGPL-3.0-only", "LGPL-3.0-only"),
                LicenseTextPart(" / ", None),
                LicenseTextPart("GPL-2.0-only", "GPL-2.0-only"),
                LicenseTextPart(" / Commercial", None),
            ),
            parts,
        )

    def test_split_license_text_prefers_longest_license_identifier(self) -> None:
        parts = split_license_text("MIT-CMU / MIT")

        self.assertEqual(
            (
                LicenseTextPart("MIT-CMU", "MIT-CMU"),
                LicenseTextPart(" / ", None),
                LicenseTextPart("MIT", "MIT"),
            ),
            parts,
        )

    def test_load_license_document_reads_local_english_text(self) -> None:
        document = load_license_document("LGPL-3.0-only")

        self.assertIsNotNone(document)
        assert document is not None
        self.assertEqual("LGPL-3.0-only", document.key)
        self.assertEqual("GNU Lesser General Public License v3.0 only", document.title)
        self.assertIn("GNU LESSER GENERAL PUBLIC LICENSE", document.body)
        self.assertIn("Version 3, 29 June 2007", document.body)

    def test_load_license_document_returns_none_for_unknown_key(self) -> None:
        self.assertIsNone(load_license_document("Commercial"))

    def test_load_third_party_licenses_prefers_license_expression(self) -> None:
        metadata_by_package = {
            "PySide2": self._message({"License-Expression": "GPL-3.0-only", "License": "Legacy License"}),
        }

        licenses = self._load_with_metadata(metadata_by_package)

        pyside = self._find_license(licenses, "PySide2")
        self.assertEqual("PySide2", pyside.display_name)
        self.assertEqual("1.2.3", pyside.version)
        self.assertEqual("GPL-3.0-only", pyside.license_text)

    def test_load_third_party_licenses_falls_back_to_license_and_classifier(self) -> None:
        metadata_by_package = {
            "numpy": self._message({"License": "BSD-3-Clause"}),
            "Pillow": self._message(
                {},
                classifiers=["License :: OSI Approved :: MIT-CMU License"],
            ),
        }

        licenses = self._load_with_metadata(metadata_by_package)

        numpy = self._find_license(licenses, "numpy")
        pillow = self._find_license(licenses, "Pillow")
        self.assertEqual("BSD-3-Clause", numpy.license_text)
        self.assertEqual("MIT-CMU License", pillow.license_text)

    def test_optional_rawpy_missing_is_reported_without_failing(self) -> None:
        def fake_version(package_name: str) -> str:
            if package_name == "rawpy":
                raise metadata.PackageNotFoundError(package_name)
            return "1.2.3"

        def fake_metadata(package_name: str) -> Message:
            if package_name == "rawpy":
                raise metadata.PackageNotFoundError(package_name)
            return self._message({"License": "MIT"})

        with (
            patch.object(metadata, "version", side_effect=fake_version),
            patch.object(metadata, "metadata", side_effect=fake_metadata),
        ):
            licenses = load_third_party_licenses()

        rawpy = self._find_license(licenses, "rawpy")
        self.assertEqual(NOT_INSTALLED_VERSION, rawpy.version)
        self.assertEqual("MIT", rawpy.license_text)
        self.assertEqual("Optional RAW image support.", rawpy.notes)

    def _load_with_metadata(self, metadata_by_package: dict[str, Message]):
        def fake_version(package_name: str) -> str:
            if package_name == "rawpy":
                raise metadata.PackageNotFoundError(package_name)
            return "1.2.3"

        def fake_metadata(package_name: str) -> Message:
            if package_name == "rawpy":
                raise metadata.PackageNotFoundError(package_name)
            return metadata_by_package.get(package_name, self._message({"License": "MIT"}))

        with (
            patch.object(metadata, "version", side_effect=fake_version),
            patch.object(metadata, "metadata", side_effect=fake_metadata),
        ):
            return load_third_party_licenses()

    def _message(self, fields: dict[str, str], classifiers: list[str] | None = None) -> Message:
        message = Message()
        for key, value in fields.items():
            message[key] = value
        for classifier in classifiers or []:
            message["Classifier"] = classifier
        return message

    def _find_license(self, licenses, package_name: str):
        for license_info in licenses:
            if license_info.package_name == package_name:
                return license_info
        self.fail(f"Missing license entry for {package_name}")


if __name__ == "__main__":
    unittest.main()
