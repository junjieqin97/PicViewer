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

from pic_viewer.controllers.main_controller_tabs_mixin import MainControllerTabsMixin  # noqa: E402
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

    def test_image_tabs_have_left_aligned_tab_bar_style(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        style_sheet = ui.tabsImages.styleSheet()
        self.assertIn("QTabWidget#tabsImages::tab-bar", style_sheet)
        self.assertIn("alignment: left", style_sheet)
        self.assertEqual("", ui.tabsInfo.styleSheet())

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


if __name__ == "__main__":
    unittest.main()
