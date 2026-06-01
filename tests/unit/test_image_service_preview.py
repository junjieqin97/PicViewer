from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.image_service import ImageService  # noqa: E402
from pic_viewer.common.errors import ImageLoadError  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import WorkingColorSpace  # noqa: E402
from pic_viewer.domain.rules.focus_peaking import FocusPeakLevel  # noqa: E402


class ImageServicePreviewTests(unittest.TestCase):
    """Validate fast preview loading flow."""

    def setUp(self) -> None:
        self.reader = MagicMock()
        self.analyzer = MagicMock()
        self.metadata_reader = MagicMock()
        self.color_converter = MagicMock()
        self.service = ImageService(
            reader=self.reader,
            analyzer=self.analyzer,
            metadata_reader=self.metadata_reader,
            color_converter=self.color_converter,
        )
        self.path = Path("/tmp/sample.jpg")

    def test_load_preview_returns_preview_payload(self) -> None:
        preview_bgr = np.zeros((8, 8, 3), dtype=np.uint8)
        preview_rgb = np.ones((8, 8, 3), dtype=np.uint8)
        display_rgb = np.full((8, 8, 3), 2, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        self.reader.read_preview_with_color_profile_info.return_value = (preview_bgr, source_profile)
        self.analyzer.build_preview_rgb.return_value = preview_rgb
        self.color_converter.convert_working_rgb_to_srgb.return_value = display_rgb

        result = self.service.load_preview(self.path, WorkingColorSpace.DISPLAY_P3)

        self.reader.read_preview_with_color_profile_info.assert_called_once_with(
            self.path,
            working_color_space=WorkingColorSpace.DISPLAY_P3,
            assumed_source_color_space=WorkingColorSpace.SRGB,
        )
        self.analyzer.build_preview_rgb.assert_called_once_with(preview_bgr)
        self.color_converter.convert_working_rgb_to_srgb.assert_called_once_with(
            preview_rgb,
            WorkingColorSpace.DISPLAY_P3,
        )
        self.assertEqual(WorkingColorSpace.DISPLAY_P3, result.working_color_space)
        self.assertEqual(WorkingColorSpace.SRGB, result.assumed_source_color_space)
        self.assertEqual(source_profile, result.source_color_profile)
        np.testing.assert_array_equal(result.preview_rgb, display_rgb)

    def test_load_preview_defaults_to_app_working_color_space(self) -> None:
        preview_bgr = np.zeros((8, 8, 3), dtype=np.uint8)
        preview_rgb = np.ones((8, 8, 3), dtype=np.uint8)
        display_rgb = np.full((8, 8, 3), 2, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        self.reader.read_preview_with_color_profile_info.return_value = (preview_bgr, source_profile)
        self.analyzer.build_preview_rgb.return_value = preview_rgb
        self.color_converter.convert_working_rgb_to_srgb.return_value = display_rgb

        result = self.service.load_preview(self.path)

        self.reader.read_preview_with_color_profile_info.assert_called_once_with(
            self.path,
            working_color_space=WorkingColorSpace.PROPHOTO_RGB,
            assumed_source_color_space=WorkingColorSpace.SRGB,
        )
        self.color_converter.convert_working_rgb_to_srgb.assert_called_once_with(
            preview_rgb,
            WorkingColorSpace.PROPHOTO_RGB,
        )
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, result.working_color_space)

    def test_load_preview_passes_specified_source_color_space(self) -> None:
        preview_bgr = np.zeros((8, 8, 3), dtype=np.uint8)
        preview_rgb = np.ones((8, 8, 3), dtype=np.uint8)
        display_rgb = np.full((8, 8, 3), 2, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="Display P3",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        self.reader.read_preview_with_color_profile_info.return_value = (preview_bgr, source_profile)
        self.analyzer.build_preview_rgb.return_value = preview_rgb
        self.color_converter.convert_working_rgb_to_srgb.return_value = display_rgb

        result = self.service.load_preview(
            self.path,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.DISPLAY_P3,
        )

        self.reader.read_preview_with_color_profile_info.assert_called_once_with(
            self.path,
            working_color_space=WorkingColorSpace.PROPHOTO_RGB,
            assumed_source_color_space=WorkingColorSpace.DISPLAY_P3,
        )
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, result.working_color_space)
        self.assertEqual(WorkingColorSpace.DISPLAY_P3, result.assumed_source_color_space)

    def test_load_preview_propagates_image_load_error(self) -> None:
        self.reader.read_preview_with_color_profile_info.side_effect = ImageLoadError("bad image")

        with self.assertRaises(ImageLoadError):
            self.service.load_preview(self.path)

    def test_load_preview_wraps_unexpected_exception(self) -> None:
        self.reader.read_preview_with_color_profile_info.side_effect = RuntimeError("boom")

        with self.assertRaises(ImageLoadError) as ctx:
            self.service.load_preview(self.path)

        self.assertEqual("Unable to read this image file", str(ctx.exception))

    def test_pseudo_color_preview_returns_unchanged_pixels_when_all_overlays_are_off(self) -> None:
        preview_rgb = np.full((8, 8, 3), 64, dtype=np.uint8)

        result = self.service.build_preview_with_pseudo_color_overlay(
            preview_rgb,
            show_underexposed=False,
            show_overexposed=False,
            focus_peak_level=None,
        )

        np.testing.assert_array_equal(result, preview_rgb)

    def test_pseudo_color_preview_combines_exposure_and_focus_peaking(self) -> None:
        preview_rgb = np.zeros((12, 12, 3), dtype=np.uint8)
        preview_rgb[:, 6:] = 255

        result = self.service.build_preview_with_pseudo_color_overlay(
            preview_rgb,
            show_underexposed=True,
            show_overexposed=True,
            focus_peak_level=FocusPeakLevel.HIGH,
        )

        self.assertFalse(np.array_equal(result, preview_rgb))
        blue_dominant = result[:, :, 2] > result[:, :, 0]
        blue_dominant &= result[:, :, 2] > result[:, :, 1]
        self.assertTrue(bool(np.any(blue_dominant)))


if __name__ == "__main__":
    unittest.main()
