"""Discover ICC profiles from operating-system profile directories."""

from __future__ import annotations

import logging
from pathlib import Path
import platform

logger = logging.getLogger(__name__)

MACOS_COLOR_PROFILE_ROOT = Path("/Library/ColorSync/Profiles")
WINDOWS_COLOR_PROFILE_ROOT = Path(r"C:\Windows\System32\spool\drivers\color")
ICC_PROFILE_SUFFIXES = {".icc", ".icm"}


def discover_system_color_profile_paths(platform_name: str | None = None) -> list[Path]:
    """Return ICC/ICM profile paths from the current operating system.

    Args:
        platform_name: Optional platform override for tests. When omitted,
            the current platform from ``platform.system()`` is used.

    Returns:
        A stable list of profile paths from the supported system directory and
        its first-level child directories. Unsupported platforms return an
        empty list.
    """

    system_name = platform_name if platform_name is not None else platform.system()
    if system_name == "Darwin":
        root = MACOS_COLOR_PROFILE_ROOT
    elif system_name == "Windows":
        root = WINDOWS_COLOR_PROFILE_ROOT
    else:
        return []

    return _discover_profile_paths(root)


def _discover_profile_paths(root: Path) -> list[Path]:
    """Return root and first-level ICC/ICM files under ``root``."""

    if not root.exists() or not root.is_dir():
        return []

    profiles: list[Path] = []
    for entry in _safe_iterdir(root):
        if _is_profile_file(entry):
            profiles.append(entry)
            continue
        if entry.is_dir():
            profiles.extend(
                child for child in _safe_iterdir(entry) if _is_profile_file(child)
            )

    return sorted(profiles, key=lambda path: (path.name.casefold(), str(path).casefold()))


def _safe_iterdir(path: Path) -> list[Path]:
    """Return directory entries while tolerating unavailable system paths."""

    try:
        return list(path.iterdir())
    except OSError:
        logger.info(
            "Unable to scan color profile directory: path=%s",
            path,
            exc_info=True,
        )
        return []


def _is_profile_file(path: Path) -> bool:
    """Return whether ``path`` is an ICC/ICM file."""

    return path.is_file() and path.suffix.lower() in ICC_PROFILE_SUFFIXES
