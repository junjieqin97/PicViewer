"""Application metadata helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from importlib import metadata
import logging
from pathlib import Path
from typing import Any, Optional

try:  # pragma: no cover - exercised implicitly on Python 3.11+
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - needed for Python 3.9/3.10
    tomllib = None  # type: ignore[assignment]

PACKAGE_NAME = "picviewer"
APP_NAME = "PicViewer"
COPYRIGHT_OWNER = "junjieqin"
UNKNOWN_VERSION = "unknown"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppMetadata:
    """User-visible application metadata."""

    name: str
    version: str
    copyright_owner: str


def load_app_metadata(project_root: Optional[Path] = None) -> AppMetadata:
    """Load metadata displayed in application UI."""

    return AppMetadata(
        name=APP_NAME,
        version=resolve_app_version(project_root=project_root),
        copyright_owner=COPYRIGHT_OWNER,
    )


def resolve_app_version(project_root: Optional[Path] = None) -> str:
    """Resolve application version from pyproject metadata or package metadata."""

    root = _default_project_root() if project_root is None else project_root
    version = _read_pyproject_version(root / "pyproject.toml")
    if version:
        return version

    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return UNKNOWN_VERSION


def _default_project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _read_pyproject_version(pyproject_path: Path) -> Optional[str]:
    if not pyproject_path.exists():
        return None

    try:
        pyproject_text = pyproject_path.read_text(encoding="utf-8")
    except OSError:
        logger.exception("Failed to read pyproject metadata: %s", pyproject_path)
        return None

    if tomllib is not None:
        try:
            data = tomllib.loads(pyproject_text)
        except tomllib.TOMLDecodeError:
            logger.exception("Failed to parse pyproject metadata: %s", pyproject_path)
            return None
        project = data.get("project", {})
        if isinstance(project, dict):
            version = project.get("version")
            if isinstance(version, str):
                return version
        return None

    return _read_pyproject_version_without_tomllib(pyproject_text)


def _read_pyproject_version_without_tomllib(pyproject_text: str) -> Optional[str]:
    in_project_section = False
    for raw_line in pyproject_text.splitlines():
        line = raw_line.strip()
        if line == "[project]":
            in_project_section = True
            continue
        if line.startswith("[") and line.endswith("]"):
            in_project_section = False
            continue
        if not in_project_section or not line.startswith("version"):
            continue

        key, separator, value = line.partition("=")
        if separator and key.strip() == "version":
            parsed = _literal_string(value.strip())
            if parsed is not None:
                return parsed
    return None


def _literal_string(value: str) -> Optional[str]:
    try:
        parsed: Any = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None
    if isinstance(parsed, str):
        return parsed
    return None
