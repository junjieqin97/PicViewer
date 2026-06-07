from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402
from pic_viewer.ui.resources import styles  # noqa: E402


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

    def test_help_menu_contains_about_and_third_party_license_actions(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("actThirdPartyLicenses", ui.actThirdPartyLicenses.objectName())
        self.assertEqual("Third-Party License Information", ui.actThirdPartyLicenses.text())
        self.assertEqual(
            [ui.actAbout, ui.actThirdPartyLicenses],
            [action for action in ui.menuHelp.actions() if not action.isSeparator()],
        )

    def test_view_menu_contains_appearance_theme_actions(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("menuAppearance", ui.menuAppearance.objectName())
        self.assertEqual("Appearance", ui.menuAppearance.title())
        self.assertIn(ui.menuAppearance.menuAction(), ui.menuView.actions())

        actions = (ui.actAppearanceLight, ui.actAppearanceDark)
        self.assertEqual(["Light", "Dark"], [action.text() for action in actions])
        self.assertTrue(all(action.isCheckable() for action in actions))
        self.assertTrue(ui.actionGroupAppearance.isExclusive())
        self.assertEqual(
            [ui.actAppearanceLight, ui.actAppearanceDark],
            ui.actionGroupAppearance.actions(),
        )

    def test_view_menu_places_metadata_overlay_before_appearance(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        view_actions = [action for action in ui.menuView.actions() if not action.isSeparator()]

        self.assertLess(
            view_actions.index(ui.actToggleMetadataOverlay),
            view_actions.index(ui.menuAppearance.menuAction()),
        )
        self.assertEqual(ui.actToggleMetadataOverlay, view_actions[3])
        self.assertEqual(ui.menuAppearance.menuAction(), view_actions[-1])

    def test_image_context_menu_contains_show_in_folder_action(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        context_actions = [action for action in ui.menuImageContext.actions() if not action.isSeparator()]

        self.assertEqual("actShowInFolder", ui.actShowInFolder.objectName())
        self.assertEqual("Show in Folder", ui.actShowInFolder.text())
        self.assertTrue(ui.actShowInFolder.shortcut().isEmpty())
        self.assertEqual(
            [ui.actZoomIn, ui.actZoomOut, ui.actFitToWindow, ui.actShowInFolder],
            context_actions,
        )
        self.assertNotIn(ui.actShowInFolder, ui.menuFile.actions())
        self.assertNotIn(ui.actShowInFolder, ui.menuView.actions())
        self.assertNotIn(ui.actShowInFolder, ui.menuTools.actions())
        self.assertNotIn(ui.actShowInFolder, ui.menuHelp.actions())

    def test_initial_appearance_action_follows_system_theme(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        self.addCleanup(window.deleteLater)

        with patch(
            "pic_viewer.ui.windows.main_window.styles.resolve_system_theme",
            return_value=styles.AppearanceTheme.DARK,
        ):
            ui.setup_ui(window)

        self.assertFalse(ui.actAppearanceLight.isChecked())
        self.assertTrue(ui.actAppearanceDark.isChecked())
        self.assertEqual(styles.load_stylesheet(styles.AppearanceTheme.DARK), window.styleSheet())

    def test_appearance_actions_switch_stylesheet_at_runtime(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        self.addCleanup(window.deleteLater)

        with patch(
            "pic_viewer.ui.windows.main_window.styles.resolve_system_theme",
            return_value=styles.AppearanceTheme.LIGHT,
        ):
            ui.setup_ui(window)

        self.assertTrue(ui.actAppearanceLight.isChecked())
        self.assertEqual(styles.load_stylesheet(styles.AppearanceTheme.LIGHT), window.styleSheet())

        ui.actAppearanceDark.trigger()
        self.assertTrue(ui.actAppearanceDark.isChecked())
        self.assertEqual(styles.load_stylesheet(styles.AppearanceTheme.DARK), window.styleSheet())

        ui.actAppearanceLight.trigger()
        self.assertTrue(ui.actAppearanceLight.isChecked())
        self.assertEqual(styles.load_stylesheet(styles.AppearanceTheme.LIGHT), window.styleSheet())

    def test_light_appearance_uses_dark_neutral_icons_visible_in_menus(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        self.addCleanup(window.deleteLater)

        with patch(
            "pic_viewer.ui.windows.main_window.styles.resolve_system_theme",
            return_value=styles.AppearanceTheme.LIGHT,
        ):
            ui.setup_ui(window)

        for action in (
            ui.actModeLuma,
            ui.actToggleMetadataOverlay,
            ui.actToggleCrossReferenceLine,
            ui.actToggleDiagonalReferenceLine,
            ui.actToggleThirdsReferenceLine,
        ):
            with self.subTest(action=action.objectName()):
                self.assertTrue(action.isIconVisibleInMenu())
                self.assertLess(_minimum_icon_luminance(action.icon()), 80)


def _minimum_icon_luminance(icon: QtGui.QIcon) -> float:
    image = icon.pixmap(20, 20).toImage()
    luminance_values: list[float] = []
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color.alpha() == 0:
                continue
            luminance_values.append(
                (0.2126 * color.red()) + (0.7152 * color.green()) + (0.0722 * color.blue())
            )
    return min(luminance_values)


if __name__ == "__main__":
    unittest.main()
