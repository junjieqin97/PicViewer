from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class MainWindowShortcutTests(unittest.TestCase):
    """Validate key shortcuts configured in MainWindowUI."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_pseudo_color_shortcuts(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        under = ui.actToggleUnderexposed.shortcut().toString(QtGui.QKeySequence.PortableText)
        over = ui.actToggleOverexposed.shortcut().toString(QtGui.QKeySequence.PortableText)

        self.assertEqual("Ctrl+Shift+P", under)
        self.assertEqual("Ctrl+P", over)

    def test_checkable_view_menu_labels_are_state_names(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertTrue(ui.actToggleInfoPanel.isCheckable())
        self.assertTrue(ui.actToggleFilmstrip.isCheckable())
        self.assertEqual("Info Panel", ui.actToggleInfoPanel.text())
        self.assertEqual("Filmstrip", ui.actToggleFilmstrip.text())
        self.assertNotIn("Show/Hide", ui.actToggleInfoPanel.text())
        self.assertNotIn("Show/Hide", ui.actToggleFilmstrip.text())


if __name__ == "__main__":
    unittest.main()
