"""Negative controls prove visual checks reject their intended regressions."""
from PySide6 import QtCore, QtGui

from tests.unit.qt_test_utils import QtWidgetTestCase
from tests.visual.assertions import (
    require_canvas, require_contained, require_contrast, require_focus_delta,
)


class VisualAssertionTests(QtWidgetTestCase):
    def test_containment_accepts_boundary_and_rejects_clipping_and_empty(self) -> None:
        outer = QtCore.QRect(0, 0, 20, 20)
        require_contained(outer, outer)
        for inner in (QtCore.QRect(1, 0, 20, 20), QtCore.QRect()):
            with self.subTest(inner=inner), self.assertRaises(AssertionError):
                require_contained(inner, outer)

    def test_contrast_rejects_unreadable_state(self) -> None:
        require_contrast(QtGui.QColor('white'), QtGui.QColor('black'))
        with self.assertRaisesRegex(AssertionError, 'contrast'):
            require_contrast(QtGui.QColor('#888888'), QtGui.QColor('#999999'))

    def test_focus_rejects_missing_indicator(self) -> None:
        before = QtGui.QImage(20, 20, QtGui.QImage.Format.Format_RGB32)
        before.fill(QtGui.QColor('black'))
        with self.assertRaisesRegex(AssertionError, 'focus indicator'):
            require_focus_delta(before, before, '#ffd166')
        after = before.copy()
        for x in range(10):
            after.setPixelColor(x, 0, QtGui.QColor('#ffd166'))
        require_focus_delta(before, after, '#ffd166')

    def test_canvas_rejects_changed_color_at_high_dpi(self) -> None:
        image = QtGui.QImage(20, 20, QtGui.QImage.Format.Format_RGB32)
        image.setDevicePixelRatio(2)
        image.fill(QtGui.QColor('#202020'))
        require_canvas(image, QtCore.QPoint(2, 2), '#202020')
        with self.assertRaisesRegex(AssertionError, 'Canvas differs'):
            require_canvas(image, QtCore.QPoint(2, 2), '#ffffff')
