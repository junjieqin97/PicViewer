"""Centralized QSS resource loading."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from PySide6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)

STYLESHEET_NAME = "main.qss"
LIGHT_STYLESHEET_NAME = "main_light.qss"
ICON_DIR_PLACEHOLDER = "@PICVIEWER_ICON_DIR@"


class AppearanceTheme(str, Enum):
    """Supported application appearance themes."""

    LIGHT = "light"
    DARK = "dark"


_STYLESHEET_NAMES = {
    AppearanceTheme.LIGHT: LIGHT_STYLESHEET_NAME,
    AppearanceTheme.DARK: STYLESHEET_NAME,
}


def theme_from_color_scheme(color_scheme: object) -> AppearanceTheme:
    """Map a Qt color scheme value to an application appearance theme.

    Args:
        color_scheme: A value returned from QStyleHints.colorScheme().

    Returns:
        The matching appearance theme. Unknown or unsupported values fall back to light.
    """

    if color_scheme == QtCore.Qt.ColorScheme.Dark:
        return AppearanceTheme.DARK
    return AppearanceTheme.LIGHT


def resolve_system_theme(app: QtWidgets.QApplication | None = None) -> AppearanceTheme:
    """Resolve the startup appearance theme from the operating system.

    Args:
        app: Optional application instance. If omitted, the current QApplication is used.

    Returns:
        Dark when the operating system reports a dark color scheme; light otherwise.
    """

    application = app if app is not None else QtWidgets.QApplication.instance()
    if application is None:
        return AppearanceTheme.LIGHT
    try:
        color_scheme = application.styleHints().colorScheme()
    except (AttributeError, RuntimeError):
        logger.exception("Failed to resolve system color scheme")
        return AppearanceTheme.LIGHT
    return theme_from_color_scheme(color_scheme)


def stylesheet_path(theme: AppearanceTheme | None = None) -> Path:
    """Return the path to the application QSS resource for a theme."""

    selected_theme = theme if theme is not None else resolve_system_theme()
    return Path(__file__).resolve().with_name(_STYLESHEET_NAMES[selected_theme])


def _icon_resource_dir() -> Path:
    """Return the directory containing icon resources referenced by QSS."""

    return Path(__file__).resolve().parents[1] / "icons"


def _resolve_resource_placeholders(style_sheet: str) -> str:
    """Replace QSS resource placeholders with absolute resource paths."""

    return style_sheet.replace(ICON_DIR_PLACEHOLDER, _icon_resource_dir().as_posix())


def load_stylesheet(theme: AppearanceTheme | None = None) -> str:
    """Load the QSS resource for a theme.

    Returns:
        The QSS content, or an empty string if the resource cannot be read.
    """

    path = stylesheet_path(theme)
    try:
        return _resolve_resource_placeholders(path.read_text(encoding="utf-8"))
    except OSError:
        logger.exception("Failed to load stylesheet resource: %s", path)
        return ""


def apply_stylesheet(
    widget: QtWidgets.QWidget,
    theme: AppearanceTheme | None = None,
) -> AppearanceTheme:
    """Apply the selected QSS resource to a widget tree.

    Args:
        widget: Root widget whose children should inherit the stylesheet.
        theme: Explicit theme, or None to resolve the operating system theme.

    Returns:
        The theme that was applied.
    """

    selected_theme = theme if theme is not None else resolve_system_theme()
    widget.setStyleSheet(load_stylesheet(selected_theme))
    return selected_theme
