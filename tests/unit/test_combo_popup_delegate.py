from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.ui.widgets.combo_popup_delegate import ComboPopupItemDelegate  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class ComboPopupItemDelegateTests(QtWidgetTestCase):
    """Validate combo popup item highlighting independent of platform delegates."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_delegate_paints_hovered_item_background_from_palette_highlight(self) -> None:
        delegate = ComboPopupItemDelegate()
        model = QtGui.QStandardItemModel()
        model.appendRow(QtGui.QStandardItem("Display P3"))
        option = self._item_option(QtWidgets.QStyle.StateFlag.State_MouseOver)
        image = QtGui.QImage(option.rect.size(), QtGui.QImage.Format.Format_ARGB32)
        image.fill(option.palette.color(QtGui.QPalette.ColorRole.Base))

        painter = QtGui.QPainter(image)
        try:
            delegate.paint(painter, option, model.index(0, 0))
        finally:
            painter.end()

        self.assertEqual(
            option.palette.color(QtGui.QPalette.ColorRole.Highlight).name(),
            image.pixelColor(3, option.rect.center().y()).name(),
        )

    def test_delegate_paints_selected_item_background_from_palette_highlight(self) -> None:
        delegate = ComboPopupItemDelegate()
        model = QtGui.QStandardItemModel()
        model.appendRow(QtGui.QStandardItem("Adobe RGB (1998)"))
        option = self._item_option(QtWidgets.QStyle.StateFlag.State_Selected)
        image = QtGui.QImage(option.rect.size(), QtGui.QImage.Format.Format_ARGB32)
        image.fill(option.palette.color(QtGui.QPalette.ColorRole.Base))

        painter = QtGui.QPainter(image)
        try:
            delegate.paint(painter, option, model.index(0, 0))
        finally:
            painter.end()

        self.assertEqual(
            option.palette.color(QtGui.QPalette.ColorRole.Highlight).name(),
            image.pixelColor(3, option.rect.center().y()).name(),
        )

    def test_analysis_combos_use_combo_popup_delegate(self) -> None:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        self.addCleanup(window.deleteLater)

        for combo in (
            ui.comboAnalysisSamplePrecision,
            ui.comboSpecifiedImageColorSpace,
            ui.comboRenderingIntent,
            ui.comboDisplayColorSpace,
        ):
            with self.subTest(combo=combo.objectName()):
                self.assertIsInstance(combo.itemDelegate(), ComboPopupItemDelegate)

    @staticmethod
    def _item_option(state: QtWidgets.QStyle.StateFlag) -> QtWidgets.QStyleOptionViewItem:
        option = QtWidgets.QStyleOptionViewItem()
        option.rect = QtCore.QRect(0, 0, 160, 24)
        option.state = QtWidgets.QStyle.StateFlag.State_Enabled | state
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor("#171a1e"))
        palette.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor("#edf1f5"))
        palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor("#3d6fa3"))
        palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtGui.QColor("#ffffff"))
        option.palette = palette
        return option


if __name__ == "__main__":
    unittest.main()
