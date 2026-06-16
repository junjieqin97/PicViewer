"""Focus peaking pseudo-color overlay utilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from pic_viewer.domain.models.bit_depth import ChannelBitDepth


class FocusPeakLevel(Enum):
    """Sensitivity levels for focus peaking overlays."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class FocusPeakingOptions:
    """Options for focus peaking pseudo-color overlays.

    Attributes:
        level: Sensitivity level. HIGH marks more pixels; LOW marks only the strongest peaks.
        overlay_alpha: Blend factor in range [0, 1].
        peak_color_rgb: Overlay color for focus peak pixels.
    """

    level: FocusPeakLevel
    overlay_alpha: float = 0.65
    peak_color_rgb: tuple[int, int, int] = (0, 0, 255)


_EDGE_THRESHOLDS_BY_LEVEL = {
    FocusPeakLevel.HIGH: 32.0,
    FocusPeakLevel.MEDIUM: 72.0,
    FocusPeakLevel.LOW: 128.0,
}


def apply_focus_peaking_overlay(rgb: np.ndarray, options: FocusPeakingOptions) -> np.ndarray:
    """Apply blue focus peaking pseudo-color overlays on an RGB image.

    Args:
        rgb: Input RGB image with shape ``(H, W, 3)``.
        options: Overlay behavior options.

    Returns:
        A new RGB image with focus peak pixels highlighted.

    Raises:
        ValueError: If input image shape or options are invalid.
    """

    _validate_image(rgb)
    _validate_options(options)

    output = rgb.copy()
    peak_mask = build_focus_peak_mask(rgb, options)
    _blend_mask(
        output,
        peak_mask,
        color_rgb=options.peak_color_rgb,
        alpha=options.overlay_alpha,
    )
    return output


def build_focus_peak_mask(rgb: np.ndarray, options: FocusPeakingOptions) -> np.ndarray:
    """Build a boolean focus peak mask from luminance edge strength."""

    _validate_image(rgb)
    _validate_options(options)

    luma = _compute_luma(rgb)
    edge_strength = _compute_edge_strength(luma)
    max_value = ChannelBitDepth.from_dtype(rgb.dtype).max_value
    threshold = _EDGE_THRESHOLDS_BY_LEVEL[options.level] * (max_value / 255.0)
    return edge_strength >= threshold


def _validate_image(rgb: np.ndarray) -> None:
    """Validate RGB image shape."""

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must have shape (H, W, 3)")
    if rgb.dtype not in (np.dtype(np.uint8), np.dtype(np.uint16)):
        raise ValueError("rgb must use uint8 or uint16 channels")


def _validate_options(options: FocusPeakingOptions) -> None:
    """Validate focus peaking options."""

    if not isinstance(options.level, FocusPeakLevel):
        raise ValueError("level must be a FocusPeakLevel")
    if options.overlay_alpha < 0.0 or options.overlay_alpha > 1.0:
        raise ValueError("overlay_alpha must be in [0, 1]")


def _compute_luma(rgb: np.ndarray) -> np.ndarray:
    """Compute luminance from RGB image."""

    rgb32 = rgb.astype(np.float32)
    return (0.299 * rgb32[:, :, 0]) + (0.587 * rgb32[:, :, 1]) + (0.114 * rgb32[:, :, 2])


def _compute_edge_strength(luma: np.ndarray) -> np.ndarray:
    """Compute Sobel edge magnitude for focus peak detection."""

    grad_x = cv2.Sobel(luma, cv2.CV_32F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(luma, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(grad_x, grad_y)


def _blend_mask(
    output: np.ndarray,
    mask: np.ndarray,
    color_rgb: tuple[int, int, int],
    alpha: float,
) -> None:
    """Alpha blend a single pseudo-color over masked pixels in-place."""

    if not np.any(mask):
        return

    max_value = ChannelBitDepth.from_dtype(output.dtype).max_value
    scale = max_value / 255.0
    color = np.asarray(color_rgb, dtype=np.float32) * scale
    source = output[mask].astype(np.float32)
    blended = np.rint((1.0 - alpha) * source + (alpha * color))
    output[mask] = np.clip(blended, 0, max_value).astype(output.dtype)
