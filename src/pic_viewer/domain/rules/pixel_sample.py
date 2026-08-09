"""Pixel sampling helpers for analysis-space image data."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np

from pic_viewer.domain.models.bit_depth import ChannelBitDepth


class ColorReadoutType(str, Enum):
    """Supported fixed color readout display formats."""

    RGBL = "rgbl"
    HSB = "hsb"
    HSL = "hsl"


DEFAULT_COLOR_READOUT_TYPE = ColorReadoutType.RGBL


@dataclass(frozen=True)
class PixelSample:
    """RGB and luma values sampled from one analysis pixel."""

    red: int
    green: int
    blue: int
    luma: int


@dataclass(frozen=True)
class ColorReadout:
    """Persistent color readout anchored to one analysis-space pixel."""

    readout_id: int
    x: int
    y: int
    sample: PixelSample
    bit_depth: ChannelBitDepth = ChannelBitDepth.EIGHT

    def display_values(
        self,
        readout_type: ColorReadoutType = DEFAULT_COLOR_READOUT_TYPE,
    ) -> tuple[str, ...]:
        """Return values formatted for the selected color readout type."""

        if readout_type is ColorReadoutType.HSB:
            hue, saturation, brightness = self._hsb_values()
            return (f"H {hue}°", f"S {saturation}%", f"B {brightness}%")
        if readout_type is ColorReadoutType.HSL:
            hue, saturation, lightness = self._hsl_values()
            return (f"H {hue}°", f"S {saturation}%", f"L {lightness}%")
        return (
            str(self.sample.red),
            str(self.sample.green),
            str(self.sample.blue),
            str(self.sample.luma),
        )

    def display_text(
        self,
        readout_type: ColorReadoutType = DEFAULT_COLOR_READOUT_TYPE,
    ) -> str:
        """Return the fixed user-visible readout text."""

        return "  ".join(self.display_values(readout_type))

    def _normalized_rgb(self) -> tuple[float, float, float]:
        maximum = self.bit_depth.max_value
        return (
            _clamp_unit(self.sample.red / maximum),
            _clamp_unit(self.sample.green / maximum),
            _clamp_unit(self.sample.blue / maximum),
        )

    def _hsb_values(self) -> tuple[int, int, int]:
        hue, saturation, brightness = colorsys.rgb_to_hsv(*self._normalized_rgb())
        return (_round_hue(hue), _round_percentage(saturation), _round_percentage(brightness))

    def _hsl_values(self) -> tuple[int, int, int]:
        hue, lightness, saturation = colorsys.rgb_to_hls(*self._normalized_rgb())
        return (_round_hue(hue), _round_percentage(saturation), _round_percentage(lightness))


def _clamp_unit(value: float) -> float:
    return min(1.0, max(0.0, value))


def _round_hue(value: float) -> int:
    return int(value * 360.0 + 0.5) % 360


def _round_percentage(value: float) -> int:
    return min(100, max(0, int(value * 100.0 + 0.5)))


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
