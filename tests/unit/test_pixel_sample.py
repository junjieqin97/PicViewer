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

from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402


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

    def test_sample_analysis_pixel_preserves_sixteen_bit_channel_values(self) -> None:
        module = self._pixel_sample_module()
        bgr = np.array([[[1000, 32000, 65000]]], dtype=np.uint16)
        expected_luma = int(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)[0, 0])

        sample = module.sample_analysis_pixel(bgr, 0, 0)

        self.assertEqual(65000, sample.red)
        self.assertEqual(32000, sample.green)
        self.assertEqual(1000, sample.blue)
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

    def test_color_readout_formats_hsb_and_hsl_values(self) -> None:
        module = self._pixel_sample_module()
        readout = module.ColorReadout(
            readout_id=7,
            x=12,
            y=34,
            sample=module.PixelSample(red=0, green=128, blue=255, luma=105),
        )

        self.assertEqual(
            ("H 210°", "S 100%", "B 100%"),
            readout.display_values(module.ColorReadoutType.HSB),
        )
        self.assertEqual(
            ("H 210°", "S 100%", "L 50%"),
            readout.display_values(module.ColorReadoutType.HSL),
        )

    def test_color_readout_hsb_and_hsl_cover_primary_and_achromatic_boundaries(self) -> None:
        module = self._pixel_sample_module()
        cases = (
            (
                module.PixelSample(255, 0, 0, 76),
                ("H 0°", "S 100%", "B 100%"),
                ("H 0°", "S 100%", "L 50%"),
            ),
            (
                module.PixelSample(0, 255, 0, 150),
                ("H 120°", "S 100%", "B 100%"),
                ("H 120°", "S 100%", "L 50%"),
            ),
            (
                module.PixelSample(0, 0, 255, 29),
                ("H 240°", "S 100%", "B 100%"),
                ("H 240°", "S 100%", "L 50%"),
            ),
            (
                module.PixelSample(0, 0, 0, 0),
                ("H 0°", "S 0%", "B 0%"),
                ("H 0°", "S 0%", "L 0%"),
            ),
            (
                module.PixelSample(255, 255, 255, 255),
                ("H 0°", "S 0%", "B 100%"),
                ("H 0°", "S 0%", "L 100%"),
            ),
            (
                module.PixelSample(128, 128, 128, 128),
                ("H 0°", "S 0%", "B 50%"),
                ("H 0°", "S 0%", "L 50%"),
            ),
        )

        for sample, expected_hsb, expected_hsl in cases:
            with self.subTest(sample=sample):
                readout = module.ColorReadout(1, 0, 0, sample)
                self.assertEqual(
                    expected_hsb,
                    readout.display_values(module.ColorReadoutType.HSB),
                )
                self.assertEqual(
                    expected_hsl,
                    readout.display_values(module.ColorReadoutType.HSL),
                )

    def test_color_readout_normalizes_hsb_and_hsl_using_sample_bit_depth(self) -> None:
        module = self._pixel_sample_module()
        eight_bit = module.ColorReadout(
            1,
            0,
            0,
            module.PixelSample(255, 128, 0, 151),
            ChannelBitDepth.EIGHT,
        )
        sixteen_bit = module.ColorReadout(
            2,
            0,
            0,
            module.PixelSample(65535, 32896, 0, 38807),
            ChannelBitDepth.SIXTEEN,
        )

        self.assertEqual(
            eight_bit.display_values(module.ColorReadoutType.HSB),
            sixteen_bit.display_values(module.ColorReadoutType.HSB),
        )
        self.assertEqual(
            eight_bit.display_values(module.ColorReadoutType.HSL),
            sixteen_bit.display_values(module.ColorReadoutType.HSL),
        )


if __name__ == "__main__":
    unittest.main()
