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
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class ImageLoadStateTests(unittest.TestCase):
    """Validate inline loading, failure, and retry states for image tabs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_new_image_tab_shows_preview_loading_state(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")

        controller.open_image(path)

        state = ui.tabsImages.findChild(QtWidgets.QWidget, "widgetImageLoadState")
        title = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateTitle")
        detail = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateDetail")
        stack = ui.tabsImages.findChild(QtWidgets.QStackedWidget, "stackImageContent")
        self.assertIsNotNone(state)
        self.assertIsNotNone(title)
        self.assertIsNotNone(detail)
        self.assertIsNotNone(stack)
        self.assertIs(stack.currentWidget(), state)
        self.assertEqual("正在加载预览", title.text())
        self.assertIn(path.name, detail.text())

    def test_full_load_failure_shows_specific_inline_reason(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/unsupported.raw")
        controller.open_image(path)

        controller._on_error(path, 1, "不支持该图片格式")

        title = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateTitle")
        reason = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateReason")
        lbl_image = ui.tabsImages.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(title)
        self.assertIsNotNone(reason)
        self.assertIsNotNone(lbl_image)
        self.assertEqual("无法打开图片", title.text())
        self.assertEqual("不支持该图片格式", reason.text())
        self.assertNotEqual("加载失败", lbl_image.text())

    def test_retry_clears_error_and_restarts_preview_and_full_load(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/retry.jpg")
        controller.open_image(path)
        controller._on_error(path, 1, "无法读取该图片文件")
        controller._ensure_preview_load.reset_mock()
        controller._ensure_full_load.reset_mock()

        retry = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonImageLoadRetry")
        self.assertIsNotNone(retry)
        retry.click()

        self.assertNotIn(str(path), controller._load_error_by_path)
        controller._ensure_preview_load.assert_called_once_with(path, 2)
        controller._ensure_full_load.assert_called_once_with(path, 2)

    def _build_controller(self) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController]:
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
        controller._preview_tasks_by_path = {}
        controller._load_tasks_by_path = {}
        controller._load_error_by_path = {}
        controller._active_session_by_path = {}
        controller._session_counter_by_path = {}
        controller._syncing_selection = False
        controller._zoom_by_path = {}
        controller._fit_to_window_by_path = {}
        controller._analysis_render_key_by_path = {}
        controller._tab_preview_render_key_by_path = {}
        controller._show_underexposed = False
        controller._show_overexposed = False
        controller._image_context_menu = ui.menuImageContext
        controller._cursor_override_target = None
        controller._image_dragging = False
        controller._image_drag_start_pos = None
        controller._image_drag_start_scroll = None
        controller._image_drag_scroll_area = None
        controller._ensure_preview_load = MagicMock()  # type: ignore[method-assign]
        controller._ensure_full_load = MagicMock()  # type: ignore[method-assign]
        controller.update_info_for_image = MagicMock()  # type: ignore[method-assign]
        return window, ui, controller


class InfoPanelLoadStateTests(unittest.TestCase):
    """Validate right-side analysis and metadata placeholders."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_loading_image_shows_analysis_loading_placeholders(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/loading.jpg")
        controller._load_tasks_by_path[str(path)] = object()

        MainController.update_info_for_image(controller, path)

        self.assertEqual("正在生成直方图…", ui.widgetHistogram.text())
        self.assertEqual("正在生成波形图…", ui.widgetWaveform.text())
        self.assertEqual("正在读取元数据…", ui.tableMetadataGeneral.item(0, 0).text())

    def test_failed_image_shows_analysis_failure_and_reason(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/fail.jpg")
        controller._load_error_by_path[str(path)] = "无法读取该图片文件"

        MainController.update_info_for_image(controller, path)

        self.assertEqual("图片加载失败，无法生成分析", ui.widgetHistogram.text())
        self.assertEqual("图片加载失败，无法生成分析", ui.widgetWaveform.text())
        self.assertEqual("失败原因", ui.tableMetadataGeneral.item(1, 0).text())
        self.assertEqual("无法读取该图片文件", ui.tableMetadataGeneral.item(1, 1).text())

    def _build_controller(self) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._images_by_path = {}
        controller._preview_by_path = {}
        controller._load_tasks_by_path = {}
        controller._preview_tasks_by_path = {}
        controller._load_error_by_path = {}
        controller._last_metadata_path = None
        return window, ui, controller


if __name__ == "__main__":
    unittest.main()
