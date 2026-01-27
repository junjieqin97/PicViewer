from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.rules.analysis import ImageAnalyzer, WAVE_AXIS_MARGIN  # noqa: E402


def make_gradient_bgr(size: int = 64) -> np.ndarray:
    """Create a deterministic grayscale gradient BGR image."""

    gradient = np.linspace(0, 255, size * size, dtype=np.uint8).reshape(size, size)
    return np.dstack([gradient, gradient, gradient])


def is_yellow_rgb(pixel: np.ndarray) -> bool:
    """Heuristic check for yellow pixels in RGB space."""

    red, green, blue = (int(pixel[0]), int(pixel[1]), int(pixel[2]))
    return red >= 150 and green >= 150 and blue <= 120


class HighDpiRenderingTests(unittest.TestCase):
    """Validate DPR-aware rendering behavior in the analyzer."""

    def setUp(self) -> None:
        self.image_bgr = make_gradient_bgr(32)
        self.analyzer = ImageAnalyzer()

    def test_render_respects_requested_sizes(self) -> None:
        """Histogram and waveform outputs should match requested sizes."""

        hist_size = (400, 800)
        wave_size = (500, 900)
        histogram = self.analyzer.render_histogram_luma(self.image_bgr, hist_size=hist_size)
        waveform = self.analyzer.render_waveform_luma(self.image_bgr, wave_size=wave_size)

        self.assertEqual(hist_size, histogram.shape[:2])
        self.assertEqual(wave_size, waveform.shape[:2])

    def test_waveform_axis_margin_scales_with_dpr(self) -> None:
        """Axis margin should scale with DPR when rendering to physical pixels."""

        logical_wave_size = (320, 640)
        dpr = 2.0
        physical_wave_size = (
            int(round(logical_wave_size[0] * dpr)),
            int(round(logical_wave_size[1] * dpr)),
        )
        waveform = self.analyzer.render_waveform_luma(
            self.image_bgr,
            wave_size=physical_wave_size,
            pixel_ratio=dpr,
        )

        expected_margin = int(round(WAVE_AXIS_MARGIN * dpr))
        expected_margin = min(waveform.shape[1] - 1, max(0, expected_margin))
        axis_x = min(waveform.shape[1] - 1, max(0, expected_margin - 1))

        self.assertGreaterEqual(axis_x, WAVE_AXIS_MARGIN)
        self.assertTrue(is_yellow_rgb(waveform[waveform.shape[0] // 2, axis_x]))

    def test_analysis_source_and_preview_are_capped(self) -> None:
        """Analysis source and preview sizes should respect configured caps."""

        large_bgr = np.zeros((1000, 800, 3), dtype=np.uint8)
        analyzer = ImageAnalyzer(max_display_edge=400, max_analysis_edge=500)
        result = analyzer.analyze(large_bgr)

        analysis_edge = max(result.analysis_bgr.shape[:2])
        preview_edge = max(result.preview_rgb.shape[:2])

        self.assertLessEqual(analysis_edge, 500)
        self.assertLessEqual(preview_edge, 400)
        self.assertGreaterEqual(analysis_edge, preview_edge)


if __name__ == "__main__":
    unittest.main()
