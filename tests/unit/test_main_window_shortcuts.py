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
        peak_high = ui.actPeakHigh.shortcut().toString(QtGui.QKeySequence.PortableText)
        peak_medium = ui.actPeakMedium.shortcut().toString(QtGui.QKeySequence.PortableText)
        peak_low = ui.actPeakLow.shortcut().toString(QtGui.QKeySequence.PortableText)

        self.assertEqual("Ctrl+Shift+P", under)
        self.assertEqual("Ctrl+P", over)
        self.assertEqual("F3", peak_high)
        self.assertEqual("F2", peak_medium)
        self.assertEqual("F1", peak_low)

    def test_checkable_view_menu_labels_are_state_names(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertTrue(ui.actToggleInfoPanel.isCheckable())
        self.assertTrue(ui.actToggleAnalysisToolbar.isCheckable())
        self.assertTrue(ui.actToggleFilmstrip.isCheckable())
        self.assertEqual("Info Panel", ui.actToggleInfoPanel.text())
        self.assertEqual("Analysis Toolbar", ui.actToggleAnalysisToolbar.text())
        self.assertEqual("Filmstrip", ui.actToggleFilmstrip.text())
        self.assertNotIn("Show/Hide", ui.actToggleInfoPanel.text())
        self.assertNotIn("Show/Hide", ui.actToggleAnalysisToolbar.text())
        self.assertNotIn("Show/Hide", ui.actToggleFilmstrip.text())

    def test_analysis_toolbar_shortcut(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        shortcut = ui.actToggleAnalysisToolbar.shortcut().toString(
            QtGui.QKeySequence.PortableText
        )

        self.assertEqual("Ctrl+Up", shortcut)

    def test_focus_peaking_menu_has_three_checkable_levels(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("menuFocusPeaking", ui.menuFocusPeaking.objectName())
        self.assertEqual("Show Peaks", ui.menuFocusPeaking.title())
        self.assertIn(ui.menuFocusPeaking.menuAction(), ui.menuPseudoColor.actions())

        actions = (ui.actPeakHigh, ui.actPeakMedium, ui.actPeakLow)
        self.assertEqual(["High", "Medium", "Low"], [action.text() for action in actions])
        self.assertTrue(all(action.isCheckable() for action in actions))
        self.assertFalse(any(action.isChecked() for action in actions))


if __name__ == "__main__":
    unittest.main()
