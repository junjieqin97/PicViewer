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
WAVE_INTENSITY_PERCENTILE = 99.5
WAVE_LOG_GAIN = 6.0
WAVE_GAMMA = 0.7
WAVE_BLUR_SIGMA = 0.8
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


class ImageAnalyzer:
    """Compute histogram and waveform images for a given image."""

    def __init__(
        self,
        hist_size: tuple[int, int] = DEFAULT_HIST_SIZE,
        wave_size: tuple[int, int] = DEFAULT_WAVE_SIZE,
        max_display_edge: int = 2048,
    ) -> None:
        """Create analyzer with configurable output resolutions.

        Args:
            hist_size: (height, width) for histogram canvases.
            wave_size: (height, width) for waveform canvases.
            max_display_edge: Max edge length for preview_rgb to avoid UI卡顿.
        """

        self._hist_height, self._hist_width = hist_size
        self._wave_height, self._wave_width = wave_size
        self._max_display_edge = max_display_edge
        self._wave_intensity_percentile = WAVE_INTENSITY_PERCENTILE
        self._wave_log_gain = WAVE_LOG_GAIN
        self._wave_gamma = WAVE_GAMMA
        self._wave_blur_sigma = WAVE_BLUR_SIGMA

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
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            source_size = (rgb.shape[0], rgb.shape[1])
            preview_rgb = self._build_preview_rgb(rgb)
            histogram_rgb = self._render_histogram_channels(bgr, [0, 1, 2])
            histogram_luma = self._render_histogram_luma(bgr)
            histogram_b = self._render_histogram_channels(bgr, [0])
            histogram_g = self._render_histogram_channels(bgr, [1])
            histogram_r = self._render_histogram_channels(bgr, [2])
            waveform_rgb = self._render_waveform_channels(bgr, [0, 1, 2])
            waveform_luma = self._render_waveform_luma(bgr)
            waveform_b = self._render_waveform_channels(bgr, [0])
            waveform_g = self._render_waveform_channels(bgr, [1])
            waveform_r = self._render_waveform_channels(bgr, [2])
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("图像分析失败")
            raise ImageProcessError("图像分析失败") from exc

        return AnalysisResult(
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

    def _build_preview_rgb(self, rgb: np.ndarray) -> np.ndarray:
        """Downscale large images to a UI-friendly size."""

        height, width, _ = rgb.shape
        max_edge = max(height, width)
        if max_edge <= self._max_display_edge:
            return rgb

        scale = self._max_display_edge / float(max_edge)
        new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
        return cv2.resize(rgb, new_size, interpolation=cv2.INTER_AREA)

    def _draw_histogram(
        self,
        hist_img: np.ndarray,
        values: np.ndarray,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a histogram curve on the given canvas."""

        hist = cv2.calcHist([values], [0], None, [self._hist_width], [0, 256])
        cv2.normalize(hist, hist, 0, self._hist_height - 1, cv2.NORM_MINMAX)
        hist = hist.flatten().astype(np.int32)
        for x in range(1, self._hist_width):
            y1 = self._hist_height - 1 - hist[x - 1]
            y2 = self._hist_height - 1 - hist[x]
            cv2.line(hist_img, (x - 1, y1), (x, y2), color, 1, lineType=cv2.LINE_AA)

    def _render_histogram_channels(self, bgr: np.ndarray, channels: list[int]) -> np.ndarray:
        """Render histogram image for selected BGR channels."""

        hist_img = np.zeros((self._hist_height, self._hist_width, 3), dtype=np.uint8)
        for channel in channels:
            values = bgr[:, :, channel]
            self._draw_histogram(hist_img, values, CHANNEL_COLORS[channel])
        return cv2.cvtColor(hist_img, cv2.COLOR_BGR2RGB)

    def _render_histogram_luma(self, bgr: np.ndarray) -> np.ndarray:
        """Render luminance histogram image."""

        hist_img = np.zeros((self._hist_height, self._hist_width, 3), dtype=np.uint8)
        luma = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        self._draw_histogram(hist_img, luma, LUMA_COLOR)
        return cv2.cvtColor(hist_img, cv2.COLOR_BGR2RGB)

    def _render_waveform_channels(self, bgr: np.ndarray, channels: list[int]) -> np.ndarray:
        """Render waveform image for selected BGR channels."""

        resized = self._resize_for_waveform(bgr)
        wave = np.zeros((self._wave_height, self._wave_width, 3), dtype=np.float32)
        xs = np.repeat(np.arange(self._wave_width), resized.shape[0])
        for channel in channels:
            values = resized[:, :, channel].astype(np.int32)
            ys = self._wave_height - 1 - (values * (self._wave_height - 1) // 255)
            ys_flat = ys.T.reshape(-1)
            np.add.at(wave[:, :, channel], (ys_flat, xs), 1.0)
        return self._normalize_waveform_color(wave)

    def _render_waveform_luma(self, bgr: np.ndarray) -> np.ndarray:
        """Render luminance waveform image."""

        luma = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        resized = self._resize_for_waveform(luma)
        wave = np.zeros((self._wave_height, self._wave_width), dtype=np.float32)
        xs = np.repeat(np.arange(self._wave_width), resized.shape[0])
        values = resized.astype(np.int32)
        ys = self._wave_height - 1 - (values * (self._wave_height - 1) // 255)
        ys_flat = ys.T.reshape(-1)
        np.add.at(wave, (ys_flat, xs), 1.0)
        return self._normalize_waveform_gray(wave)

    def _resize_for_waveform(self, image: np.ndarray) -> np.ndarray:
        """Resize image to waveform width while preserving aspect ratio."""

        height = max(1, image.shape[0] * self._wave_width // max(1, image.shape[1]))
        return cv2.resize(image, (self._wave_width, height), interpolation=cv2.INTER_AREA)

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

    def _normalize_waveform_color(self, wave: np.ndarray) -> np.ndarray:
        """Normalize a multi-channel waveform into an RGB image."""

        normalized_channels = [
            self._normalize_single_wave(wave[:, :, idx]) for idx in range(wave.shape[2])
        ]
        stacked = np.stack(normalized_channels, axis=2)
        return cv2.cvtColor(stacked, cv2.COLOR_BGR2RGB)

    def _normalize_waveform_gray(self, wave: np.ndarray) -> np.ndarray:
        """Normalize a grayscale waveform into an RGB image."""

        normalized = self._normalize_single_wave(wave)
        return np.repeat(normalized[:, :, None], 3, axis=2)
