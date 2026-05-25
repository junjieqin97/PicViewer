"""Helpers for pruning unused PyInstaller runtime entries."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Sequence, TypeVar

TocEntry = TypeVar("TocEntry", bound=tuple[str, ...])

SUPPORTED_QT_TRANSLATIONS = {
    "qt_zh_CN.qm",
    "qtbase_zh_CN.qm",
    "qt_en.qm",
    "qtbase_en.qm",
}

MACOS_PLATFORM_PLUGIN = "qcocoa"
WINDOWS_PLATFORM_PLUGIN = "qwindows"
SVG_IMAGE_PLUGIN = "qsvg"
SVG_ICON_PLUGIN = "qsvgicon"


def filter_pyinstaller_analysis_toc(entries: Sequence[TocEntry], platform: str) -> list[TocEntry]:
    """Return PyInstaller TOC entries after conservative PySide6 pruning.

    Args:
        entries: PyInstaller analysis entries whose first item is the packaged
            destination path.
        platform: The value of ``sys.platform`` for the target build.

    Returns:
        A list preserving original entry order and tuple values while removing
        known-unused PySide6 network, plugin, and translation entries.
    """

    return [entry for entry in entries if not _should_remove_entry(entry[0], platform)]


def _should_remove_entry(destination: str, platform: str) -> bool:
    normalized = _normalize_destination(destination)
    basename = PurePosixPath(normalized).name

    if _is_qt_network_extension(normalized) or _is_qt_network_library(basename):
        return True
    if _is_excluded_plugin(normalized, platform):
        return True
    if _is_excluded_qt_translation(normalized, basename):
        return True
    return False


def _normalize_destination(destination: str) -> str:
    return destination.replace("\\", "/")


def _is_qt_network_extension(destination: str) -> bool:
    return destination.startswith("PySide6/QtNetwork.")


def _is_qt_network_library(basename: str) -> bool:
    return basename.startswith(("libQt6Network.", "Qt6Network."))


def _is_excluded_plugin(destination: str, platform: str) -> bool:
    plugin_prefix = "PySide6/Qt/plugins/"
    if not destination.startswith(plugin_prefix):
        return False

    plugin_path = destination.removeprefix(plugin_prefix)
    parts = plugin_path.split("/", maxsplit=1)
    if len(parts) != 2:
        return False

    plugin_type, plugin_file = parts
    plugin_name = _plugin_name(plugin_file)

    if plugin_type in {"networkinformation", "tls"}:
        return True
    if plugin_type == "platforms":
        return _is_excluded_platform_plugin(plugin_name, platform)
    if plugin_type == "imageformats":
        return plugin_name != SVG_IMAGE_PLUGIN
    if plugin_type == "iconengines":
        return plugin_name != SVG_ICON_PLUGIN
    return False


def _is_excluded_platform_plugin(plugin_name: str, platform: str) -> bool:
    if platform == "darwin":
        return plugin_name != MACOS_PLATFORM_PLUGIN
    if platform == "win32":
        return plugin_name != WINDOWS_PLATFORM_PLUGIN
    return False


def _plugin_name(file_name: str) -> str:
    stem = file_name.lower()
    for suffix in (".dylib", ".dll", ".so"):
        if stem.endswith(suffix):
            stem = stem.removesuffix(suffix)
            break
    if stem.startswith("lib"):
        stem = stem.removeprefix("lib")
    return stem


def _is_excluded_qt_translation(destination: str, basename: str) -> bool:
    if not destination.startswith("PySide6/Qt/translations/"):
        return False
    return basename not in SUPPORTED_QT_TRANSLATIONS
