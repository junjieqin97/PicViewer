"""Metadata reader backed by pyexiv2.

Dependency: pyexiv2>=2.15.5 (`pip install "pyexiv2>=2.15.5,<3"`).
"""

from __future__ import annotations

import importlib
import logging
from pathlib import Path
import threading
from types import ModuleType
from typing import Any, Iterable, Mapping, Tuple

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataEntry, MetadataSection

logger = logging.getLogger(__name__)


class MetadataReader:
    """Read image metadata into structured sections."""

    _read_lock = threading.RLock()
    _TIFF_PREFIXES = ("Exif.Image.", "Exif.Thumbnail.")

    def warm_up(self) -> None:
        """Load the optional pyexiv2 backend before image workers start.

        pyexiv2 loads native libraries through ctypes on first import. Doing
        that from a background QRunnable can hold the Python GIL long enough
        to make the Qt main thread appear frozen while opening the first image.
        Warm-up failures are non-fatal because metadata is optional.
        """

        try:
            self._load_pyexiv2()
        except (ImportError, OSError):
            logger.warning("pyexiv2 is not available, metadata warm-up skipped", exc_info=True)

    def read(self, path: Path) -> ImageMetadata:
        """Extract metadata; failures degrade gracefully to empty sections.

        Args:
            path: Image file path.

        Returns:
            ImageMetadata: Structured metadata grouped for the existing UI.
        """

        if not path.exists() or not path.is_file():
            logger.warning("Metadata read failed, file not found: %s", path)
            return self._empty()

        try:
            pyexiv2 = self._load_pyexiv2()
        except (ImportError, OSError):
            logger.warning("pyexiv2 is not available, metadata read skipped: %s", path, exc_info=True)
            return self._empty()

        try:
            with self._read_lock:
                with pyexiv2.Image(str(path), "utf-8") as image:
                    exif_data = image.read_exif("utf-8")
                    iptc_data = image.read_iptc("utf-8")
        except FileNotFoundError:
            logger.warning("Metadata read failed, file not found: %s", path)
            return self._empty()
        except Exception:  # pragma: no cover - defensive fallback for native parser failures
            logger.exception("Error extracting metadata: %s", path)
            return self._empty()

        return ImageMetadata(
            general=tuple(),
            exif=self._normalize_items(exif_data.items()),
            iptc=self._normalize_items(iptc_data.items()),
            tiff=self._extract_tiff(exif_data),
        )

    def _load_pyexiv2(self) -> ModuleType:
        """Import pyexiv2 lazily so startup is not blocked by native load errors."""

        return importlib.import_module("pyexiv2")

    def _extract_tiff(self, exif_data: Mapping[Any, Any]) -> MetadataSection:
        """Derive the TIFF section from Exif.Image and Exif.Thumbnail tags."""

        items = (
            (key, value)
            for key, value in exif_data.items()
            if any(str(key).startswith(prefix) for prefix in self._TIFF_PREFIXES)
        )
        return self._normalize_items(items)

    def _normalize_items(self, items: Iterable[Tuple[Any, Any]]) -> MetadataSection:
        """Normalize backend tag keys and values for display."""

        entries: list[MetadataEntry] = []
        for key, value in items:
            label = self._label_for_key(key)
            entries.append((label, self._stringify(value)))
        entries.sort(key=lambda pair: (pair[0], pair[1]))
        return tuple(entries)

    def _label_for_key(self, key: Any) -> str:
        """Return the final tag component used by the current UI tables."""

        key_text = str(key)
        if "." not in key_text:
            return key_text
        return key_text.rsplit(".", maxsplit=1)[-1]

    def _stringify(self, value: Any) -> str:
        """Convert pyexiv2 metadata values into deterministic display text."""

        if value is None:
            return ""
        if isinstance(value, bytes):
            return self._stringify_bytes(value)
        if isinstance(value, Mapping):
            return ", ".join(
                f"{self._stringify(key)}: {self._stringify(value[key])}"
                for key in sorted(value, key=lambda item: str(item))
            )
        if isinstance(value, (list, tuple, set, frozenset)):
            ordered = value if isinstance(value, (list, tuple)) else sorted(value, key=lambda item: str(item))
            return ", ".join(self._stringify(item) for item in ordered)
        return str(value)

    def _stringify_bytes(self, value: bytes) -> str:
        try:
            decoded = value.decode("utf-8")
        except UnicodeDecodeError:
            return value.hex()

        cleaned = decoded.strip("\x00")
        if cleaned and all(char.isprintable() or char in "\n\r\t" for char in cleaned):
            return cleaned
        return value.hex()

    def _empty(self) -> ImageMetadata:
        empty: MetadataSection = tuple()
        return ImageMetadata(
            general=empty,
            exif=empty,
            iptc=empty,
            tiff=empty,
        )
