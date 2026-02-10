"""Pure image analysis logic without UI dependencies."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

from pic_viewer.common.errors import ImageProcessError

logger = logging.getLogger(__name__)

DEFAULT_HIST_SIZE = (320, 512)
DEFAULT_WAVE_SIZE = (320, 640)
DEFAULT_MAX_DISPLAY_EDGE = 4096
DEFAULT_MAX_ANALYSIS_EDGE = 4096
WAVE_INTENSITY_PERCENTILE = 99.5
WAVE_LOG_GAIN = 6.0
WAVE_GAMMA = 0.7
WAVE_BLUR_SIGMA = 0.8
WAVE_AXIS_MARGIN = 0
WAVE_AXIS_LABELS = (0, 20, 40, 60, 80, 100)
WAVE_AXIS_TICKS = (20, 40, 60, 80)
WAVE_AXIS_COLOR_BGR = (0, 255, 255)
# <= 0 表示刻度线从 Y 轴贯穿到波形图右侧
WAVE_AXIS_TICK_LENGTH = 0
WAVE_AXIS_FONT_SCALE = 0.4
WAVE_AXIS_THICKNESS = 1
WAVE_AXIS_TEXT_X = 4
ANALYSIS_BG_COLOR_BGR = (64, 64, 64)
LUMA_COLOR = (200, 200, 200)
CHANNEL_COLORS = {
    0: (255, 0, 0),
    1: (0, 255, 0),
    2: (0, 0, 255),
}


@dataclass(frozen=True)
class AnalysisResult:
    """Computed image analysis artifacts.

    Attributes:
        analysis_bgr: Downscaled BGR source used for analysis re-rendering.
        preview_rgb: Downscaled RGB preview for UI display.
        source_size: Original image size (height, width).
        histogram_rgb: RGB histogram plot image.
        histogram_luma: Luma histogram plot image.
        histogram_r: Red channel histogram plot image.
        histogram_g: Green channel histogram plot image.
        histogram_b: Blue channel histogram plot image.
        waveform_rgb: RGB waveform plot image.
        waveform_luma: Luma waveform plot image.
        waveform_r: Red channel waveform plot image.
        waveform_g: Green channel waveform plot image.
        waveform_b: Blue channel waveform plot image.
    """

    analysis_bgr: np.ndarray
    preview_rgb: np.ndarray
    source_size: tuple[int, int]
    histogram_rgb: np.ndarray
    histogram_luma: np.ndarray
    histogram_r: np.ndarray
    histogram_g: np.ndarray
    histogram_b: np.ndarray
    waveform_rgb: np.ndarray
    waveform_luma: np.ndarray
    waveform_r: np.ndarray
    waveform_g: np.ndarray
    waveform_b: np.ndarray


@dataclass(frozen=True)
class HistogramGeometry:
    """Resolved histogram canvas parameters."""

    height: int
    width: int
    thickness: int


@dataclass(frozen=True)
class WaveformGeometry:
    """Resolved waveform canvas parameters."""

    height: int
    width: int
    axis_margin: int
    plot_width: int
    axis_text_x: int
    axis_font_scale: float
    axis_thickness: int
    axis_tick_length: int


class ImageAnalyzer:
    """Compute histogram and waveform images for a given image."""

    def __init__(
        self,
        hist_size: tuple[int, int] = DEFAULT_HIST_SIZE,
        wave_size: tuple[int, int] = DEFAULT_WAVE_SIZE,
        max_display_edge: int = DEFAULT_MAX_DISPLAY_EDGE,
        max_analysis_edge: int = DEFAULT_MAX_ANALYSIS_EDGE,
    ) -> None:
        """Create analyzer with configurable output resolutions.

        Args:
            hist_size: (height, width) for histogram canvases.
            wave_size: (height, width) for waveform canvases.
            max_display_edge: Max edge length for preview_rgb to avoid UI卡顿.
            max_analysis_edge: Max edge length for stored analysis_bgr.
        """

        self._hist_height, self._hist_width = hist_size
        self._wave_height, self._wave_width = wave_size
        self._max_display_edge = max(1, int(max_display_edge))
        self._max_analysis_edge = max(self._max_display_edge, int(max_analysis_edge))
        self._wave_intensity_percentile = WAVE_INTENSITY_PERCENTILE
        self._wave_log_gain = WAVE_LOG_GAIN
        self._wave_gamma = WAVE_GAMMA
        self._wave_blur_sigma = WAVE_BLUR_SIGMA
        self._wave_axis_margin_base = WAVE_AXIS_MARGIN
        self._wave_axis_labels = WAVE_AXIS_LABELS
        self._wave_axis_ticks = set(WAVE_AXIS_TICKS)
        self._wave_axis_color_bgr = WAVE_AXIS_COLOR_BGR
        self._wave_axis_tick_length_base = WAVE_AXIS_TICK_LENGTH
        self._wave_axis_font_scale_base = WAVE_AXIS_FONT_SCALE
        self._wave_axis_thickness_base = WAVE_AXIS_THICKNESS
        self._wave_axis_text_x_base = WAVE_AXIS_TEXT_X
        self._analysis_bg_color_bgr = ANALYSIS_BG_COLOR_BGR

    def analyze(self, bgr: np.ndarray) -> AnalysisResult:
        """Generate analysis artifacts from BGR input.

        Args:
            bgr: Source image in BGR format.

        Returns:
            AnalysisResult: RGB image plus histogram and waveform previews.

        Raises:
            ImageProcessError: If processing fails.
        """

        try:
            source_size = (int(bgr.shape[0]), int(bgr.shape[1]))
            analysis_bgr = self._build_analysis_source_bgr(bgr)
            analysis_rgb = cv2.cvtColor(analysis_bgr, cv2.COLOR_BGR2RGB)
            preview_rgb = self._build_preview_rgb(analysis_rgb)
            histogram_rgb = self.render_histogram_channels(analysis_bgr, [0, 1, 2])
            histogram_luma = self.render_histogram_luma(analysis_bgr)
            histogram_b = self.render_histogram_channels(analysis_bgr, [0])
            histogram_g = self.render_histogram_channels(analysis_bgr, [1])
            histogram_r = self.render_histogram_channels(analysis_bgr, [2])
            waveform_rgb = self.render_waveform_channels(analysis_bgr, [0, 1, 2])
            waveform_luma = self.render_waveform_luma(analysis_bgr)
            waveform_b = self.render_waveform_channels(analysis_bgr, [0])
            waveform_g = self.render_waveform_channels(analysis_bgr, [1])
            waveform_r = self.render_waveform_channels(analysis_bgr, [2])
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("Image analysis failed")
            raise ImageProcessError("图像分析失败") from exc

        return AnalysisResult(
            analysis_bgr=analysis_bgr,
            preview_rgb=preview_rgb,
            source_size=source_size,
            histogram_rgb=histogram_rgb,
            histogram_luma=histogram_luma,
            histogram_r=histogram_r,
            histogram_g=histogram_g,
            histogram_b=histogram_b,
            waveform_rgb=waveform_rgb,
            waveform_luma=waveform_luma,
            waveform_r=waveform_r,
            waveform_g=waveform_g,
            waveform_b=waveform_b,
        )

    def build_preview_rgb(self, bgr: np.ndarray) -> np.ndarray:
        """Build a UI preview from a BGR image without full analysis."""

        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return self._build_preview_rgb(rgb)

    def _build_analysis_source_bgr(self, bgr: np.ndarray) -> np.ndarray:
        """Downscale large images for analysis stability and re-rendering."""

        height, width = int(bgr.shape[0]), int(bgr.shape[1])
        max_edge = max(height, width)
        if max_edge <= self._max_analysis_edge:
            return bgr

        scale = self._max_analysis_edge / float(max_edge)
        new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
        return cv2.resize(bgr, new_size, interpolation=cv2.INTER_AREA)

    def _build_preview_rgb(self, rgb: np.ndarray) -> np.ndarray:
        """Downscale large images to a UI-friendly size."""

        height, width, _ = rgb.shape
        max_edge = max(height, width)
        if max_edge <= self._max_display_edge:
            return rgb

        scale = self._max_display_edge / float(max_edge)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return cv2.resize(rgb, new_size, interpolation=cv2.INTER_AREA)

    def render_histogram_channels(
        self,
        bgr: np.ndarray,
        channels: list[int],
        hist_size: tuple[int, int] | None = None,
        pixel_ratio: float = 1.0,
    ) -> np.ndarray:
        """Render histogram image for selected BGR channels."""

        geometry = self._resolve_histogram_geometry(hist_size, pixel_ratio)
        hist_img = np.full(
            (geometry.height, geometry.width, 3),
            self._analysis_bg_color_bgr,
            dtype=np.uint8,
        )
        for channel in channels:
            values = bgr[:, :, channel]
            self._draw_histogram(hist_img, values, CHANNEL_COLORS[channel], geometry)
        return cv2.cvtColor(hist_img, cv2.COLOR_BGR2RGB)

    def render_histogram_luma(
        self,
        bgr: np.ndarray,
        hist_size: tuple[int, int] | None = None,
        pixel_ratio: float = 1.0,
    ) -> np.ndarray:
        """Render luminance histogram image."""

        geometry = self._resolve_histogram_geometry(hist_size, pixel_ratio)
        hist_img = np.full(
            (geometry.height, geometry.width, 3),
            self._analysis_bg_color_bgr,
            dtype=np.uint8,
        )
        luma = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        self._draw_histogram(hist_img, luma, LUMA_COLOR, geometry)
        return cv2.cvtColor(hist_img, cv2.COLOR_BGR2RGB)

    def _resolve_histogram_geometry(
        self,
        hist_size: tuple[int, int] | None,
        pixel_ratio: float,
    ) -> HistogramGeometry:
        """Resolve histogram geometry using defaults and DPR."""

        if hist_size is None:
            hist_height, hist_width = self._hist_height, self._hist_width
        else:
            hist_height, hist_width = hist_size
        hist_height = max(1, int(hist_height))
        hist_width = max(1, int(hist_width))
        dpr = max(1.0, float(pixel_ratio))
        thickness = max(1, int(round(dpr)))
        return HistogramGeometry(height=hist_height, width=hist_width, thickness=thickness)

    def _draw_histogram(
        self,
        hist_img: np.ndarray,
        values: np.ndarray,
        color: tuple[int, int, int],
        geometry: HistogramGeometry,
    ) -> None:
        """Draw a histogram curve on the given canvas."""

        hist = cv2.calcHist([values], [0], None, [geometry.width], [0, 256])
        cv2.normalize(hist, hist, 0, geometry.height - 1, cv2.NORM_MINMAX)
        hist = hist.flatten().astype(np.int32)
        for x in range(1, geometry.width):
            y1 = geometry.height - 1 - hist[x - 1]
            y2 = geometry.height - 1 - hist[x]
            cv2.line(
                hist_img,
                (x - 1, y1),
                (x, y2),
                color,
                geometry.thickness,
                lineType=cv2.LINE_AA,
            )

    def render_waveform_channels(
        self,
        bgr: np.ndarray,
        channels: list[int],
        wave_size: tuple[int, int] | None = None,
        pixel_ratio: float = 1.0,
    ) -> np.ndarray:
        """Render waveform image for selected BGR channels."""

        geometry = self._resolve_waveform_geometry(wave_size, pixel_ratio)
        resized = self._resize_for_waveform(bgr, geometry.plot_width)
        wave = np.zeros((geometry.height, geometry.width, 3), dtype=np.float32)
        xs = np.repeat(np.arange(geometry.plot_width), resized.shape[0]) + geometry.axis_margin
        for channel in channels:
            values = resized[:, :, channel].astype(np.int32)
            ys = geometry.height - 1 - (values * (geometry.height - 1) // 255)
            ys_flat = ys.T.reshape(-1)
            np.add.at(wave[:, :, channel], (ys_flat, xs), 1.0)
        return self._normalize_waveform_color(wave, geometry)

    def render_waveform_luma(
        self,
        bgr: np.ndarray,
        wave_size: tuple[int, int] | None = None,
        pixel_ratio: float = 1.0,
    ) -> np.ndarray:
        """Render luminance waveform image."""

        geometry = self._resolve_waveform_geometry(wave_size, pixel_ratio)
        luma = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        resized = self._resize_for_waveform(luma, geometry.plot_width)
        wave = np.zeros((geometry.height, geometry.width), dtype=np.float32)
        xs = np.repeat(np.arange(geometry.plot_width), resized.shape[0]) + geometry.axis_margin
        values = resized.astype(np.int32)
        ys = geometry.height - 1 - (values * (geometry.height - 1) // 255)
        ys_flat = ys.T.reshape(-1)
        np.add.at(wave, (ys_flat, xs), 1.0)
        return self._normalize_waveform_gray(wave, geometry)

    def _resolve_waveform_geometry(
        self,
        wave_size: tuple[int, int] | None,
        pixel_ratio: float,
    ) -> WaveformGeometry:
        """Resolve waveform geometry using defaults and DPR."""

        if wave_size is None:
            wave_height, wave_width = self._wave_height, self._wave_width
        else:
            wave_height, wave_width = wave_size
        wave_height = max(1, int(wave_height))
        wave_width = max(1, int(wave_width))

        dpr = max(1.0, float(pixel_ratio))
        axis_margin = int(round(self._wave_axis_margin_base * dpr))
        axis_margin = min(wave_width - 1, max(0, axis_margin)) if wave_width > 1 else 0
        plot_width = max(1, wave_width - axis_margin)

        axis_text_x = max(1, int(round(self._wave_axis_text_x_base * dpr)))
        axis_font_scale = max(0.1, self._wave_axis_font_scale_base * dpr)
        axis_thickness = max(1, int(round(self._wave_axis_thickness_base * dpr)))
        if self._wave_axis_tick_length_base > 0:
            axis_tick_length = int(round(self._wave_axis_tick_length_base * dpr))
        else:
            axis_tick_length = self._wave_axis_tick_length_base

        return WaveformGeometry(
            height=wave_height,
            width=wave_width,
            axis_margin=axis_margin,
            plot_width=plot_width,
            axis_text_x=axis_text_x,
            axis_font_scale=axis_font_scale,
            axis_thickness=axis_thickness,
            axis_tick_length=axis_tick_length,
        )

    def _resize_for_waveform(self, image: np.ndarray, plot_width: int) -> np.ndarray:
        """Resize image to waveform plot width while preserving aspect ratio."""

        height = max(1, image.shape[0] * plot_width // max(1, image.shape[1]))
        return cv2.resize(image, (plot_width, height), interpolation=cv2.INTER_AREA)

    def _normalize_single_wave(self, wave: np.ndarray) -> np.ndarray:
        """Apply percentile-based scaling and tone boost to a single-channel wave."""

        if not np.any(wave):
            return np.zeros_like(wave, dtype=np.uint8)

        nonzero = wave[wave > 0]
        clip_value = (
            float(np.percentile(nonzero, self._wave_intensity_percentile))
            if nonzero.size > 0
            else float(wave.max())
        )
        clip_value = clip_value if clip_value > 0 else float(wave.max())
        if clip_value <= 0:
            return np.zeros_like(wave, dtype=np.uint8)

        scaled = np.clip(wave / clip_value, 0.0, 1.0)
        boosted = np.log1p(scaled * self._wave_log_gain) / np.log1p(self._wave_log_gain)
        boosted = np.power(boosted, self._wave_gamma)
        if self._wave_blur_sigma > 0:
            boosted = cv2.GaussianBlur(
                boosted, (0, 0), self._wave_blur_sigma, borderType=cv2.BORDER_REPLICATE
            )

        return np.clip(boosted * 255.0, 0, 255).astype(np.uint8)

    def _normalize_waveform_color(self, wave: np.ndarray, geometry: WaveformGeometry) -> np.ndarray:
        """Normalize a multi-channel waveform into an RGB image."""

        normalized_channels = [
            self._normalize_single_wave(wave[:, :, idx]) for idx in range(wave.shape[2])
        ]
        stacked_bgr = np.stack(normalized_channels, axis=2)
        stacked_bgr = cv2.add(stacked_bgr, self._analysis_bg_color_bgr)
        self._apply_waveform_axis(stacked_bgr, geometry)
        return cv2.cvtColor(stacked_bgr, cv2.COLOR_BGR2RGB)

    def _normalize_waveform_gray(self, wave: np.ndarray, geometry: WaveformGeometry) -> np.ndarray:
        """Normalize a grayscale waveform into an RGB image."""

        normalized = self._normalize_single_wave(wave)
        stacked_bgr = np.repeat(normalized[:, :, None], 3, axis=2)
        stacked_bgr = cv2.add(stacked_bgr, self._analysis_bg_color_bgr)
        self._apply_waveform_axis(stacked_bgr, geometry)
        return cv2.cvtColor(stacked_bgr, cv2.COLOR_BGR2RGB)

    def _exposure_to_y(self, exposure_value: int, wave_height: int) -> int:
        """Map an exposure value in [0, 100] to a waveform Y coordinate."""

        clamped = min(100, max(0, exposure_value))
        return int(round((1.0 - clamped / 100.0) * (wave_height - 1)))

    def _apply_waveform_axis(self, canvas_bgr: np.ndarray, geometry: WaveformGeometry) -> None:
        """Draw the exposure axis with yellow labels and tick marks."""

        height, width, _ = canvas_bgr.shape
        axis_x = min(width - 1, max(0, geometry.axis_margin - 1))
        axis_color = self._wave_axis_color_bgr

        cv2.line(
            canvas_bgr,
            (axis_x, 0),
            (axis_x, height - 1),
            axis_color,
            geometry.axis_thickness,
            lineType=cv2.LINE_8,
        )

        for exposure_value in self._wave_axis_labels:
            y = self._exposure_to_y(exposure_value, height)

            if exposure_value in self._wave_axis_ticks:
                if geometry.axis_tick_length <= 0:
                    tick_start_x = axis_x
                    tick_end_x = width - 1
                else:
                    tick_start_x = axis_x
                    tick_end_x = min(width - 1, axis_x + geometry.axis_tick_length)
                cv2.line(
                    canvas_bgr,
                    (tick_start_x, y),
                    (tick_end_x, y),
                    axis_color,
                    geometry.axis_thickness,
                    lineType=cv2.LINE_8,
                )

            label = str(exposure_value)
            (text_w, text_h), baseline = cv2.getTextSize(
                label,
                cv2.FONT_HERSHEY_SIMPLEX,
                geometry.axis_font_scale,
                geometry.axis_thickness,
            )
            baseline_y = y + text_h // 2
            baseline_y = max(text_h + 2, min(height - baseline - 2, baseline_y))
            if exposure_value in self._wave_axis_ticks:
                baseline_y = min(height - baseline - 2, baseline_y + max(4, text_h // 2))
            text_x = min(width - text_w, axis_x + geometry.axis_thickness + geometry.axis_text_x)
            cv2.putText(
                canvas_bgr,
                label,
                (text_x, baseline_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                geometry.axis_font_scale,
                axis_color,
                geometry.axis_thickness,
                lineType=cv2.LINE_AA,
            )
