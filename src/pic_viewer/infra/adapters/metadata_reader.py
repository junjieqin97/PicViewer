"""Metadata reader backed by Pillow.

依赖: Pillow>=10 (`pip install "Pillow>=10"`).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, Tuple

from PIL import ExifTags, Image, JpegImagePlugin, TiffTags  # type: ignore

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataEntry, MetadataSection

logger = logging.getLogger(__name__)


class MetadataReader:
    """Read image metadata into structured sections."""

    def read(self, path: Path) -> ImageMetadata:
        """Extract metadata; failures degrade gracefully to empty sections."""

        try:
            with Image.open(path) as image:
                exif = self._extract_exif(image)
                iptc = self._extract_iptc(image)
                tiff = self._extract_tiff(image)
        except FileNotFoundError:
            logger.warning("元数据读取失败，文件不存在: %s", path)
            return self._empty()
        except Exception:  # pragma: no cover - 防御性兜底
            logger.exception("提取元数据时出错: %s", path)
            return self._empty()

        return ImageMetadata(
            general=tuple(),
            exif=exif,
            iptc=iptc,
            tiff=tiff,
        )

    def _extract_exif(self, image: Image.Image) -> MetadataSection:
        mapping = getattr(image, "getexif", None)
        if mapping is None:
            return tuple()
        exif = image.getexif()
        if not exif:
            return tuple()
        name_lookup = ExifTags.TAGS
        return self._normalize_items(exif.items(), name_lookup)

    def _extract_iptc(self, image: Image.Image) -> MetadataSection:
        try:
            data = JpegImagePlugin.getiptcinfo(image)
        except Exception:  # pragma: no cover - 防御性兜底
            logger.debug("解析IPTC信息失败", exc_info=True)
            return tuple()
        if not data:
            return tuple()
        return self._normalize_items(data.items(), None)

    def _extract_tiff(self, image: Image.Image) -> MetadataSection:
        tags = getattr(image, "tag_v2", None)
        if tags is None:
            return tuple()
        name_lookup = getattr(TiffTags, "TAGS_V2", getattr(TiffTags, "TAGS", {}))
        return self._normalize_items(tags.items(), name_lookup)

    def _normalize_items(
        self, items: Iterable[Tuple[Any, Any]], name_lookup: dict[Any, str] | None
    ) -> MetadataSection:
        entries: list[MetadataEntry] = []
        for key, value in items:
            label = name_lookup.get(key, str(key)) if name_lookup is not None else str(key)
            entries.append((str(label), self._stringify(value)))
        entries.sort(key=lambda pair: pair[0])
        return tuple(entries)

    def _stringify(self, value: Any) -> str:
        if isinstance(value, bytes):
            try:
                return value.decode("utf-8", errors="ignore") or value.hex()
            except Exception:  # pragma: no cover - 防御性兜底
                return value.hex()
        if isinstance(value, (list, tuple)):
            return ", ".join(self._stringify(v) for v in value)
        return str(value)

    def _empty(self) -> ImageMetadata:
        empty: MetadataSection = tuple()
        return ImageMetadata(
            general=empty,
            exif=empty,
            iptc=empty,
            tiff=empty,
        )
