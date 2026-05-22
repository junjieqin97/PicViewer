from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide2 import QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.third_party_license_service import ThirdPartyLicenseInfo  # noqa: E402
from pic_viewer.ui.windows.third_party_license_dialog import ThirdPartyLicenseDialog  # noqa: E402


class ThirdPartyLicenseDialogTests(unittest.TestCase):
    """Validate the third-party license dialog presentation."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_dialog_renders_license_rows_as_read_only_plain_text(self) -> None:
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

        text = dialog.findChild(QtWidgets.QPlainTextEdit, "textThirdPartyLicenses")
        self.assertIsNotNone(text)
        self.assertTrue(text.isReadOnly())
        self.assertEqual(QtWidgets.QPlainTextEdit.NoWrap, text.lineWrapMode())
        self.assertEqual(
            "\n".join(
                [
                    "PySide2 5.15.2.1 LGPL-3.0-only / GPL-2.0-only / Commercial",
                    "rawpy Not installed MIT",
                ]
            ),
            text.toPlainText(),
        )
        self.assertIsNone(dialog.findChild(QtWidgets.QTableWidget, "tableThirdPartyLicenses"))


if __name__ == "__main__":
    unittest.main()
