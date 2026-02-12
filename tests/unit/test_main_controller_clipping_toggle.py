from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.ui.widgets.histogram_clipping_label import HistogramClippingLabel  # noqa: E402


class MainControllerClippingToggleTests(unittest.TestCase):
    """Validate clipping marker signal flow and refresh behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def setUp(self) -> None:
        self.widget = HistogramClippingLabel()
        self.act_toggle_underexposed = QtWidgets.QAction()
        self.act_toggle_underexposed.setCheckable(True)
        self.act_toggle_overexposed = QtWidgets.QAction()
        self.act_toggle_overexposed.setCheckable(True)
        self.controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(self.controller)
        self.controller._ui = SimpleNamespace(
            widgetHistogram=self.widget,
            actToggleUnderexposed=self.act_toggle_underexposed,
            actToggleOverexposed=self.act_toggle_overexposed,
        )
        self.controller._show_underexposed = False
        self.controller._show_overexposed = False
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
        action_under = QtWidgets.QAction()
        action_under.setCheckable(True)
        action_over = QtWidgets.QAction()
        action_over.setCheckable(True)
        controller._ui = SimpleNamespace(
            widgetHistogram=widget,
            actToggleUnderexposed=action_under,
            actToggleOverexposed=action_over,
        )
        controller._show_underexposed = True
        controller._show_overexposed = False
        self.addCleanup(widget.deleteLater)

        MainController._sync_histogram_overlay_state(controller)

        self.assertTrue(action_under.isChecked())
        self.assertFalse(action_over.isChecked())
        self.assertTrue(widget.underexposed_active())
        self.assertFalse(widget.overexposed_active())


if __name__ == "__main__":
    unittest.main()
