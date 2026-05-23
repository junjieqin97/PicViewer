from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide2 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.third_party_license_service import ThirdPartyLicenseInfo  # noqa: E402
from pic_viewer.ui.windows import third_party_license_dialog as dialog_module  # noqa: E402
from pic_viewer.ui.windows.third_party_license_dialog import (  # noqa: E402
    LicenseDocumentDialog,
    ThirdPartyLicenseDialog,
)


class ThirdPartyLicenseDialogTests(unittest.TestCase):
    """Validate the third-party license dialog presentation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_dialog_renders_known_license_identifiers_as_links(self) -> None:
        licenses = [
            ThirdPartyLicenseInfo(
                "PySide2",
                "PySide2",
                "5.15.2.1",
                "LGPL-3.0-only / GPL-2.0-only / Commercial",
                "",
            ),
            ThirdPartyLicenseInfo("rawpy", "rawpy", "Not installed", "MIT", "Optional RAW image support."),
        ]

        dialog = ThirdPartyLicenseDialog(licenses)
        self.addCleanup(dialog.deleteLater)

        text = dialog.findChild(QtWidgets.QTextBrowser, "textThirdPartyLicenses")
        self.assertIsNotNone(text)
        assert text is not None
        self.assertTrue(text.isReadOnly())
        self.assertFalse(text.openExternalLinks())
        html = text.toHtml()
        self.assertIn('href="license:LGPL-3.0-only"', html)
        self.assertIn('href="license:GPL-2.0-only"', html)
        self.assertIn('href="license:MIT"', html)
        self.assertIn("Commercial", text.toPlainText())
        self.assertNotIn('href="license:Commercial"', html)
        self.assertIsNone(dialog.findChild(QtWidgets.QPlainTextEdit, "textThirdPartyLicenses"))

    def test_dialog_does_not_link_license_keys_inside_regular_words(self) -> None:
        licenses = [
            ThirdPartyLicenseInfo(
                "NumPy",
                "numpy",
                "2.2.6",
                "NOT LIMITED TO CONSEQUENTIAL DAMAGES",
                "",
            ),
        ]

        dialog = ThirdPartyLicenseDialog(licenses)
        self.addCleanup(dialog.deleteLater)

        text = dialog.findChild(QtWidgets.QTextBrowser, "textThirdPartyLicenses")
        self.assertIsNotNone(text)
        assert text is not None
        self.assertIn("NOT LIMITED TO CONSEQUENTIAL DAMAGES", text.toPlainText())
        self.assertNotIn('href="license:MIT"', text.toHtml())

    def test_license_link_opens_document_dialog(self) -> None:
        licenses = [
            ThirdPartyLicenseInfo(
                "PySide2",
                "PySide2",
                "5.15.2.1",
                "LGPL-3.0-only / GPL-2.0-only / Commercial",
                "",
            ),
        ]
        shown_documents: list[tuple[str, str, str, object | None]] = []

        class FakeLicenseDocumentDialog:
            def __init__(
                self,
                title: str,
                body: str,
                parent: object | None = None,
            ) -> None:
                shown_documents.append((title, body, "created", parent))

            def exec_(self) -> int:
                title, body, _, parent = shown_documents[-1]
                shown_documents[-1] = (title, body, "executed", parent)
                return 0

        dialog = ThirdPartyLicenseDialog(licenses)
        self.addCleanup(dialog.deleteLater)

        original_document_dialog = dialog_module.LicenseDocumentDialog
        dialog_module.LicenseDocumentDialog = FakeLicenseDocumentDialog  # type: ignore[assignment]
        self.addCleanup(setattr, dialog_module, "LicenseDocumentDialog", original_document_dialog)

        dialog._open_license_url(QtCore.QUrl("license:LGPL-3.0-only"))

        self.assertEqual(1, len(shown_documents))
        title, body, state, parent = shown_documents[0]
        self.assertEqual("GNU Lesser General Public License v3.0 only", title)
        self.assertIn("GNU LESSER GENERAL PUBLIC LICENSE", body)
        self.assertEqual("executed", state)
        self.assertIs(dialog, parent)

    def test_document_dialog_renders_license_body_as_read_only_plain_text(self) -> None:
        dialog = LicenseDocumentDialog("MIT License", "MIT License\n\nPermission is hereby granted")
        self.addCleanup(dialog.deleteLater)

        text = dialog.findChild(QtWidgets.QPlainTextEdit, "textLicenseDocument")

        self.assertIsNotNone(text)
        assert text is not None
        self.assertTrue(text.isReadOnly())
        self.assertEqual("MIT License\n\nPermission is hereby granted", text.toPlainText())


if __name__ == "__main__":
    unittest.main()
