from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.ui.resources import styles  # noqa: E402


class UiStylesTests(unittest.TestCase):
    """Validate centralized QSS resource loading."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_load_stylesheet_returns_main_qss_content(self) -> None:
        style_sheet = styles.load_stylesheet()

        self.assertIn("QTabWidget#tabsImages::tab-bar", style_sheet)
        self.assertIn("alignment: left", style_sheet)
        self.assertIn("QStatusBar", style_sheet)

    def test_stylesheet_does_not_override_native_tab_close_button(self) -> None:
        style_sheet = styles.load_stylesheet()

        self.assertNotIn("QTabBar::close-button", style_sheet)

    def test_load_stylesheet_returns_empty_string_when_file_missing(self) -> None:
        missing_path = PROJECT_ROOT / "missing-main.qss"

        with patch.object(styles, "stylesheet_path", return_value=missing_path):
            self.assertEqual("", styles.load_stylesheet())

    def test_apply_stylesheet_sets_loaded_qss_on_widget(self) -> None:
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)

        styles.apply_stylesheet(window)

        self.assertEqual(styles.load_stylesheet(), window.styleSheet())


if __name__ == "__main__":
    unittest.main()
