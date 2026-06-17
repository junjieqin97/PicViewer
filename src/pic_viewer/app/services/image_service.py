"""Application service for image loading and analysis."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from pic_viewer.app.dto.analysis_view import AnalysisView, AnalysisViewSettings, LumaRgbMode, RgbChannel
from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult, PreviewLoadResult
from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection
from pic_viewer.common.errors import ImageLoadError
from pic_viewer.domain.models.bit_depth import ChannelBitDepth
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    DEFAULT_DISPLAY_COLOR_SPACE,
    ColorProfileSpec,
    LocalColorProfile,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent
from pic_viewer.domain.rules.analysis import ImageAnalyzer
from pic_viewer.domain.rules.exposure_overlay import ExposureOverlayOptions, apply_exposure_overlay
from pic_viewer.domain.rules.focus_peaking import (
    FocusPeakLevel,
    FocusPeakingOptions,
    apply_focus_peaking_overlay,
)
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter
from pic_viewer.infra.adapters.image_reader import ImageReader
from pic_viewer.infra.adapters.metadata_reader import MetadataReader

logger = logging.getLogger(__name__)


class ImageService:
    """Coordinate image I/O and analysis use cases."""

    def __init__(
        self,
        reader: ImageReader,
        analyzer: ImageAnalyzer,
        metadata_reader: MetadataReader,
        color_converter: ColorProfileConverter,
    ) -> None:
        self._reader = reader
        self._analyzer = analyzer
        self._metadata_reader = metadata_reader
        self._color_converter = color_converter

    def load_and_analyze(
        self,
        path: Path,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
        analysis_bit_depth: ChannelBitDepth = ChannelBitDepth.EIGHT,
    ) -> ImageLoadResult:
        """Load an image, compute analysis artifacts, and read metadata.

        Args:
            path: Path to image file.
            display_color_space: Target RGB display color space.
            assumed_source_color_space: Source color space to use when ICC is unavailable.
            rendering_intent: ICC rendering intent used for gamut mapping.

        Returns:
            ImageLoadResult: Analysis payload and metadata for the UI layer.

        Raises:
            ImageLoadError: If reading fails.
            ImageProcessError: If processing fails.
        """

        try:
            read_result = self._reader.read_with_profile_and_depth(
                path,
                display_color_space=display_color_space,
                assumed_source_color_space=assumed_source_color_space,
                rendering_intent=rendering_intent,
            )
        except ImageLoadError:
            raise
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("Failed to read image: %s", path)
            raise ImageLoadError("Unable to read this image file") from exc

        result = self._analyzer.analyze(
            read_result.bgr,
            analysis_bit_depth=analysis_bit_depth,
        )
        analysis = ImageAnalysis(
            analysis_bgr=result.analysis_bgr,
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
            display_color_space=display_color_space,
            assumed_source_color_space=assumed_source_color_space,
            rendering_intent=rendering_intent,
            source_color_profile=read_result.source_color_profile,
            cms_bit_depth=read_result.cms_bit_depth,
            analysis_bit_depth=result.analysis_bit_depth,
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

    def load_local_color_profile(self, path: Path) -> LocalColorProfile:
        """Load and validate a user-selected local ICC profile."""

        return self._color_converter.load_local_profile(path)

    def warm_up_optional_backends(self) -> None:
        """Prepare optional native backends before background image loads start."""

        self._metadata_reader.warm_up()

    def read_metadata(self, path: Path) -> ImageMetadata:
        """Read structured image metadata without decoding or analyzing pixels."""

        return self._metadata_reader.read(path)

    def load_preview(
        self,
        path: Path,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> PreviewLoadResult:
        """Load a lightweight preview without metadata or analysis plots."""

        try:
            read_result = self._reader.read_preview_with_profile_and_depth(
                path,
                display_color_space=display_color_space,
                assumed_source_color_space=assumed_source_color_space,
                rendering_intent=rendering_intent,
            )
        except ImageLoadError:
            raise
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("Failed to read preview: %s", path)
            raise ImageLoadError("Unable to read this image file") from exc

        preview_rgb = self._analyzer.build_preview_rgb(read_result.bgr)
        return PreviewLoadResult(
            preview_rgb=preview_rgb,
            display_color_space=display_color_space,
            assumed_source_color_space=assumed_source_color_space,
            rendering_intent=rendering_intent,
            source_color_profile=read_result.source_color_profile,
            cms_bit_depth=read_result.cms_bit_depth,
        )

    def render_analysis_view(
        self,
        analysis: ImageAnalysis,
        settings: AnalysisViewSettings,
        hist_size: tuple[int, int],
        wave_size: tuple[int, int],
        pixel_ratio: float,
    ) -> AnalysisView:
        """Render a DPR-aware analysis view for the given settings and sizes.

        This keeps the domain renderer free of Qt types by accepting pure
        (height, width) pixel sizes and a scalar DPR.
        """

        hist_height, hist_width = hist_size
        wave_height, wave_width = wave_size
        if hist_height <= 0 or hist_width <= 0 or wave_height <= 0 or wave_width <= 0:
            return self._select_precomputed_view(analysis, settings)

        try:
            source_bgr = analysis.analysis_bgr
            if getattr(source_bgr, "size", 0) == 0:
                return self._select_precomputed_view(analysis, settings)
            histogram_rgb, waveform_rgb = self._render_with_settings(
                source_bgr,
                settings,
                hist_size,
                wave_size,
                pixel_ratio,
            )
            return AnalysisView(histogram_rgb=histogram_rgb, waveform_rgb=waveform_rgb)
        except Exception:  # pragma: no cover - defensive fallback
            logger.exception("Failed to render analysis view")
            return self._select_precomputed_view(analysis, settings)

    def build_preview_with_exposure_overlay(
        self,
        preview_rgb: np.ndarray,
        show_underexposed: bool,
        show_overexposed: bool,
    ) -> np.ndarray:
        """Return a display preview with optional clipping pseudo-color overlays."""

        return self.build_preview_with_pseudo_color_overlay(
            preview_rgb,
            show_underexposed=show_underexposed,
            show_overexposed=show_overexposed,
            focus_peak_level=None,
        )

    def build_preview_with_pseudo_color_overlay(
        self,
        preview_rgb: np.ndarray,
        show_underexposed: bool,
        show_overexposed: bool,
        focus_peak_level: FocusPeakLevel | None,
    ) -> np.ndarray:
        """Return a display preview with optional pseudo-color overlays."""

        if not show_underexposed and not show_overexposed:
            if focus_peak_level is None:
                return preview_rgb
            return apply_focus_peaking_overlay(
                preview_rgb,
                FocusPeakingOptions(level=focus_peak_level),
            )

        options = ExposureOverlayOptions(
            show_underexposed=show_underexposed,
            show_overexposed=show_overexposed,
        )
        output = apply_exposure_overlay(preview_rgb, options)
        if focus_peak_level is None:
            return output
        return apply_focus_peaking_overlay(
            output,
            FocusPeakingOptions(level=focus_peak_level),
        )

    def _render_with_settings(
        self,
        source_bgr: np.ndarray,
        settings: AnalysisViewSettings,
        hist_size: tuple[int, int],
        wave_size: tuple[int, int],
        pixel_ratio: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Render histogram and waveform using the current view settings."""

        if settings.mode == LumaRgbMode.LUMA:
            histogram_rgb = self._analyzer.render_histogram_luma(
                source_bgr,
                hist_size=hist_size,
                pixel_ratio=pixel_ratio,
            )
            waveform_rgb = self._analyzer.render_waveform_luma(
                source_bgr,
                wave_size=wave_size,
                pixel_ratio=pixel_ratio,
            )
            return histogram_rgb, waveform_rgb

        channels = self._channels_for(settings.channel)
        histogram_rgb = self._analyzer.render_histogram_channels(
            source_bgr,
            channels=channels,
            hist_size=hist_size,
            pixel_ratio=pixel_ratio,
        )
        waveform_rgb = self._analyzer.render_waveform_channels(
            source_bgr,
            channels=channels,
            wave_size=wave_size,
            pixel_ratio=pixel_ratio,
        )
        return histogram_rgb, waveform_rgb

    def _channels_for(self, channel: RgbChannel) -> list[int]:
        """Map view channel selection to BGR channel indices."""

        if channel == RgbChannel.RED:
            return [2]
        if channel == RgbChannel.GREEN:
            return [1]
        if channel == RgbChannel.BLUE:
            return [0]
        return [0, 1, 2]

    def _select_precomputed_view(
        self,
        analysis: ImageAnalysis,
        settings: AnalysisViewSettings,
    ) -> AnalysisView:
        """Select the precomputed view as a safe fallback."""

        if settings.mode == LumaRgbMode.LUMA:
            return AnalysisView(histogram_rgb=analysis.histogram_luma, waveform_rgb=analysis.waveform_luma)

        if settings.channel == RgbChannel.RED:
            return AnalysisView(histogram_rgb=analysis.histogram_r, waveform_rgb=analysis.waveform_r)
        if settings.channel == RgbChannel.GREEN:
            return AnalysisView(histogram_rgb=analysis.histogram_g, waveform_rgb=analysis.waveform_g)
        if settings.channel == RgbChannel.BLUE:
            return AnalysisView(histogram_rgb=analysis.histogram_b, waveform_rgb=analysis.waveform_b)
        return AnalysisView(histogram_rgb=analysis.histogram_rgb, waveform_rgb=analysis.waveform_rgb)

    def _build_general_metadata(self, path: Path, analysis: ImageAnalysis) -> MetadataSection:
        """Assemble general metadata similar to macOS 预览."""

        entries: list[tuple[str, str]] = [
            ("File Name", path.name),
            ("Path", str(path)),
        ]
        try:
            size_bytes = path.stat().st_size
            entries.append(("Size", self._format_size(size_bytes)))
        except OSError:
            logger.warning("Failed to read file size: %s", path, exc_info=True)
            entries.append(("Size", "Unknown"))

        try:
            height, width = analysis.source_size
            entries.append(("Resolution", f"{width} x {height}"))
        except Exception:
            logger.warning("Failed to read resolution: %s", path, exc_info=True)
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
