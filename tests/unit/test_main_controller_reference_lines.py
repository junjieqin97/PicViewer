from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402


class MainControllerReferenceLineTests(QtWidgetTestCase):
    """Validate controller state flow for global reference line toggles."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_reference_line_toggle_updates_only_requested_flag(self) -> None:
        module = self._reference_lines_module()
        controller, labels = self._build_controller_with_labels()

        MainController._on_cross_reference_line_toggled(controller, True)
        MainController._on_diagonal_reference_line_toggled(controller, True)

        self.assertEqual(
            module.ReferenceLineSettings(cross=True, diagonal=True, thirds=False),
            controller._reference_line_settings,
        )
        for label in labels:
            self.assertEqual(controller._reference_line_settings, label.reference_line_settings())

    def test_new_image_preview_page_receives_current_reference_line_settings(self) -> None:
        module = self._reference_lines_module()
        window = QtWidgets.QWidget()
        self.addCleanup(window.deleteLater)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._reference_line_settings = module.ReferenceLineSettings(cross=True, thirds=True)
        controller._image_context_menu = QtWidgets.QMenu(window)
        controller._cursor_override_target = None
        self.addCleanup(controller._image_context_menu.deleteLater)

        image_page = MainController._build_image_preview_page(controller, window)

        lbl_image = image_page.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(lbl_image)
        self.assertEqual(controller._reference_line_settings, lbl_image.reference_line_settings())

    def tearDown(self) -> None:
        self._app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self._app.processEvents()

    def _build_controller_with_labels(self):
        module = self._reference_lines_module()
        from pic_viewer.ui.widgets.image_display_label import ImageDisplayLabel

        tabs = QtWidgets.QTabWidget()
        self.addCleanup(tabs.deleteLater)
        labels = []
        for index in range(2):
            tab = QtWidgets.QWidget()
            layout = QtWidgets.QVBoxLayout(tab)
            label = ImageDisplayLabel(tab)
            label.setObjectName("lblImage")
            layout.addWidget(label)
            tabs.addTab(tab, f"Image {index}")
            labels.append(label)

        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller)
        action_cross = QtGui.QAction()
        action_cross.setCheckable(True)
        action_diagonal = QtGui.QAction()
        action_diagonal.setCheckable(True)
        action_thirds = QtGui.QAction()
        action_thirds.setCheckable(True)
        controller._ui = SimpleNamespace(
            tabsImages=tabs,
            actToggleCrossReferenceLine=action_cross,
            actToggleDiagonalReferenceLine=action_diagonal,
            actToggleThirdsReferenceLine=action_thirds,
        )
        controller._reference_line_settings = module.ReferenceLineSettings()
        return controller, labels

    def _reference_lines_module(self):
        import importlib
        import importlib.util

        spec = importlib.util.find_spec("pic_viewer.domain.rules.reference_lines")
        assert spec is not None, "reference_lines module should exist"
        return importlib.import_module("pic_viewer.domain.rules.reference_lines")


if __name__ == "__main__":
    unittest.main()
