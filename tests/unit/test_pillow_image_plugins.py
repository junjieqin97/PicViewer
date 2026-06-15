from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class PillowImagePluginRegistrationTests(unittest.TestCase):
    """Validate optional Pillow image plugin registration."""

    def test_register_optional_pillow_image_plugins_is_idempotent(self) -> None:
        module = importlib.import_module("pic_viewer.infra.adapters.pillow_image_plugins")
        module._registered = False
        heif_module = types.SimpleNamespace(register_heif_opener=unittest.mock.MagicMock())
        avif_module = types.SimpleNamespace()

        def fake_import(name: str, *_args: object, **_kwargs: object) -> object:
            if name == "pillow_avif":
                return avif_module
            if name == "pillow_heif":
                return heif_module
            raise ImportError(name)

        with patch("importlib.import_module", side_effect=fake_import):
            module.register_optional_pillow_image_plugins()
            module.register_optional_pillow_image_plugins()

        heif_module.register_heif_opener.assert_called_once_with(thumbnails=False)

    def test_register_optional_pillow_image_plugins_logs_missing_plugins_without_failing(self) -> None:
        module = importlib.import_module("pic_viewer.infra.adapters.pillow_image_plugins")
        module._registered = False

        with (
            patch("importlib.import_module", side_effect=ImportError("missing")),
            self.assertLogs("pic_viewer.infra.adapters.pillow_image_plugins", level="INFO") as logs,
        ):
            module.register_optional_pillow_image_plugins()

        self.assertTrue(any("Pillow AVIF plugin is not available" in message for message in logs.output))
        self.assertTrue(any("Pillow HEIF plugin is not available" in message for message in logs.output))


if __name__ == "__main__":
    unittest.main()
