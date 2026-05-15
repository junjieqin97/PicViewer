from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from PyQt5 import QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.app_metadata_service import AppMetadata  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402


class AboutDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_about_text_contains_version_product_copy_and_copyright(self) -> None:
        controller = MainController.__new__(MainController)
        controller._tr = lambda text: text  # type: ignore[method-assign]
        metadata = AppMetadata(name="PicViewer", version="1.2.3", copyright_owner="junjieqin")

        text = MainController._build_about_text(controller, metadata)

        self.assertIn("PicViewer", text)
        self.assertIn("Version 1.2.3", text)
        self.assertIn("camera RAW files", text)
        self.assertIn("Copyright (c) junjieqin. All rights reserved.", text)
        self.assertNotIn("demo", text.lower())

    def test_show_about_uses_generated_about_text(self) -> None:
        controller = MainController.__new__(MainController)
        controller._main_window = QtWidgets.QMainWindow()
        controller._tr = lambda text: text  # type: ignore[method-assign]
        metadata = AppMetadata(name="PicViewer", version="4.5.6", copyright_owner="junjieqin")

        with (
            patch(
                "pic_viewer.controllers.main_controller_interaction_mixin.load_app_metadata",
                return_value=metadata,
            ),
            patch.object(QtWidgets.QMessageBox, "information") as information,
        ):
            MainController._show_about(controller)

        information.assert_called_once()
        _, title, text = information.call_args.args
        self.assertEqual("About", title)
        self.assertIn("Version 4.5.6", text)
        self.assertIn("junjieqin", text)
        self.assertNotIn("demo", text.lower())


if __name__ == "__main__":
    unittest.main()
