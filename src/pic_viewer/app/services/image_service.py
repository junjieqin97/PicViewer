"""Application service for image loading and analysis."""

from __future__ import annotations

import logging
from pathlib import Path

from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult
from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection
from pic_viewer.common.errors import ImageLoadError
from pic_viewer.domain.rules.analysis import ImageAnalyzer
from pic_viewer.infra.adapters.image_reader import ImageReader
from pic_viewer.infra.adapters.metadata_reader import MetadataReader

logger = logging.getLogger(__name__)


class ImageService:
    """Coordinate image I/O and analysis use cases."""

    def __init__(self, reader: ImageReader, analyzer: ImageAnalyzer, metadata_reader: MetadataReader) -> None:
        self._reader = reader
        self._analyzer = analyzer
        self._metadata_reader = metadata_reader

    def load_and_analyze(self, path: Path) -> ImageLoadResult:
        """Load an image, compute analysis artifacts, and read metadata.

        Args:
            path: Path to image file.

        Returns:
            ImageLoadResult: Analysis payload and metadata for the UI layer.

        Raises:
            ImageLoadError: If reading fails.
            ImageProcessError: If processing fails.
        """

        try:
            bgr = self._reader.read(path)
        except ImageLoadError:
            raise
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("读取图片失败: %s", path)
            raise ImageLoadError("无法读取该图片文件") from exc

        result = self._analyzer.analyze(bgr)
        analysis = ImageAnalysis(
            preview_rgb=result.preview_rgb,
            source_size=result.source_size,
            histogram_rgb=result.histogram_rgb,
            histogram_luma=result.histogram_luma,
            histogram_r=result.histogram_r,
            histogram_g=result.histogram_g,
            histogram_b=result.histogram_b,
            waveform_rgb=result.waveform_rgb,
            waveform_luma=result.waveform_luma,
            waveform_r=result.waveform_r,
            waveform_g=result.waveform_g,
            waveform_b=result.waveform_b,
        )

        raw_metadata = self._metadata_reader.read(path)
        general_metadata = self._build_general_metadata(path, analysis)
        metadata = ImageMetadata(
            general=general_metadata,
            exif=raw_metadata.exif,
            iptc=raw_metadata.iptc,
            tiff=raw_metadata.tiff,
        )

        return ImageLoadResult(analysis=analysis, metadata=metadata)

    def _build_general_metadata(self, path: Path, analysis: ImageAnalysis) -> MetadataSection:
        """Assemble general metadata similar to macOS 预览."""

        entries: list[tuple[str, str]] = [
            ("文件名", path.name),
            ("路径", str(path)),
        ]
        try:
            size_bytes = path.stat().st_size
            entries.append(("大小", self._format_size(size_bytes)))
        except OSError:
            logger.warning("读取文件大小失败: %s", path, exc_info=True)
            entries.append(("大小", "未知"))

        try:
            height, width = analysis.source_size
            entries.append(("分辨率", f"{width} x {height}"))
        except Exception:
            logger.warning("读取分辨率失败: %s", path, exc_info=True)
        return tuple(entries)

    def _format_size(self, size_bytes: int) -> str:
        """Format file size for display."""

        units = ["bytes", "KB", "MB", "GB"]
        size = float(size_bytes)
        unit = 0
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024.0
            unit += 1
        return f"{size:.1f} {units[unit]}"
