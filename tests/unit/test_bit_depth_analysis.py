from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402
from pic_viewer.domain.rules.analysis import ImageAnalyzer  # noqa: E402


class BitDepthAnalysisTests(unittest.TestCase):
    """Validate analysis sampling precision behavior."""

    def test_default_analysis_sampling_downcasts_sixteen_bit_display_source_to_eight_bit(self) -> None:
        analyzer = ImageAnalyzer(hist_size=(32, 64), wave_size=(32, 64))
        bgr = np.array(
            [
                [[0, 32768, 65535], [65535, 32768, 0]],
                [[1024, 2048, 4096], [65000, 64000, 63000]],
            ],
            dtype=np.uint16,
        )

        result = analyzer.analyze(bgr)

        self.assertEqual(np.uint16, result.preview_rgb.dtype)
        self.assertEqual(np.uint8, result.analysis_bgr.dtype)
        self.assertEqual(ChannelBitDepth.EIGHT, result.analysis_bit_depth)

    def test_sixteen_bit_analysis_sampling_preserves_available_sixteen_bit_source(self) -> None:
        analyzer = ImageAnalyzer(hist_size=(32, 64), wave_size=(32, 64))
        bgr = np.array(
            [
                [[0, 32768, 65535], [65535, 32768, 0]],
                [[1024, 2048, 4096], [65000, 64000, 63000]],
            ],
            dtype=np.uint16,
        )

        result = analyzer.analyze(bgr, analysis_bit_depth=ChannelBitDepth.SIXTEEN)

        self.assertEqual(np.uint16, result.preview_rgb.dtype)
        self.assertEqual(np.uint16, result.analysis_bgr.dtype)
        self.assertEqual(ChannelBitDepth.SIXTEEN, result.analysis_bit_depth)

    def test_sixteen_bit_sampling_does_not_fake_precision_for_eight_bit_source(self) -> None:
        analyzer = ImageAnalyzer(hist_size=(32, 64), wave_size=(32, 64))
        bgr = np.array([[[0, 128, 255], [255, 128, 0]]], dtype=np.uint8)

        result = analyzer.analyze(bgr, analysis_bit_depth=ChannelBitDepth.SIXTEEN)

        self.assertEqual(np.uint8, result.preview_rgb.dtype)
        self.assertEqual(np.uint8, result.analysis_bgr.dtype)
        self.assertEqual(ChannelBitDepth.EIGHT, result.analysis_bit_depth)


if __name__ == "__main__":
    unittest.main()
