from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.common.errors import ImageLoadError  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import WorkingColorSpace  # noqa: E402
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

    def test_read_preview_applies_working_color_space_conversion(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_working_space.return_value = converted
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image = reader.read_preview(path, max_edge=2000, working_color_space=WorkingColorSpace.DISPLAY_P3)

        np.testing.assert_array_equal(image, converted)
        converter.convert_file_bgr_to_working_space.assert_called_once_with(
            path,
            reduced,
            WorkingColorSpace.DISPLAY_P3,
            WorkingColorSpace.SRGB,
            RenderingIntent.PERCEPTUAL,
        )

    def test_read_preview_defaults_to_app_working_color_space(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_working_space.return_value = converted
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image = reader.read_preview(path, max_edge=2000)

        np.testing.assert_array_equal(image, converted)
        converter.convert_file_bgr_to_working_space.assert_called_once_with(
            path,
            reduced,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.SRGB,
            RenderingIntent.PERCEPTUAL,
        )

    def test_read_with_color_profile_info_defaults_to_app_working_color_space(self) -> None:
        converted = np.full((12, 12, 3), 128, dtype=np.uint8)
        profile_info = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        converter = unittest.mock.MagicMock()
        converter.convert_file_bgr_to_working_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        source = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=source):
                image, info = reader.read_with_color_profile_info(path)

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_working_space_with_info.assert_called_once_with(
            path,
            source,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.SRGB,
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
        converter.convert_file_bgr_to_working_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image, info = reader.read_preview_with_color_profile_info(
                    path,
                    max_edge=2000,
                    working_color_space=WorkingColorSpace.DISPLAY_P3,
                    rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
                )

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_working_space_with_info.assert_called_once_with(
            path,
            reduced,
            WorkingColorSpace.DISPLAY_P3,
            WorkingColorSpace.SRGB,
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
        converter.convert_file_bgr_to_working_space_with_info.return_value = (converted, profile_info)
        reader = ImageReader(allow_raw=False, color_converter=converter)
        reduced = np.zeros((12, 12, 3), dtype=np.uint8)

        with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
            path = Path(tmp.name)
            with patch("pic_viewer.infra.adapters.image_reader.cv2.imread", return_value=reduced):
                image, info = reader.read_preview_with_color_profile_info(
                    path,
                    max_edge=2000,
                    working_color_space=WorkingColorSpace.PROPHOTO_RGB,
                    assumed_source_color_space=WorkingColorSpace.DISPLAY_P3,
                    rendering_intent=RenderingIntent.ABSOLUTE_COLORIMETRIC,
                )

        np.testing.assert_array_equal(image, converted)
        self.assertEqual(profile_info, info)
        converter.convert_file_bgr_to_working_space_with_info.assert_called_once_with(
            path,
            reduced,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.DISPLAY_P3,
            RenderingIntent.ABSOLUTE_COLORIMETRIC,
        )

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
