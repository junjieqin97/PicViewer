from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide2 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.analysis_view import (  # noqa: E402
    AnalysisView,
    AnalysisViewSettings,
    LumaRgbMode,
    RgbChannel,
)
from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult  # noqa: E402
from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
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
        self.assertEqual("Loading preview", title.text())
        self.assertIn(path.name, detail.text())

    def test_full_load_failure_shows_specific_inline_reason(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/unsupported.raw")
        controller.open_image(path)

        controller._on_error(path, 1, "Unsupported image format")

        title = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateTitle")
        reason = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateReason")
        lbl_image = ui.tabsImages.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(title)
        self.assertIsNotNone(reason)
        self.assertIsNotNone(lbl_image)
        self.assertEqual("Unable to Open Image", title.text())
        self.assertEqual("Unsupported image format", reason.text())
        self.assertNotEqual("Failed to load", lbl_image.text())

    def test_retry_clears_error_and_restarts_preview_and_full_load(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/retry.jpg")
        controller.open_image(path)
        controller._on_error(path, 1, "Unable to read this image file")
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

        self.assertEqual("Generating histogram...", ui.widgetHistogram.text())
        self.assertEqual("Generating waveform...", ui.widgetWaveform.text())
        self.assertEqual("Reading metadata...", ui.tableMetadataGeneral.item(0, 0).text())

    def test_failed_image_shows_analysis_failure_and_reason(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/fail.jpg")
        controller._load_error_by_path[str(path)] = "Unable to read this image file"

        MainController.update_info_for_image(controller, path)

        self.assertEqual("Image failed to load. Analysis is unavailable.", ui.widgetHistogram.text())
        self.assertEqual("Image failed to load. Analysis is unavailable.", ui.widgetWaveform.text())
        self.assertEqual("Failure Reason", ui.tableMetadataGeneral.item(1, 0).text())
        self.assertEqual("Unable to read this image file", ui.tableMetadataGeneral.item(1, 1).text())

    def test_switching_back_to_cached_image_refreshes_analysis_pixmaps(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path_a = Path("/tmp/a.jpg")
        path_b = Path("/tmp/b.jpg")
        controller._images_by_path[str(path_a)] = self._image_result((255, 0, 0))
        controller._images_by_path[str(path_b)] = self._image_result((0, 255, 0))

        MainController.update_info_for_image(controller, path_a)
        self.assertEqual((255, 0, 0), self._center_pixmap_color(ui.widgetHistogram))
        MainController.update_info_for_image(controller, path_b)
        self.assertEqual((0, 255, 0), self._center_pixmap_color(ui.widgetHistogram))
        MainController.update_info_for_image(controller, path_a)

        self.assertEqual((255, 0, 0), self._center_pixmap_color(ui.widgetHistogram))
        self.assertEqual((255, 0, 0), self._center_pixmap_color(ui.widgetWaveform))

    def test_refreshing_same_image_reuses_current_analysis_pixmaps(self) -> None:
        window, _ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path = Path("/tmp/a.jpg")
        controller._images_by_path[str(path)] = self._image_result((255, 0, 0))

        MainController.update_info_for_image(controller, path)
        MainController.update_info_for_image(controller, path)

        controller._image_service.render_analysis_view.assert_called_once()

    def test_long_metadata_values_have_full_value_tooltips(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        long_value = "/tmp/" + ("nested/" * 8) + "sample-with-a-long-name.jpg"

        controller._populate_metadata_table(
            ui.tableMetadataGeneral,
            (("Path", long_value),),
            "No general metadata",
        )

        value_item = ui.tableMetadataGeneral.item(0, 1)
        self.assertEqual(long_value, value_item.text())
        self.assertEqual(long_value, value_item.toolTip())

    def test_empty_metadata_state_spans_both_columns_and_is_not_selectable(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        controller._populate_metadata_table(ui.tableMetadataExif, tuple(), "No Exif metadata")

        table = ui.tableMetadataExif
        empty_item = table.item(0, 0)
        self.assertEqual("No Exif metadata", empty_item.text())
        self.assertEqual(2, table.columnSpan(0, 0))
        self.assertEqual(QtCore.Qt.AlignCenter, empty_item.textAlignment())
        self.assertFalse(empty_item.flags() & QtCore.Qt.ItemIsSelectable)

    def test_metadata_table_clears_empty_span_when_entries_return(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        controller._populate_metadata_table(ui.tableMetadataTiff, tuple(), "No TIFF metadata")
        controller._populate_metadata_table(ui.tableMetadataTiff, (("Make", "Example"),), "No TIFF metadata")

        table = ui.tableMetadataTiff
        self.assertEqual(1, table.columnSpan(0, 0))
        self.assertEqual("Make", table.item(0, 0).text())
        self.assertEqual("Example", table.item(0, 1).text())

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

    def _configure_analysis_rendering(self, controller: MainController) -> None:
        controller._analysis_histogram_size = QtCore.QSize(8, 8)
        controller._analysis_waveform_size = QtCore.QSize(8, 8)
        controller._analysis_resize_active = False
        controller._analysis_render_key_by_path = {}
        controller._current_analysis_render_key = None
        controller._view_settings = AnalysisViewSettings(
            mode=LumaRgbMode.LUMA,
            channel=RgbChannel.ALL,
        )
        controller._view_service = MagicMock()
        controller._view_service.build_view.side_effect = self._build_luma_view
        controller._image_service = MagicMock()
        controller._image_service.render_analysis_view.side_effect = self._render_luma_view

    def _build_luma_view(self, analysis: ImageAnalysis, _settings: AnalysisViewSettings) -> AnalysisView:
        return AnalysisView(
            histogram_rgb=analysis.histogram_luma,
            waveform_rgb=analysis.waveform_luma,
        )

    def _render_luma_view(
        self,
        analysis: ImageAnalysis,
        settings: AnalysisViewSettings,
        _hist_size: tuple[int, int],
        _wave_size: tuple[int, int],
        _dpr: float,
    ) -> AnalysisView:
        return self._build_luma_view(analysis, settings)

    def _image_result(self, color_rgb: tuple[int, int, int]) -> ImageLoadResult:
        rgb = np.zeros((8, 8, 3), dtype=np.uint8)
        rgb[:] = color_rgb
        analysis = ImageAnalysis(
            analysis_bgr=rgb[:, :, ::-1],
            preview_rgb=rgb,
            source_size=(8, 8),
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
        return ImageLoadResult(
            analysis=analysis,
            metadata=ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple()),
        )

    def _center_pixmap_color(self, label: QtWidgets.QLabel) -> tuple[int, int, int]:
        pixmap = label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        image = pixmap.toImage()
        color = image.pixelColor(image.width() // 2, image.height() // 2)
        return color.red(), color.green(), color.blue()


if __name__ == "__main__":
    unittest.main()
