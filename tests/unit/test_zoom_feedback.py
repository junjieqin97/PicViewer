from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402


class MainControllerZoomFeedbackTests(unittest.TestCase):
    """Validate status-bar feedback for image zoom actions."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_fit_to_window_shows_fit_status(self) -> None:
        window, controller, path = self._build_controller()
        self.addCleanup(window.deleteLater)

        MainController._fit_to_window(controller)

        self.assertEqual("缩放：适配窗口", window.statusBar().currentMessage())
        self.assertEqual((1.0, True), MainController._get_zoom_state(controller, path))
        controller._refresh_current_image_pixmap.assert_called_once_with()

    def test_zoom_in_from_fit_shows_percent_status_and_disables_fit(self) -> None:
        window, controller, path = self._build_controller()
        self.addCleanup(window.deleteLater)

        MainController._zoom_in(controller)

        self.assertEqual("缩放：125%", window.statusBar().currentMessage())
        self.assertEqual((1.25, False), MainController._get_zoom_state(controller, path))
        controller._refresh_current_image_pixmap.assert_called_once_with()

    def test_zoom_status_uses_clamped_percent_at_zoom_bounds(self) -> None:
        zoom_step = 1.25
        cases = (
            (5.9, zoom_step, "缩放：600%", 6.0),
            (0.11, 1 / zoom_step, "缩放：10%", 0.1),
        )
        for initial_zoom, factor, expected_status, expected_zoom in cases:
            with self.subTest(expected_status=expected_status):
                window, controller, path = self._build_controller(initial_zoom=initial_zoom, fit=False)
                self.addCleanup(window.deleteLater)

                MainController._adjust_zoom(controller, factor)

                self.assertEqual(expected_status, window.statusBar().currentMessage())
                self.assertEqual((expected_zoom, False), MainController._get_zoom_state(controller, path))

    def test_zoom_action_without_current_image_keeps_status_bar_unchanged(self) -> None:
        window, controller, _ = self._build_controller(current_path=None)
        self.addCleanup(window.deleteLater)
        window.statusBar().showMessage("unchanged")

        MainController._zoom_in(controller)
        MainController._fit_to_window(controller)

        self.assertEqual("unchanged", window.statusBar().currentMessage())
        controller._refresh_current_image_pixmap.assert_not_called()

    def _build_controller(
        self,
        initial_zoom: float = 1.0,
        fit: bool = True,
        current_path: Path | None = Path("/tmp/photo.jpg"),
    ) -> tuple[QtWidgets.QMainWindow, MainController, Path]:
        window = QtWidgets.QMainWindow()
        path = Path("/tmp/photo.jpg")
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._main_window = window
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._zoom_by_path = {str(path): initial_zoom}
        controller._fit_to_window_by_path = {str(path): fit}
        controller._zoom_step = 1.25
        controller._zoom_min = 0.1
        controller._zoom_max = 6.0
        controller._current_image_path = MagicMock(return_value=current_path)  # type: ignore[method-assign]
        controller._refresh_current_image_pixmap = MagicMock()  # type: ignore[method-assign]
        return window, controller, path


if __name__ == "__main__":
    unittest.main()
