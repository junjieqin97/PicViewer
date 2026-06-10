from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.app_metadata_service import AppMetadata  # noqa: E402
from pic_viewer.app.services.third_party_license_service import ThirdPartyLicenseInfo  # noqa: E402
from pic_viewer.controllers.main_controller import MainController  # noqa: E402


class AboutDialogTests(QtWidgetTestCase):
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

        self.assertIn("<strong>PicViewer</strong>", text)
        self.assertIn("<strong>Version 1.2.3</strong>", text)
        self.assertIn("camera RAW files", text)
        self.assertIn('class="about-light"', text)
        self.assertIn('font-weight: 300;', text)
        self.assertIn("Copyright (c) 2025-2026 junjieqin. All rights reserved.", text)
        self.assertNotIn("demo", text.lower())

    def test_show_about_uses_generated_about_text(self) -> None:
        controller = MainController.__new__(MainController)
        controller._main_window = object()
        controller._tr = lambda text: text  # type: ignore[method-assign]
        metadata = AppMetadata(name="PicViewer", version="4.5.6", copyright_owner="junjieqin")
        shown_boxes: list[object] = []
        fake_pixmap = object()

        class FakeIcon:
            def __init__(self) -> None:
                self.requested_size: tuple[int, int] | None = None

            def pixmap(self, width: int, height: int) -> object:
                self.requested_size = (width, height)
                return fake_pixmap

        fake_icon = FakeIcon()

        class FakeMessageBox:
            Ok = QtWidgets.QMessageBox.StandardButton.Ok

            class StandardButton:
                Ok = QtWidgets.QMessageBox.StandardButton.Ok

            def __init__(self, parent: object) -> None:
                self.parent = parent
                self.title = ""
                self.text_format = None
                self.text_value = ""
                self.icon_pixmap = None
                self.standard_buttons = None

            @staticmethod
            def information(*_: object) -> None:
                raise AssertionError("About dialog must use a configurable QMessageBox instance.")

            def setWindowTitle(self, title: str) -> None:
                self.title = title

            def setTextFormat(self, text_format: QtCore.Qt.TextFormat) -> None:
                self.text_format = text_format

            def setText(self, text: str) -> None:
                self.text_value = text

            def setIconPixmap(self, pixmap) -> None:  # type: ignore[no-untyped-def]
                self.icon_pixmap = pixmap

            def setStandardButtons(self, buttons) -> None:  # type: ignore[no-untyped-def]
                self.standard_buttons = buttons

            def exec(self) -> int:
                shown_boxes.append(self)
                return self.Ok

            def text(self) -> str:
                return self.text_value

            def iconPixmap(self):  # type: ignore[no-untyped-def]
                return self.icon_pixmap

        with (
            patch(
                "pic_viewer.controllers.main_controller_interaction_mixin.load_app_metadata",
                return_value=metadata,
            ),
            patch(
                "pic_viewer.controllers.main_controller_interaction_mixin.load_app_icon",
                return_value=fake_icon,
            ),
            patch.object(QtWidgets, "QMessageBox", FakeMessageBox),
        ):
            MainController._show_about(controller)

        self.assertEqual(1, len(shown_boxes))
        message_box = shown_boxes[0]
        text = message_box.text()
        self.assertEqual("About", message_box.title)
        self.assertEqual(QtCore.Qt.TextFormat.RichText, message_box.text_format)
        self.assertEqual(FakeMessageBox.Ok, message_box.standard_buttons)
        self.assertEqual((64, 64), fake_icon.requested_size)
        self.assertIs(fake_pixmap, message_box.iconPixmap())
        self.assertIn("Version 4.5.6", text)
        self.assertIn("2025-2026", text)
        self.assertIn("junjieqin", text)
        self.assertIn("<strong>", text)
        self.assertIn('class="about-light"', text)
        self.assertIn('font-weight: 300;', text)
        self.assertNotIn("demo", text.lower())

    def test_show_third_party_licenses_loads_data_and_executes_dialog(self) -> None:
        controller = MainController.__new__(MainController)
        controller._main_window = object()
        licenses = [
            ThirdPartyLicenseInfo(
                "PySide6",
                "PySide6",
                "6.8.0",
                "LGPL-3.0-only / GPL-2.0-only / GPL-3.0-only / Commercial",
                "",
            ),
        ]
        shown_dialogs: list[object] = []

        class FakeDialog:
            def __init__(self, license_infos: list[ThirdPartyLicenseInfo], parent: object | None = None) -> None:
                self.license_infos = license_infos
                self.parent = parent

            def exec(self) -> int:
                shown_dialogs.append(self)
                return 0

        with (
            patch(
                "pic_viewer.controllers.main_controller_interaction_mixin.load_third_party_licenses",
                return_value=licenses,
            ) as load_licenses,
            patch(
                "pic_viewer.controllers.main_controller_interaction_mixin.ThirdPartyLicenseDialog",
                FakeDialog,
            ),
        ):
            MainController._show_third_party_licenses(controller)

        load_licenses.assert_called_once_with()
        self.assertEqual(1, len(shown_dialogs))
        dialog = shown_dialogs[0]
        self.assertIs(licenses, dialog.license_infos)
        self.assertIs(controller._main_window, dialog.parent)


if __name__ == "__main__":
    unittest.main()
