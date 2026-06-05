from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageCms

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.common.errors import ColorProfileLoadError  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import LocalColorProfile, ColorSpacePreset  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter  # noqa: E402


class ColorProfileConverterTests(unittest.TestCase):
    """Validate ICC color conversion behavior for image loading."""

    def test_builtin_display_color_spaces_resolve_to_icc_profiles(self) -> None:
        converter = ColorProfileConverter()

        for color_space in ColorSpacePreset:
            with self.subTest(color_space=color_space):
                profile = converter.profile_for(color_space)

                self.assertIsInstance(profile, ImageCms.ImageCmsProfile)

    def test_local_icc_file_loads_profile_spec_with_bytes_and_stable_key(self) -> None:
        converter = ColorProfileConverter()
        profile_bytes = converter.profile_bytes_for(ColorSpacePreset.SRGB)

        with TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "camera-profile.icc"
            profile_path.write_bytes(profile_bytes)

            profile = converter.load_local_profile(profile_path)

        self.assertIsInstance(profile, LocalColorProfile)
        self.assertEqual("camera-profile.icc", profile.path.name)
        self.assertEqual(profile_bytes, profile.profile_bytes)
        self.assertTrue(profile.display_name)
        self.assertTrue(profile.stable_key.startswith("local:"))

    def test_local_icc_file_rejects_non_icc_extension(self) -> None:
        converter = ColorProfileConverter()

        with TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "profile.txt"
            profile_path.write_bytes(converter.profile_bytes_for(ColorSpacePreset.SRGB))

            with self.assertRaises(ColorProfileLoadError) as ctx:
                converter.load_local_profile(profile_path)

        self.assertEqual("ICC profile files must use .icc or .icm extension", str(ctx.exception))

    def test_actual_cms_conversion_supports_all_builtin_display_color_spaces(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.arange(27, dtype=np.uint8).reshape((3, 3, 3))

        with patch.object(
            converter,
            "_read_embedded_icc_profile",
            return_value=converter.profile_bytes_for(ColorSpacePreset.SRGB),
        ):
            for color_space in ColorSpacePreset:
                with self.subTest(color_space=color_space):
                    result = converter.convert_file_bgr_to_display_space(
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
            result = converter.convert_file_bgr_to_display_space(
                Path("/tmp/no-profile.jpg"),
                bgr,
                ColorSpacePreset.SRGB,
            )

        np.testing.assert_array_equal(result, bgr)

    def test_missing_embedded_profile_reports_srgb_default_source_info(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.arange(12, dtype=np.uint8).reshape((2, 2, 3))

        with patch.object(converter, "_read_embedded_icc_profile", return_value=None):
            _pixels, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/no-profile.jpg"),
                bgr,
                ColorSpacePreset.SRGB,
            )

        self.assertEqual(ImageColorProfileStatus.MISSING, info.status)
        self.assertEqual("sRGB", info.display_name)
        self.assertTrue(info.uses_srgb_fallback)
        self.assertEqual(ColorSpacePreset.SRGB, info.assumed_color_space)

    def test_missing_embedded_profile_uses_specified_source_color_space(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (12, 34, 56))

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=None),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/no-profile.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
                assumed_source_color_space=ColorSpacePreset.DISPLAY_P3,
            )

        transform.assert_called_once()
        self.assertEqual(ImageColorProfileStatus.MISSING, info.status)
        self.assertEqual("Display P3", info.display_name)
        self.assertEqual(ColorSpacePreset.DISPLAY_P3, info.assumed_color_space)
        self.assertTrue(info.uses_srgb_fallback)
        np.testing.assert_array_equal(result[0, 0], np.array([56, 34, 12], dtype=np.uint8))

    def test_missing_embedded_profile_uses_local_source_color_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (12, 34, 56))
        local_profile = LocalColorProfile(
            display_name="Local sRGB",
            path=Path("/tmp/local-source.icc"),
            profile_bytes=converter.profile_bytes_for(ColorSpacePreset.SRGB),
        )

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=None),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/no-profile.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
                assumed_source_color_space=local_profile,
            )

        transform.assert_called_once()
        self.assertEqual(ImageColorProfileStatus.MISSING, info.status)
        self.assertEqual("Local sRGB", info.display_name)
        self.assertEqual(local_profile, info.assumed_color_space)
        self.assertTrue(info.uses_srgb_fallback)
        np.testing.assert_array_equal(result[0, 0], np.array([56, 34, 12], dtype=np.uint8))

    def test_embedded_profile_reports_normalized_profile_name(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (1, 2, 3))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.SRGB),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.getProfileName") as name_reader,
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            name_reader.return_value = "  Example\nProfile\tName  "
            transform.return_value = converted_rgb
            _pixels, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
            )

        self.assertEqual(ImageColorProfileStatus.EMBEDDED, info.status)
        self.assertEqual("Example Profile Name", info.display_name)
        self.assertFalse(info.uses_srgb_fallback)

    def test_embedded_profile_conversion_returns_bgr_with_original_shape_and_dtype(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((2, 3, 3), dtype=np.uint8)
        bgr[:, :, 0] = 200
        converted_rgb = Image.new("RGB", (3, 2), (10, 20, 30))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.SRGB),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result = converter.convert_file_bgr_to_display_space(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
            )

        transform.assert_called_once()
        self.assertEqual(bgr.shape, result.shape)
        self.assertEqual(np.uint8, result.dtype)
        np.testing.assert_array_equal(result[0, 0], np.array([30, 20, 10], dtype=np.uint8))

    def test_embedded_profile_conversion_uses_selected_rendering_intent(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (10, 20, 30))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.SRGB),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            converter.convert_file_bgr_to_display_space(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
                rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
            )

        transform.assert_called_once()
        self.assertEqual(ImageCms.Intent.RELATIVE_COLORIMETRIC, transform.call_args.kwargs["renderingIntent"])

    def test_invalid_embedded_profile_falls_back_to_srgb_source_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (11, 22, 33))

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=b"not-an-icc-profile"),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result = converter.convert_file_bgr_to_display_space(
                Path("/tmp/bad-profile.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
            )

        transform.assert_called_once()
        np.testing.assert_array_equal(result[0, 0], np.array([33, 22, 11], dtype=np.uint8))

    def test_invalid_embedded_profile_reports_unreadable_icc_default_source_info(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (11, 22, 33))

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=b"not-an-icc-profile"),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            _pixels, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/bad-profile.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
            )

        self.assertEqual(ImageColorProfileStatus.INVALID, info.status)
        self.assertEqual("sRGB", info.display_name)
        self.assertTrue(info.uses_srgb_fallback)
        self.assertEqual(ColorSpacePreset.SRGB, info.assumed_color_space)

    def test_invalid_embedded_profile_uses_specified_source_color_space(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (22, 33, 44))

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=b"not-an-icc-profile"),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.return_value = converted_rgb
            result, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/bad-profile.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
                assumed_source_color_space=ColorSpacePreset.ADOBE_RGB_1998,
            )

        transform.assert_called_once()
        self.assertEqual(ImageColorProfileStatus.INVALID, info.status)
        self.assertEqual("Adobe RGB (1998)", info.display_name)
        self.assertEqual(ColorSpacePreset.ADOBE_RGB_1998, info.assumed_color_space)
        self.assertTrue(info.uses_srgb_fallback)
        np.testing.assert_array_equal(result[0, 0], np.array([44, 33, 22], dtype=np.uint8))

    def test_embedded_profile_transform_failure_retries_with_srgb_source_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (77, 88, 99))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.DISPLAY_P3),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.side_effect = [ImageCms.PyCMSError("bad transform"), converted_rgb]
            result = converter.convert_file_bgr_to_display_space(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
            )

        self.assertEqual(2, transform.call_count)
        np.testing.assert_array_equal(result[0, 0], np.array([99, 88, 77], dtype=np.uint8))

    def test_embedded_profile_transform_failure_reports_conversion_fallback_info(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (77, 88, 99))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.DISPLAY_P3),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.getProfileName") as name_reader,
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            name_reader.return_value = "Display P3"
            transform.side_effect = [ImageCms.PyCMSError("bad transform"), converted_rgb]
            _pixels, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
            )

        self.assertEqual(ImageColorProfileStatus.CONVERSION_FAILED, info.status)
        self.assertEqual("sRGB", info.display_name)
        self.assertTrue(info.uses_srgb_fallback)
        self.assertEqual(ColorSpacePreset.SRGB, info.assumed_color_space)

    def test_embedded_profile_transform_failure_retries_with_specified_source_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (17, 27, 37))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.DISPLAY_P3),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            transform.side_effect = [ImageCms.PyCMSError("bad transform"), converted_rgb]
            result, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
                assumed_source_color_space=ColorSpacePreset.ADOBE_RGB_1998,
            )

        self.assertEqual(2, transform.call_count)
        self.assertEqual(ImageColorProfileStatus.CONVERSION_FAILED, info.status)
        self.assertEqual("Adobe RGB (1998)", info.display_name)
        self.assertEqual(ColorSpacePreset.ADOBE_RGB_1998, info.assumed_color_space)
        self.assertTrue(info.uses_srgb_fallback)
        np.testing.assert_array_equal(result[0, 0], np.array([37, 27, 17], dtype=np.uint8))

    def test_embedded_profile_ignores_specified_source_color_space_when_conversion_succeeds(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.zeros((1, 1, 3), dtype=np.uint8)
        converted_rgb = Image.new("RGB", (1, 1), (41, 51, 61))

        with (
            patch.object(
                converter,
                "_read_embedded_icc_profile",
                return_value=converter.profile_bytes_for(ColorSpacePreset.SRGB),
            ),
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.getProfileName") as name_reader,
            patch("pic_viewer.infra.adapters.color_profile_converter.ImageCms.profileToProfile") as transform,
        ):
            name_reader.return_value = "Embedded sRGB"
            transform.return_value = converted_rgb
            _result, info = converter.convert_file_bgr_to_display_space_with_info(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.PROPHOTO_RGB,
                assumed_source_color_space=ColorSpacePreset.DISPLAY_P3,
            )

        transform.assert_called_once()
        self.assertEqual(ImageColorProfileStatus.EMBEDDED, info.status)
        self.assertEqual("Embedded sRGB", info.display_name)
        self.assertIsNone(info.assumed_color_space)

    def test_qt_color_space_for_builtin_display_space_is_valid(self) -> None:
        converter = ColorProfileConverter()

        color_space = converter.qt_color_space_for(ColorSpacePreset.DISPLAY_P3)

        self.assertTrue(color_space.isValid())

    def test_qt_color_space_for_local_profile_is_valid(self) -> None:
        converter = ColorProfileConverter()
        local_profile = LocalColorProfile(
            display_name="Local Display",
            path=Path("/tmp/local-display.icc"),
            profile_bytes=converter.profile_bytes_for(ColorSpacePreset.SRGB),
        )

        color_space = converter.qt_color_space_for(local_profile)

        self.assertTrue(color_space.isValid())


if __name__ == "__main__":
    unittest.main()
