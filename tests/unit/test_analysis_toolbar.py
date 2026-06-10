from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class AnalysisToolbarTests(QtWidgetTestCase):
    """Validate the compact top analysis toolbar."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_toolbar_is_top_level_compact_and_hidden_by_view_action(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("widgetAnalysisToolbar", ui.widgetAnalysisToolbar.objectName())
        self.assertIs(ui.widgetAnalysisToolbar, ui.layoutMain.itemAt(0).widget())
        self.assertIs(ui.splitMain, ui.layoutMain.itemAt(1).widget())
        self.assertIs(ui.frameFilmstrip, ui.layoutMain.itemAt(2).widget())
        self.assertEqual(QtWidgets.QSizePolicy.Policy.Fixed, ui.widgetAnalysisToolbar.sizePolicy().verticalPolicy())
        self.assertLessEqual(ui.widgetAnalysisToolbar.maximumHeight(), 30)
        self.assertTrue(ui.widgetAnalysisToolbar.isVisibleTo(window) or not window.isVisible())

        self.assertEqual("actToggleAnalysisToolbar", ui.actToggleAnalysisToolbar.objectName())
        self.assertTrue(ui.actToggleAnalysisToolbar.isCheckable())
        self.assertTrue(ui.actToggleAnalysisToolbar.isChecked())
        self.assertIn(ui.actToggleAnalysisToolbar, ui.menuView.actions())

    def test_toolbar_buttons_are_icon_only_and_reuse_menu_actions(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        action_by_button = {
            ui.buttonToolbarModeLuma: ui.actModeLuma,
            ui.buttonToolbarModeRgb: ui.actModeRgb,
            ui.buttonToolbarChannelAll: ui.actChannelAll,
            ui.buttonToolbarChannelRed: ui.actChannelRed,
            ui.buttonToolbarChannelGreen: ui.actChannelGreen,
            ui.buttonToolbarChannelBlue: ui.actChannelBlue,
            ui.buttonToolbarUnderexposed: ui.actToggleUnderexposed,
            ui.buttonToolbarOverexposed: ui.actToggleOverexposed,
            ui.buttonToolbarPeakHigh: ui.actPeakHigh,
            ui.buttonToolbarPeakMedium: ui.actPeakMedium,
            ui.buttonToolbarPeakLow: ui.actPeakLow,
            ui.buttonToolbarCrossReferenceLine: ui.actToggleCrossReferenceLine,
            ui.buttonToolbarDiagonalReferenceLine: ui.actToggleDiagonalReferenceLine,
            ui.buttonToolbarThirdsReferenceLine: ui.actToggleThirdsReferenceLine,
            ui.buttonToolbarMetadataOverlay: ui.actToggleMetadataOverlay,
        }

        for button, action in action_by_button.items():
            with self.subTest(button=button.objectName()):
                self.assertIs(action, button.defaultAction())
                self.assertEqual(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly, button.toolButtonStyle())
                self.assertLessEqual(button.iconSize().height(), 18)
                self.assertLessEqual(button.iconSize().width(), 18)
                self.assertFalse(button.icon().isNull())
                self.assertEqual(action.text(), button.toolTip())

        self.assertTrue(ui.actToggleMetadataOverlay.isCheckable())
        self.assertTrue(ui.actToggleMetadataOverlay.isChecked())
        self.assertIn(ui.actToggleMetadataOverlay, ui.menuView.actions())

    def test_toolbar_button_group_is_centered_between_stretches(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        layout = ui.widgetAnalysisToolbar.layout()

        self.assertIsNotNone(layout.itemAt(0).spacerItem())
        self.assertEqual(
            ui.buttonToolbarMetadataOverlay.minimumSize(),
            layout.itemAt(0).spacerItem().sizeHint(),
        )
        self.assertIsNotNone(layout.itemAt(1).spacerItem())
        self.assertIsNotNone(layout.itemAt(layout.count() - 2).spacerItem())
        self.assertIs(ui.buttonToolbarModeLuma, layout.itemAt(2).widget())
        self.assertIs(ui.buttonToolbarThirdsReferenceLine, layout.itemAt(layout.count() - 3).widget())
        self.assertIs(ui.buttonToolbarMetadataOverlay, layout.itemAt(layout.count() - 1).widget())

    def test_controller_toggle_analysis_toolbar_changes_toolbar_visibility(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui

        MainController._toggle_analysis_toolbar(controller, False)
        self.assertTrue(ui.widgetAnalysisToolbar.isHidden())

        MainController._toggle_analysis_toolbar(controller, True)
        self.assertFalse(ui.widgetAnalysisToolbar.isHidden())


if __name__ == "__main__":
    unittest.main()
