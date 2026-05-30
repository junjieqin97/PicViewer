from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.image_analysis import ImageLoadResult, PreviewLoadResult  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import WorkingColorSpace  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402
from pic_viewer.ui.workers.image_worker import ImageLoadTask, PreviewLoadTask  # noqa: E402


class WorkingColorSpaceControllerTests(unittest.TestCase):
    """Validate UI-driven working color space reload behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_worker_tasks_pass_working_color_space_to_service(self) -> None:
        service = MagicMock()
        path = Path("/tmp/profiled.jpg")
        preview_result = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            working_color_space=WorkingColorSpace.DISPLAY_P3,
        )
        service.load_preview.return_value = preview_result
        service.load_and_analyze.return_value = MagicMock()

        PreviewLoadTask(service, path, WorkingColorSpace.DISPLAY_P3).run()
        ImageLoadTask(service, path, WorkingColorSpace.PROPHOTO_RGB).run()

        service.load_preview.assert_called_once_with(path, WorkingColorSpace.DISPLAY_P3)
        service.load_and_analyze.assert_called_once_with(path, WorkingColorSpace.PROPHOTO_RGB)

    def test_switching_working_color_space_clears_image_caches_and_reloads_open_tabs(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        tab = QtWidgets.QWidget()
        tab.setProperty("image_path", str(path))
        ui.tabsImages.addTab(tab, path.name)
        ui.tabsImages.setCurrentIndex(0)
        key = str(path)
        controller._images_by_path[key] = object()
        controller._preview_by_path[key] = object()
        controller._load_error_by_path[key] = "old error"
        controller._preview_tasks_by_path[key] = object()
        controller._load_tasks_by_path[key] = object()
        controller._analysis_render_key_by_path[key] = object()
        controller._tab_preview_render_key_by_path[key] = object()
        controller._zoom_by_path[key] = 2.0

        index = ui.comboWorkingColorSpace.findData(WorkingColorSpace.DISPLAY_P3)
        MainController._on_working_color_space_changed(controller, index)

        self.assertEqual(WorkingColorSpace.DISPLAY_P3, controller._working_color_space)
        self.assertNotIn(key, controller._images_by_path)
        self.assertNotIn(key, controller._preview_by_path)
        self.assertNotIn(key, controller._load_error_by_path)
        self.assertNotIn(key, controller._preview_tasks_by_path)
        self.assertNotIn(key, controller._load_tasks_by_path)
        self.assertNotIn(key, controller._analysis_render_key_by_path)
        self.assertNotIn(key, controller._tab_preview_render_key_by_path)
        self.assertEqual(2.0, controller._zoom_by_path[key])
        controller._ensure_preview_load.assert_called_once_with(path, 1)
        controller._ensure_full_load.assert_called_once_with(path, 1)
        controller.update_info_for_image.assert_called_once_with(path)

    def test_stale_preview_result_from_old_working_space_is_ignored(self) -> None:
        window, _, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._preview_tasks_by_path[key] = object()
        controller._working_color_space = WorkingColorSpace.DISPLAY_P3
        result = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            working_color_space=WorkingColorSpace.SRGB,
            source_color_profile=ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
            ),
        )
        controller._ui.labelImageColorSpaceValue.setText("Display P3 (embedded ICC)")

        MainController._on_preview_loaded(controller, path, 1, result)

        self.assertNotIn(key, controller._preview_by_path)
        self.assertEqual("Display P3 (embedded ICC)", controller._ui.labelImageColorSpaceValue.text())

    def test_stale_full_load_result_from_old_working_space_is_ignored(self) -> None:
        window, _, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._load_tasks_by_path[key] = object()
        controller._working_color_space = WorkingColorSpace.DISPLAY_P3
        analysis = MagicMock()
        analysis.working_color_space = WorkingColorSpace.SRGB
        analysis.source_color_profile = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        result = ImageLoadResult(analysis=analysis, metadata=MagicMock())
        controller._ui.labelImageColorSpaceValue.setText("Display P3 (embedded ICC)")

        MainController._on_loaded(controller, path, 1, result)

        self.assertNotIn(key, controller._images_by_path)
        self.assertEqual("Display P3 (embedded ICC)", controller._ui.labelImageColorSpaceValue.text())

    def _build_controller(self) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._main_window = window
        controller._ui = ui
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._working_color_space = WorkingColorSpace.SRGB
        controller._images_by_path = {}
        controller._preview_by_path = {}
        controller._preview_tasks_by_path = {}
        controller._load_tasks_by_path = {}
        controller._load_error_by_path = {}
        controller._active_session_by_path = {}
        controller._session_counter_by_path = {}
        controller._detached_image_windows = {}
        controller._analysis_render_key_by_path = {}
        controller._tab_preview_render_key_by_path = {}
        controller._zoom_by_path = {}
        controller._ensure_preview_load = MagicMock()  # type: ignore[method-assign]
        controller._ensure_full_load = MagicMock()  # type: ignore[method-assign]
        controller.update_info_for_image = MagicMock()  # type: ignore[method-assign]
        controller._update_filmstrip_icon = MagicMock()  # type: ignore[method-assign]
        controller._refresh_tab_preview_pixmap = MagicMock()  # type: ignore[method-assign]
        return window, ui, controller


if __name__ == "__main__":
    unittest.main()
