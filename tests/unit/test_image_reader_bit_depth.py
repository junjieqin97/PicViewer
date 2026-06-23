from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import ColorSpacePreset  # noqa: E402
from pic_viewer.infra.adapters import image_reader as image_reader_module  # noqa: E402
from pic_viewer.infra.adapters.image_reader import ImageReader  # noqa: E402


class ImageReaderBitDepthTests(unittest.TestCase):
    """Validate decode and CMS bit-depth selection."""

    def test_raw_suffix_uses_rawpy_before_opencv_and_requests_sixteen_bit_prophoto_output(self) -> None:
        raw_rgb = np.array([[[1, 2, 3]]], dtype=np.uint16)
        fake_raw = MagicMock()
        fake_raw.__enter__.return_value = fake_raw
        fake_raw.__exit__.return_value = None
        fake_raw.postprocess.return_value = raw_rgb
        srgb_color = object()
        prophoto_color = object()
        fake_rawpy = types.SimpleNamespace(
            ColorSpace=types.SimpleNamespace(sRGB=srgb_color, ProPhoto=prophoto_color),
            imread=MagicMock(return_value=fake_raw),
        )
        profile_info = ImageColorProfileInfo(
            display_name="ProPhoto RGB",
            status=ImageColorProfileStatus.RAW_DECODED,
            uses_srgb_fallback=False,
            assumed_color_space=ColorSpacePreset.PROPHOTO_RGB,
        )
        converter = MagicMock()
        converter.convert_file_bgr_to_display_space_with_depth.return_value = (
            raw_rgb[:, :, ::-1],
            profile_info,
            ChannelBitDepth.SIXTEEN,
        )
        reader = ImageReader(allow_raw=True, color_converter=converter)

        with tempfile.NamedTemporaryFile(suffix=".dng") as tmp:
            path = Path(tmp.name)
            with (
                patch.dict(sys.modules, {"rawpy": fake_rawpy}),
                patch("pic_viewer.infra.adapters.image_reader.cv2.imread") as imread,
            ):
                result = reader.read_with_profile_and_depth(path)

        imread.assert_not_called()
        fake_raw.postprocess.assert_called_once()
        self.assertEqual(16, fake_raw.postprocess.call_args.kwargs["output_bps"])
        self.assertIs(prophoto_color, fake_raw.postprocess.call_args.kwargs["output_color"])
        self.assertEqual(ChannelBitDepth.SIXTEEN, result.source_bit_depth)
        self.assertEqual(ChannelBitDepth.SIXTEEN, result.cms_bit_depth)
        self.assertEqual(profile_info, result.source_color_profile)
        self.assertTrue(result.is_raw)
        converter.convert_file_bgr_to_display_space_with_depth.assert_called_once()
        raw_source_info = converter.convert_file_bgr_to_display_space_with_depth.call_args.kwargs[
            "source_color_profile_override"
        ]
        self.assertEqual(ImageColorProfileStatus.RAW_DECODED, raw_source_info.status)
        self.assertEqual(ColorSpacePreset.PROPHOTO_RGB, raw_source_info.assumed_color_space)

    def test_non_raw_sixteen_bit_decode_preserves_sixteen_bit_cms_depth(self) -> None:
        source = np.array([[[1000, 2000, 3000]]], dtype=np.uint16)
        profile_info = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        converter = MagicMock()
        converter.convert_file_bgr_to_display_space_with_depth.return_value = (
            source.copy(),
            profile_info,
            ChannelBitDepth.SIXTEEN,
        )
        reader = ImageReader(allow_raw=False, color_converter=converter)

        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            path = Path(tmp.name)
            with patch.object(reader, "_read_pyvips_non_raw", return_value=source):
                result = reader.read_with_profile_and_depth(path, display_color_space=ColorSpacePreset.DISPLAY_P3)

        self.assertEqual(np.uint16, result.bgr.dtype)
        self.assertEqual(ChannelBitDepth.SIXTEEN, result.source_bit_depth)
        self.assertEqual(ChannelBitDepth.SIXTEEN, result.cms_bit_depth)
        self.assertFalse(result.is_raw)
        converter.convert_file_bgr_to_display_space_with_depth.assert_called_once()

    @unittest.skipUnless(image_reader_module.pyvips is not None, "pyvips/libvips is not available")
    def test_actual_pyvips_decoder_preserves_sixteen_bit_png(self) -> None:
        source = np.array([[[1000, 2000, 3000], [60000, 32000, 12000]]], dtype=np.uint16)
        reader = ImageReader(allow_raw=False)

        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "sixteen-bit.png"
            self.assertTrue(cv2.imwrite(str(path), source))

            decoded = reader._read_pyvips_non_raw(path)

        self.assertIsNotNone(decoded)
        self.assertEqual(np.uint16, decoded.dtype)
        np.testing.assert_array_equal(source, decoded)


if __name__ == "__main__":
    unittest.main()
