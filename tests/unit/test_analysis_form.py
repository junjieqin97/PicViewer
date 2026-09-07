"""Regression coverage for narrow Analysis fields and complete source values."""

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtWidgets

from pic_viewer.ui.resources.styles import AppearanceTheme
from pic_viewer.ui.windows.main_window import MainWindowUI


class AnalysisFormTests(QtWidgetTestCase):
    def test_fields_fill_minimum_panel_and_keep_long_values(self) -> None:
        for theme in AppearanceTheme:
            for size in ((900, 600), (1200, 800)):
                with self.subTest(theme=theme, size=size):
                    window = QtWidgets.QMainWindow()
                    self.addCleanup(window.deleteLater)
                    ui = MainWindowUI()
                    ui.setup_ui(window)
                    ui.apply_appearance_theme(theme)
                    window.resize(*size)
                    window.show()
                    ui.splitMain.setSizes([size[0], ui.info_panel_min_width])
                    status = "VeryLongProfileNameWithoutSpaces" * 8
                    ui.labelImageColorSpaceValue.setText(status)
                    fields = (
                        (ui.labelAnalysisSamplePrecisionTitle, ui.comboAnalysisSamplePrecision),
                        (ui.labelSpecifiedImageColorSpaceTitle, ui.comboSpecifiedImageColorSpace),
                        (ui.labelRenderingIntentTitle, ui.comboRenderingIntent),
                        (ui.labelDisplayColorSpaceTitle, ui.comboDisplayColorSpace),
                    )
                    for title, combo in fields:
                        combo.addItem(status, "profile-data")
                        combo.setCurrentIndex(combo.count() - 1)
                    self._app.processEvents()
                    self.assertLessEqual(
                        ui.analysisScrollContent.width(), ui.scrollAnalysis.viewport().width()
                    )
                    for title, combo in fields:
                        self.assertEqual(title.x(), combo.x())
                        self.assertGreater(combo.y(), title.geometry().bottom())
                        self.assertEqual(combo.width(), combo.parentWidget().width())
                        self.assertEqual(status, combo.currentText())
                        self.assertEqual(status, combo.toolTip())
                        self.assertEqual("profile-data", combo.currentData())
                    self.assertEqual(status, ui.labelImageColorSpaceValue.text())
                    self.assertEqual(status, ui.labelImageColorSpaceValue.toolTip())
                    ui.scrollAnalysis.ensureWidgetVisible(ui.frameWaveformAnalysis)
                    self._app.processEvents()
                    top = ui.frameWaveformAnalysis.mapTo(
                        ui.scrollAnalysis.viewport(), QtCore.QPoint()
                    ).y()
                    self.assertGreaterEqual(top, 0)
                    self.assertLessEqual(
                        top + ui.frameWaveformAnalysis.height(),
                        ui.scrollAnalysis.viewport().height(),
                    )
                    window.close()

    def test_selected_tooltip_tracks_blank_disabled_and_changed_text(self) -> None:
        window = QtWidgets.QMainWindow()
        self.addCleanup(window.deleteLater)
        ui = MainWindowUI()
        ui.setup_ui(window)
        combo = ui.comboSpecifiedImageColorSpace
        combo.setCurrentIndex(-1)
        combo.setEnabled(False)
        self.assertEqual("", combo.toolTip())
        combo.setCurrentIndex(combo.findText("ProPhoto RGB"))
        self.assertEqual("ProPhoto RGB", combo.toolTip())
        combo.setEnabled(True)
        combo.setItemText(combo.currentIndex(), "Updated profile name")
        self.assertEqual("Updated profile name", combo.toolTip())
