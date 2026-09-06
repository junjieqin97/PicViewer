from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.ui.resources import styles  # noqa: E402


class UiStylesTests(QtWidgetTestCase):
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
        self.assertIn("QTabBar::tab:selected", style_sheet)
        self.assertIn("QTabBar::tab:hover", style_sheet)
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

    def test_selected_canvas_color_is_theme_independent_and_neutral(self) -> None:
        expected_colors = {
            styles.CanvasColor.PURE_WHITE: "#FFFFFF",
            styles.CanvasColor.MIDDLE_GRAY_18: "#777777",
            styles.CanvasColor.DEEP_NEUTRAL: "#202020",
            styles.CanvasColor.NEAR_BLACK: "#101010",
            styles.CanvasColor.PURE_BLACK: "#000000",
        }
        selectors = (
            "QWidget#pageImagePreview",
            "QScrollArea#scrollImage",
            "QWidget#viewportImageCanvas",
        )

        for canvas_color, expected_color in expected_colors.items():
            for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
                with self.subTest(canvas_color=canvas_color, theme=theme):
                    style_sheet = styles.load_stylesheet(theme, canvas_color)
                    for selector in selectors:
                        rule = self._last_style_block(style_sheet, selector)
                        self.assertEqual(
                            expected_color,
                            self._style_property(rule, "background"),
                        )

    def test_default_canvas_color_is_deep_neutral_gray(self) -> None:
        self.assertEqual(styles.CanvasColor.DEEP_NEUTRAL, styles.DEFAULT_CANVAS_COLOR)
        for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
            rule = self._last_style_block(
                styles.load_stylesheet(theme),
                "QWidget#viewportImageCanvas",
            )
            self.assertEqual("#202020", self._style_property(rule, "background"))

    def test_canvas_color_does_not_replace_loading_state_background(self) -> None:
        expected_backgrounds = {
            styles.AppearanceTheme.DARK: "#191b1f",
            styles.AppearanceTheme.LIGHT: "#eef2f6",
        }

        for theme, expected_color in expected_backgrounds.items():
            with self.subTest(theme=theme):
                style_sheet = styles.load_stylesheet(theme, styles.CanvasColor.MIDDLE_GRAY_18)
                rule = self._style_block(style_sheet, "QWidget#widgetImageLoadState")
                self.assertEqual(expected_color, self._style_property(rule, "background"))

    def test_light_stylesheet_keeps_light_image_scrollbars(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        for selector in (
            "QScrollArea#scrollImage QScrollBar:horizontal",
            "QScrollArea#scrollImage QScrollBar:vertical",
        ):
            rule = self._style_block(style_sheet, selector)
            self.assertEqual("#eef2f6", self._style_property(rule, "background"))

    def test_specified_image_color_space_selector_has_disabled_gray_styles(self) -> None:
        dark_style = styles.load_stylesheet(styles.AppearanceTheme.DARK)
        light_style = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        selector = "QWidget#tabAnalysis QComboBox#comboSpecifiedImageColorSpace:disabled"
        dark_rule = self._style_block(dark_style, selector)
        light_rule = self._style_block(light_style, selector)

        self.assertIn("color: #6f7782", dark_rule)
        self.assertIn("background: #24282e", dark_rule)
        self.assertIn("border: 1px solid #343b44", dark_rule)
        self.assertIn("color: #9aa4af", light_rule)
        self.assertIn("background: #eef2f6", light_rule)
        self.assertIn("border: 1px solid #d8e0ea", light_rule)

    def test_rendering_intent_selector_uses_color_setting_styles(self) -> None:
        dark_style = styles.load_stylesheet(styles.AppearanceTheme.DARK)
        light_style = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        self.assertIn("QLabel#labelRenderingIntentTitle", dark_style)
        self.assertIn("QWidget#tabAnalysis QComboBox", dark_style)
        self.assertIn("QLabel#labelRenderingIntentTitle", light_style)
        self.assertIn("QWidget#tabAnalysis QComboBox", light_style)

    def test_analysis_sample_precision_title_matches_color_space_title_color(self) -> None:
        expected_colors = {
            styles.AppearanceTheme.DARK: "#9aa4af",
            styles.AppearanceTheme.LIGHT: "#657386",
        }

        for theme, expected_color in expected_colors.items():
            with self.subTest(theme=theme):
                style_sheet = styles.load_stylesheet(theme)
                sample_rule = self._style_block(
                    style_sheet,
                    "QLabel#labelAnalysisSamplePrecisionTitle",
                )
                color_space_rule = self._style_block(
                    style_sheet,
                    "QLabel#labelSpecifiedImageColorSpaceTitle",
                )

                self.assertEqual(expected_color, self._style_property(sample_rule, "color"))
                self.assertEqual(
                    self._style_property(color_space_rule, "color"),
                    self._style_property(sample_rule, "color"),
                )

    def test_analysis_color_selectors_can_expand(self) -> None:
        for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
            with self.subTest(theme=theme):
                rule = self._style_block(styles.load_stylesheet(theme), "QWidget#tabAnalysis QComboBox")

                self.assertNotIn("min-width:", rule)
                self.assertNotIn("max-width:", rule)

    def test_filmstrip_filter_selectors_reuse_analysis_combo_style_blocks(self) -> None:
        shared_selector_pairs = (
            ("QWidget#tabAnalysis QComboBox", "QWidget#widgetFilmstripFilterToolbar QComboBox"),
            (
                "QWidget#tabAnalysis QComboBox QAbstractItemView",
                "QWidget#widgetFilmstripFilterToolbar QComboBox QAbstractItemView",
            ),
            (
                "QWidget#tabAnalysis QComboBox QAbstractItemView::item",
                "QWidget#widgetFilmstripFilterToolbar QComboBox QAbstractItemView::item",
            ),
            (
                "QWidget#tabAnalysis QComboBox QAbstractItemView::item:hover",
                "QWidget#widgetFilmstripFilterToolbar QComboBox QAbstractItemView::item:hover",
            ),
            (
                "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected",
                "QWidget#widgetFilmstripFilterToolbar QComboBox QAbstractItemView::item:selected",
            ),
            (
                "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected:active",
                "QWidget#widgetFilmstripFilterToolbar QComboBox QAbstractItemView::item:selected:active",
            ),
            (
                "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected:!active",
                "QWidget#widgetFilmstripFilterToolbar QComboBox QAbstractItemView::item:selected:!active",
            ),
        )

        for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
            style_sheet = styles.load_stylesheet(theme)
            with self.subTest(theme=theme):
                for analysis_selector, filmstrip_selector in shared_selector_pairs:
                    analysis_block = self._style_block(style_sheet, analysis_selector)
                    filmstrip_block = self._style_block(style_sheet, filmstrip_selector)
                    block_selectors = self._style_block_selectors(analysis_block)

                    self.assertEqual(analysis_block, filmstrip_block)
                    self.assertIn(analysis_selector, block_selectors)
                    self.assertIn(filmstrip_selector, block_selectors)

    def test_pixel_sample_value_labels_use_channel_colors(self) -> None:
        for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
            with self.subTest(theme=theme):
                style_sheet = styles.load_stylesheet(theme)

                self.assertIn("QLabel#labelPixelRedValue", style_sheet)
                self.assertIn("QLabel#labelPixelGreenValue", style_sheet)
                self.assertIn("QLabel#labelPixelBlueValue", style_sheet)
                self.assertIn("QLabel#labelPixelLumaValue", style_sheet)

                red_rule = self._style_block(style_sheet, "QLabel#labelPixelRedValue")
                green_rule = self._style_block(style_sheet, "QLabel#labelPixelGreenValue")
                blue_rule = self._style_block(style_sheet, "QLabel#labelPixelBlueValue")
                luma_rule = self._style_block(style_sheet, "QLabel#labelPixelLumaValue")
                expected_luma_color = "#ffffff" if theme == styles.AppearanceTheme.DARK else "#000000"

                self.assertIn("color: #ff4d4d", red_rule)
                self.assertIn("color: #48c774", green_rule)
                self.assertIn("color: #4da3ff", blue_rule)
                self.assertIn(f"color: {expected_luma_color}", luma_rule)

    def test_color_readout_label_styles_match_theme(self) -> None:
        dark_style = styles.load_stylesheet(styles.AppearanceTheme.DARK)
        light_style = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        dark_rule = self._style_block(dark_style, "QLabel#labelColorReadout")
        light_rule = self._style_block(light_style, "QLabel#labelColorReadout")

        self.assertIn("background: #2b3036", dark_rule)
        self.assertIn("color: #edf1f5", dark_rule)
        self.assertIn("border: 1px solid #8eb4df", dark_rule)
        self.assertIn("background: #ffffff", light_rule)
        self.assertIn("color: #1f252d", light_rule)
        self.assertIn("border: 1px solid #4d8fd3", light_rule)

    def test_analysis_combo_popup_views_use_theme_contrast(self) -> None:
        dark_style = styles.load_stylesheet(styles.AppearanceTheme.DARK)
        light_style = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        dark_popup_rule = self._style_block(
            dark_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView",
        )
        light_popup_rule = self._style_block(
            light_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView",
        )

        self.assertIn("color: #edf1f5", dark_popup_rule)
        self.assertIn("background: #171a1e", dark_popup_rule)
        self.assertIn("border: 1px solid #424a54", dark_popup_rule)
        self.assertIn("selection-background-color: #3d6fa3", dark_popup_rule)
        self.assertIn("selection-color: #ffffff", dark_popup_rule)
        self.assertIn("color: #1f252d", light_popup_rule)
        self.assertIn("background: #ffffff", light_popup_rule)
        self.assertIn("border: 1px solid #cbd6e3", light_popup_rule)
        self.assertIn("selection-background-color: #b9d7f3", light_popup_rule)
        self.assertIn("selection-color: #0f172a", light_popup_rule)

        dark_hover_rule = self._style_block(
            dark_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:hover",
        )
        dark_selected_rule = self._style_block(
            dark_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected",
        )
        light_hover_rule = self._style_block(
            light_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:hover",
        )
        light_selected_rule = self._style_block(
            light_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected",
        )
        dark_active_selected_rule = self._style_block(
            dark_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected:active",
        )
        dark_inactive_selected_rule = self._style_block(
            dark_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected:!active",
        )
        light_active_selected_rule = self._style_block(
            light_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected:active",
        )
        light_inactive_selected_rule = self._style_block(
            light_style,
            "QWidget#tabAnalysis QComboBox QAbstractItemView::item:selected:!active",
        )

        self.assertIn("background: #345f8d", dark_hover_rule)
        self.assertIn("color: #ffffff", dark_hover_rule)
        self.assertIn("background: #3d6fa3", dark_selected_rule)
        self.assertIn("color: #ffffff", dark_selected_rule)
        self.assertIn("background: #cfe5fb", light_hover_rule)
        self.assertIn("color: #0f172a", light_hover_rule)
        self.assertIn("background: #b9d7f3", light_selected_rule)
        self.assertIn("color: #0f172a", light_selected_rule)
        self.assertIn("background: #3d6fa3", dark_active_selected_rule)
        self.assertIn("background: #3d6fa3", dark_inactive_selected_rule)
        self.assertIn("background: #b9d7f3", light_active_selected_rule)
        self.assertIn("background: #b9d7f3", light_inactive_selected_rule)

        min_highlight_delta = 72
        for popup_rule, highlighted_rule in (
            (dark_popup_rule, dark_hover_rule),
            (dark_popup_rule, dark_selected_rule),
            (dark_popup_rule, dark_active_selected_rule),
            (dark_popup_rule, dark_inactive_selected_rule),
            (light_popup_rule, light_hover_rule),
            (light_popup_rule, light_selected_rule),
            (light_popup_rule, light_active_selected_rule),
            (light_popup_rule, light_inactive_selected_rule),
        ):
            with self.subTest(highlighted_rule=highlighted_rule.split("{", maxsplit=1)[0]):
                popup_background = self._style_property(popup_rule, "background")
                highlighted_background = self._style_property(highlighted_rule, "background")

                self.assertGreaterEqual(
                    self._rgb_distance(popup_background, highlighted_background),
                    min_highlight_delta,
                )

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

    def test_dark_stylesheet_uses_white_image_tab_close_button(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.DARK)

        close_button_block = self._style_block(
            style_sheet,
            "QTabWidget#tabsImages QTabBar::close-button",
        )
        close_icon_path = PROJECT_ROOT / "src/pic_viewer/ui/resources/icons/tab-close.svg"
        close_icon = close_icon_path.read_text(encoding="utf-8")

        self.assertIn("tab-close.svg", close_button_block)
        self.assertIn(close_icon_path.as_posix(), close_button_block)
        self.assertNotIn("@PICVIEWER_ICON_DIR@", close_button_block)
        self.assertIn('stroke="#ffffff"', close_icon)
        self.assertIn("width: 12px", close_button_block)
        self.assertIn("height: 12px", close_button_block)
        self.assertNotIn("QToolButton#buttonImageTabClose", style_sheet)

    def test_light_stylesheet_uses_black_image_tab_close_button(self) -> None:
        style_sheet = styles.load_stylesheet(styles.AppearanceTheme.LIGHT)

        close_button_block = self._style_block(
            style_sheet,
            "QTabWidget#tabsImages QTabBar::close-button",
        )
        close_icon_path = PROJECT_ROOT / "src/pic_viewer/ui/resources/icons/tab-close-on-light.svg"

        self.assertIn("tab-close-on-light.svg", close_button_block)
        self.assertIn(close_icon_path.as_posix(), close_button_block)
        self.assertNotIn("@PICVIEWER_ICON_DIR@", close_button_block)
        self.assertIn("width: 12px", close_button_block)
        self.assertIn("height: 12px", close_button_block)

    def test_tab_bar_tracks_use_panel_backgrounds(self) -> None:
        expected_backgrounds = {
            styles.AppearanceTheme.DARK: {
                "QTabWidget#tabsMetadata QTabBar": "#24282d",
                "QTabWidget#tabsImages QTabBar": "#24282d",
                "QTabWidget#tabsInfo QTabBar": "#24282d",
            },
            styles.AppearanceTheme.LIGHT: {
                "QTabWidget#tabsMetadata QTabBar": "#ffffff",
                "QTabWidget#tabsImages QTabBar": "#ffffff",
                "QTabWidget#tabsInfo QTabBar": "#ffffff",
            },
        }

        for theme, selector_backgrounds in expected_backgrounds.items():
            with self.subTest(theme=theme):
                style_sheet = styles.load_stylesheet(theme)

                for selector, background in selector_backgrounds.items():
                    tab_widget_selector = selector.rsplit(" ", maxsplit=1)[0]

                    self.assertIn(f"{selector} {{", style_sheet)
                    self.assertIn(f"{tab_widget_selector}::tab-bar {{", style_sheet)

                    tab_bar_block = self._style_block(style_sheet, selector)
                    tab_bar_subcontrol_block = self._style_block(style_sheet, f"{tab_widget_selector}::tab-bar")

                    self.assertIn(f"background: {background}", tab_bar_block)
                    self.assertIn(f"background: {background}", tab_bar_subcontrol_block)

    def test_tab_headers_use_rounded_top_corners(self) -> None:
        style_sheet = styles.load_stylesheet()

        self.assertIn("border-top-left-radius: 5px", style_sheet)
        self.assertIn("border-top-right-radius: 5px", style_sheet)

    def test_image_and_info_tabs_reuse_metadata_tab_header_styles(self) -> None:
        selectors = (
            "QTabWidget#tabsImages QTabBar::tab",
            "QTabWidget#tabsImages QTabBar::tab:hover",
            "QTabWidget#tabsImages QTabBar::tab:selected",
            "QTabWidget#tabsImages QTabBar::tab:selected:hover",
            "QTabWidget#tabsInfo QTabBar::tab",
            "QTabWidget#tabsInfo QTabBar::tab:hover",
            "QTabWidget#tabsInfo QTabBar::tab:selected",
            "QTabWidget#tabsInfo QTabBar::tab:selected:hover",
        )

        for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
            with self.subTest(theme=theme):
                style_sheet = styles.load_stylesheet(theme)

                for selector in selectors:
                    self.assertNotIn(f"{selector} {{", style_sheet)

    def test_tab_headers_keep_height_close_to_text_height(self) -> None:
        style_sheet = styles.load_stylesheet()

        tab_block = self._style_block(style_sheet, "QTabBar::tab")

        self.assertIn("min-height: 0px", tab_block)
        self.assertIn("padding: 2px 12px", tab_block)

    def test_tab_headers_do_not_draw_visible_borders(self) -> None:
        for theme in (styles.AppearanceTheme.DARK, styles.AppearanceTheme.LIGHT):
            with self.subTest(theme=theme):
                style_sheet = styles.load_stylesheet(theme)
                tab_block = self._style_block(style_sheet, "QTabBar::tab")

                self.assertIn("border: 1px solid transparent;", tab_block)
                self.assertIn("outline: none;", tab_block)
                self.assertNotIn("border-bottom-color:", tab_block)

                for selector in (
                    "QTabBar::tab:hover",
                    "QTabBar::tab:selected",
                ):
                    state_block = self._style_block(style_sheet, selector)

                    self.assertNotIn("border-color:", state_block)
                    self.assertNotIn("border-top-color:", state_block)
                    self.assertNotIn("border-bottom-color:", state_block)

    def test_load_stylesheet_returns_empty_string_when_file_missing(self) -> None:
        missing_path = PROJECT_ROOT / "missing-main.qss"

        with patch.object(styles, "stylesheet_path", return_value=missing_path):
            self.assertEqual("", styles.load_stylesheet(styles.AppearanceTheme.DARK))

    def test_apply_stylesheet_sets_loaded_qss_on_widget(self) -> None:
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)

        applied_theme = styles.apply_stylesheet(
            window,
            styles.AppearanceTheme.LIGHT,
            styles.CanvasColor.MIDDLE_GRAY_18,
        )

        self.assertEqual(styles.AppearanceTheme.LIGHT, applied_theme)
        self.assertEqual(
            styles.load_stylesheet(
                styles.AppearanceTheme.LIGHT,
                styles.CanvasColor.MIDDLE_GRAY_18,
            ),
            window.styleSheet(),
        )

    @staticmethod
    def _style_block(style_sheet: str, selector: str) -> str:
        search_start = 0

        while True:
            block_start = style_sheet.index("{", search_start)
            selector_start = style_sheet.rfind("}", 0, block_start) + 1
            block_end = style_sheet.index("}", block_start)
            style_block = style_sheet[selector_start:block_end]

            if selector in UiStylesTests._style_block_selectors(style_block):
                return style_block

            search_start = block_end + 1

    @staticmethod
    def _last_style_block(style_sheet: str, selector: str) -> str:
        search_start = 0
        last_match: str | None = None

        while search_start < len(style_sheet):
            block_start = style_sheet.find("{", search_start)
            if block_start < 0:
                break
            selector_start = style_sheet.rfind("}", 0, block_start) + 1
            block_end = style_sheet.index("}", block_start)
            style_block = style_sheet[selector_start:block_end]

            if selector in UiStylesTests._style_block_selectors(style_block):
                last_match = style_block

            search_start = block_end + 1

        if last_match is None:
            raise ValueError(f"Style selector not found: {selector}")
        return last_match

    @staticmethod
    def _style_block_selectors(style_block: str) -> tuple[str, ...]:
        selector_text = style_block.split("{", maxsplit=1)[0]
        return tuple(selector.strip() for selector in selector_text.split(","))

    @staticmethod
    def _style_property(style_block: str, property_name: str) -> str:
        property_start = style_block.index(f"{property_name}: ") + len(property_name) + 2
        property_end = style_block.index(";", property_start)
        return style_block[property_start:property_end]

    @staticmethod
    def _rgb_distance(first_color: str, second_color: str) -> int:
        first_channels = UiStylesTests._hex_color_channels(first_color)
        second_channels = UiStylesTests._hex_color_channels(second_color)
        return sum(abs(first - second) for first, second in zip(first_channels, second_channels))

    @staticmethod
    def _hex_color_channels(color: str) -> tuple[int, int, int]:
        color_value = color.removeprefix("#")
        return (
            int(color_value[0:2], 16),
            int(color_value[2:4], 16),
            int(color_value[4:6], 16),
        )


if __name__ == "__main__":
    unittest.main()
