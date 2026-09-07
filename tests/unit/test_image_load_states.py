from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtWidgets

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
from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult, PreviewLoadResult  # noqa: E402
from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import ColorSpacePreset  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class ImageLoadStateTests(QtWidgetTestCase):
    """Validate inline loading, failure, and retry states for image tabs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_new_image_tab_shows_loading_text_only_state(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")

        controller.open_image(path)

        state = ui.tabsImages.findChild(QtWidgets.QWidget, "widgetImageLoadState")
        title = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateTitle")
        detail = ui.tabsImages.findChild(QtWidgets.QLabel, "labelImageLoadStateDetail")
        progress = ui.tabsImages.findChild(QtWidgets.QProgressBar, "progressImageLoadState")
        stack = ui.tabsImages.findChild(QtWidgets.QStackedWidget, "stackImageContent")
        self.assertIsNotNone(state)
        self.assertIsNotNone(title)
        self.assertIsNotNone(detail)
        self.assertIsNotNone(progress)
        self.assertIsNotNone(stack)
        self.assertIs(stack.currentWidget(), state)
        self.assertEqual("Loading...", title.text())
        self.assertEqual("", detail.text())
        self.assertTrue(detail.isHidden())
        self.assertTrue(progress.isHidden())

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


class InfoPanelLoadStateTests(QtWidgetTestCase):
    """Validate right-side analysis and metadata states."""

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
        self.assertEqual("Loading", ui.labelImageColorSpaceValue.text())
        self.assertEqual("R -1", ui.labelPixelRedValue.text())
        self.assertEqual("G -1", ui.labelPixelGreenValue.text())
        self.assertEqual("B -1", ui.labelPixelBlueValue.text())
        self.assertEqual("L -1", ui.labelPixelLumaValue.text())
        self.assertEqual(-1, ui.widgetHistogram.luma_marker_value())

    def test_initial_charts_explain_how_to_show_analysis(self) -> None:
        window, ui, _controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        self.assertEqual("Open an image to view its histogram.", ui.widgetHistogram.text())
        self.assertEqual("Open an image to view its waveform.", ui.widgetWaveform.text())
        for chart in (ui.widgetHistogram, ui.widgetWaveform):
            self.assertTrue(chart.wordWrap())
            self.assertEqual(QtCore.Qt.AlignmentFlag.AlignCenter, chart.alignment())
            self._assert_label_has_no_pixmap(chart)

    def test_non_loaded_states_clear_charts_and_restore_cached_analysis(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        loaded_path = Path("/tmp/loaded.jpg")
        loading_path = Path("/tmp/loading.jpg")
        failed_path = Path("/tmp/failed.jpg")
        controller._images_by_path[str(loaded_path)] = self._image_result((64, 96, 128))
        controller._load_tasks_by_path[str(loading_path)] = object()
        controller._load_error_by_path[str(failed_path)] = "Unable to read this image file"

        for path in (None, loading_path, failed_path):
            with self.subTest(path=path):
                controller.update_info_for_image(loaded_path)
                ui.labelPixelRedValue.setText("R 64")
                ui.labelPixelGreenValue.setText("G 96")
                ui.labelPixelBlueValue.setText("B 128")
                ui.labelPixelLumaValue.setText("L 90")
                ui.widgetHistogram.set_luma_marker_value(90)
                controller.update_info_for_image(path)

                for chart in (ui.widgetHistogram, ui.widgetWaveform):
                    self._assert_label_has_no_pixmap(chart)
                    self.assertTrue(chart.text())
                for prefix, label in zip(
                    "RGBL", (ui.labelPixelRedValue, ui.labelPixelGreenValue,
                             ui.labelPixelBlueValue, ui.labelPixelLumaValue),
                ):
                    self.assertEqual(f"{prefix} -1", label.text())
                self.assertEqual(-1, ui.widgetHistogram.luma_marker_value())
                self.assertIsNone(controller._current_analysis_render_key)

                controller.update_info_for_image(loaded_path)
                for chart in (ui.widgetHistogram, ui.widgetWaveform):
                    self.assertEqual("", chart.text())
                    self.assertEqual((64, 96, 128), self._center_pixmap_color(chart))

    def test_retry_success_and_last_tab_close_update_chart_states(self) -> None:
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController(window, ui, MagicMock(), MagicMock())
        self._configure_analysis_rendering(controller)
        # Keep real load scheduling and UI refreshes, but complete workers deterministically.
        controller._thread_pool.start = MagicMock()
        path = Path("/tmp/retry-analysis.jpg")
        controller.open_image(path)
        controller._on_error(path, 1, "Unable to read this image file")
        self.assertEqual("Histogram unavailable", ui.widgetHistogram.text())

        retry = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonImageLoadRetry")
        retry.click()
        self.assertEqual("Generating histogram...", ui.widgetHistogram.text())
        self.assertEqual("Generating waveform...", ui.widgetWaveform.text())
        controller._on_loaded(path, 2, self._image_result((32, 64, 96)))
        for chart in (ui.widgetHistogram, ui.widgetWaveform):
            self.assertEqual("", chart.text())
            self.assertEqual((32, 64, 96), self._center_pixmap_color(chart))

        controller.close_current_tab()
        self.assertIsNone(controller._current_image_path())
        self.assertEqual("Open an image to view its histogram.", ui.widgetHistogram.text())
        self.assertEqual("Open an image to view its waveform.", ui.widgetWaveform.text())
        for chart in (ui.widgetHistogram, ui.widgetWaveform):
            self._assert_label_has_no_pixmap(chart)

    def test_failed_image_shows_analysis_failure_and_reason(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/fail.jpg")
        controller._load_error_by_path[str(path)] = "Unable to read this image file"

        MainController.update_info_for_image(controller, path)

        self.assertEqual("Histogram unavailable", ui.widgetHistogram.text())
        self.assertEqual("Waveform unavailable", ui.widgetWaveform.text())
        self.assertEqual("Failure Reason", ui.tableMetadataGeneral.item(1, 0).text())
        self.assertEqual("Unable to read this image file", ui.tableMetadataGeneral.item(1, 1).text())
        self.assertEqual("Unavailable", ui.labelImageColorSpaceValue.text())
        self.assertEqual("R -1", ui.labelPixelRedValue.text())
        self.assertEqual("G -1", ui.labelPixelGreenValue.text())
        self.assertEqual("B -1", ui.labelPixelBlueValue.text())
        self.assertEqual("L -1", ui.labelPixelLumaValue.text())
        self.assertEqual(-1, ui.widgetHistogram.luma_marker_value())

    def test_no_current_image_shows_not_loaded_color_space_info(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        ui.comboSpecifiedImageColorSpace.setEnabled(False)

        MainController.update_info_for_image(controller, None)

        self.assertEqual("Not Loaded", ui.labelImageColorSpaceValue.text())
        self.assertTrue(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("R -1", ui.labelPixelRedValue.text())
        self.assertEqual("G -1", ui.labelPixelGreenValue.text())
        self.assertEqual("B -1", ui.labelPixelBlueValue.text())
        self.assertEqual("L -1", ui.labelPixelLumaValue.text())
        self.assertEqual(-1, ui.widgetHistogram.luma_marker_value())

    def test_preview_payload_updates_color_space_info_before_full_load(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/preview.jpg")
        self._add_image_tab(controller, path)
        controller._preview_by_path[str(path)] = PreviewLoadResult(
            preview_rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            source_color_profile=ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
            ),
        )

        MainController.update_info_for_image(controller, path)

        self.assertEqual("sRGB (default, no embedded ICC)", ui.labelImageColorSpaceValue.text())
        self.assertTrue(ui.comboSpecifiedImageColorSpace.isEnabled())
        stack = ui.tabsImages.findChild(QtWidgets.QStackedWidget, "stackImageContent")
        state = ui.tabsImages.findChild(QtWidgets.QWidget, "widgetImageLoadState")
        lbl_image = ui.tabsImages.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(stack)
        self.assertIsNotNone(state)
        self.assertIsNotNone(lbl_image)
        self.assertIs(stack.currentWidget(), state)
        self._assert_label_has_no_pixmap(lbl_image)

    def test_preview_payload_with_embedded_icc_disables_specified_image_color_space_selector(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/profiled-preview.jpg")
        controller._preview_by_path[str(path)] = PreviewLoadResult(
            preview_rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            source_color_profile=ImageColorProfileInfo(
                display_name="Example Profile",
                status=ImageColorProfileStatus.EMBEDDED,
                uses_srgb_fallback=False,
            ),
        )

        MainController.update_info_for_image(controller, path)

        self.assertEqual("Example Profile (embedded ICC)", ui.labelImageColorSpaceValue.text())
        self.assertFalse(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("", ui.comboSpecifiedImageColorSpace.currentText())

    def test_preview_raw_payload_locks_specified_image_color_space_selector_to_prophoto(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        display_p3_index = ui.comboSpecifiedImageColorSpace.findData(ColorSpacePreset.DISPLAY_P3)
        ui.comboSpecifiedImageColorSpace.setCurrentIndex(display_p3_index)
        controller._assumed_source_color_space = ColorSpacePreset.DISPLAY_P3
        path = Path("/tmp/raw-preview.dng")
        self._add_image_tab(controller, path)
        controller._preview_by_path[str(path)] = PreviewLoadResult(
            preview_rgb=np.zeros((8, 8, 3), dtype=np.uint8),
            source_color_profile=ImageColorProfileInfo(
                display_name="ProPhoto RGB",
                status=ImageColorProfileStatus.RAW_DECODED,
                uses_srgb_fallback=False,
                assumed_color_space=ColorSpacePreset.PROPHOTO_RGB,
            ),
        )

        MainController.update_info_for_image(controller, path)

        self.assertEqual("ProPhoto RGB (RAW output)", ui.labelImageColorSpaceValue.text())
        self.assertFalse(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("ProPhoto RGB", ui.comboSpecifiedImageColorSpace.currentText())
        self.assertEqual(ColorSpacePreset.DISPLAY_P3, controller._assumed_source_color_space)

    def test_full_load_updates_color_space_info_from_analysis_payload(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path = Path("/tmp/profiled.jpg")
        controller._images_by_path[str(path)] = self._image_result(
            (255, 0, 0),
            source_color_profile=ImageColorProfileInfo(
                display_name="Example Profile",
                status=ImageColorProfileStatus.EMBEDDED,
                uses_srgb_fallback=False,
            ),
        )

        MainController.update_info_for_image(controller, path)

        self.assertEqual("Example Profile (embedded ICC)", ui.labelImageColorSpaceValue.text())
        self.assertFalse(ui.comboSpecifiedImageColorSpace.isEnabled())

    def test_full_load_with_fallback_profile_enables_specified_image_color_space_selector(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        ui.comboSpecifiedImageColorSpace.setEnabled(False)
        display_p3_index = ui.comboSpecifiedImageColorSpace.findData(ColorSpacePreset.DISPLAY_P3)
        ui.comboSpecifiedImageColorSpace.setCurrentIndex(display_p3_index)
        controller._assumed_source_color_space = ColorSpacePreset.DISPLAY_P3
        path = Path("/tmp/no-profile.jpg")
        controller._images_by_path[str(path)] = self._image_result(
            (255, 0, 0),
            source_color_profile=ImageColorProfileInfo(
                display_name="Display P3",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
                assumed_color_space=ColorSpacePreset.DISPLAY_P3,
            ),
        )

        MainController.update_info_for_image(controller, path)

        self.assertEqual("Display P3 (specified, no embedded ICC)", ui.labelImageColorSpaceValue.text())
        self.assertTrue(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("Display P3", ui.comboSpecifiedImageColorSpace.currentText())

    def test_specified_image_color_space_selector_restores_selection_after_raw_output(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        display_p3_index = ui.comboSpecifiedImageColorSpace.findData(ColorSpacePreset.DISPLAY_P3)
        ui.comboSpecifiedImageColorSpace.setCurrentIndex(display_p3_index)
        controller._assumed_source_color_space = ColorSpacePreset.DISPLAY_P3
        raw_path = Path("/tmp/raw.dng")
        fallback_path = Path("/tmp/no-profile.jpg")
        controller._images_by_path[str(raw_path)] = self._image_result(
            (255, 0, 0),
            source_color_profile=ImageColorProfileInfo(
                display_name="ProPhoto RGB",
                status=ImageColorProfileStatus.RAW_DECODED,
                uses_srgb_fallback=False,
                assumed_color_space=ColorSpacePreset.PROPHOTO_RGB,
            ),
        )
        controller._images_by_path[str(fallback_path)] = self._image_result(
            (0, 255, 0),
            source_color_profile=ImageColorProfileInfo(
                display_name="Display P3",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
                assumed_color_space=ColorSpacePreset.DISPLAY_P3,
            ),
        )

        MainController.update_info_for_image(controller, raw_path)
        self.assertFalse(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("ProPhoto RGB", ui.comboSpecifiedImageColorSpace.currentText())

        MainController.update_info_for_image(controller, fallback_path)

        self.assertTrue(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("Display P3", ui.comboSpecifiedImageColorSpace.currentText())

    def test_specified_image_color_space_selector_restores_selection_after_embedded_icc(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        display_p3_index = ui.comboSpecifiedImageColorSpace.findData(ColorSpacePreset.DISPLAY_P3)
        ui.comboSpecifiedImageColorSpace.setCurrentIndex(display_p3_index)
        controller._assumed_source_color_space = ColorSpacePreset.DISPLAY_P3
        profiled_path = Path("/tmp/profiled.jpg")
        fallback_path = Path("/tmp/no-profile.jpg")
        controller._images_by_path[str(profiled_path)] = self._image_result(
            (255, 0, 0),
            source_color_profile=ImageColorProfileInfo(
                display_name="Example Profile",
                status=ImageColorProfileStatus.EMBEDDED,
                uses_srgb_fallback=False,
            ),
        )
        controller._images_by_path[str(fallback_path)] = self._image_result(
            (0, 255, 0),
            source_color_profile=ImageColorProfileInfo(
                display_name="Display P3",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
                assumed_color_space=ColorSpacePreset.DISPLAY_P3,
            ),
        )

        MainController.update_info_for_image(controller, profiled_path)
        self.assertFalse(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("", ui.comboSpecifiedImageColorSpace.currentText())

        MainController.update_info_for_image(controller, fallback_path)

        self.assertTrue(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("Display P3", ui.comboSpecifiedImageColorSpace.currentText())

    def test_color_space_info_formats_invalid_and_conversion_fallback_states(self) -> None:
        window, _ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        invalid = MainController._format_source_color_profile_info(
            controller,
            ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.INVALID,
                uses_srgb_fallback=True,
            ),
        )
        failed = MainController._format_source_color_profile_info(
            controller,
            ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.CONVERSION_FAILED,
                uses_srgb_fallback=True,
            ),
        )

        self.assertEqual("sRGB (default, unreadable ICC)", invalid)
        self.assertEqual("sRGB (fallback, ICC conversion failed)", failed)

    def test_color_space_info_formats_specified_fallback_states(self) -> None:
        window, _ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        missing = MainController._format_source_color_profile_info(
            controller,
            ImageColorProfileInfo(
                display_name="Display P3",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
                assumed_color_space=ColorSpacePreset.DISPLAY_P3,
            ),
        )
        invalid = MainController._format_source_color_profile_info(
            controller,
            ImageColorProfileInfo(
                display_name="Adobe RGB (1998)",
                status=ImageColorProfileStatus.INVALID,
                uses_srgb_fallback=True,
                assumed_color_space=ColorSpacePreset.ADOBE_RGB_1998,
            ),
        )
        failed = MainController._format_source_color_profile_info(
            controller,
            ImageColorProfileInfo(
                display_name="Display P3",
                status=ImageColorProfileStatus.CONVERSION_FAILED,
                uses_srgb_fallback=True,
                assumed_color_space=ColorSpacePreset.DISPLAY_P3,
            ),
        )

        self.assertEqual("Display P3 (specified, no embedded ICC)", missing)
        self.assertEqual("Adobe RGB (1998) (specified, unreadable ICC)", invalid)
        self.assertEqual("Display P3 (specified fallback, ICC conversion failed)", failed)

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

    def test_update_info_refreshes_analysis_widgets_after_analysis_tab_detaches(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path = Path("/tmp/detached-analysis.jpg")
        controller._images_by_path[str(path)] = self._image_result((64, 96, 128))
        floating = ui.tabsInfo.detach_tab(ui.tabsInfo.indexOf(ui.tabAnalysis))
        self.addCleanup(floating.deleteLater)

        MainController.update_info_for_image(controller, path)

        self.assertEqual((64, 96, 128), self._center_pixmap_color(ui.widgetHistogram))
        self.assertEqual((64, 96, 128), self._center_pixmap_color(ui.widgetWaveform))

    def test_update_info_refreshes_metadata_tables_after_metadata_tab_detaches(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path = Path("/tmp/detached-metadata.jpg")
        controller._images_by_path[str(path)] = self._image_result(
            (10, 20, 30),
            metadata=ImageMetadata(
                general=(("File Name", "detached-metadata.jpg"),),
                exif=tuple(),
                iptc=tuple(),
                tiff=tuple(),
            ),
        )
        floating = ui.tabsInfo.detach_tab(ui.tabsInfo.indexOf(ui.tabMetadata))
        self.addCleanup(floating.deleteLater)

        MainController.update_info_for_image(controller, path)

        self.assertEqual("File Name", ui.tableMetadataGeneral.item(0, 0).text())
        self.assertEqual("detached-metadata.jpg", ui.tableMetadataGeneral.item(0, 1).text())

    def test_metadata_key_and_value_items_use_full_text_tooltips(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        controller._populate_metadata_table(
            ui.tableMetadataGeneral,
            (("Short Key", "Short Value"),),
            "No general metadata",
        )

        key_item = ui.tableMetadataGeneral.item(0, 0)
        value_item = ui.tableMetadataGeneral.item(0, 1)
        self.assertEqual("Short Key", key_item.text())
        self.assertEqual("Short Key", key_item.toolTip())
        self.assertEqual("Short Value", value_item.text())
        self.assertEqual("Short Value", value_item.toolTip())

    def test_metadata_copy_helper_writes_key_and_value_text_to_clipboard(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.clear()

        controller._populate_metadata_table(
            ui.tableMetadataGeneral,
            (("Camera Model", "X-T5"),),
            "No general metadata",
        )

        controller._copy_metadata_item_text(ui.tableMetadataGeneral.item(0, 0))
        self.assertEqual("Camera Model", clipboard.text())

        controller._copy_metadata_item_text(ui.tableMetadataGeneral.item(0, 1))
        self.assertEqual("X-T5", clipboard.text())

    def test_empty_metadata_state_spans_both_columns_and_is_not_selectable(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        controller._populate_metadata_table(ui.tableMetadataExif, tuple(), "No Exif metadata")

        table = ui.tableMetadataExif
        empty_item = table.item(0, 0)
        self.assertEqual("No Exif metadata", empty_item.text())
        self.assertEqual(2, table.columnSpan(0, 0))
        self.assertEqual(QtCore.Qt.AlignmentFlag.AlignCenter, empty_item.textAlignment())
        self.assertFalse(empty_item.flags() & QtCore.Qt.ItemFlag.ItemIsSelectable)
        self.assertFalse(controller._is_metadata_copyable_item(table, empty_item))

    def test_metadata_table_clears_empty_span_when_entries_return(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        controller._populate_metadata_table(ui.tableMetadataTiff, tuple(), "No TIFF metadata")
        controller._populate_metadata_table(ui.tableMetadataTiff, (("Make", "Example"),), "No TIFF metadata")

        table = ui.tableMetadataTiff
        self.assertEqual(1, table.columnSpan(0, 0))
        self.assertEqual("Make", table.item(0, 0).text())
        self.assertEqual("Example", table.item(0, 1).text())

    def test_loaded_image_updates_metadata_overlay_on_image_label(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path = Path("/tmp/overlay.jpg")
        controller._show_metadata_overlay = True
        self._add_image_tab(controller, path)
        controller._images_by_path[str(path)] = self._image_result(
            (20, 30, 40),
            metadata=ImageMetadata(
                general=(("Resolution", "6000 x 4000"),),
                exif=(
                    ("Make", "FUJIFILM"),
                    ("Model", "X-T5"),
                    ("LensModel", "XF 33mm F1.4"),
                    ("FNumber", "2.8"),
                    ("ExposureTime", "1/125"),
                    ("ISOSpeedRatings", "400"),
                ),
                iptc=tuple(),
                tiff=tuple(),
            ),
        )

        MainController.update_info_for_image(controller, path)

        lbl_image = ui.tabsImages.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(lbl_image)
        self.assertTrue(lbl_image.is_metadata_overlay_visible())
        self.assertEqual(
            (
                "FUJIFILM X-T5 XF 33mm F1.4",
                "f/2.8 1/125s ISO 400",
                "6000 x 4000",
            ),
            lbl_image.metadata_overlay_lines(),
        )

    def test_metadata_overlay_toggle_hides_current_image_overlay(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/overlay.jpg")
        controller._show_metadata_overlay = True
        self._add_image_tab(controller, path)
        controller._images_by_path[str(path)] = self._image_result((20, 30, 40))
        MainController._sync_metadata_overlay_for_path(controller, path)

        MainController._on_metadata_overlay_toggled(controller, False)

        lbl_image = ui.tabsImages.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(lbl_image)
        self.assertFalse(lbl_image.is_metadata_overlay_visible())

    def test_preview_load_updates_filmstrip_but_keeps_image_tab_loading(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/preview-only.jpg")
        self._add_image_tab(controller, path)
        controller._add_filmstrip_placeholder_item(path)
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._preview_tasks_by_path[key] = object()
        controller._update_filmstrip_icon = MagicMock()  # type: ignore[method-assign]
        controller.update_info_for_image = MagicMock()  # type: ignore[method-assign]
        result = PreviewLoadResult(
            preview_rgb=np.full((8, 8, 3), 96, dtype=np.uint8),
            source_color_profile=ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
            ),
        )

        MainController._on_preview_loaded(controller, path, 1, result)

        self.assertIs(controller._preview_by_path[key], result)
        controller._update_filmstrip_icon.assert_called_once_with(
            path,
            result.preview_rgb,
            result.display_color_space,
        )
        controller.update_info_for_image.assert_called_once_with(path)
        stack = ui.tabsImages.findChild(QtWidgets.QStackedWidget, "stackImageContent")
        state = ui.tabsImages.findChild(QtWidgets.QWidget, "widgetImageLoadState")
        lbl_image = ui.tabsImages.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(stack)
        self.assertIsNotNone(state)
        self.assertIsNotNone(lbl_image)
        self.assertIs(stack.currentWidget(), state)
        self._assert_label_has_no_pixmap(lbl_image)

    def test_full_load_shows_image_page_and_fits_current_viewport(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        path = Path("/tmp/full.jpg")
        self._add_image_tab(controller, path)
        window.resize(1200, 800)
        window.show()
        self._app.processEvents()
        result = self._image_result((20, 40, 80))
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._load_tasks_by_path[key] = object()
        controller._update_filmstrip_icon = MagicMock()  # type: ignore[method-assign]

        MainController._on_loaded(controller, path, 1, result)

        stack = ui.tabsImages.findChild(QtWidgets.QStackedWidget, "stackImageContent")
        image_page = ui.tabsImages.findChild(QtWidgets.QWidget, "pageImagePreview")
        current_tab = controller._tab_widget_for_path(path)
        self.assertIsNotNone(current_tab)
        scroll_area = current_tab.findChild(QtWidgets.QScrollArea, "scrollImage")
        lbl_image = current_tab.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(stack)
        self.assertIsNotNone(image_page)
        self.assertIsNotNone(scroll_area)
        self.assertIsNotNone(lbl_image)
        self.assertIs(stack.currentWidget(), image_page)
        pixmap = lbl_image.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        logical = controller._pixmap_logical_size(pixmap)
        self.assertEqual(scroll_area.viewport().height(), logical.height())
        self.assertLessEqual(logical.width(), scroll_area.viewport().width())

    def test_folder_full_load_refreshes_after_viewport_layout_stabilizes(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        self._configure_analysis_rendering(controller)
        controller._ensure_preview_load = MagicMock()  # type: ignore[method-assign]
        controller._ensure_full_load = MagicMock()  # type: ignore[method-assign]
        window.resize(1200, 800)
        window.show()
        self._app.processEvents()
        paths = [Path(f"/tmp/folder-{index}.jpg") for index in range(6)]
        controller._open_image_paths(paths)
        last_path = paths[-1]
        key = str(last_path)
        result = self._image_result((64, 96, 128))
        controller._active_session_by_path[key] = 1
        controller._load_tasks_by_path[key] = object()
        controller._update_filmstrip_icon = MagicMock()  # type: ignore[method-assign]

        MainController._on_loaded(controller, last_path, 1, result)
        self._app.processEvents()

        current_tab = controller._tab_widget_for_path(last_path)
        self.assertIsNotNone(current_tab)
        scroll_area = current_tab.findChild(QtWidgets.QScrollArea, "scrollImage")
        lbl_image = current_tab.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(scroll_area)
        self.assertIsNotNone(lbl_image)
        pixmap = lbl_image.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        logical = controller._pixmap_logical_size(pixmap)
        self.assertGreater(logical.width(), 500)
        self.assertGreater(logical.height(), 300)
        self.assertLessEqual(logical.width(), scroll_area.viewport().width())
        self.assertLessEqual(logical.height(), scroll_area.viewport().height())

    def _build_controller(self) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui
        controller._main_window = window
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._display_color_space = ColorSpacePreset.SRGB
        controller._assumed_source_color_space = ColorSpacePreset.SRGB
        controller._rendering_intent = RenderingIntent.PERCEPTUAL
        controller._images_by_path = {}
        controller._preview_by_path = {}
        controller._load_tasks_by_path = {}
        controller._preview_tasks_by_path = {}
        controller._load_error_by_path = {}
        controller._active_session_by_path = {}
        controller._session_counter_by_path = {}
        controller._last_metadata_path = None
        controller._show_underexposed = False
        controller._show_overexposed = False
        controller._focus_peak_level = None
        controller._show_metadata_overlay = True
        controller._zoom_by_path = {}
        controller._fit_to_window_by_path = {}
        controller._tab_preview_render_key_by_path = {}
        controller._image_context_menu = ui.menuImageContext
        controller._cursor_override_target = None
        controller._image_dragging = False
        controller._image_drag_start_pos = None
        controller._image_drag_start_scroll = None
        controller._image_drag_scroll_area = None
        controller._detached_image_windows = {}
        controller._detached_info_windows = {}
        controller._syncing_selection = False
        controller._active_image_path = None
        controller._analysis_render_key_by_path = {}
        controller._current_analysis_render_key = None
        controller._view_settings = AnalysisViewSettings(
            mode=LumaRgbMode.LUMA,
            channel=RgbChannel.ALL,
        )
        controller._image_service = MagicMock()
        controller._image_service.build_preview_with_pseudo_color_overlay.side_effect = (
            lambda preview_rgb, **_kwargs: preview_rgb
        )
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
        controller._image_service.build_preview_with_pseudo_color_overlay.side_effect = (
            lambda preview_rgb, **_kwargs: preview_rgb
        )

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

    def _image_result(
        self,
        color_rgb: tuple[int, int, int],
        metadata: ImageMetadata | None = None,
        source_color_profile: ImageColorProfileInfo | None = None,
    ) -> ImageLoadResult:
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
            source_color_profile=source_color_profile
            or ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
            ),
        )
        return ImageLoadResult(
            analysis=analysis,
            metadata=metadata or ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple()),
        )

    def _add_image_tab(self, controller: MainController, path: Path) -> None:
        tab_container = MainController._build_image_tab_container(controller, path)
        controller._ui.tabsImages.addTab(tab_container, path.name)
        controller._ui.tabsImages.setCurrentIndex(0)

    def _center_pixmap_color(self, label: QtWidgets.QLabel) -> tuple[int, int, int]:
        pixmap = label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        image = pixmap.toImage()
        color = image.pixelColor(image.width() // 2, image.height() // 2)
        return color.red(), color.green(), color.blue()

    def _assert_label_has_no_pixmap(self, label: QtWidgets.QLabel) -> None:
        pixmap = label.pixmap()
        if pixmap is None:
            return
        self.assertTrue(pixmap.isNull())


if __name__ == "__main__":
    unittest.main()
