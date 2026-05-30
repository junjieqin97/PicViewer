from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock, call

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller_tabs_mixin import MainControllerTabsMixin  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.controllers.main_controller_interaction_mixin import (  # noqa: E402
    MainControllerInteractionMixin,
)
from pic_viewer.controllers.main_controller_filmstrip_mixin import (  # noqa: E402
    MainControllerFilmstripMixin,
)
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402
from pic_viewer.ui.widgets.detachable_tabs import DetachableTabWidget  # noqa: E402


class MainWindowTabsTests(unittest.TestCase):
    """Validate tab alignment behavior in the image display area."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_image_tabs_do_not_expand_to_fill_space(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertFalse(ui.tabsImages.tabBar().expanding())

    def test_image_and_info_tabs_use_detachable_tab_widgets(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertIsInstance(ui.tabsImages, DetachableTabWidget)
        self.assertEqual("image", ui.tabsImages.tab_group())
        self.assertIsInstance(ui.tabsInfo, DetachableTabWidget)
        self.assertEqual("info", ui.tabsInfo.tab_group())
        self.assertNotIsInstance(ui.tabsMetadata, DetachableTabWidget)

    def tearDown(self) -> None:
        self._app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self._app.processEvents()

    def test_main_window_loads_left_aligned_tab_bar_style(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        style_sheet = window.styleSheet()
        self.assertIn("QTabWidget#tabsImages::tab-bar", style_sheet)
        self.assertIn("alignment: left", style_sheet)

    def test_open_image_uses_native_close_button_on_image_tab(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        self._stub_open_image_dependencies(controller)

        controller.open_image(Path("/tmp/sample.jpg"))

        button = ui.tabsImages.tabBar().tabButton(0, QtWidgets.QTabBar.ButtonPosition.RightSide)
        self.assertIsNotNone(button)
        self.assertNotEqual("buttonImageTabClose", button.objectName())

    def test_detached_image_tab_returns_to_main_tabs_when_floating_window_closes(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        self._stub_open_image_dependencies(controller)
        controller.open_image(Path("/tmp/sample.jpg"))

        floating = ui.tabsImages.detach_tab(0)
        self.addCleanup(floating.deleteLater)
        self.assertEqual(0, ui.tabsImages.count())

        floating.close()
        self._app.processEvents()

        self.assertEqual(1, ui.tabsImages.count())
        self.assertEqual("sample.jpg", ui.tabsImages.tabToolTip(0))

    def test_detached_image_tab_content_is_visible_in_floating_window(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        self._stub_open_image_dependencies(controller)
        controller.open_image(Path("/tmp/sample.jpg"))
        window.show()
        self._app.processEvents()

        floating = ui.tabsImages.detach_tab(0)
        self.addCleanup(floating.deleteLater)
        self._app.processEvents()

        self.assertFalse(floating.content_widget().isHidden())
        self.assertTrue(floating.content_widget().isVisible())
        self.assertIsNone(floating.findChild(QtWidgets.QTabBar, "floatingTabBar"))

    def test_detached_info_tab_returns_to_info_tabs_when_floating_window_closes(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        floating = ui.tabsInfo.detach_tab(0)
        self.addCleanup(floating.deleteLater)
        self.assertEqual(-1, ui.tabsInfo.indexOf(ui.tabAnalysis))

        floating.close()
        self._app.processEvents()

        self.assertGreaterEqual(ui.tabsInfo.indexOf(ui.tabAnalysis), 0)
        self.assertEqual("Analysis", ui.tabsInfo.tabText(ui.tabsInfo.indexOf(ui.tabAnalysis)))

    def test_detached_info_tab_content_is_visible_in_floating_window(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)
        window.show()
        self._app.processEvents()

        floating = ui.tabsInfo.detach_tab(ui.tabsInfo.indexOf(ui.tabAnalysis))
        self.addCleanup(floating.deleteLater)
        self._app.processEvents()

        self.assertFalse(floating.content_widget().isHidden())
        self.assertTrue(floating.content_widget().isVisible())
        self.assertIsNone(floating.findChild(QtWidgets.QTabBar, "floatingTabBar"))

    def test_closing_main_window_closes_detached_floating_windows(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        self._stub_open_image_dependencies(controller)
        controller.open_image(Path("/tmp/sample.jpg"))
        window.show()
        self._app.processEvents()

        image_floating = ui.tabsImages.detach_tab(0)
        info_floating = ui.tabsInfo.detach_tab(ui.tabsInfo.indexOf(ui.tabAnalysis))
        self.addCleanup(self._delete_widget_if_valid, image_floating)
        self.addCleanup(self._delete_widget_if_valid, info_floating)
        image_destroyed = MagicMock()
        info_destroyed = MagicMock()
        image_floating.destroyed.connect(image_destroyed)
        info_floating.destroyed.connect(info_destroyed)
        self._app.processEvents()
        self.assertTrue(image_floating.isVisible())
        self.assertTrue(info_floating.isVisible())

        window.close()
        self._app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self._app.processEvents()

        image_destroyed.assert_called_once()
        info_destroyed.assert_called_once()

    def _delete_widget_if_valid(self, widget: QtWidgets.QWidget) -> None:
        try:
            widget.deleteLater()
        except RuntimeError:
            pass

    def test_info_tabs_combine_histogram_and_waveform_in_analysis_tab(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        window.resize(1200, 800)
        window.show()
        self._app.processEvents()

        self.assertEqual("frameHistogramAnalysis", ui.widgetHistogram.parentWidget().objectName())
        self.assertEqual("frameWaveformAnalysis", ui.widgetWaveform.parentWidget().objectName())
        self.assertEqual("tabAnalysis", ui.tabAnalysis.objectName())
        self.assertEqual(2, ui.tabsInfo.count())
        self.assertEqual("Analysis", ui.tabsInfo.tabText(0))
        self.assertEqual("Metadata", ui.tabsInfo.tabText(1))
        self.assertIs(ui.tabAnalysis, ui.tabsInfo.widget(0))
        self.assertIs(ui.tabMetadata, ui.tabsInfo.widget(1))
        self.assertEqual(ui.info_panel_histogram_size, ui.widgetHistogram.size())
        self.assertEqual(ui.info_panel_waveform_size, ui.widgetWaveform.size())

        histogram_frame = ui.frameHistogramAnalysis
        waveform_frame = ui.frameWaveformAnalysis
        self.assertEqual(QtWidgets.QSizePolicy.Policy.Fixed, histogram_frame.sizePolicy().horizontalPolicy())
        self.assertEqual(QtWidgets.QSizePolicy.Policy.Fixed, histogram_frame.sizePolicy().verticalPolicy())
        self.assertEqual(QtWidgets.QSizePolicy.Policy.Fixed, waveform_frame.sizePolicy().horizontalPolicy())
        self.assertEqual(QtWidgets.QSizePolicy.Policy.Fixed, waveform_frame.sizePolicy().verticalPolicy())

        max_histogram_height = ui.info_panel_histogram_size.height() + 24
        max_waveform_height = ui.info_panel_waveform_size.height() + 24
        self.assertLessEqual(histogram_frame.height(), max_histogram_height)
        self.assertLessEqual(waveform_frame.height(), max_waveform_height)

        analysis_layout = ui.tabAnalysis.layout()
        self.assertIs(ui.widgetWorkingColorSpace, analysis_layout.itemAt(0).widget())
        self.assertIs(histogram_frame, analysis_layout.itemAt(1).widget())
        self.assertIs(waveform_frame, analysis_layout.itemAt(2).widget())
        expected_alignment = QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop
        self.assertEqual(expected_alignment, analysis_layout.itemAt(1).alignment())
        self.assertEqual(expected_alignment, analysis_layout.itemAt(2).alignment())

    def test_filmstrip_allows_full_file_name_display(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual(QtCore.QSize(72, 72), ui.listFilmstrip.iconSize())
        self.assertEqual(4, ui.listFilmstrip.spacing())
        self.assertFalse(ui.listFilmstrip.uniformItemSizes())
        self.assertFalse(ui.listFilmstrip.wordWrap())
        self.assertEqual(QtCore.Qt.TextElideMode.ElideNone, ui.listFilmstrip.textElideMode())

    def test_filmstrip_has_fixed_height_without_vertical_splitter(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertFalse(hasattr(ui, "splitVertical"))
        self.assertIs(ui.widgetAnalysisToolbar, ui.layoutMain.itemAt(0).widget())
        self.assertIs(ui.splitMain, ui.layoutMain.itemAt(1).widget())
        self.assertIs(ui.frameFilmstrip, ui.layoutMain.itemAt(2).widget())
        self.assertEqual(ui.FILMSTRIP_HEIGHT, ui.frameFilmstrip.minimumHeight())
        self.assertEqual(ui.FILMSTRIP_HEIGHT, ui.frameFilmstrip.maximumHeight())
        self.assertEqual(QtWidgets.QSizePolicy.Policy.Fixed, ui.frameFilmstrip.sizePolicy().verticalPolicy())

    def test_status_bar_has_hidden_filmstrip_summary_label(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        status_labels = window.statusBar().findChildren(QtWidgets.QLabel, "labelFilmstripSummary")

        self.assertIn(ui.labelFilmstripSummary, status_labels)
        self.assertEqual("labelFilmstripSummary", ui.labelFilmstripSummary.objectName())
        self.assertTrue(ui.labelFilmstripSummary.isHidden())
        self.assertEqual("", ui.labelFilmstripSummary.text())

    def test_hidden_filmstrip_shows_current_file_summary(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        self._add_summary_image(ui, controller, Path("/tmp/first.jpg"))
        self._add_summary_image(ui, controller, Path("/tmp/second.jpg"))
        ui.tabsImages.setCurrentIndex(1)
        ui.listFilmstrip.setCurrentRow(1)

        MainController._toggle_filmstrip(controller, False)

        self.assertFalse(ui.labelFilmstripSummary.isHidden())
        self.assertEqual("Current: second.jpg (2/2)", ui.labelFilmstripSummary.text())
        self.assertEqual(
            f"Filmstrip hidden. Current file: {Path('/tmp/second.jpg')}",
            ui.labelFilmstripSummary.toolTip(),
        )

    def test_hidden_filmstrip_summary_uses_full_long_file_name(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/very-long-camera-filename-00123.raw")
        self._add_summary_image(ui, controller, path)

        MainController._toggle_filmstrip(controller, False)

        self.assertEqual(
            f"Current: {path.name} (1/1)",
            ui.labelFilmstripSummary.text(),
        )

    def test_hidden_filmstrip_summary_updates_when_tab_changes(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        self._add_summary_image(ui, controller, Path("/tmp/first.jpg"))
        self._add_summary_image(ui, controller, Path("/tmp/second.jpg"))
        MainController._toggle_filmstrip(controller, False)

        ui.tabsImages.setCurrentIndex(1)
        MainController._on_tab_changed(controller, 1)

        self.assertEqual("Current: second.jpg (2/2)", ui.labelFilmstripSummary.text())

    def test_controller_finds_detached_image_tab_by_path(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/current.jpg")
        self._add_summary_image(ui, controller, path)

        floating = ui.tabsImages.detach_tab(0)
        self.addCleanup(floating.deleteLater)
        MainController._on_image_tab_detached(controller, floating)

        self.assertIs(floating.content_widget(), controller._tab_widget_for_path(path))
        self.assertEqual(path, controller._current_image_path())

    def test_filmstrip_click_activates_detached_image_window(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/current.jpg")
        self._add_summary_image(ui, controller, path)
        floating = ui.tabsImages.detach_tab(0)
        self.addCleanup(floating.deleteLater)
        MainController._on_image_tab_detached(controller, floating)
        controller._activate_detached_image_window = MagicMock()  # type: ignore[method-assign]

        MainController._on_filmstrip_row_changed(controller, 0)

        controller._activate_detached_image_window.assert_called_once_with(path)

    def test_filmstrip_click_refreshes_current_docked_neighbor_after_detached_middle_image(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        paths = [Path("/tmp/first.jpg"), Path("/tmp/second.jpg"), Path("/tmp/third.jpg")]
        for path in paths:
            self._add_summary_image(ui, controller, path)
        ui.tabsImages.setCurrentIndex(1)
        floating = ui.tabsImages.detach_tab(1, show=False)
        self.addCleanup(floating.deleteLater)
        MainController._on_image_tab_detached(controller, floating)
        controller.update_info_for_image.reset_mock()
        controller._ensure_full_load.reset_mock()

        ui.listFilmstrip.setCurrentRow(2)
        MainController._on_filmstrip_row_changed(controller, 2)

        self.assertEqual(paths[2], controller._current_docked_image_path())
        self.assertEqual(paths[2], controller._active_image_path)
        controller.update_info_for_image.assert_called_once_with(paths[2])
        controller._ensure_full_load.assert_called_once_with(paths[2])

    def test_filmstrip_click_refreshes_current_docked_neighbor_after_detached_last_image(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        paths = [Path("/tmp/first.jpg"), Path("/tmp/second.jpg"), Path("/tmp/third.jpg")]
        for path in paths:
            self._add_summary_image(ui, controller, path)
        ui.tabsImages.setCurrentIndex(2)
        floating = ui.tabsImages.detach_tab(2, show=False)
        self.addCleanup(floating.deleteLater)
        MainController._on_image_tab_detached(controller, floating)
        controller.update_info_for_image.reset_mock()
        controller._ensure_full_load.reset_mock()

        ui.listFilmstrip.setCurrentRow(1)
        MainController._on_filmstrip_row_changed(controller, 1)

        self.assertEqual(paths[1], controller._current_docked_image_path())
        self.assertEqual(paths[1], controller._active_image_path)
        controller.update_info_for_image.assert_called_once_with(paths[1])
        controller._ensure_full_load.assert_called_once_with(paths[1])

    def test_reattaching_info_tab_restores_visible_info_panel(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        ui.actToggleInfoPanel.setChecked(False)
        ui.scrollInfo.setVisible(False)
        floating = ui.tabsInfo.detach_tab(0)
        self.addCleanup(floating.deleteLater)

        floating.return_to_tabs()
        MainController._on_info_tab_reattached(controller, floating)

        self.assertTrue(ui.actToggleInfoPanel.isChecked())
        self.assertFalse(ui.scrollInfo.isHidden())

    def test_showing_filmstrip_hides_current_file_summary(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        self._add_summary_image(ui, controller, Path("/tmp/current.jpg"))
        MainController._toggle_filmstrip(controller, False)

        MainController._toggle_filmstrip(controller, True)

        self.assertTrue(ui.labelFilmstripSummary.isHidden())
        self.assertEqual("", ui.labelFilmstripSummary.text())
        self.assertEqual("", ui.labelFilmstripSummary.toolTip())

    def test_closing_last_image_hides_filmstrip_summary(self) -> None:
        window, ui, controller = self._build_filmstrip_summary_controller()
        self.addCleanup(window.deleteLater)
        self._add_summary_image(ui, controller, Path("/tmp/current.jpg"))
        MainController._toggle_filmstrip(controller, False)
        controller._images_by_path = {}  # type: ignore[attr-defined]
        controller._preview_by_path = {}  # type: ignore[attr-defined]
        controller._load_error_by_path = {}  # type: ignore[attr-defined]
        controller._zoom_by_path = {}  # type: ignore[attr-defined]
        controller._fit_to_window_by_path = {}  # type: ignore[attr-defined]
        controller._analysis_render_key_by_path = {}  # type: ignore[attr-defined]
        controller._tab_preview_render_key_by_path = {}  # type: ignore[attr-defined]
        controller._cancel_tasks_for_path = MagicMock()  # type: ignore[method-assign]
        controller._ensure_empty_image_placeholder = MagicMock()  # type: ignore[method-assign]

        MainController.close_tab(controller, 0)

        self.assertTrue(ui.labelFilmstripSummary.isHidden())
        self.assertEqual("", ui.labelFilmstripSummary.text())

    def test_image_tab_title_uses_full_long_file_name(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/very-long-camera-filename-00123.raw")
        tab = QtWidgets.QWidget()

        ui.tabsImages.addTab(tab, "")
        controller._update_tab_title(0, path)

        self.assertEqual(path.name, ui.tabsImages.tabText(0))
        self.assertEqual(path.name, ui.tabsImages.tabToolTip(0))

    def test_filmstrip_item_uses_full_name_tooltip_and_dynamic_size(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        path = Path("/tmp/very-long-camera-filename-00123.raw")

        controller._add_filmstrip_placeholder_item(path)

        item = ui.listFilmstrip.item(0)
        self.assertIsNotNone(item)
        self.assertEqual(path.name, item.text())
        self.assertEqual(path.name, item.toolTip())
        self.assertEqual(QtCore.Qt.AlignmentFlag.AlignCenter, item.textAlignment())
        self.assertGreaterEqual(
            item.sizeHint().width(),
            ui.listFilmstrip.fontMetrics().horizontalAdvance(path.name),
        )
        self.assertEqual(ui.filmstrip_item_size().height(), item.sizeHint().height())

    def test_filmstrip_thumbnail_size_is_capped_for_default_height(self) -> None:
        controller = _FilmstripSizingController()
        controller._ui = _FakeFilmstripUi(viewport_height=104, font_height=14)  # type: ignore[attr-defined]
        controller._filmstrip_icon_side = 96  # type: ignore[attr-defined]

        self.assertLessEqual(controller._calculate_filmstrip_icon_side(), 72)

    def test_analysis_mode_summary_is_visible_above_info_tabs(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("widgetAnalysisModeSummary", ui.widgetAnalysisModeSummary.objectName())
        self.assertEqual("labelAnalysisModeTitle", ui.labelAnalysisModeTitle.objectName())
        self.assertEqual("labelAnalysisModeValue", ui.labelAnalysisModeValue.objectName())
        self.assertEqual("labelAnalysisChannelTitle", ui.labelAnalysisChannelTitle.objectName())
        self.assertEqual("labelAnalysisChannelValue", ui.labelAnalysisChannelValue.objectName())
        self.assertEqual("labelPseudoColorTitle", ui.labelPseudoColorTitle.objectName())
        self.assertEqual("labelPseudoColorValue", ui.labelPseudoColorValue.objectName())

        self.assertIs(ui.widgetAnalysisModeSummary, ui.layoutInfo.itemAt(0).widget())
        self.assertIs(ui.tabsInfo, ui.layoutInfo.itemAt(1).widget())
        self.assertEqual(2, ui.tabsInfo.count())
        self.assertEqual("Analysis", ui.tabsInfo.tabText(0))
        self.assertEqual("Metadata", ui.tabsInfo.tabText(1))
        self.assertEqual("Analysis Mode", ui.labelAnalysisModeTitle.text())
        self.assertEqual("Luma Mode", ui.labelAnalysisModeValue.text())
        self.assertEqual("RGB Channels", ui.labelAnalysisChannelTitle.text())
        self.assertEqual("Not Applicable", ui.labelAnalysisChannelValue.text())
        self.assertEqual("Pseudo Color State", ui.labelPseudoColorTitle.text())
        self.assertEqual(
            "Underexposed: Off / Overexposed: Off / Peaks: Off",
            ui.labelPseudoColorValue.text(),
        )

    def test_analysis_tab_has_working_color_space_selector(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        self.assertEqual("labelWorkingColorSpaceTitle", ui.labelWorkingColorSpaceTitle.objectName())
        self.assertEqual("comboWorkingColorSpace", ui.comboWorkingColorSpace.objectName())
        self.assertEqual("Working Color Space", ui.labelWorkingColorSpaceTitle.text())
        self.assertEqual(
            ["sRGB", "Display P3", "Adobe RGB (1998)", "ProPhoto RGB"],
            [ui.comboWorkingColorSpace.itemText(index) for index in range(ui.comboWorkingColorSpace.count())],
        )
        self.assertEqual("sRGB", ui.comboWorkingColorSpace.currentText())

    def test_metadata_tables_keep_fixed_key_column_and_stretched_value_column(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        tables = (
            ui.tableMetadataGeneral,
            ui.tableMetadataExif,
            ui.tableMetadataIptc,
            ui.tableMetadataTiff,
        )
        for table in tables:
            header = table.horizontalHeader()
            self.assertEqual(QtWidgets.QHeaderView.ResizeMode.Fixed, header.sectionResizeMode(0))
            self.assertEqual(QtWidgets.QHeaderView.ResizeMode.Stretch, header.sectionResizeMode(1))
            self.assertEqual(ui.METADATA_KEY_COLUMN_WIDTH, table.columnWidth(0))
            self.assertFalse(table.wordWrap())
            self.assertEqual(QtCore.Qt.TextElideMode.ElideRight, table.textElideMode())

    def test_empty_image_placeholder_hides_tab_bar(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)

        controller._ensure_empty_image_placeholder()

        placeholder = ui.tabsImages.findChild(QtWidgets.QWidget, "tabImagePlaceholder")
        self.assertIsNotNone(placeholder)
        self.assertTrue(ui.tabsImages.tabBar().isHidden())

    def test_empty_image_placeholder_has_action_buttons(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)

        controller._ensure_empty_image_placeholder()

        open_file = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonEmptyOpenFile")
        open_folder = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonEmptyOpenFolder")
        self.assertIsNotNone(open_file)
        self.assertIsNotNone(open_folder)
        self.assertEqual(ui.actOpenFile.text(), open_file.text())
        self.assertEqual(ui.actOpenFolder.text(), open_folder.text())

    def test_empty_image_placeholder_buttons_trigger_actions(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        open_file_triggered = MagicMock()
        open_folder_triggered = MagicMock()
        ui.actOpenFile.triggered.connect(open_file_triggered)
        ui.actOpenFolder.triggered.connect(open_folder_triggered)
        self.addCleanup(window.deleteLater)

        controller._ensure_empty_image_placeholder()
        open_file = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonEmptyOpenFile")
        open_folder = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonEmptyOpenFolder")
        self.assertIsNotNone(open_file)
        self.assertIsNotNone(open_folder)

        open_file.click()
        open_folder.click()

        open_file_triggered.assert_called_once()
        open_folder_triggered.assert_called_once()

    def test_empty_image_placeholder_shows_shortcuts_and_formats(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)

        controller._ensure_empty_image_placeholder()

        labels = ui.tabsImages.findChildren(QtWidgets.QLabel)
        label_texts = [label.text() for label in labels]
        format_label = ui.tabsImages.findChild(QtWidgets.QLabel, "labelEmptyFormats")
        self.assertIsNotNone(format_label)
        self.assertIn("JPG", format_label.text())
        self.assertIn("PNG", format_label.text())
        self.assertIn("TIFF", format_label.text())
        self.assertIn("DNG", format_label.text())
        open_file_shortcut = controller._shortcut_text(ui.actOpenFile)
        open_folder_shortcut = controller._shortcut_text(ui.actOpenFolder)
        self.assertTrue(any(open_file_shortcut in text for text in label_texts))
        self.assertTrue(any(open_folder_shortcut in text for text in label_texts))

    def test_empty_image_placeholder_shows_drop_hint(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)

        controller._ensure_empty_image_placeholder()

        drop_hint = ui.tabsImages.findChild(QtWidgets.QLabel, "labelEmptyDropHint")
        self.assertIsNotNone(drop_hint)
        self.assertEqual("Drop files here to open them", drop_hint.text())

    def test_empty_image_placeholder_keeps_shortcuts_below_buttons(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)

        controller._ensure_empty_image_placeholder()
        window.resize(1200, 800)
        window.show()
        self._app.processEvents()

        open_file = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonEmptyOpenFile")
        open_folder = ui.tabsImages.findChild(QtWidgets.QPushButton, "buttonEmptyOpenFolder")
        open_file_shortcut = ui.tabsImages.findChild(QtWidgets.QLabel, "labelEmptyOpenFileShortcut")
        open_folder_shortcut = ui.tabsImages.findChild(QtWidgets.QLabel, "labelEmptyOpenFolderShortcut")

        self.assertIsNotNone(open_file)
        self.assertIsNotNone(open_folder)
        self.assertIsNotNone(open_file_shortcut)
        self.assertIsNotNone(open_folder_shortcut)
        self.assertIs(open_file.parentWidget(), open_file_shortcut.parentWidget())
        self.assertIs(open_folder.parentWidget(), open_folder_shortcut.parentWidget())
        self.assertLess(open_file.geometry().bottom(), open_file_shortcut.geometry().top())
        self.assertLess(open_folder.geometry().bottom(), open_folder_shortcut.geometry().top())

    def test_image_preview_canvas_exposes_styled_scroll_area(self) -> None:
        window, ui, controller = self._build_image_preview_controller()
        self.addCleanup(window.deleteLater)

        image_page = controller._build_image_preview_page(window)

        scroll_area = image_page.findChild(QtWidgets.QScrollArea, "scrollImage")
        lbl_image = image_page.findChild(QtWidgets.QLabel, "lblImage")
        self.assertIsNotNone(scroll_area)
        self.assertIsNotNone(lbl_image)
        self.assertEqual(QtWidgets.QFrame.Shape.NoFrame, scroll_area.frameShape())
        self.assertEqual("viewportImageCanvas", scroll_area.viewport().objectName())
        self.assertEqual(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded, scroll_area.horizontalScrollBarPolicy())
        self.assertEqual(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded, scroll_area.verticalScrollBarPolicy())
        self.assertTrue(scroll_area.property("_image_drag_area"))
        self.assertTrue(scroll_area.viewport().property("_image_drag_area"))
        self.assertTrue(lbl_image.property("_image_drag_area"))
        self.assertTrue(scroll_area.property("_image_zoom_area"))
        self.assertTrue(scroll_area.viewport().property("_image_zoom_area"))
        self.assertTrue(lbl_image.property("_image_zoom_area"))

    def test_wheel_up_on_image_zoom_area_zooms_in(self) -> None:
        window, _ui, controller = self._build_image_preview_controller()
        self.addCleanup(window.deleteLater)
        widget = QtWidgets.QWidget(window)
        self.addCleanup(widget.deleteLater)
        widget.setProperty("_image_zoom_area", True)
        controller._zoom_in = MagicMock()  # type: ignore[method-assign]
        controller._zoom_out = MagicMock()  # type: ignore[method-assign]
        event = self._wheel_event(120)

        handled = controller._handle_image_wheel_zoom_event(widget, event)

        self.assertTrue(handled)
        self.assertTrue(event.accepted)
        controller._zoom_in.assert_called_once_with()
        controller._zoom_out.assert_not_called()

    def test_wheel_down_on_image_zoom_area_zooms_out(self) -> None:
        window, _ui, controller = self._build_image_preview_controller()
        self.addCleanup(window.deleteLater)
        widget = QtWidgets.QWidget(window)
        self.addCleanup(widget.deleteLater)
        widget.setProperty("_image_zoom_area", True)
        controller._zoom_in = MagicMock()  # type: ignore[method-assign]
        controller._zoom_out = MagicMock()  # type: ignore[method-assign]
        event = self._wheel_event(-120)

        handled = controller._handle_image_wheel_zoom_event(widget, event)

        self.assertTrue(handled)
        self.assertTrue(event.accepted)
        controller._zoom_in.assert_not_called()
        controller._zoom_out.assert_called_once_with()

    def test_wheel_on_non_image_zoom_area_is_not_consumed(self) -> None:
        window, _ui, controller = self._build_image_preview_controller()
        self.addCleanup(window.deleteLater)
        widget = QtWidgets.QWidget(window)
        self.addCleanup(widget.deleteLater)
        controller._zoom_in = MagicMock()  # type: ignore[method-assign]
        controller._zoom_out = MagicMock()  # type: ignore[method-assign]
        event = self._wheel_event(120)

        handled = controller._handle_image_wheel_zoom_event(widget, event)

        self.assertFalse(handled)
        self.assertFalse(event.accepted)
        controller._zoom_in.assert_not_called()
        controller._zoom_out.assert_not_called()

    def test_drop_mime_data_filters_local_supported_image_files(self) -> None:
        window, _ui, controller = self._build_drop_controller()
        self.addCleanup(window.deleteLater)

        with self._temporary_drop_files() as paths:
            mime_data = QtCore.QMimeData()
            mime_data.setUrls(
                [
                    QtCore.QUrl.fromLocalFile(str(paths["image"])),
                    QtCore.QUrl.fromLocalFile(str(paths["text"])),
                    QtCore.QUrl.fromLocalFile(str(paths["directory"])),
                    QtCore.QUrl("https://example.com/remote.jpg"),
                ]
            )

            supported = controller._supported_drop_paths(mime_data)

        self.assertEqual([paths["image"]], supported)

    def test_open_image_paths_batches_multiple_files_and_activates_last(self) -> None:
        window, ui, controller = self._build_tabs_controller()
        self.addCleanup(window.deleteLater)
        first = Path("/tmp/first.jpg")
        second = Path("/tmp/second.png")
        controller.open_image = MagicMock()  # type: ignore[method-assign]
        controller._activate_existing_path = MagicMock()  # type: ignore[method-assign]

        controller._open_image_paths([first, second])

        controller.open_image.assert_has_calls(
            [
                call(first, activate=False),
                call(second, activate=False),
            ]
        )
        controller._activate_existing_path.assert_called_once_with(second)
        self.assertEqual(0, ui.tabsImages.signalsBlocked())
        self.assertEqual(0, ui.listFilmstrip.signalsBlocked())

    def test_open_dropped_images_warns_when_no_supported_files_exist(self) -> None:
        window, _ui, controller = self._build_drop_controller()
        self.addCleanup(window.deleteLater)

        with self._temporary_drop_files() as paths:
            mime_data = QtCore.QMimeData()
            mime_data.setUrls(
                [
                    QtCore.QUrl.fromLocalFile(str(paths["text"])),
                    QtCore.QUrl.fromLocalFile(str(paths["directory"])),
                    QtCore.QUrl("https://example.com/remote.jpg"),
                ]
            )

            controller._open_dropped_images_from_mime_data(mime_data)

        controller._open_image_paths.assert_not_called()
        controller._show_no_supported_drop_files_message.assert_called_once()

    def _build_tabs_controller(
        self,
    ) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainControllerTabsMixin]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainControllerTabsMixin()
        controller._ui = ui  # type: ignore[attr-defined]
        controller._main_window = window  # type: ignore[attr-defined]
        controller._tr = lambda text: text  # type: ignore[attr-defined]
        return window, ui, controller

    def _stub_open_image_dependencies(self, controller: MainControllerTabsMixin) -> None:
        controller._images_by_path = {}  # type: ignore[attr-defined]
        controller._load_error_by_path = {}  # type: ignore[attr-defined]
        controller._remove_empty_image_placeholder = lambda: None  # type: ignore[method-assign]
        controller._build_image_tab_container = lambda path: QtWidgets.QWidget()  # type: ignore[method-assign]
        controller._set_zoom_state = lambda *args: None  # type: ignore[method-assign]
        controller._show_tab_loading_state = lambda *args: None  # type: ignore[method-assign]
        controller._add_filmstrip_placeholder_item = lambda path: None  # type: ignore[method-assign]
        controller._start_path_session = lambda path: 1  # type: ignore[method-assign]
        controller._ensure_preview_load = lambda *args: None  # type: ignore[method-assign]
        controller._ensure_full_load = lambda *args: None  # type: ignore[method-assign]
        controller._refresh_actions_state = lambda: None  # type: ignore[method-assign]

    def _build_image_preview_controller(
        self,
    ) -> tuple[QtWidgets.QMainWindow, MainWindowUI, "_ImagePreviewController"]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = _ImagePreviewController(window)
        controller._ui = ui  # type: ignore[attr-defined]
        controller._tr = lambda text: text  # type: ignore[attr-defined]
        controller._image_context_menu = ui.menuImageContext  # type: ignore[attr-defined]
        controller._cursor_override_target = None  # type: ignore[attr-defined]
        return window, ui, controller

    def _build_drop_controller(
        self,
    ) -> tuple[QtWidgets.QMainWindow, MainWindowUI, "_DropController"]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = _DropController(window)
        controller._ui = ui  # type: ignore[attr-defined]
        controller._tr = lambda text: text  # type: ignore[attr-defined]
        controller._open_image_paths = MagicMock()  # type: ignore[method-assign]
        controller._show_no_supported_drop_files_message = MagicMock()  # type: ignore[method-assign]
        return window, ui, controller

    def _build_filmstrip_summary_controller(
        self,
    ) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui
        controller._main_window = window
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._syncing_selection = False
        controller._active_image_path = None
        controller._detached_image_windows = {}
        controller._detached_info_windows = {}
        controller._schedule_filmstrip_resize = MagicMock()  # type: ignore[method-assign]
        controller.update_info_for_image = MagicMock()  # type: ignore[method-assign]
        controller._refresh_actions_state = MagicMock()  # type: ignore[method-assign]
        controller._ensure_full_load = MagicMock()  # type: ignore[method-assign]
        return window, ui, controller

    def _add_summary_image(
        self,
        ui: MainWindowUI,
        controller: MainController,
        path: Path,
    ) -> None:
        tab = QtWidgets.QWidget()
        tab.setProperty("image_path", str(path))
        ui.tabsImages.addTab(tab, path.name)
        controller._add_filmstrip_placeholder_item(path)

    class _TemporaryDropFiles:
        def __init__(self) -> None:
            self._tmp_dir: object | None = None
            self.paths: dict[str, Path] = {}

        def __enter__(self) -> dict[str, Path]:
            self._tmp_dir = tempfile.TemporaryDirectory()
            root = Path(self._tmp_dir.__enter__())  # type: ignore[union-attr]
            image = root / "image.JPG"
            text = root / "notes.txt"
            directory = root / "folder.png"
            image.write_bytes(b"image")
            text.write_text("not an image", encoding="utf-8")
            directory.mkdir()
            self.paths = {"image": image, "text": text, "directory": directory}
            return self.paths

        def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            if self._tmp_dir is not None:
                self._tmp_dir.__exit__(exc_type, exc, tb)  # type: ignore[attr-defined]

    def _temporary_drop_files(self) -> "_TemporaryDropFiles":
        return self._TemporaryDropFiles()

    def _wheel_event(self, angle_delta_y: int) -> "_FakeWheelEvent":
        return _FakeWheelEvent(angle_delta_y)


class _ImagePreviewController(
    MainControllerTabsMixin,
    MainControllerInteractionMixin,
    QtCore.QObject,
):
    """Minimal controller for image preview widget construction tests."""

    def __init__(self, parent: QtCore.QObject) -> None:
        QtCore.QObject.__init__(self, parent)


class _DropController(
    MainControllerInteractionMixin,
    QtCore.QObject,
):
    """Minimal controller for file-drop helper tests."""

    def __init__(self, parent: QtCore.QObject) -> None:
        QtCore.QObject.__init__(self, parent)


class _FakeWheelEvent:
    def __init__(self, angle_delta_y: int) -> None:
        self.accepted = False
        self._angle_delta = QtCore.QPoint(0, angle_delta_y)

    def type(self) -> QtCore.QEvent.Type:
        return QtCore.QEvent.Type.Wheel

    def angleDelta(self) -> QtCore.QPoint:
        return self._angle_delta

    def pixelDelta(self) -> QtCore.QPoint:
        return QtCore.QPoint(0, 0)

    def accept(self) -> None:
        self.accepted = True


class _FilmstripSizingController(MainControllerFilmstripMixin):
    """Minimal controller for filmstrip sizing tests."""


class _FakeViewport:
    def __init__(self, height: int) -> None:
        self._height = height

    def height(self) -> int:
        return self._height


class _FakeFontMetrics:
    def __init__(self, height: int) -> None:
        self._height = height

    def height(self) -> int:
        return self._height


class _FakeFilmstripList:
    def __init__(self, viewport_height: int, font_height: int) -> None:
        self._viewport = _FakeViewport(viewport_height)
        self._font_metrics = _FakeFontMetrics(font_height)

    def viewport(self) -> _FakeViewport:
        return self._viewport

    def fontMetrics(self) -> _FakeFontMetrics:
        return self._font_metrics


class _FakeFilmstripUi:
    FILMSTRIP_ICON_SIDE = 72
    FILMSTRIP_MIN_ICON_SIDE = 48
    FILMSTRIP_ITEM_VERTICAL_PADDING = 18

    def __init__(self, viewport_height: int, font_height: int) -> None:
        self.listFilmstrip = _FakeFilmstripList(viewport_height, font_height)


if __name__ == "__main__":
    unittest.main()
