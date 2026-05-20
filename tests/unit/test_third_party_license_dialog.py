from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtWidgets

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

    def test_dialog_renders_license_rows_in_read_only_table(self) -> None:
        licenses = [
            ThirdPartyLicenseInfo("PyQt5", "PyQt5", "5.15.11", "GPL-3.0-only", ""),
            ThirdPartyLicenseInfo("rawpy", "rawpy", "Not installed", "MIT", "Optional RAW image support."),
        ]

        dialog = ThirdPartyLicenseDialog(licenses)
        self.addCleanup(dialog.deleteLater)

        table = dialog.findChild(QtWidgets.QTableWidget, "tableThirdPartyLicenses")
        self.assertIsNotNone(table)
        self.assertEqual(2, table.rowCount())
        self.assertEqual(4, table.columnCount())
        self.assertEqual(["Library", "Version", "License", "Notes"], self._headers(table))
        self.assertEqual("PyQt5", table.item(0, 0).text())
        self.assertEqual("5.15.11", table.item(0, 1).text())
        self.assertEqual("GPL-3.0-only", table.item(0, 2).text())
        self.assertEqual("rawpy", table.item(1, 0).text())
        self.assertEqual("Not installed", table.item(1, 1).text())
        self.assertEqual("MIT", table.item(1, 2).text())
        self.assertEqual("Optional RAW image support.", table.item(1, 3).text())
        self.assertEqual(QtWidgets.QAbstractItemView.NoEditTriggers, table.editTriggers())

    def _headers(self, table: QtWidgets.QTableWidget) -> list[str]:
        return [
            table.horizontalHeaderItem(column).text()
            for column in range(table.columnCount())
        ]


if __name__ == "__main__":
    unittest.main()
