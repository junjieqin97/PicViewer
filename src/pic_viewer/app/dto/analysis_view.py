"""DTOs for selecting analysis preview images."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class LumaRgbMode(Enum):
    """Histogram/waveform display mode."""

    LUMA = "luma"
    RGB = "rgb"


class RgbChannel(Enum):
    """RGB channel selection within RGB mode."""

    ALL = "all"
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@dataclass(frozen=True)
class AnalysisViewSettings:
    """Current view settings for histogram and waveform previews."""

    mode: LumaRgbMode
    channel: RgbChannel


@dataclass(frozen=True)
class AnalysisView:
    """Selected preview images for display."""

    histogram_rgb: np.ndarray
    waveform_rgb: np.ndarray
