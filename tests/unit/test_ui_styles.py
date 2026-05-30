from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

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

    def test_load_stylesheet_returns_dark_qss_content(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.DARK)

        self.assertIn("QMenuBar", style_sheet)
        self.assertIn("QMenuBar::item", style_sheet)
        self.assertIn("color: #f0f3f6", style_sheet)
        self.assertIn("QTabWidget#tabsImages::tab-bar", style_sheet)
        self.assertIn("alignment: left", style_sheet)
        self.assertIn("QTabWidget#tabsImages QTabBar::tab:selected", style_sheet)
        self.assertIn("QTabWidget#tabsImages QTabBar::tab:hover", style_sheet)
        self.assertIn("QScrollArea#scrollImage", style_sheet)
        self.assertIn("QWidget#viewportImageCanvas", style_sheet)
        self.assertIn("QScrollArea#scrollImage QScrollBar:horizontal", style_sheet)
        self.assertIn("QScrollArea#scrollImage QScrollBar:vertical", style_sheet)
        self.assertIn("QFrame#widgetAnalysisToolbar", style_sheet)
        self.assertIn("QFrame#widgetAnalysisToolbar QToolButton:checked", style_sheet)
        self.assertIn("QStatusBar", style_sheet)
        self.assertIn("QLabel#labelFilmstripSummary", style_sheet)
        self.assertIn("QWidget#floatingTabWindow", style_sheet)
        self.assertIn("QWidget#floatingTabContent", style_sheet)
        self.assertNotIn("QTabBar#floatingTabBar", style_sheet)

    def test_load_stylesheet_returns_light_qss_content(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        self.assertIn("QMenuBar", style_sheet)
        self.assertIn("QMenuBar::item", style_sheet)
        self.assertIn("color: #1f252d", style_sheet)
        self.assertIn("QTabWidget#tabsImages::tab-bar", style_sheet)
        self.assertIn("alignment: left", style_sheet)
        self.assertIn("QFrame#widgetAnalysisToolbar", style_sheet)
        self.assertIn("QStatusBar", style_sheet)
        self.assertIn("QWidget#floatingTabWindow", style_sheet)
        self.assertIn("QWidget#floatingTabContent", style_sheet)
        self.assertNotIn("QTabBar#floatingTabBar", style_sheet)

    def test_light_stylesheet_keeps_toolbar_button_background_transparent(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        selector = "QFrame#widgetAnalysisToolbar QToolButton {"
        rule = style_sheet.split(selector, maxsplit=1)[1].split("}", maxsplit=1)[0]

        self.assertIn("background: transparent;", rule)

    def test_light_stylesheet_uses_light_image_canvas_background(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        for selector in (
            "QWidget#pageImagePreview",
            "QScrollArea#scrollImage",
            "QWidget#viewportImageCanvas",
        ):
            rule = self._style_block(style_sheet, selector)
            self.assertIn("background: #ffffff", rule)
            self.assertNotIn("background: #1d2228", rule)

        for selector in (
            "QScrollArea#scrollImage QScrollBar:horizontal",
            "QScrollArea#scrollImage QScrollBar:vertical",
        ):
            rule = self._style_block(style_sheet, selector)
            self.assertIn("background: #eef2f6", rule)
            self.assertNotIn("background: #20262d", rule)

    def test_theme_from_color_scheme_maps_system_values(self) -> None:
        self.assertEqual(
            styles.AppearanceTheme.LIGHT,
            styles.theme_from_color_scheme(QtCore.Qt.ColorScheme.Light),
        )
        self.assertEqual(
            styles.AppearanceTheme.DARK,
            styles.theme_from_color_scheme(QtCore.Qt.ColorScheme.Dark),
        )
        self.assertEqual(
            styles.AppearanceTheme.LIGHT,
            styles.theme_from_color_scheme(QtCore.Qt.ColorScheme.Unknown),
        )
        self.assertEqual(styles.AppearanceTheme.LIGHT, styles.theme_from_color_scheme(object()))

    def test_stylesheet_does_not_override_native_tab_close_button(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.DARK)

        self.assertNotIn("QTabBar::close-button", style_sheet)
        self.assertNotIn("QToolButton#buttonImageTabClose", style_sheet)

    def test_tab_headers_use_rounded_top_corners(self) -> None:
        style_sheet = styles.load_stylesheet()

        self.assertIn("border-top-left-radius: 5px", style_sheet)
        self.assertIn("border-top-right-radius: 5px", style_sheet)
        self.assertIn("border-top-left-radius: 6px", style_sheet)
        self.assertIn("border-top-right-radius: 6px", style_sheet)

    def test_tab_headers_keep_height_close_to_text_height(self) -> None:
        style_sheet = styles.load_stylesheet()

        tab_block = self._style_block(style_sheet, "QTabBar::tab")
        image_tab_block = self._style_block(style_sheet, "QTabWidget#tabsImages QTabBar::tab")

        self.assertIn("min-height: 0px", tab_block)
        self.assertIn("padding: 2px 12px", tab_block)
        self.assertIn("min-height: 0px", image_tab_block)
        self.assertIn("padding: 2px 10px 2px 12px", image_tab_block)

    def test_load_stylesheet_returns_empty_string_when_file_missing(self) -> None:
        missing_path = PROJECT_ROOT / "missing-main.qss"

        with patch.object(styles, "stylesheet_path", return_value=missing_path):
            self.assertEqual("", styles.load_stylesheet(styles.AppearanceTheme.DARK))

    def test_apply_stylesheet_sets_loaded_qss_on_widget(self) -> None:
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)

        applied_theme = styles.apply_stylesheet(window, styles.AppearanceTheme.LIGHT)

        self.assertEqual(styles.AppearanceTheme.LIGHT, applied_theme)
        self.assertEqual(
            styles.load_stylesheet(styles.AppearanceTheme.LIGHT),
            window.styleSheet(),
        )

    @staticmethod
    def _style_block(style_sheet: str, selector: str) -> str:
        block_start = style_sheet.index(f"{selector} {{")
        block_end = style_sheet.index("}", block_start)
        return style_sheet[block_start:block_end]


if __name__ == "__main__":
    unittest.main()
