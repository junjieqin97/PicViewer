"""Exposure clipping pseudo-color overlay utilities."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ExposureOverlayOptions:
    """Options for under/over exposure pseudo-color overlays.

    Attributes:
        show_underexposed: Whether to highlight underexposed areas.
        show_overexposed: Whether to highlight overexposed areas.
        underexposed_threshold: Luma threshold for underexposure (inclusive).
        overexposed_threshold: Luma threshold for overexposure (inclusive).
        overlay_alpha: Blend factor in range [0, 1].
        underexposed_color_rgb: Overlay color for underexposed mask.
        overexposed_color_rgb: Overlay color for overexposed mask.
    """

    show_underexposed: bool = False
    show_overexposed: bool = False
    underexposed_threshold: int = 5
    overexposed_threshold: int = 250
    overlay_alpha: float = 0.65
    underexposed_color_rgb: tuple[int, int, int] = (0, 255, 0)
    overexposed_color_rgb: tuple[int, int, int] = (255, 0, 0)


def apply_exposure_overlay(rgb: np.ndarray, options: ExposureOverlayOptions) -> np.ndarray:
    """Apply under/over exposure pseudo-color overlays on an RGB image.

    The overlay order is fixed: underexposed first, then overexposed.
    This ensures overexposed color wins when masks overlap.

    Args:
        rgb: Input RGB image with shape ``(H, W, 3)``.
        options: Overlay behavior options.

    Returns:
        A new RGB image with pseudo-color overlays applied.

    Raises:
        ValueError: If input image shape is invalid.
    """

    _validate_image(rgb)
    _validate_options(options)

    if not options.show_underexposed and not options.show_overexposed:
        return rgb.copy()

    output = rgb.copy()
    luma = _compute_luma(rgb)

    if options.show_underexposed:
        under_mask = luma <= int(options.underexposed_threshold)
        _blend_mask(
            output,
            under_mask,
            color_rgb=options.underexposed_color_rgb,
            alpha=options.overlay_alpha,
        )

    if options.show_overexposed:
        over_mask = luma >= int(options.overexposed_threshold)
        _blend_mask(
            output,
            over_mask,
            color_rgb=options.overexposed_color_rgb,
            alpha=options.overlay_alpha,
        )

    return output


def _validate_image(rgb: np.ndarray) -> None:
    """Validate RGB image shape."""

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("rgb must have shape (H, W, 3)")


def _validate_options(options: ExposureOverlayOptions) -> None:
    """Validate overlay options."""

    if options.overlay_alpha < 0.0 or options.overlay_alpha > 1.0:
        raise ValueError("overlay_alpha must be in [0, 1]")


def _compute_luma(rgb: np.ndarray) -> np.ndarray:
    """Compute luminance from RGB image."""

    rgb32 = rgb.astype(np.float32)
    # ITU-R BT.601 luma weights for RGB input.
    return (0.299 * rgb32[:, :, 0]) + (0.587 * rgb32[:, :, 1]) + (0.114 * rgb32[:, :, 2])


def _blend_mask(
    output: np.ndarray,
    mask: np.ndarray,
    color_rgb: tuple[int, int, int],
    alpha: float,
) -> None:
    """Alpha blend a single pseudo-color over masked pixels in-place."""

    if not np.any(mask):
        return

    color = np.asarray(color_rgb, dtype=np.float32)
    source = output[mask].astype(np.float32)
    blended = np.rint((1.0 - alpha) * source + (alpha * color))
    output[mask] = np.clip(blended, 0, 255).astype(np.uint8)
