"""DTOs for transferring image analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from pic_viewer.app.dto.metadata import ImageMetadata
from pic_viewer.domain.models.bit_depth import ChannelBitDepth
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    DEFAULT_DISPLAY_COLOR_SPACE,
    ColorProfileSpec,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent

DEFAULT_SOURCE_COLOR_PROFILE = ImageColorProfileInfo(
    display_name="sRGB",
    status=ImageColorProfileStatus.MISSING,
    uses_srgb_fallback=True,
    assumed_color_space=DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
)


@dataclass(frozen=True)
class ImageAnalysis:
    """Image analysis output for UI layer.

    Attributes:
        analysis_bgr: Downscaled BGR source for analysis re-rendering.
        preview_rgb: Downscaled RGB image for display.
        source_size: Original image size as (height, width).
        histogram_rgb: Combined RGB histogram plot.
        histogram_luma: Luma histogram plot.
        histogram_r: Red channel histogram plot.
        histogram_g: Green channel histogram plot.
        histogram_b: Blue channel histogram plot.
        waveform_rgb: Combined RGB waveform plot.
        waveform_luma: Luma waveform plot.
        waveform_r: Red channel waveform plot.
        waveform_g: Green channel waveform plot.
        waveform_b: Blue channel waveform plot.
        display_color_space: Color space used for analysis data.
        assumed_source_color_space: Fallback source color space used when ICC is unavailable.
        rendering_intent: ICC rendering intent used for gamut mapping.
        source_color_profile: Source ICC profile status used for decoding.
        cms_bit_depth: Bit depth used by CMS output/display source.
        analysis_bit_depth: Actual bit depth used by analysis sampling.
    """

    analysis_bgr: np.ndarray
    preview_rgb: np.ndarray
    source_size: Tuple[int, int]
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
    display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE
    assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE
    rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT
    source_color_profile: ImageColorProfileInfo = DEFAULT_SOURCE_COLOR_PROFILE
    cms_bit_depth: ChannelBitDepth = ChannelBitDepth.EIGHT
    analysis_bit_depth: ChannelBitDepth = ChannelBitDepth.EIGHT


@dataclass(frozen=True)
class ImageLoadResult:
    """Aggregated image payload for UI consumption."""

    analysis: ImageAnalysis
    metadata: ImageMetadata


@dataclass(frozen=True)
class PreviewLoadResult:
    """Fast preview payload used for incremental loading."""

    preview_rgb: np.ndarray
    display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE
    assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE
    rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT
    source_color_profile: ImageColorProfileInfo = DEFAULT_SOURCE_COLOR_PROFILE
    cms_bit_depth: ChannelBitDepth = ChannelBitDepth.EIGHT
