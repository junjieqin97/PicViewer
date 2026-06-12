from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.domain.rules.focus_peaking import FocusPeakLevel  # noqa: E402
from pic_viewer.ui.widgets.histogram_clipping_label import HistogramClippingLabel  # noqa: E402


class MainControllerClippingToggleTests(QtWidgetTestCase):
    """Validate clipping marker signal flow and refresh behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def setUp(self) -> None:
        super().setUp()
        self.widget = HistogramClippingLabel()
        self.act_toggle_underexposed = QtGui.QAction()
        self.act_toggle_underexposed.setCheckable(True)
        self.act_toggle_overexposed = QtGui.QAction()
        self.act_toggle_overexposed.setCheckable(True)
        self.act_peak_high = QtGui.QAction()
        self.act_peak_high.setCheckable(True)
        self.act_peak_medium = QtGui.QAction()
        self.act_peak_medium.setCheckable(True)
        self.act_peak_low = QtGui.QAction()
        self.act_peak_low.setCheckable(True)
        self.controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(self.controller)
        self.controller._ui = SimpleNamespace(
            widgetHistogram=self.widget,
            actToggleUnderexposed=self.act_toggle_underexposed,
            actToggleOverexposed=self.act_toggle_overexposed,
            actPeakHigh=self.act_peak_high,
            actPeakMedium=self.act_peak_medium,
            actPeakLow=self.act_peak_low,
        )
        self.controller._show_underexposed = False
        self.controller._show_overexposed = False
        self.controller._focus_peak_level = None
        self.controller._sync_histogram_overlay_state = MagicMock()
        self.controller._refresh_overlay_for_current_image = MagicMock()
        self.addCleanup(self.widget.deleteLater)

    def test_underexposed_signal_triggers_state_and_refresh(self) -> None:
        self.widget.underexposed_toggled.connect(self.controller._on_underexposed_toggled)

        self.widget.underexposed_toggled.emit(True)

        self.assertTrue(self.controller._show_underexposed)
        self.controller._sync_histogram_overlay_state.assert_called_once_with()
        self.controller._refresh_overlay_for_current_image.assert_called_once_with()

    def test_overexposed_signal_triggers_state_and_refresh(self) -> None:
        self.widget.overexposed_toggled.connect(self.controller._on_overexposed_toggled)

        self.widget.overexposed_toggled.emit(True)

        self.assertTrue(self.controller._show_overexposed)
        self.controller._sync_histogram_overlay_state.assert_called_once_with()
        self.controller._refresh_overlay_for_current_image.assert_called_once_with()

    def test_repeat_signal_value_does_not_trigger_refresh(self) -> None:
        self.controller._show_underexposed = True
        self.widget.underexposed_toggled.connect(self.controller._on_underexposed_toggled)

        self.widget.underexposed_toggled.emit(True)

        self.controller._sync_histogram_overlay_state.assert_not_called()
        self.controller._refresh_overlay_for_current_image.assert_not_called()

    def test_hovering_triangles_updates_hover_state_and_cursor(self) -> None:
        self.widget.resize(256, 100)

        self._send_mouse_move(self.widget, QtCore.QPoint(10, 10))

        self.assertEqual("underexposed", self.widget._hovered_triangle)
        self.assertEqual(QtCore.Qt.CursorShape.PointingHandCursor, self.widget.cursor().shape())

        self._send_mouse_move(self.widget, QtCore.QPoint(245, 10))

        self.assertEqual("overexposed", self.widget._hovered_triangle)
        self.assertEqual(QtCore.Qt.CursorShape.PointingHandCursor, self.widget.cursor().shape())

        self._send_mouse_move(self.widget, QtCore.QPoint(128, 80))

        self.assertIsNone(self.widget._hovered_triangle)
        self.assertNotEqual(QtCore.Qt.CursorShape.PointingHandCursor, self.widget.cursor().shape())

        self._send_mouse_move(self.widget, QtCore.QPoint(10, 10))
        self.widget.leaveEvent(QtCore.QEvent(QtCore.QEvent.Type.Leave))

        self.assertIsNone(self.widget._hovered_triangle)
        self.assertNotEqual(QtCore.Qt.CursorShape.PointingHandCursor, self.widget.cursor().shape())

    def test_clicking_triangles_emits_toggle_signals(self) -> None:
        self.widget.resize(256, 100)
        underexposed_toggled = MagicMock()
        overexposed_toggled = MagicMock()
        self.widget.underexposed_toggled.connect(underexposed_toggled)
        self.widget.overexposed_toggled.connect(overexposed_toggled)

        self._send_mouse_press(self.widget, QtCore.QPoint(10, 10))
        self._send_mouse_press(self.widget, QtCore.QPoint(245, 10))

        underexposed_toggled.assert_called_once_with(True)
        overexposed_toggled.assert_called_once_with(True)

    def test_luma_marker_value_can_be_set_and_cleared(self) -> None:
        self.assertTrue(hasattr(self.widget, "set_luma_marker_value"))
        self.assertTrue(hasattr(self.widget, "luma_marker_value"))

        self.widget.set_luma_marker_value(128)

        self.assertEqual(128, self.widget.luma_marker_value())

        self.widget.set_luma_marker_value(-1)

        self.assertEqual(-1, self.widget.luma_marker_value())

    def test_luma_marker_renders_black_vertical_line(self) -> None:
        self.assertTrue(hasattr(self.widget, "set_luma_marker_value"))
        self.widget.resize(256, 100)
        pixmap = QtGui.QPixmap(256, 100)
        pixmap.fill(QtGui.QColor(255, 255, 255))
        self.widget.setPixmap(pixmap)
        self.widget.set_luma_marker_value(128)

        image = QtGui.QImage(self.widget.size(), QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor(255, 255, 255))
        self.widget.render(image)

        self.assertEqual(QtGui.QColor(0, 0, 0), QtGui.QColor(image.pixel(128, 50)))

    def test_tooltip_event_uses_qhelp_event_positions(self) -> None:
        self.widget.resize(256, 100)
        self.widget.set_triangle_tooltips("Under", "Over")
        event = QtGui.QHelpEvent(
            QtCore.QEvent.Type.ToolTip,
            QtCore.QPoint(10, 10),
            QtCore.QPoint(100, 100),
        )

        with patch.object(QtWidgets.QToolTip, "showText") as show_text:
            handled = self.widget.event(event)

        self.assertTrue(handled)
        show_text.assert_called_once_with(QtCore.QPoint(100, 100), "Under", self.widget)

    def _send_mouse_move(self, widget: HistogramClippingLabel, pos: QtCore.QPoint) -> None:
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseMove,
            QtCore.QPointF(pos),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        widget.mouseMoveEvent(event)

    def _send_mouse_press(self, widget: HistogramClippingLabel, pos: QtCore.QPoint) -> None:
        event = QtGui.QMouseEvent(
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QPointF(pos),
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.MouseButton.LeftButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
        )
        widget.mousePressEvent(event)

    def test_refresh_overlay_clears_cache_and_refreshes_current_tab(self) -> None:
        controller = MainController.__new__(MainController)
        current_path = Path("/tmp/current.jpg")
        controller._tab_preview_render_key_by_path = {str(current_path): ("cached",)}
        controller._current_image_path = MagicMock(return_value=current_path)
        controller._refresh_current_image_pixmap = MagicMock()

        MainController._refresh_overlay_for_current_image(controller)

        self.assertNotIn(str(current_path), controller._tab_preview_render_key_by_path)
        controller._refresh_current_image_pixmap.assert_called_once_with()

    def test_refresh_overlay_ignores_when_no_current_path(self) -> None:
        controller = MainController.__new__(MainController)
        controller._tab_preview_render_key_by_path = {"/tmp/a.jpg": ("cached",)}
        controller._current_image_path = MagicMock(return_value=None)
        controller._refresh_current_image_pixmap = MagicMock()

        MainController._refresh_overlay_for_current_image(controller)

        self.assertIn("/tmp/a.jpg", controller._tab_preview_render_key_by_path)
        controller._refresh_current_image_pixmap.assert_not_called()

    def test_menu_underexposed_toggle_triggers_state_and_refresh(self) -> None:
        self.act_toggle_underexposed.toggled.connect(self.controller._on_underexposed_toggled)

        self.act_toggle_underexposed.setChecked(True)

        self.assertTrue(self.controller._show_underexposed)
        self.controller._sync_histogram_overlay_state.assert_called_once_with()
        self.controller._refresh_overlay_for_current_image.assert_called_once_with()

    def test_menu_overexposed_toggle_triggers_state_and_refresh(self) -> None:
        self.act_toggle_overexposed.toggled.connect(self.controller._on_overexposed_toggled)

        self.act_toggle_overexposed.setChecked(True)

        self.assertTrue(self.controller._show_overexposed)
        self.controller._sync_histogram_overlay_state.assert_called_once_with()
        self.controller._refresh_overlay_for_current_image.assert_called_once_with()

    def test_sync_overlay_state_updates_menu_actions_and_widget(self) -> None:
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller)
        widget = HistogramClippingLabel()
        action_under = QtGui.QAction()
        action_under.setCheckable(True)
        action_over = QtGui.QAction()
        action_over.setCheckable(True)
        controller._ui = SimpleNamespace(
            widgetHistogram=widget,
            actToggleUnderexposed=action_under,
            actToggleOverexposed=action_over,
        )
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._show_underexposed = True
        controller._show_overexposed = False
        self.addCleanup(widget.deleteLater)

        MainController._sync_histogram_overlay_state(controller)

        self.assertTrue(action_under.isChecked())
        self.assertFalse(action_over.isChecked())
        self.assertTrue(widget.underexposed_active())
        self.assertFalse(widget.overexposed_active())

    def test_sync_overlay_state_updates_both_histogram_clipping_states(self) -> None:
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller)
        widget = HistogramClippingLabel()
        action_under = QtGui.QAction()
        action_under.setCheckable(True)
        action_over = QtGui.QAction()
        action_over.setCheckable(True)
        controller._ui = SimpleNamespace(
            widgetHistogram=widget,
            actToggleUnderexposed=action_under,
            actToggleOverexposed=action_over,
        )
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._show_underexposed = True
        controller._show_overexposed = True
        self.addCleanup(widget.deleteLater)

        MainController._sync_histogram_overlay_state(controller)

        self.assertTrue(action_under.isChecked())
        self.assertTrue(action_over.isChecked())
        self.assertTrue(widget.underexposed_active())
        self.assertTrue(widget.overexposed_active())

    def test_focus_peak_level_toggle_selects_one_level_and_refreshes(self) -> None:
        self.controller._tr = lambda text: text  # type: ignore[method-assign]
        self.controller._sync_histogram_overlay_state = (
            lambda: MainController._sync_histogram_overlay_state(self.controller)
        )

        MainController._on_focus_peak_level_triggered(self.controller, FocusPeakLevel.HIGH)

        self.assertEqual(FocusPeakLevel.HIGH, self.controller._focus_peak_level)
        self.assertTrue(self.act_peak_high.isChecked())
        self.assertFalse(self.act_peak_medium.isChecked())
        self.assertFalse(self.act_peak_low.isChecked())
        self.controller._refresh_overlay_for_current_image.assert_called_once_with()

    def test_focus_peak_level_toggle_turns_off_current_level(self) -> None:
        self.controller._tr = lambda text: text  # type: ignore[method-assign]
        self.controller._focus_peak_level = FocusPeakLevel.MEDIUM
        self.controller._sync_histogram_overlay_state = (
            lambda: MainController._sync_histogram_overlay_state(self.controller)
        )

        MainController._on_focus_peak_level_triggered(self.controller, FocusPeakLevel.MEDIUM)

        self.assertIsNone(self.controller._focus_peak_level)
        self.assertFalse(self.act_peak_high.isChecked())
        self.assertFalse(self.act_peak_medium.isChecked())
        self.assertFalse(self.act_peak_low.isChecked())
        self.controller._refresh_overlay_for_current_image.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
