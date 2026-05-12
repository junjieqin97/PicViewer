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

from pic_viewer.app.dto.analysis_view import (  # noqa: E402
    AnalysisViewSettings,
    LumaRgbMode,
    RgbChannel,
)
from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.ui.windows.main_window import MainWindowUI  # noqa: E402


class MainControllerAnalysisModeSummaryTests(unittest.TestCase):
    """Validate visible analysis mode summary synchronization."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_luma_mode_summary_marks_rgb_channel_not_applicable(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)
        controller._view_settings = AnalysisViewSettings(
            mode=LumaRgbMode.LUMA,
            channel=RgbChannel.RED,
        )

        MainController._sync_view_actions(controller)

        self.assertEqual("明度模式", ui.labelAnalysisModeValue.text())
        self.assertEqual("不适用", ui.labelAnalysisChannelValue.text())

    def test_rgb_all_channel_summary_updates_when_mode_changes(self) -> None:
        window, ui, controller = self._build_controller()
        self.addCleanup(window.deleteLater)

        MainController._change_view_mode(controller, LumaRgbMode.RGB)

        self.assertEqual("RGB模式", ui.labelAnalysisModeValue.text())
        self.assertEqual("全部", ui.labelAnalysisChannelValue.text())

    def test_rgb_single_channel_summary_updates_when_channel_changes(self) -> None:
        expected = (
            (RgbChannel.RED, "红"),
            (RgbChannel.GREEN, "绿"),
            (RgbChannel.BLUE, "蓝"),
        )
        for channel, label in expected:
            with self.subTest(channel=channel):
                window, ui, controller = self._build_controller()
                self.addCleanup(window.deleteLater)

                MainController._change_channel(controller, channel)

                self.assertEqual("RGB模式", ui.labelAnalysisModeValue.text())
                self.assertEqual(label, ui.labelAnalysisChannelValue.text())

    def _build_controller(self) -> tuple[QtWidgets.QMainWindow, MainWindowUI, MainController]:
        window = QtWidgets.QMainWindow()
        ui = MainWindowUI()
        ui.setup_ui(window)
        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._ui = ui
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._view_settings = AnalysisViewSettings(
            mode=LumaRgbMode.LUMA,
            channel=RgbChannel.ALL,
        )
        controller._refresh_view_for_current_image = MagicMock()  # type: ignore[method-assign]
        return window, ui, controller


if __name__ == "__main__":
    unittest.main()
