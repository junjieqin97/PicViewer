from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import unittest

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AppIconResourceTests(QtWidgetTestCase):
    """Validate PicViewer application icon runtime resources."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_app_icon_loader_returns_non_empty_icon(self) -> None:
        spec = importlib.util.find_spec("pic_viewer.ui.resources.icons")
        self.assertIsNotNone(spec, "Icon resource module should exist.")

        icon_module = importlib.import_module("pic_viewer.ui.resources.icons")
        icon = icon_module.load_app_icon()

        self.assertFalse(icon.isNull())

    def test_expected_icon_assets_are_available(self) -> None:
        icon_dir = PROJECT_ROOT / "src" / "pic_viewer" / "ui" / "resources" / "icons"
        expected_files = [
            "picviewer.svg",
            "picviewer-16.png",
            "picviewer-32.png",
            "picviewer-48.png",
            "picviewer-64.png",
            "picviewer-128.png",
            "picviewer-256.png",
            "picviewer-512.png",
            "picviewer-1024.png",
        ]

        for file_name in expected_files:
            with self.subTest(file_name=file_name):
                self.assertTrue((icon_dir / file_name).is_file())

    def test_packaging_icon_assets_are_available(self) -> None:
        icon_dir = PROJECT_ROOT / "packaging" / "icons"

        self.assertTrue((icon_dir / "picviewer.ico").is_file())
        self.assertTrue((icon_dir / "picviewer.icns").is_file())
