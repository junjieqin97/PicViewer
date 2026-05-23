from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.rules.exposure_overlay import (  # noqa: E402
    ExposureOverlayOptions,
    apply_exposure_overlay,
)


def blend_rgb(source: tuple[int, int, int], color: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    """Blend RGB tuples with the same rule used in the overlay module."""

    src = np.asarray(source, dtype=np.float32)
    dst = np.asarray(color, dtype=np.float32)
    mixed = np.rint((1.0 - alpha) * src + alpha * dst)
    mixed = np.clip(mixed, 0, 255).astype(np.uint8)
    return int(mixed[0]), int(mixed[1]), int(mixed[2])


class ExposureOverlayTests(unittest.TestCase):
    """Validate under/over exposure pseudo-color overlay behavior."""

    def test_underexposed_overlay_only(self) -> None:
        image = np.array(
            [
                [[0, 0, 0], [6, 6, 6]],
            ],
            dtype=np.uint8,
        )
        options = ExposureOverlayOptions(show_underexposed=True, show_overexposed=False)

        result = apply_exposure_overlay(image, options)

        expected_under = blend_rgb((0, 0, 0), (0, 255, 0), 0.65)
        self.assertTupleEqual(expected_under, tuple(int(v) for v in result[0, 0]))
        self.assertTupleEqual((6, 6, 6), tuple(int(v) for v in result[0, 1]))

    def test_overexposed_overlay_only(self) -> None:
        image = np.array(
            [
                [[249, 249, 249], [255, 255, 255]],
            ],
            dtype=np.uint8,
        )
        options = ExposureOverlayOptions(show_underexposed=False, show_overexposed=True)

        result = apply_exposure_overlay(image, options)

        expected_over = blend_rgb((255, 255, 255), (255, 0, 0), 0.65)
        self.assertTupleEqual((249, 249, 249), tuple(int(v) for v in result[0, 0]))
        self.assertTupleEqual(expected_over, tuple(int(v) for v in result[0, 1]))

    def test_overexposed_overlay_wins_when_masks_overlap(self) -> None:
        image = np.array([[[100, 100, 100]]], dtype=np.uint8)
        options = ExposureOverlayOptions(
            show_underexposed=True,
            show_overexposed=True,
            underexposed_threshold=255,
            overexposed_threshold=0,
        )

        result = apply_exposure_overlay(image, options)

        expected = blend_rgb((100, 100, 100), (0, 255, 0), 0.65)
        expected = blend_rgb(expected, (255, 0, 0), 0.65)
        self.assertTupleEqual(expected, tuple(int(v) for v in result[0, 0]))

    def test_threshold_boundaries(self) -> None:
        image = np.array(
            [
                [[5, 5, 5], [6, 6, 6], [249, 249, 249], [250, 250, 250]],
            ],
            dtype=np.uint8,
        )
        options = ExposureOverlayOptions(show_underexposed=True, show_overexposed=True)

        result = apply_exposure_overlay(image, options)

        expected_under = blend_rgb((5, 5, 5), (0, 255, 0), 0.65)
        expected_over = blend_rgb((250, 250, 250), (255, 0, 0), 0.65)
        self.assertTupleEqual(expected_under, tuple(int(v) for v in result[0, 0]))
        self.assertTupleEqual((6, 6, 6), tuple(int(v) for v in result[0, 1]))
        self.assertTupleEqual((249, 249, 249), tuple(int(v) for v in result[0, 2]))
        self.assertTupleEqual(expected_over, tuple(int(v) for v in result[0, 3]))

    def test_invalid_shape_raises_value_error(self) -> None:
        invalid = np.zeros((8, 8), dtype=np.uint8)
        options = ExposureOverlayOptions(show_underexposed=True)

        with self.assertRaises(ValueError):
            apply_exposure_overlay(invalid, options)


if __name__ == "__main__":
    unittest.main()
