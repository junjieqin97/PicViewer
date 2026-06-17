from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.rules.focus_peaking import (  # noqa: E402
    FocusPeakLevel,
    FocusPeakingOptions,
    apply_focus_peaking_overlay,
    build_focus_peak_mask,
)


def blend_rgb(source: tuple[int, int, int], color: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    """Blend RGB tuples with the same rule used by pseudo-color overlays."""

    src = np.asarray(source, dtype=np.float32)
    dst = np.asarray(color, dtype=np.float32)
    mixed = np.rint((1.0 - alpha) * src + alpha * dst)
    mixed = np.clip(mixed, 0, 255).astype(np.uint8)
    return int(mixed[0]), int(mixed[1]), int(mixed[2])


def blend_rgb16(source: tuple[int, int, int], color: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    """Blend 16-bit RGB tuples with scaled overlay colors."""

    src = np.asarray(source, dtype=np.float32)
    dst = np.asarray(color, dtype=np.float32)
    mixed = np.rint((1.0 - alpha) * src + alpha * dst)
    mixed = np.clip(mixed, 0, 65535).astype(np.uint16)
    return int(mixed[0]), int(mixed[1]), int(mixed[2])


class FocusPeakingTests(unittest.TestCase):
    """Validate focus peaking pseudo-color overlay behavior."""

    def test_peak_levels_are_ordered_by_sensitivity(self) -> None:
        image = np.zeros((16, 24, 3), dtype=np.uint8)
        image[:, 6:12] = 45
        image[:, 12:18] = 120
        image[:, 18:] = 255

        high = build_focus_peak_mask(image, FocusPeakingOptions(level=FocusPeakLevel.HIGH))
        medium = build_focus_peak_mask(image, FocusPeakingOptions(level=FocusPeakLevel.MEDIUM))
        low = build_focus_peak_mask(image, FocusPeakingOptions(level=FocusPeakLevel.LOW))

        self.assertGreaterEqual(int(high.sum()), int(medium.sum()))
        self.assertGreaterEqual(int(medium.sum()), int(low.sum()))
        self.assertGreater(int(low.sum()), 0)

    def test_blue_overlay_is_applied_to_peak_pixels(self) -> None:
        image = np.zeros((12, 12, 3), dtype=np.uint8)
        image[:, 6:] = 255
        options = FocusPeakingOptions(level=FocusPeakLevel.LOW)

        result = apply_focus_peaking_overlay(image, options)
        mask = build_focus_peak_mask(image, options)
        y, x = np.argwhere(mask)[0]

        expected = blend_rgb(
            tuple(int(v) for v in image[y, x]),
            options.peak_color_rgb,
            options.overlay_alpha,
        )
        self.assertTupleEqual(expected, tuple(int(v) for v in result[y, x]))

    def test_sixteen_bit_peak_threshold_scales_and_overlay_preserves_dtype(self) -> None:
        image = np.zeros((12, 12, 3), dtype=np.uint16)
        image[:, 6:] = 65535
        options = FocusPeakingOptions(level=FocusPeakLevel.LOW)

        result = apply_focus_peaking_overlay(image, options)
        mask = build_focus_peak_mask(image, options)
        y, x = np.argwhere(mask)[0]

        self.assertEqual(np.uint16, result.dtype)
        expected = blend_rgb16(
            tuple(int(v) for v in image[y, x]),
            (0, 0, 65535),
            options.overlay_alpha,
        )
        self.assertTupleEqual(expected, tuple(int(v) for v in result[y, x]))

    def test_flat_image_returns_unchanged_copy(self) -> None:
        image = np.full((8, 8, 3), 128, dtype=np.uint8)

        result = apply_focus_peaking_overlay(
            image,
            FocusPeakingOptions(level=FocusPeakLevel.HIGH),
        )

        np.testing.assert_array_equal(result, image)
        self.assertIsNot(result, image)

    def test_invalid_shape_raises_value_error(self) -> None:
        invalid = np.zeros((8, 8), dtype=np.uint8)

        with self.assertRaises(ValueError):
            apply_focus_peaking_overlay(
                invalid,
                FocusPeakingOptions(level=FocusPeakLevel.HIGH),
            )


if __name__ == "__main__":
    unittest.main()
