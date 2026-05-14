"""Application settings loader."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def default_log_dir() -> Path:
    """Return the default PicViewer log directory.

    Returns:
        Path: User-specific log directory under ``~/.PicViewer/logs``.
    """

    return Path.home() / ".PicViewer" / "logs"


@dataclass(frozen=True)
class AppSettings:
    """Runtime configuration for PicViewer."""

    log_level: str
    allow_raw: bool
    language_override: str | None
    developer_mode: bool
    log_dir: Path


def load_settings(developer_mode: bool = False) -> AppSettings:
    """Load settings from environment variables.

    Args:
        developer_mode: Whether file logging should be enabled for developer runs.

    Returns:
        AppSettings: Parsed settings with defaults applied.
    """

    log_level = os.getenv("PICVIEWER_LOG_LEVEL", "INFO")
    allow_raw = os.getenv("PICVIEWER_ALLOW_RAW", "1").lower() not in {"0", "false", "no"}
    language_override = os.getenv("PICVIEWER_LANG")
    return AppSettings(
        log_level=log_level,
        allow_raw=allow_raw,
        language_override=language_override,
        developer_mode=developer_mode,
        log_dir=default_log_dir(),
    )
