from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

import cv2
import numpy as np
from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtGui, QtWidgets

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult  # noqa: E402
from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.domain.rules.reference_lines import ReferenceLineSettings  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class MainControllerPixelSampleTests(QtWidgetTestCase):
    """Validate mouse-driven RGB/luma sample updates."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_mouse_move_over_current_image_updates_sample_values_and_marker(self) -> None:
        window, ui, controller, path, label, bgr = self._build_loaded_image_controller()
        self.addCleanup(window.deleteLater)
        expected_luma = int(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)[1, 2])
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(2, 1),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )

        MainController.eventFilter(controller, label, event)

        self.assertEqual(path, controller._current_image_path())
        self.assertEqual("30", ui.labelPixelRedValue.text())
        self.assertEqual("20", ui.labelPixelGreenValue.text())
        self.assertEqual("10", ui.labelPixelBlueValue.text())
        self.assertEqual(str(expected_luma), ui.labelPixelLumaValue.text())
        self.assertEqual(expected_luma, ui.widgetHistogram.luma_marker_value())

    def test_mouse_leave_image_resets_sample_values_and_marker(self) -> None:
        _window, ui, controller, _path, label, _bgr = self._build_loaded_image_controller()
        self.addCleanup(_window.deleteLater)
        ui.labelPixelRedValue.setText("30")
        ui.labelPixelGreenValue.setText("20")
        ui.labelPixelBlueValue.setText("10")
        ui.labelPixelLumaValue.setText("22")
        ui.widgetHistogram.set_luma_marker_value(22)

        MainController.eventFilter(controller, label, QtCore.QEvent(QtCore.QEvent.Type.Leave))

        self.assertEqual("-1", ui.labelPixelRedValue.text())
        self.assertEqual("-1", ui.labelPixelGreenValue.text())
        self.assertEqual("-1", ui.labelPixelBlueValue.text())
        self.assertEqual("-1", ui.labelPixelLumaValue.text())
        self.assertEqual(-1, ui.widgetHistogram.luma_marker_value())

    def _build_loaded_image_controller(
        self,
    ) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController, Path, QtWidgets.QLabel, np.ndarray]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._main_window = window
        controller._ui = ui
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._images_by_path = {}
        controller._preview_by_path = {}
        controller._load_error_by_path = {}
        controller._load_tasks_by_path = {}
        controller._preview_tasks_by_path = {}
        controller._detached_image_windows = {}
        controller._reference_line_settings = ReferenceLineSettings()
        controller._syncing_selection = False
        controller._active_image_path = None
        controller._cursor_override_target = None
        controller._image_dragging = False
        controller._image_drag_start_pos = None
        controller._image_drag_start_scroll = None
        controller._image_drag_scroll_area = None
        controller._image_context_menu = ui.menuImageContext
        controller._refresh_actions_state = MagicMock()  # type: ignore[method-assign]
        controller._ensure_full_load = MagicMock()  # type: ignore[method-assign]
        controller._sync_filmstrip_summary = MagicMock()  # type: ignore[method-assign]

        path = Path("/tmp/pixel-sample.jpg")
        tab_container = MainController._build_image_tab_container(controller, path)
        ui.tabsImages.addTab(tab_container, path.name)
        ui.tabsImages.setCurrentIndex(0)
        label = tab_container.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(label)
        label.resize(4, 4)
        pixmap = QtGui.QPixmap(4, 4)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        label.setPixmap(pixmap)

        bgr = np.zeros((4, 4, 3), dtype=np.uint8)
        bgr[1, 2] = [10, 20, 30]
        rgb = bgr[:, :, ::-1].copy()
        analysis = ImageAnalysis(
            analysis_bgr=bgr,
            preview_rgb=rgb,
            source_size=(4, 4),
            histogram_rgb=rgb,
            histogram_luma=rgb,
            histogram_r=rgb,
            histogram_g=rgb,
            histogram_b=rgb,
            waveform_rgb=rgb,
            waveform_luma=rgb,
            waveform_r=rgb,
            waveform_g=rgb,
            waveform_b=rgb,
        )
        controller._images_by_path[str(path)] = ImageLoadResult(
            analysis=analysis,
            metadata=ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple()),
        )
        return window, ui, controller, path, label, bgr


if __name__ == "__main__":
    unittest.main()
