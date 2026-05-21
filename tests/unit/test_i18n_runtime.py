from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from PySide2 import QtCore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.controllers.main_controller import MainController  # noqa: E402
from pic_viewer.ui.i18n.runtime import (  # noqa: E402
    CHINESE_LANGUAGE,
    DEFAULT_LANGUAGE,
    install_translator,
    resolve_language,
)


class I18nRuntimeTests(unittest.TestCase):
    def test_override_has_higher_priority_than_system_locale(self) -> None:
        resolved = resolve_language(language_override="en", system_locale_name="zh_CN")
        self.assertEqual("en", resolved)

    def test_system_english_locale_maps_to_en(self) -> None:
        resolved = resolve_language(language_override=None, system_locale_name="en_US")
        self.assertEqual("en", resolved)

    def test_system_chinese_locale_maps_to_zh_cn(self) -> None:
        resolved = resolve_language(language_override=None, system_locale_name="zh_CN")
        self.assertEqual(CHINESE_LANGUAGE, resolved)

    def test_unsupported_system_locale_falls_back_to_english(self) -> None:
        resolved = resolve_language(language_override=None, system_locale_name="fr_FR")
        self.assertEqual(DEFAULT_LANGUAGE, resolved)

    def test_install_translator_returns_none_for_source_language(self) -> None:
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

    def test_install_translator_falls_back_when_chinese_qm_missing(self) -> None:
        app = QtCore.QCoreApplication.instance()
        if app is None:
            app = QtCore.QCoreApplication([])

        with tempfile.TemporaryDirectory() as tmp_dir:
            active, translator = install_translator(
                app=app,
                language=CHINESE_LANGUAGE,
                translations_root=Path(tmp_dir),
            )

        self.assertEqual(DEFAULT_LANGUAGE, active)
        self.assertIsNone(translator)

    def test_controller_error_localization_mapping(self) -> None:
        controller = MainController.__new__(MainController)
        controller._tr = lambda text: f"translated:{text}"  # type: ignore[method-assign]

        localized = controller._localize_backend_error_message("Image file does not exist")
        self.assertEqual("translated:Image file does not exist", localized)

        fallback = controller._localize_backend_error_message("unknown-message")
        self.assertEqual("translated:An unknown error occurred while processing the image", fallback)

    def test_controller_translation_checks_mixin_contexts(self) -> None:
        controller = MainController.__new__(MainController)

        def fake_translate(context: str, text: str) -> str:
            if context == "MainControllerTabsMixin":
                return "translated empty state"
            return text

        with patch.object(QtCore.QCoreApplication, "translate", side_effect=fake_translate):
            translated = MainController._tr(controller, "Start Browsing Photos")

        self.assertEqual("translated empty state", translated)

    def test_controller_translation_finds_load_state_text(self) -> None:
        controller = MainController.__new__(MainController)

        def fake_translate(context: str, text: str) -> str:
            if context == "MainControllerTabsMixin" and text == "Unable to Open Image":
                return "translated load failure"
            return text

        with patch.object(QtCore.QCoreApplication, "translate", side_effect=fake_translate):
            translated = MainController._tr(controller, "Unable to Open Image")

        self.assertEqual("translated load failure", translated)

    def test_controller_general_metadata_localization_mapping(self) -> None:
        controller = MainController.__new__(MainController)
        controller._tr = lambda text: f"translated:{text}"  # type: ignore[method-assign]

        localized = controller._localize_general_metadata_entries(
            (
                ("File Name", "sample.jpg"),
                ("Size", "Unknown"),
                ("Other", "keep as-is"),
            )
        )

        self.assertEqual(("translated:File Name", "sample.jpg"), localized[0])
        self.assertEqual(("translated:Size", "translated:Unknown"), localized[1])
        self.assertEqual(("Other", "keep as-is"), localized[2])


if __name__ == "__main__":
    unittest.main()
