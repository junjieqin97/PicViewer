"""Application icon resource loading."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore, QtGui

logger = logging.getLogger(__name__)

ICON_BASENAME = "picviewer"
ICON_SIZES = (16, 32, 48, 64, 128, 256, 512, 1024)


def icons_dir() -> Path:
    """Return the directory containing PicViewer icon resources."""

    return Path(__file__).resolve().parent


def icon_path(file_name: str) -> Path:
    """Return the absolute path for an icon resource file."""

    return icons_dir() / file_name


def load_app_icon() -> QtGui.QIcon:
    """Load the multi-resolution PicViewer application icon."""

    icon = QtGui.QIcon()
    for size in ICON_SIZES:
        path = icon_path(f"{ICON_BASENAME}-{size}.png")
        if path.is_file():
            icon.addFile(str(path), QtCore.QSize(size, size))

    if icon.isNull():
        svg_path = icon_path(f"{ICON_BASENAME}.svg")
        if svg_path.is_file():
            icon.addFile(str(svg_path))

    if icon.isNull():
        logger.warning("PicViewer application icon resources are missing: %s", icons_dir())
    return icon
