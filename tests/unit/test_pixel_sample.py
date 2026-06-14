from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
import unittest

import cv2
import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class PixelSampleTests(unittest.TestCase):
    """Validate RGB and luma sampling from analysis-space pixels."""

    def _pixel_sample_module(self):
        module_name = "pic_viewer.domain.rules.pixel_sample"
        self.assertIsNotNone(
            importlib.util.find_spec(module_name),
            "pixel_sample module should exist",
        )
        return importlib.import_module(module_name)

    def test_sample_analysis_pixel_returns_rgb_and_luma_from_bgr_source(self) -> None:
        module = self._pixel_sample_module()
        bgr = np.array(
            [
                [[10, 20, 30], [40, 50, 60]],
                [[70, 80, 90], [100, 110, 120]],
            ],
            dtype=np.uint8,
        )
        expected_luma = int(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)[1, 0])

        sample = module.sample_analysis_pixel(bgr, 0, 1)

        self.assertEqual(90, sample.red)
        self.assertEqual(80, sample.green)
        self.assertEqual(70, sample.blue)
        self.assertEqual(expected_luma, sample.luma)

    def test_sample_analysis_pixel_returns_invalid_for_out_of_bounds(self) -> None:
        module = self._pixel_sample_module()
        bgr = np.zeros((2, 2, 3), dtype=np.uint8)

        self.assertEqual(module.INVALID_PIXEL_SAMPLE, module.sample_analysis_pixel(bgr, -1, 0))
        self.assertEqual(module.INVALID_PIXEL_SAMPLE, module.sample_analysis_pixel(bgr, 2, 0))
        self.assertEqual(module.INVALID_PIXEL_SAMPLE, module.sample_analysis_pixel(bgr, 0, 2))

    def test_sample_analysis_pixel_returns_invalid_for_bad_input_shape(self) -> None:
        module = self._pixel_sample_module()

        self.assertEqual(
            module.INVALID_PIXEL_SAMPLE,
            module.sample_analysis_pixel(np.zeros((0, 0, 3), dtype=np.uint8), 0, 0),
        )
        self.assertEqual(
            module.INVALID_PIXEL_SAMPLE,
            module.sample_analysis_pixel(np.zeros((2, 2), dtype=np.uint8), 0, 0),
        )
        self.assertEqual(
            module.INVALID_PIXEL_SAMPLE,
            module.sample_analysis_pixel(np.zeros((2, 2, 4), dtype=np.uint8), 0, 0),
        )

    def test_color_readout_formats_only_rgb_and_luma_numbers(self) -> None:
        module = self._pixel_sample_module()

        readout = module.ColorReadout(
            readout_id=7,
            x=12,
            y=34,
            sample=module.PixelSample(red=11, green=22, blue=33, luma=44),
        )

        self.assertEqual(("11", "22", "33", "44"), readout.display_values())
        self.assertEqual("11  22  33  44", readout.display_text())


if __name__ == "__main__":
    unittest.main()
