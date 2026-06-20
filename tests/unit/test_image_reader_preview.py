from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import cv2
import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.common.errors import ImageLoadError  # noqa: E402
from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import LocalColorProfile, ColorSpacePreset  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.infra.adapters.image_reader import ImageReader  # noqa: E402


class ImageReaderPreviewTests(unittest.TestCase):
    """Validate reduced-cost preview decoding behavior."""

    def test_read_preview_prefers_reduced_decode(self) -> None:
        reader = ImageReader(allow_raw=False)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)

            def fake_imread(_: str, flag: int) -> np.ndarray | None:
                if flag == cv2.IMREAD_REDUCED_COLOR_8:
                    return reduced
                return None

            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", side_effect=fake_imread) as imread:
                image = reader.read_preview(path, max_edge=2000)

        np.testing.assert_array_equal(image, reduced)
        self.assertGreaterEqual(imread.call_count, 1)

    def test_read_preview_applies_display_color_space_conversion(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space.return_value = converted
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image = reader.read_preview(path, max_edge=2000, display_color_space=ColorSpacePreset.DISPLAY_P3)

        np.testing.assert_array_equal(image, converted)
        converter.convert_file_bgr_to_display_space.assert_called_once_with(
            path,
            reduced,
            ColorSpacePreset.DISPLAY_P3,
            ColorSpacePreset.SRGB,
            RenderingIntent.PERCEPTUAL,
        )

    def test_read_preview_defaults_to_app_display_color_space(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space.return_value = converted
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image = reader.read_preview(path, max_edge=2000)

        np.testing.assert_array_equal(image, converted)
        converter.convert_file_bgr_to_display_space.assert_called_once_with(
            path,
            reduced,
            ColorSpacePreset.SRGB,
            ColorSpacePreset.SRGB,
            RenderingIntent.PERCEPTUAL,
        )

    def test_read_with_color_profile_info_defaults_to_app_display_color_space(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        profile_info = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        source = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=source):
                image, info = reader.read_with_color_profile_info(path)

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_display_space_with_info.assert_called_once_with(
            path,
            source,
            ColorSpacePreset.SRGB,
            ColorSpacePreset.SRGB,
            RenderingIntent.PERCEPTUAL,
        )

    def test_read_preview_with_color_profile_info_returns_pixels_and_source_info(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        profile_info = ImageColorProfileInfo(
            display_name="Display P3",
            status=ImageColorProfileStatus.EMBEDDED,
            uses_srgb_fallback=False,
        )
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image, info = reader.read_preview_with_color_profile_info(
                    path,
                    max_edge=2000,
                    display_color_space=ColorSpacePreset.DISPLAY_P3,
                    rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
                )

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_display_space_with_info.assert_called_once_with(
            path,
            reduced,
            ColorSpacePreset.DISPLAY_P3,
            ColorSpacePreset.SRGB,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )

    def test_read_preview_with_color_profile_info_passes_specified_source_color_space(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        profile_info = ImageColorProfileInfo(
            display_name="Display P3",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image, info = reader.read_preview_with_color_profile_info(
                    path,
                    max_edge=2000,
                    display_color_space=ColorSpacePreset.PROPHOTO_RGB,
                    assumed_source_color_space=ColorSpacePreset.DISPLAY_P3,
                    rendering_intent=RenderingIntent.ABSOLUTE_COLORIMETRIC,
                )

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_display_space_with_info.assert_called_once_with(
            path,
            reduced,
            ColorSpacePreset.PROPHOTO_RGB,
            ColorSpacePreset.DISPLAY_P3,
            RenderingIntent.ABSOLUTE_COLORIMETRIC,
        )

    def test_read_preview_with_color_profile_info_passes_local_color_profiles(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        display_profile = LocalColorProfile(
            display_name="Local Display",
            path=Path("/tmp/display.icc"),
            profile_bytes=b"display-profile",
        )
        source_profile_spec = LocalColorProfile(
            display_name="Local Source",
            path=Path("/tmp/source.icc"),
            profile_bytes=b"source-profile",
        )
        profile_info = ImageColorProfileInfo(
            display_name="Local Source",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
            assumed_color_space=source_profile_spec,
        )
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image, info = reader.read_preview_with_color_profile_info(
                    path,
                    max_edge=2000,
                    display_color_space=display_profile,
                    assumed_source_color_space=source_profile_spec,
                    rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
                )

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_display_space_with_info.assert_called_once_with(
            path,
            reduced,
            display_profile,
            source_profile_spec,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )

    def test_raw_preview_requests_prophoto_output_and_source_override(self) -> None:
        raw_rgb = np.array([[[1, 2, 3], [4, 5, 6]]], dtype=np.uint16)
        fake_raw = unittest.mock.MagicMock()
        fake_raw.__enter__.return_value = fake_raw
        fake_raw.__exit__.return_value = None
        fake_raw.postprocess.return_value = raw_rgb
        srgb_color = object()
        prophoto_color = object()
        fake_rawpy = types.SimpleNamespace(
            ColorSpace=types.SimpleNamespace(sRGB=srgb_color, ProPhoto=prophoto_color),
            imread=unittest.mock.MagicMock(return_value=fake_raw),
        )
        profile_info = ImageColorProfileInfo(
            display_name="ProPhoto RGB",
            status=ImageColorProfileStatus.RAW_DECODED,
            uses_srgb_fallback=False,
            assumed_color_space=ColorSpacePreset.PROPHOTO_RGB,
        )
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space_with_depth.return_value = (
            raw_rgb[:, :, ::-1],
            profile_info,
            ChannelBitDepth.SIXTEEN,
        )
        reader = ImageReader(allow_raw=True, color_converter=converter)

        with tempfile.NamedTemporaryFile(suffix=".nef") as tmp:
            path = Path(tmp.name)
            with patch.dict(sys.modules, {"rawpy": fake_rawpy}):
                result = reader.read_preview_with_profile_and_depth(
                    path,
                    max_edge=2000,
                    display_color_space=ColorSpacePreset.DISPLAY_P3,
                    assumed_source_color_space=ColorSpacePreset.ADOBE_RGB_1998,
                    rendering_intent=RenderingIntent.SATURATION,
                )

        fake_raw.postprocess.assert_called_once()
        self.assertTrue(fake_raw.postprocess.call_args.kwargs["half_size"])
        self.assertEqual(16, fake_raw.postprocess.call_args.kwargs["output_bps"])
        self.assertIs(prophoto_color, fake_raw.postprocess.call_args.kwargs["output_color"])
        self.assertEqual(profile_info, result.source_color_profile)
        converter.convert_file_bgr_to_display_space_with_depth.assert_called_once()
        call = converter.convert_file_bgr_to_display_space_with_depth.call_args
        self.assertEqual(ColorSpacePreset.DISPLAY_P3, call.args[2])
        self.assertEqual(ColorSpacePreset.PROPHOTO_RGB, call.args[3])
        self.assertEqual(RenderingIntent.SATURATION, call.args[4])
        raw_source_info = call.kwargs["source_color_profile_override"]
        self.assertEqual(ImageColorProfileStatus.RAW_DECODED, raw_source_info.status)
        self.assertEqual(ColorSpacePreset.PROPHOTO_RGB, raw_source_info.assumed_color_space)

    def test_read_preview_uses_pillow_fallback_when_opencv_cannot_decode(self) -> None:
        reader = ImageReader(allow_raw=False)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "phone.HEIC"
            Image.new("RGB", (2, 1), (10, 20, 30)).save(path, format="PNG")

            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=None):
                image = reader.read_preview(path, max_edge=2000)

        self.assertEqual((1, 2, 3), image.shape)
        self.assertEqual(np.uint8, image.dtype)
        np.testing.assert_array_equal(image[0, 0], np.array([30, 20, 10], dtype=np.uint8))

    def test_read_preview_pillow_fallback_resizes_to_max_edge_before_conversion(self) -> None:
        converted = np.full((1, 2, 3), 127, dtype=np.uint8)
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_display_space.return_value = converted
        reader = ImageReader(allow_raw=False, color_converter=converter)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sample.avif"
            Image.new("RGB", (8, 4), (1, 2, 3)).save(path, format="PNG")

            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=None):
                image = reader.read_preview(path, max_edge=2)

        np.testing.assert_array_equal(image, converted)
        resized = converter.convert_file_bgr_to_display_space.call_args.args[1]
        self.assertEqual((1, 2, 3), resized.shape)
        np.testing.assert_array_equal(resized[0, 0], np.array([3, 2, 1], dtype=np.uint8))

    def test_read_preview_raises_for_unsupported_format_when_raw_disabled(self) -> None:
        reader = ImageReader(allow_raw=False)
        with tempfile.NamedTemporaryFile(suffix=".raw") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=None):
                with self.assertRaises(ImageLoadError) as ctx:
                    reader.read_preview(path)
        self.assertEqual("Unsupported image format", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
