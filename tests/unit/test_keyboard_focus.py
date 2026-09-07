"""Keyboard navigation and rendered focus regressions for both themes."""
from __future__ import annotations

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from tests.unit.qt_test_utils import QtWidgetTestCase
from pic_viewer.ui.resources.styles import AppearanceTheme, apply_stylesheet
from pic_viewer.ui.windows.main_window import MainWindowUI


class KeyboardFocusTests(QtWidgetTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.window = QtWidgets.QMainWindow()
        self.ui = MainWindowUI()
        self.ui.setup_ui(self.window)
        self.window.resize(900, 600)
        self.addCleanup(self.window.deleteLater)
        self.window.show()
        self.window.activateWindow()
        self._app.processEvents()

    def test_toolbar_keyboard_activation_and_accessible_state(self) -> None:
        button = self.ui.buttonToolbarUnderexposed
        button.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
        self._app.processEvents()
        self.assertTrue(button.hasFocus())
        before = button.isChecked()
        QtTest.QTest.keyClick(button, QtCore.Qt.Key.Key_Space)
        self.assertEqual(not before, self.ui.actToggleUnderexposed.isChecked())
        accessible = QtGui.QAccessible.queryAccessibleInterface(button)
        self.assertEqual(self.ui.actToggleUnderexposed.text(), accessible.text(QtGui.QAccessible.Text.Name))
        self.assertEqual(button.isChecked(), accessible.state().checked)
        self.assertEqual(QtCore.Qt.FocusPolicy.NoFocus, self.ui.widgetHistogram.focusPolicy())
        self.assertIn('Tools > Pseudo Color', self.ui.widgetHistogram.accessibleDescription())

    def test_tab_navigation_skips_disabled_and_hidden_buttons(self) -> None:
        first = self.ui.buttonToolbarModeLuma
        skipped = self.ui.buttonToolbarModeRgb
        destination = self.ui.buttonToolbarChannelAll
        destination.setEnabled(True)
        for hidden in (False, True):
            skipped.setEnabled(hidden)
            skipped.setVisible(not hidden)
            first.setFocus()
            QtTest.QTest.keyClick(first, QtCore.Qt.Key.Key_Tab)
            self.assertIs(destination, self._app.focusWidget())
            QtTest.QTest.keyClick(destination, QtCore.Qt.Key.Key_Backtab)
            self.assertIs(first, self._app.focusWidget())

    def test_rendered_focus_is_visible_without_geometry_changes(self) -> None:
        table = self.ui.tableMetadataGeneral
        table.setRowCount(1)
        table.setItem(0, 0, QtWidgets.QTableWidgetItem('Camera'))
        table.setItem(0, 1, QtWidgets.QTableWidgetItem('Example'))
        table.setCurrentCell(0, 0)
        filmstrip = self.ui.listFilmstrip
        filmstrip.addItem('Example.jpg')
        filmstrip.setCurrentRow(0)
        for theme, color in ((AppearanceTheme.DARK, '#ffd166'), (AppearanceTheme.LIGHT, '#805000')):
            apply_stylesheet(self.window, theme)
            self.ui.tabsInfo.setCurrentWidget(self.ui.tabMetadata)
            widgets = [self.ui.buttonToolbarUnderexposed, self.ui.comboFilmstripExtensionFilter,
                       self.ui.tabsInfo.tabBar(), self.ui.tabsMetadata.tabBar(), table, filmstrip]
            for widget in widgets:
                with self.subTest(theme=theme, widget=widget.objectName()):
                    widget.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
                    self._app.processEvents()
                    self.assertTrue(widget.hasFocus())
                    size = widget.size()
                    focused = widget.grab().toImage()
                    count = self._color_count(focused, color)
                    self.assertGreater(count, 4)
                    if widget in (table, filmstrip):
                        item_image = widget.viewport().grab(
                            widget.visualRect(widget.currentIndex())
                        ).toImage()
                        self.assertGreater(self._color_count(item_image, color), 4)
                    self.ui.buttonToolbarModeLuma.setFocus()
                    self._app.processEvents()
                    self.assertEqual(size, widget.size())
                    self.assertLess(self._color_count(widget.grab().toImage(), color), count)
            self.assertEqual(30, self.ui.widgetAnalysisToolbar.height())

    def test_push_button_and_detached_analysis_focus(self) -> None:
        button = QtWidgets.QPushButton('Open Image...')
        button.setObjectName('buttonEmptyOpenFile')
        self.ui.tabsImages.addTab(button, 'Empty')
        self.ui.tabsImages.setCurrentWidget(button)
        for theme, color in ((AppearanceTheme.DARK, '#ffd166'), (AppearanceTheme.LIGHT, '#805000')):
            apply_stylesheet(self.window, theme)
            self.window.activateWindow()
            button.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
            self._app.processEvents()
            self.assertGreater(self._color_count(button.grab().toImage(), color), 4)
            floating = self.ui.tabsInfo.detach_tab(self.ui.tabsInfo.indexOf(self.ui.tabAnalysis))
            try:
                floating.activateWindow()
                combo = self.ui.comboDisplayColorSpace
                combo.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
                self._app.processEvents()
                self.assertTrue(combo.hasFocus())
                self.assertGreater(self._color_count(combo.grab().toImage(), color), 4)
            finally:
                self.ui.tabsInfo.reattach_floating_window(floating)

    @staticmethod
    def _color_count(image: QtGui.QImage, color: str) -> int:
        target_hue = QtGui.QColor(color).hue()
        # Dashed QSS borders blend with the background during rasterization.
        return sum(
            abs(image.pixelColor(x, y).hue() - target_hue) < 8
            and image.pixelColor(x, y).saturationF() > 0.15
            for x in range(image.width()) for y in range(image.height())
        )
