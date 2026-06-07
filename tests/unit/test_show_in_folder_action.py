from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402


class ShowInFolderActionTests(unittest.TestCase):
    """Validate image context menu folder-opening behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_show_current_image_in_folder_opens_parent_directory_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.jpg"
            controller, window, tabs = self._build_controller_with_current_path(image_path)
            self.addCleanup(window.deleteLater)
            self.addCleanup(tabs.deleteLater)

            with patch.object(QtGui.QDesktopServices, "openUrl", return_value=True) as open_url:
                MainController._show_current_image_in_folder(controller)

        open_url.assert_called_once()
        opened_url = open_url.call_args.args[0]
        self.assertTrue(opened_url.isLocalFile())
        self.assertEqual(Path(tmp_dir), Path(opened_url.toLocalFile()))

    def test_show_current_image_in_folder_without_current_path_warns_without_opening(self) -> None:
        controller, window, tabs = self._build_controller_with_current_path(None)
        self.addCleanup(window.deleteLater)
        self.addCleanup(tabs.deleteLater)

        with patch.object(QtGui.QDesktopServices, "openUrl", return_value=True) as open_url:
            with patch.object(QtWidgets.QMessageBox, "warning") as warning:
                MainController._show_current_image_in_folder(controller)

        open_url.assert_not_called()
        warning.assert_called_once_with(
            window,
            "Warning",
            "Unable to open the image folder.",
        )

    def test_show_current_image_in_folder_with_missing_parent_warns_without_opening(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            missing_image_path = Path(tmp_dir) / "missing" / "sample.jpg"
            controller, window, tabs = self._build_controller_with_current_path(missing_image_path)
            self.addCleanup(window.deleteLater)
            self.addCleanup(tabs.deleteLater)

        with patch.object(QtGui.QDesktopServices, "openUrl", return_value=True) as open_url:
            with patch.object(QtWidgets.QMessageBox, "warning") as warning:
                MainController._show_current_image_in_folder(controller)

        open_url.assert_not_called()
        warning.assert_called_once_with(
            window,
            "Warning",
            "Unable to open the image folder.",
        )

    def test_show_current_image_in_folder_warns_when_desktop_service_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.jpg"
            controller, window, tabs = self._build_controller_with_current_path(image_path)
            self.addCleanup(window.deleteLater)
            self.addCleanup(tabs.deleteLater)

            with patch.object(QtGui.QDesktopServices, "openUrl", return_value=False) as open_url:
                with patch.object(QtWidgets.QMessageBox, "warning") as warning:
                    MainController._show_current_image_in_folder(controller)

        open_url.assert_called_once()
        warning.assert_called_once_with(
            window,
            "Warning",
            "Unable to open the image folder.",
        )

    def test_refresh_actions_state_enables_show_in_folder_for_current_existing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.jpg"
            controller, window, tabs = self._build_controller_with_current_path(image_path)
            self.addCleanup(window.deleteLater)
            self.addCleanup(tabs.deleteLater)

            MainController._refresh_actions_state(controller)

        self.assertTrue(controller._ui.actShowInFolder.isEnabled())

    def test_refresh_actions_state_disables_show_in_folder_without_current_path(self) -> None:
        controller, window, tabs = self._build_controller_with_current_path(None)
        self.addCleanup(window.deleteLater)
        self.addCleanup(tabs.deleteLater)

        MainController._refresh_actions_state(controller)

        self.assertFalse(controller._ui.actShowInFolder.isEnabled())

    def _build_controller_with_current_path(
        self,
        image_path: Path | None,
    ) -> tuple[MainController, QtWidgets.QMainWindow, QtWidgets.QTabWidget]:
        window = QtWidgets.QMainWindow()
        tabs = QtWidgets.QTabWidget()
        if image_path is not None:
            tab = QtWidgets.QWidget()
            tab.setProperty("image_path", str(image_path))
            tabs.addTab(tab, image_path.name)

        controller = MainController.__new__(MainController)
        QtCore.QObject.__init__(controller, window)
        controller._main_window = window
        controller._active_image_path = None
        controller._detached_image_windows = {}
        controller._tr = lambda text: text  # type: ignore[method-assign]
        controller._ui = SimpleNamespace(
            tabsImages=tabs,
            actCloseTab=QtGui.QAction(window),
            actZoomIn=QtGui.QAction(window),
            actZoomOut=QtGui.QAction(window),
            actFitToWindow=QtGui.QAction(window),
            actShowInFolder=QtGui.QAction(window),
        )
        return controller, window, tabs

    def tearDown(self) -> None:
        self._app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self._app.processEvents()


if __name__ == "__main__":
    unittest.main()
