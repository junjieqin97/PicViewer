"""Logging configuration for PicViewer."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from pic_viewer.config.settings import AppSettings

LOG_FILE_NAME = "picviewer.log"
LOG_FILE_MAX_BYTES = 5 * 1024 * 1024
LOG_FILE_BACKUP_COUNT = 5
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: AppSettings) -> None:
    """Configure root logger handlers for the current runtime mode.

    Args:
        settings: Runtime settings that include log level and developer mode.
    """

    level = _resolve_log_level(settings.log_level)
    if settings.developer_mode:
        try:
            handler = _create_file_handler(settings)
        except OSError:
            handler = _create_console_handler()
            _install_root_handler(level, handler)
            logging.getLogger(__name__).exception("Failed to initialize file logging; falling back to console")
            return
    else:
        handler = _create_console_handler()

    _install_root_handler(level, handler)


def _resolve_log_level(log_level: str) -> int:
    normalized = log_level.upper()
    resolved = logging.getLevelName(normalized)
    if isinstance(resolved, int):
        return resolved
    return logging.INFO


def _create_console_handler() -> logging.Handler:
    return logging.StreamHandler()


def _create_file_handler(settings: AppSettings) -> logging.Handler:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    return RotatingFileHandler(
        filename=settings.log_dir / LOG_FILE_NAME,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=LOG_FILE_BACKUP_COUNT,
        encoding="utf-8",
    )


def _install_root_handler(level: int, handler: logging.Handler) -> None:
    root_logger = logging.getLogger()
    for existing_handler in root_logger.handlers[:]:
        root_logger.removeHandler(existing_handler)
        existing_handler.close()

    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
