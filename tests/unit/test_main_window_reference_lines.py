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

from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class MainWindowReferenceLineTests(QtWidgetTestCase):
    """Validate reference line menu actions and image label compatibility."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_tools_menu_contains_independent_reference_line_actions(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("menuReferenceLines", ui.menuReferenceLines.objectName())
        self.assertEqual("Reference Lines", ui.menuReferenceLines.title())
        self.assertIn(ui.menuReferenceLines.menuAction(), ui.menuTools.actions())
        self.assertNotIn(ui.menuReferenceLines.menuAction(), ui.menuView.actions())

        actions = (
            ui.actToggleCrossReferenceLine,
            ui.actToggleDiagonalReferenceLine,
            ui.actToggleThirdsReferenceLine,
        )
        self.assertEqual(
            ["Cross Reference Line", "Diagonal Reference Line", "Rule of Thirds Reference Line"],
            [action.text() for action in actions],
        )
        self.assertTrue(all(action.isCheckable() for action in actions))
        self.assertFalse(any(action.isChecked() for action in actions))

        ui.actToggleCrossReferenceLine.setChecked(True)

        self.assertTrue(ui.actToggleCrossReferenceLine.isChecked())
        self.assertFalse(ui.actToggleDiagonalReferenceLine.isChecked())
        self.assertFalse(ui.actToggleThirdsReferenceLine.isChecked())

    def test_reference_line_toolbar_buttons_reuse_actions_and_have_icons(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        action_by_button = {
            ui.buttonToolbarCrossReferenceLine: ui.actToggleCrossReferenceLine,
            ui.buttonToolbarDiagonalReferenceLine: ui.actToggleDiagonalReferenceLine,
            ui.buttonToolbarThirdsReferenceLine: ui.actToggleThirdsReferenceLine,
        }

        for button, action in action_by_button.items():
            with self.subTest(button=button.objectName()):
                self.assertIs(action, button.defaultAction())
                self.assertEqual(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly, button.toolButtonStyle())
                self.assertLessEqual(button.iconSize().height(), 18)
                self.assertLessEqual(button.iconSize().width(), 18)
                self.assertFalse(button.icon().isNull())
                self.assertEqual(action.text(), button.toolTip())

    def test_image_preview_uses_label_compatible_display_widget(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        from pic_viewer.controllers.main_controller import MainController

        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui
        image_page = controller._build_image_preview_page(window)

        lbl_image = image_page.findChild(QtWidgets.QLabel, "lblImage")

        self.assertIsNotNone(lbl_image)
        self.assertTrue(hasattr(lbl_image, "set_reference_line_settings"))

    def tearDown(self) -> None:
        self._app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self._app.processEvents()


if __name__ == "__main__":
    unittest.main()
