"""Centralized QSS resource loading."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide2 import QtWidgets

logger = logging.getLogger(__name__)

STYLESHEET_NAME = "main.qss"


def stylesheet_path() -> Path:
    """Return the path to the main application QSS resource."""

    return Path(__file__).resolve().with_name(STYLESHEET_NAME)


def load_stylesheet() -> str:
    """Load the main QSS resource.

    Returns:
        The QSS content, or an empty string if the resource cannot be read.
    """

    path = stylesheet_path()
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Failed to load stylesheet resource: %s", path)
        return ""


def apply_stylesheet(widget: QtWidgets.QWidget) -> None:
    """Apply the central QSS resource to a widget tree."""

    widget.setStyleSheet(load_stylesheet())
