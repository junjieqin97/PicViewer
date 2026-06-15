"""Pixel sampling helpers for analysis-space image data."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class PixelSample:
    """RGB and luma values sampled from one analysis pixel."""

    red: int
    green: int
    blue: int
    luma: int


@dataclass(frozen=True)
class ColorReadout:
    """Persistent RGB/luma readout anchored to one analysis-space pixel."""

    readout_id: int
    x: int
    y: int
    sample: PixelSample

    def display_values(self) -> tuple[str, str, str, str]:
        """Return RGB and luma values as four display-ready numbers."""

        return (
            str(self.sample.red),
            str(self.sample.green),
            str(self.sample.blue),
            str(self.sample.luma),
        )

    def display_text(self) -> str:
        """Return the fixed user-visible numeric readout text."""

        return "  ".join(self.display_values())


INVALID_PIXEL_SAMPLE = PixelSample(red=-1, green=-1, blue=-1, luma=-1)


def sample_analysis_pixel(analysis_bgr: np.ndarray, x: int, y: int) -> PixelSample:
    """Return RGB and luma values for one BGR analysis-space pixel.

    Args:
        analysis_bgr: Analysis image data in BGR channel order.
        x: Pixel x-coordinate in analysis image space.
        y: Pixel y-coordinate in analysis image space.

    Returns:
        PixelSample: RGB values plus luma, or INVALID_PIXEL_SAMPLE when the
        source image or coordinates are invalid.
    """

    if not isinstance(analysis_bgr, np.ndarray):
        return INVALID_PIXEL_SAMPLE
    if analysis_bgr.ndim != 3 or analysis_bgr.shape[2] != 3:
        return INVALID_PIXEL_SAMPLE
    height, width, _channels = analysis_bgr.shape
    if height <= 0 or width <= 0:
        return INVALID_PIXEL_SAMPLE
    if x < 0 or y < 0 or x >= width or y >= height:
        return INVALID_PIXEL_SAMPLE

    pixel = analysis_bgr[y : y + 1, x : x + 1]
    blue, green, red = (int(value) for value in pixel[0, 0])
    luma = int(cv2.cvtColor(pixel, cv2.COLOR_BGR2GRAY)[0, 0])
    return PixelSample(red=red, green=green, blue=blue, luma=luma)
