from __future__ import annotations

import io
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.config.logging_config import configure_logging
from pic_viewer.config.settings import AppSettings


class LoggingConfigTests(unittest.TestCase):
    """Validate PicViewer logging destination configuration."""

    def setUp(self) -> None:
        self.root_logger = logging.getLogger()
        self.original_handlers = self.root_logger.handlers[:]
        self.original_level = self.root_logger.level
        for handler in self.original_handlers:
            self.root_logger.removeHandler(handler)

    def tearDown(self) -> None:
        for handler in self.root_logger.handlers[:]:
            self.root_logger.removeHandler(handler)
            handler.close()
        for handler in self.original_handlers:
            self.root_logger.addHandler(handler)
        self.root_logger.setLevel(self.original_level)

    def test_default_mode_configures_single_console_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = AppSettings(
                log_level="INFO",
                allow_raw=True,
                language_override=None,
                developer_mode=False,
                log_dir=Path(tmp_dir),
            )

            configure_logging(settings)

        self.assertEqual(1, len(self.root_logger.handlers))
        handler = self.root_logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertNotIsInstance(handler, logging.FileHandler)

    def test_developer_mode_creates_rotating_file_handler_and_writes_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_dir = Path(tmp_dir) / "logs"
            settings = AppSettings(
                log_level="INFO",
                allow_raw=True,
                language_override=None,
                developer_mode=True,
                log_dir=log_dir,
            )

            configure_logging(settings)
            logging.getLogger("pic_viewer.tests.logging_config").info("Developer mode logging test")
            for handler in self.root_logger.handlers:
                handler.flush()

            log_file = log_dir / "picviewer.log"
            self.assertTrue(log_file.exists())
            self.assertIn("Developer mode logging test", log_file.read_text(encoding="utf-8"))
            self.assertEqual(1, len(self.root_logger.handlers))
            self.assertIsInstance(self.root_logger.handlers[0], RotatingFileHandler)

    def test_developer_mode_falls_back_to_console_when_file_logging_fails(self) -> None:
        error_stream = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = AppSettings(
                log_level="INFO",
                allow_raw=True,
                language_override=None,
                developer_mode=True,
                log_dir=Path(tmp_dir) / "logs",
            )

            with (
                patch("pic_viewer.config.logging_config.RotatingFileHandler", side_effect=OSError("denied")),
                patch("sys.stderr", error_stream),
            ):
                configure_logging(settings)

        self.assertEqual(1, len(self.root_logger.handlers))
        handler = self.root_logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertNotIsInstance(handler, logging.FileHandler)
        self.assertIn("Failed to initialize file logging; falling back to console", error_stream.getvalue())


if __name__ == "__main__":
    unittest.main()
