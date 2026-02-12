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

from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class MainWindowTabsTests(unittest.TestCase):
    """Validate tab alignment behavior in the image display area."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_image_tabs_do_not_expand_to_fill_space(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertFalse(ui.tabsImages.tabBar().expanding())

    def test_image_tabs_have_left_aligned_tab_bar_style(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        style_sheet = ui.tabsImages.styleSheet()
        self.assertIn("QTabWidget#tabsImages::tab-bar", style_sheet)
        self.assertIn("alignment: left", style_sheet)
        self.assertEqual("", ui.tabsInfo.styleSheet())


if __name__ == "__main__":
    unittest.main()
