"""Centralized QSS resource loading."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path

from PySide6 import QtCore, QtWidgets

logger = logging.getLogger(__name__)

STYLESHEET_NAME = "main.qss"
LIGHT_STYLESHEET_NAME = "main_light.qss"
DEEP_NEUTRAL_CANVAS_STYLESHEET_NAME = "canvas_deep_neutral.qss"
MIDDLE_GRAY_18_CANVAS_STYLESHEET_NAME = "canvas_middle_gray_18.qss"
NEAR_BLACK_CANVAS_STYLESHEET_NAME = "canvas_near_black.qss"
ICON_DIR_PLACEHOLDER = "@PICVIEWER_ICON_DIR@"


class AppearanceTheme(str, Enum):
    """Supported application appearance themes."""

    LIGHT = "light"
    DARK = "dark"


class CanvasColor(str, Enum):
    """Supported neutral image canvas colors."""

    DEEP_NEUTRAL = "deep-neutral"
    MIDDLE_GRAY_18 = "middle-gray-18"
    NEAR_BLACK = "near-black"


DEFAULT_CANVAS_COLOR = CanvasColor.DEEP_NEUTRAL


_STYLESHEET_NAMES = {
    AppearanceTheme.LIGHT: LIGHT_STYLESHEET_NAME,
    AppearanceTheme.DARK: STYLESHEET_NAME,
}

_CANVAS_STYLESHEET_NAMES = {
    CanvasColor.DEEP_NEUTRAL: DEEP_NEUTRAL_CANVAS_STYLESHEET_NAME,
    CanvasColor.MIDDLE_GRAY_18: MIDDLE_GRAY_18_CANVAS_STYLESHEET_NAME,
    CanvasColor.NEAR_BLACK: NEAR_BLACK_CANVAS_STYLESHEET_NAME,
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


def canvas_stylesheet_path(canvas_color: CanvasColor = DEFAULT_CANVAS_COLOR) -> Path:
    """Return the path to the QSS resource for a neutral canvas color."""

    return Path(__file__).resolve().with_name(_CANVAS_STYLESHEET_NAMES[canvas_color])


def _icon_resource_dir() -> Path:
    """Return the directory containing icon resources referenced by QSS."""

    return Path(__file__).resolve().parents[1] / "icons"


def _resolve_resource_placeholders(style_sheet: str) -> str:
    """Replace QSS resource placeholders with absolute resource paths."""

    return style_sheet.replace(ICON_DIR_PLACEHOLDER, _icon_resource_dir().as_posix())


def load_stylesheet(
    theme: AppearanceTheme | None = None,
    canvas_color: CanvasColor = DEFAULT_CANVAS_COLOR,
) -> str:
    """Load and combine the QSS resources for a theme and canvas color.

    Args:
        theme: Explicit appearance theme, or None to resolve the system theme.
        canvas_color: Neutral color used around loaded images.

    Returns:
        The combined QSS content, or an empty string if a resource cannot be read.
    """

    paths = (stylesheet_path(theme), canvas_stylesheet_path(canvas_color))
    try:
        style_sheet = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        return _resolve_resource_placeholders(style_sheet)
    except OSError:
        logger.exception("Failed to load stylesheet resources: %s", paths)
        return ""


def apply_stylesheet(
    widget: QtWidgets.QWidget,
    theme: AppearanceTheme | None = None,
    canvas_color: CanvasColor = DEFAULT_CANVAS_COLOR,
) -> AppearanceTheme:
    """Apply the selected QSS resource to a widget tree.

    Args:
        widget: Root widget whose children should inherit the stylesheet.
        theme: Explicit theme, or None to resolve the operating system theme.
        canvas_color: Neutral color used around loaded images.

    Returns:
        The theme that was applied.
    """

    selected_theme = theme if theme is not None else resolve_system_theme()
    widget.setStyleSheet(load_stylesheet(selected_theme, canvas_color))
    return selected_theme
