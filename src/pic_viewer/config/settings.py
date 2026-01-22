"""Application settings loader."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AppSettings:
    """Runtime configuration for PicViewer."""

    log_level: str
    allow_raw: bool


def load_settings() -> AppSettings:
    """Load settings from environment variables.

    Returns:
        AppSettings: Parsed settings with defaults applied.
    """

    log_level = os.getenv("PICVIEWER_LOG_LEVEL", "INFO")
    allow_raw = os.getenv("PICVIEWER_ALLOW_RAW", "1").lower() not in {"0", "false", "no"}
    return AppSettings(log_level=log_level, allow_raw=allow_raw)
