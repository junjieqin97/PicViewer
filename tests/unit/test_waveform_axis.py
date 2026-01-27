from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.rules.analysis import (  # noqa: E402
    ImageAnalyzer,
    WAVE_AXIS_LABELS,
    WAVE_AXIS_MARGIN,
    WAVE_AXIS_TICKS,
)


def exposure_to_y(exposure_value: int, height: int) -> int:
    """Map exposure percentage to waveform Y coordinate."""

    clamped = min(100, max(0, exposure_value))
    return int(round((1.0 - clamped / 100.0) * (height - 1)))


def is_yellow_rgb(pixel: np.ndarray) -> bool:
    """Heuristic check for yellow pixels in RGB space."""

    red, green, blue = (int(pixel[0]), int(pixel[1]), int(pixel[2]))
    return red >= 150 and green >= 150 and blue <= 120


def has_yellow_left_of_axis(image: np.ndarray, y_center: int, axis_x: int) -> bool:
    """Check for yellow pixels left of the axis near the expected label row."""

    height = image.shape[0]
    y_min = max(0, y_center - 8)
    y_max = min(height - 1, y_center + 8)
    label_x_end = max(0, axis_x - 3)
    region = image[y_min : y_max + 1, : label_x_end + 1]
    mask = (region[:, :, 0] >= 150) & (region[:, :, 1] >= 150) & (region[:, :, 2] <= 120)
    return bool(mask.any())


@unittest.skip("waveform axis implementation pending")
class WaveformAxisTests(unittest.TestCase):
    """Validate exposure axis rendering on waveform previews."""

    def setUp(self) -> None:
        # Use a deterministic gradient image to generate a stable waveform.
        gradient = np.linspace(0, 255, 64, dtype=np.uint8).reshape(8, 8)
        self.image_bgr = np.dstack([gradient, gradient, gradient])
        self.analyzer = ImageAnalyzer()

    def test_waveform_axis_ticks_are_yellow(self) -> None:
        """Tick marks for 20/40/60/80 should be drawn in yellow."""

        waveform = self.analyzer.analyze(self.image_bgr).waveform_luma
        height, width, _ = waveform.shape
        axis_x = min(width - 1, max(0, WAVE_AXIS_MARGIN - 1))
        sample_x = min(width - 1, axis_x + 3)

        for exposure_value in WAVE_AXIS_TICKS:
            y = exposure_to_y(exposure_value, height)
            self.assertTrue(
                is_yellow_rgb(waveform[y, sample_x]),
                msg=f"Expected yellow tick at exposure={exposure_value}, y={y}",
            )

    def test_waveform_axis_labels_exist_left_of_axis(self) -> None:
        """All exposure labels should appear on the left side of the axis."""

        waveform = self.analyzer.analyze(self.image_bgr).waveform_luma
        height, width, _ = waveform.shape
        axis_x = min(width - 1, max(0, WAVE_AXIS_MARGIN - 1))

        for exposure_value in WAVE_AXIS_LABELS:
            y = exposure_to_y(exposure_value, height)
            self.assertTrue(
                has_yellow_left_of_axis(waveform, y, axis_x),
                msg=f"Expected yellow label near exposure={exposure_value}, y={y}",
            )


if __name__ == "__main__":
    unittest.main()
