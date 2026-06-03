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
from pic_viewer.common.errors import ColorProfileLoadError  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import LocalColorProfile, WorkingColorSpace  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402
from pic_viewer.ui.workers.image_worker import ImageLoadTask, PreviewLoadTask  # noqa: E402


class WorkingColorSpaceControllerTests(unittest.TestCase):
    """Validate UI-driven working color space reload behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_worker_tasks_pass_color_spaces_to_service(self) -> None:
        service = MagicMock()
        path = Path("/tmp/profiled.jpg")
        preview_result = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            working_color_space=WorkingColorSpace.DISPLAY_P3,
            assumed_source_color_space=WorkingColorSpace.ADOBE_RGB_1998,
            rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        service.load_preview.return_value = preview_result
        service.load_and_analyze.return_value = MagicMock()

        PreviewLoadTask(
            service,
            path,
            WorkingColorSpace.DISPLAY_P3,
            WorkingColorSpace.ADOBE_RGB_1998,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        ).run()
        ImageLoadTask(
            service,
            path,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.DISPLAY_P3,
            RenderingIntent.ABSOLUTE_COLORIMETRIC,
        ).run()

        service.load_preview.assert_called_once_with(
            path,
            WorkingColorSpace.DISPLAY_P3,
            WorkingColorSpace.ADOBE_RGB_1998,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        service.load_and_analyze.assert_called_once_with(
            path,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.DISPLAY_P3,
            RenderingIntent.ABSOLUTE_COLORIMETRIC,
        )

    def test_worker_tasks_pass_local_color_profiles_to_service(self) -> None:
        service = MagicMock()
        path = Path("/tmp/profiled.jpg")
        working_profile = self._local_profile(name="Local Working", file_name="working.icc")
        source_profile = self._local_profile(name="Local Source", file_name="source.icc")
        service.load_preview.return_value = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            working_color_space=working_profile,
            assumed_source_color_space=source_profile,
            rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        service.load_and_analyze.return_value = MagicMock()

        PreviewLoadTask(
            service,
            path,
            working_profile,
            source_profile,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        ).run()
        ImageLoadTask(
            service,
            path,
            working_profile,
            source_profile,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        ).run()

        service.load_preview.assert_called_once_with(
            path,
            working_profile,
            source_profile,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        service.load_and_analyze.assert_called_once_with(
            path,
            working_profile,
            source_profile,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )

    def test_worker_tasks_default_to_app_working_color_space(self) -> None:
        service = MagicMock()
        path = Path("/tmp/profiled.jpg")
        service.load_preview.return_value = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
        )
        service.load_and_analyze.return_value = MagicMock()

        PreviewLoadTask(service, path).run()
        ImageLoadTask(service, path).run()

        service.load_preview.assert_called_once_with(
            path,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.SRGB,
            RenderingIntent.PERCEPTUAL,
        )
        service.load_and_analyze.assert_called_once_with(
            path,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.SRGB,
            RenderingIntent.PERCEPTUAL,
        )

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

    def test_switching_specified_image_color_space_clears_image_caches_and_reloads_open_tabs(self) -> None:
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

        index = ui.comboSpecifiedImageColorSpace.findData(WorkingColorSpace.DISPLAY_P3)
        MainController._on_assumed_source_color_space_changed(controller, index)

        self.assertEqual(WorkingColorSpace.DISPLAY_P3, controller._assumed_source_color_space)
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

    def test_switching_rendering_intent_clears_image_caches_and_reloads_open_tabs(self) -> None:
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

        index = ui.comboRenderingIntent.findData(RenderingIntent.RELATIVE_COLORIMETRIC)
        MainController._on_rendering_intent_changed(controller, index)

        self.assertEqual(RenderingIntent.RELATIVE_COLORIMETRIC, controller._rendering_intent)
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

    def test_choose_local_working_icc_loads_profile_and_reloads_open_images(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        local_profile = self._local_profile(name="Local Working", file_name="working.icc")
        controller._image_service = MagicMock()
        controller._image_service.load_local_color_profile.return_value = local_profile
        controller._reload_open_images_for_color_settings = MagicMock()  # type: ignore[method-assign]
        choose_index = ui.comboWorkingColorSpace.findText("Choose a local ICC...")

        with unittest.mock.patch(
            "pic_viewer.controllers.main_controller_analysis_mixin.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("/tmp/working.icc", "ICC Profiles (*.icc *.icm)"),
        ):
            MainController._on_working_color_space_changed(controller, choose_index)

        controller._image_service.load_local_color_profile.assert_called_once_with(Path("/tmp/working.icc"))
        self.assertEqual(local_profile, controller._working_color_space)
        self.assertEqual(local_profile, ui.comboWorkingColorSpace.currentData())
        self.assertEqual("Local Working", ui.comboWorkingColorSpace.currentText())
        self.assertEqual(
            "Choose a local ICC...",
            ui.comboWorkingColorSpace.itemText(ui.comboWorkingColorSpace.count() - 1),
        )
        controller._reload_open_images_for_color_settings.assert_called_once()

    def test_choose_local_source_icc_loads_profile_and_reloads_open_images(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        local_profile = self._local_profile(name="Local Source", file_name="source.icc")
        controller._image_service = MagicMock()
        controller._image_service.load_local_color_profile.return_value = local_profile
        controller._reload_open_images_for_color_settings = MagicMock()  # type: ignore[method-assign]
        choose_index = ui.comboSpecifiedImageColorSpace.findText("Choose a local ICC...")

        with unittest.mock.patch(
            "pic_viewer.controllers.main_controller_analysis_mixin.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("/tmp/source.icc", "ICC Profiles (*.icc *.icm)"),
        ):
            MainController._on_assumed_source_color_space_changed(controller, choose_index)

        controller._image_service.load_local_color_profile.assert_called_once_with(Path("/tmp/source.icc"))
        self.assertEqual(local_profile, controller._assumed_source_color_space)
        self.assertEqual(local_profile, ui.comboSpecifiedImageColorSpace.currentData())
        self.assertEqual("Local Source", ui.comboSpecifiedImageColorSpace.currentText())
        controller._reload_open_images_for_color_settings.assert_called_once()

    def test_canceling_local_icc_choice_restores_previous_working_color_space(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        controller._image_service = MagicMock()
        controller._reload_open_images_for_color_settings = MagicMock()  # type: ignore[method-assign]
        choose_index = ui.comboWorkingColorSpace.findText("Choose a local ICC...")

        with unittest.mock.patch(
            "pic_viewer.controllers.main_controller_analysis_mixin.QtWidgets.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            MainController._on_working_color_space_changed(controller, choose_index)

        controller._image_service.load_local_color_profile.assert_not_called()
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, controller._working_color_space)
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, ui.comboWorkingColorSpace.currentData())
        controller._reload_open_images_for_color_settings.assert_not_called()

    def test_invalid_local_icc_choice_warns_and_restores_previous_working_color_space(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        controller._image_service = MagicMock()
        controller._image_service.load_local_color_profile.side_effect = ColorProfileLoadError(
            "Unable to load ICC profile"
        )
        controller._reload_open_images_for_color_settings = MagicMock()  # type: ignore[method-assign]
        choose_index = ui.comboWorkingColorSpace.findText("Choose a local ICC...")

        with (
            unittest.mock.patch(
                "pic_viewer.controllers.main_controller_analysis_mixin.QtWidgets.QFileDialog.getOpenFileName",
                return_value=("/tmp/bad.icc", "ICC Profiles (*.icc *.icm)"),
            ),
            unittest.mock.patch(
                "pic_viewer.controllers.main_controller_analysis_mixin.QtWidgets.QMessageBox.warning"
            ) as warning,
        ):
            MainController._on_working_color_space_changed(controller, choose_index)

        controller._image_service.load_local_color_profile.assert_called_once_with(Path("/tmp/bad.icc"))
        warning.assert_called_once()
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, controller._working_color_space)
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, ui.comboWorkingColorSpace.currentData())
        controller._reload_open_images_for_color_settings.assert_not_called()

    def test_specified_source_selector_restores_local_profile_after_embedded_icc(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        local_profile = self._local_profile(name="Local Source", file_name="source.icc")
        controller._assumed_source_color_space = local_profile
        MainController._set_combo_local_color_profile(controller, ui.comboSpecifiedImageColorSpace, local_profile)

        MainController._sync_specified_image_color_space_enabled(
            controller,
            ImageColorProfileInfo(
                display_name="Embedded",
                status=ImageColorProfileStatus.EMBEDDED,
                uses_srgb_fallback=False,
            ),
        )
        self.assertFalse(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual("", ui.comboSpecifiedImageColorSpace.currentText())

        MainController._sync_specified_image_color_space_enabled(
            controller,
            ImageColorProfileInfo(
                display_name="Local Source",
                status=ImageColorProfileStatus.MISSING,
                uses_srgb_fallback=True,
                assumed_color_space=local_profile,
            ),
        )

        self.assertTrue(ui.comboSpecifiedImageColorSpace.isEnabled())
        self.assertEqual(local_profile, ui.comboSpecifiedImageColorSpace.currentData())
        self.assertEqual("Local Source", ui.comboSpecifiedImageColorSpace.currentText())

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
            assumed_source_color_space=WorkingColorSpace.SRGB,
            rendering_intent=RenderingIntent.PERCEPTUAL,
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

    def test_stale_preview_result_from_old_specified_image_color_space_is_ignored(self) -> None:
        window, _, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._preview_tasks_by_path[key] = object()
        controller._working_color_space = WorkingColorSpace.DISPLAY_P3
        controller._assumed_source_color_space = WorkingColorSpace.ADOBE_RGB_1998
        result = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            working_color_space=WorkingColorSpace.DISPLAY_P3,
            assumed_source_color_space=WorkingColorSpace.SRGB,
            rendering_intent=RenderingIntent.PERCEPTUAL,
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

    def test_stale_preview_result_from_old_rendering_intent_is_ignored(self) -> None:
        window, _, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._preview_tasks_by_path[key] = object()
        controller._working_color_space = WorkingColorSpace.DISPLAY_P3
        controller._assumed_source_color_space = WorkingColorSpace.ADOBE_RGB_1998
        controller._rendering_intent = RenderingIntent.RELATIVE_COLORIMETRIC
        result = PreviewLoadResult(
            preview_rgb=np.zeros((1, 1, 3), dtype=np.uint8),
            working_color_space=WorkingColorSpace.DISPLAY_P3,
            assumed_source_color_space=WorkingColorSpace.ADOBE_RGB_1998,
            rendering_intent=RenderingIntent.PERCEPTUAL,
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
        analysis.assumed_source_color_space = WorkingColorSpace.SRGB
        analysis.rendering_intent = RenderingIntent.PERCEPTUAL
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

    def test_stale_full_load_result_from_old_specified_image_color_space_is_ignored(self) -> None:
        window, _, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._load_tasks_by_path[key] = object()
        controller._working_color_space = WorkingColorSpace.DISPLAY_P3
        controller._assumed_source_color_space = WorkingColorSpace.ADOBE_RGB_1998
        analysis = MagicMock()
        analysis.working_color_space = WorkingColorSpace.DISPLAY_P3
        analysis.assumed_source_color_space = WorkingColorSpace.SRGB
        analysis.rendering_intent = RenderingIntent.PERCEPTUAL
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

    def test_stale_full_load_result_from_old_rendering_intent_is_ignored(self) -> None:
        window, _, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/sample.jpg")
        key = str(path)
        controller._active_session_by_path[key] = 1
        controller._load_tasks_by_path[key] = object()
        controller._working_color_space = WorkingColorSpace.DISPLAY_P3
        controller._assumed_source_color_space = WorkingColorSpace.ADOBE_RGB_1998
        controller._rendering_intent = RenderingIntent.RELATIVE_COLORIMETRIC
        analysis = MagicMock()
        analysis.working_color_space = WorkingColorSpace.DISPLAY_P3
        analysis.assumed_source_color_space = WorkingColorSpace.ADOBE_RGB_1998
        analysis.rendering_intent = RenderingIntent.PERCEPTUAL
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
        controller._working_color_space = WorkingColorSpace.PROPHOTO_RGB
        controller._assumed_source_color_space = WorkingColorSpace.SRGB
        controller._rendering_intent = RenderingIntent.PERCEPTUAL
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

    def _local_profile(self, name: str = "Local Profile", file_name: str = "local.icc") -> LocalColorProfile:
        return LocalColorProfile(
            display_name=name,
            path=Path("/tmp") / file_name,
            profile_bytes=b"fake-profile-bytes",
        )


if __name__ == "__main__":
    unittest.main()
