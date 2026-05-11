from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from PyQt5 import QtCore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.ui.i18n.runtime import DEFAULT_LANGUAGE, install_translator, resolve_language  # noqa: E402


class I18nRuntimeTests(unittest.TestCase):
    def test_override_has_higher_priority_than_system_locale(self) -> None:
        resolved = resolve_language(language_override="en", system_locale_name="zh_CN")
        self.assertEqual("en", resolved)

    def test_system_english_locale_maps_to_en(self) -> None:
        resolved = resolve_language(language_override=None, system_locale_name="en_US")
        self.assertEqual("en", resolved)

    def test_unsupported_system_locale_falls_back_to_chinese(self) -> None:
        resolved = resolve_language(language_override=None, system_locale_name="fr_FR")
        self.assertEqual(DEFAULT_LANGUAGE, resolved)

    def test_install_translator_falls_back_when_qm_missing(self) -> None:
        app = QtCore.QCoreApplication.instance()
        if app is None:
            app = QtCore.QCoreApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            active, translator = install_translator(
                app=app,
                language="en",
                translations_root=Path(tmp_dir),
            )

        self.assertEqual(DEFAULT_LANGUAGE, active)
        self.assertIsNone(translator)

    def test_controller_error_localization_mapping(self) -> None:
        controller = MainController.__new__(MainController)
        controller._tr = lambda text: f"translated:{text}"  # type: ignore[method-assign]

        localized = controller._localize_backend_error_message("图片文件不存在")
        self.assertEqual("translated:图片文件不存在", localized)

        fallback = controller._localize_backend_error_message("unknown-message")
        self.assertEqual("translated:处理图片时发生未知错误", fallback)

    def test_controller_translation_checks_mixin_contexts(self) -> None:
        controller = MainController.__new__(MainController)

        def fake_translate(context: str, text: str) -> str:
            if context == "MainControllerTabsMixin":
                return "translated empty state"
            return text

        with patch.object(QtCore.QCoreApplication, "translate", side_effect=fake_translate):
            translated = MainController._tr(controller, "开始浏览照片")

        self.assertEqual("translated empty state", translated)

    def test_controller_translation_finds_load_state_text(self) -> None:
        controller = MainController.__new__(MainController)

        def fake_translate(context: str, text: str) -> str:
            if context == "MainControllerTabsMixin" and text == "无法打开图片":
                return "translated load failure"
            return text

        with patch.object(QtCore.QCoreApplication, "translate", side_effect=fake_translate):
            translated = MainController._tr(controller, "无法打开图片")

        self.assertEqual("translated load failure", translated)

    def test_controller_general_metadata_localization_mapping(self) -> None:
        controller = MainController.__new__(MainController)
        controller._tr = lambda text: f"translated:{text}"  # type: ignore[method-assign]

        localized = controller._localize_general_metadata_entries(
            (
                ("文件名", "sample.jpg"),
                ("大小", "未知"),
                ("其他", "保留原样"),
            )
        )

        self.assertEqual(("translated:文件名", "sample.jpg"), localized[0])
        self.assertEqual(("translated:大小", "translated:未知"), localized[1])
        self.assertEqual(("其他", "保留原样"), localized[2])


if __name__ == "__main__":
    unittest.main()
