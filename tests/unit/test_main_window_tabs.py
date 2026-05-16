from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import MagicMock, call

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller_tabs_mixin import MainControllerTabsMixin  # noqa: E402
from pic_viewer.controllers.main_controller_interaction_mixin import (  # noqa: E402
    MainControllerInteractionMixin,
)
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


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

        button = ui.tabsImages.tabBar().tabButton(0, QtWidgets.QTabBar.RightSide)
        self.assertIsNotNone(button)
        self.assertNotEqual("buttonImageTabClose", button.objectName())

    def test_analysis_widgets_are_wrapped_in_fixed_top_aligned_frames(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        window.resize(1200, 800)
        window.show()
        self._app.processEvents()

        self.assertEqual("frameHistogramAnalysis", ui.widgetHistogram.parentWidget().objectName())
        self.assertEqual("frameWaveformAnalysis", ui.widgetWaveform.parentWidget().objectName())
        self.assertEqual(ui.info_panel_histogram_size, ui.widgetHistogram.size())
        self.assertEqual(ui.info_panel_waveform_size, ui.widgetWaveform.size())

        histogram_frame = ui.frameHistogramAnalysis
        waveform_frame = ui.frameWaveformAnalysis
        self.assertEqual(QtWidgets.QSizePolicy.Fixed, histogram_frame.sizePolicy().horizontalPolicy())
        self.assertEqual(QtWidgets.QSizePolicy.Fixed, histogram_frame.sizePolicy().verticalPolicy())
        self.assertEqual(QtWidgets.QSizePolicy.Fixed, waveform_frame.sizePolicy().horizontalPolicy())
        self.assertEqual(QtWidgets.QSizePolicy.Fixed, waveform_frame.sizePolicy().verticalPolicy())

        max_histogram_height = ui.info_panel_histogram_size.height() + 24
        max_waveform_height = ui.info_panel_waveform_size.height() + 24
        self.assertLessEqual(histogram_frame.height(), max_histogram_height)
        self.assertLessEqual(waveform_frame.height(), max_waveform_height)

        histogram_layout_item = ui.tabHistogram.layout().itemAt(0)
        waveform_layout_item = ui.tabWaveform.layout().itemAt(0)
        expected_alignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop
        self.assertEqual(expected_alignment, histogram_layout_item.alignment())
        self.assertEqual(expected_alignment, waveform_layout_item.alignment())

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
        self.assertEqual("Analysis Mode", ui.labelAnalysisModeTitle.text())
        self.assertEqual("Luma Mode", ui.labelAnalysisModeValue.text())
        self.assertEqual("RGB Channels", ui.labelAnalysisChannelTitle.text())
        self.assertEqual("Not Applicable", ui.labelAnalysisChannelValue.text())
        self.assertEqual("Pseudo Color State", ui.labelPseudoColorTitle.text())
        self.assertEqual("Underexposed: Off / Overexposed: Off", ui.labelPseudoColorValue.text())

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
            self.assertEqual(QtWidgets.QHeaderView.Fixed, header.sectionResizeMode(0))
            self.assertEqual(QtWidgets.QHeaderView.Stretch, header.sectionResizeMode(1))
            self.assertEqual(ui.METADATA_KEY_COLUMN_WIDTH, table.columnWidth(0))
            self.assertFalse(table.wordWrap())
            self.assertEqual(QtCore.Qt.ElideRight, table.textElideMode())

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
        self.assertEqual(QtWidgets.QFrame.NoFrame, scroll_area.frameShape())
        self.assertEqual("viewportImageCanvas", scroll_area.viewport().objectName())
        self.assertEqual(QtCore.Qt.ScrollBarAsNeeded, scroll_area.horizontalScrollBarPolicy())
        self.assertEqual(QtCore.Qt.ScrollBarAsNeeded, scroll_area.verticalScrollBarPolicy())
        self.assertTrue(scroll_area.property("_image_drag_area"))
        self.assertTrue(scroll_area.viewport().property("_image_drag_area"))
        self.assertTrue(lbl_image.property("_image_drag_area"))

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
        controller = _ImagePreviewController()
        QtCore.QObject.__init__(controller, window)
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
        controller = _DropController()
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui  # type: ignore[attr-defined]
        controller._tr = lambda text: text  # type: ignore[attr-defined]
        controller._open_image_paths = MagicMock()  # type: ignore[method-assign]
        controller._show_no_supported_drop_files_message = MagicMock()  # type: ignore[method-assign]
        return window, ui, controller

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


class _ImagePreviewController(
    MainControllerTabsMixin,
    MainControllerInteractionMixin,
    QtCore.QObject,
):
    """Minimal controller for image preview widget construction tests."""


class _DropController(
    MainControllerInteractionMixin,
    QtCore.QObject,
):
    """Minimal controller for file-drop helper tests."""


if __name__ == "__main__":
    unittest.main()
