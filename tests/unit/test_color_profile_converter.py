from __future__ import annotations

import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageCms

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.models.color_space import WorkingColorSpace  # noqa: E402
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter  # noqa: E402


class ColorProfileConverterTests(unittest.TestCase):
    """Validate ICC color conversion behavior for image loading."""

    def test_builtin_working_color_spaces_resolve_to_icc_profiles(self) -> None:
        converter = ColorProfileConverter()

        for color_space in WorkingColorSpace:
            with self.subTest(color_space=color_space):
                profile = converter.profile_for(color_space)

                self.assertIsInstance(profile, ImageCms.ImageCmsProfile)

    def test_actual_cms_conversion_supports_all_builtin_working_color_spaces(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.arange(27, dtype=np.uint8).reshape((3, 3, 3))

        with patch.object(
            converter,
            "_read_embedded_icc_profile",
            return_value=converter.profile_bytes_for(WorkingColorSpace.SRGB),
        ):
            for color_space in WorkingColorSpace:
                with self.subTest(color_space=color_space):
                    result = converter.convert_file_bgr_to_working_space(
                        Path("/tmp/profiled.jpg"),
                        bgr,
                        color_space,
                    )

                    self.assertEqual(bgr.shape, result.shape)
                    self.assertEqual(np.uint8, result.dtype)

    def test_missing_embedded_profile_uses_srgb_source_and_keeps_srgb_pixels(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.arange(12, dtype=np.uint8).reshape((2, 2, 3))

        with patch.object(converter, "_read_embedded_icc_profile", return_value=None):
            result = converter.convert_file_bgr_to_working_space(
                Path("/tmp/no-profile.jpg"),
                bgr,
                WorkingColorSpace.SRGB,
            )

        np.testing.assert_array_equal(result, bgr)

    def test_embedded_profile_conversion_returns_bgr_with_original_shape_and_dtype(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((2, 3, 3), dtype=np.uint8)
        bgr[:, :, 0] = 200
        converted_rgb = Image.new("RGB", (3, 2), (10, 20, 30))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(WorkingColorSpace.SRGB),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result = converter.convert_file_bgr_to_working_space(
                Path("/tmp/profiled.jpg"),
                bgr,
                WorkingColorSpace.DISPLAY_P3,
            )

        transform.assert_called_once()
        self.assertEqual(bgr.shape, result.shape)
        self.assertEqual(np.uint8, result.dtype)
        np.testing.assert_array_equal(result[0, 0], np.array([30, 20, 10], dtype=np.uint8))

    def test_invalid_embedded_profile_falls_back_to_srgb_source_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (11, 22, 33))

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=b"not-an-icc-profile"),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result = converter.convert_file_bgr_to_working_space(
                Path("/tmp/bad-profile.jpg"),
                bgr,
                WorkingColorSpace.PROPHOTO_RGB,
            )

        transform.assert_called_once()
        np.testing.assert_array_equal(result[0, 0], np.array([33, 22, 11], dtype=np.uint8))

    def test_embedded_profile_transform_failure_retries_with_srgb_source_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (77, 88, 99))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(WorkingColorSpace.DISPLAY_P3),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.side_effect = [ImageCms.PyCMSError("bad transform"), converted_rgb]
            result = converter.convert_file_bgr_to_working_space(
                Path("/tmp/profiled.jpg"),
                bgr,
                WorkingColorSpace.PROPHOTO_RGB,
            )

        self.assertEqual(2, transform.call_count)
        np.testing.assert_array_equal(result[0, 0], np.array([99, 88, 77], dtype=np.uint8))

    def test_working_space_preview_converts_back_to_srgb_for_display(self) -> None:
        converter = ColorProfileConverter()
        working_rgb = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (44, 55, 66))

        with patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform:
            transform.return_value = converted_rgb
            result = converter.convert_working_rgb_to_srgb(
                working_rgb,
                WorkingColorSpace.ADOBE_RGB_1998,
            )

        transform.assert_called_once()
        np.testing.assert_array_equal(result[0, 0], np.array([44, 55, 66], dtype=np.uint8))


if __name__ == "__main__":
    unittest.main()
