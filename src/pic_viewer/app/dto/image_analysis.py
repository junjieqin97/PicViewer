"""DTOs for transferring image analysis results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

from pic_viewer.app.dto.metadata import ImageMetadata


@dataclass(frozen=True)
class ImageAnalysis:
    """Image analysis output for UI layer.

    Attributes:
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
    """

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


@dataclass(frozen=True)
class ImageLoadResult:
    """Aggregated image payload for UI consumption."""

    analysis: ImageAnalysis
    metadata: ImageMetadata
