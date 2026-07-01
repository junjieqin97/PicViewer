from __future__ import annotations

import importlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import types
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.common.errors import ColorProfileLoadError  # noqa: E402
from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import LocalColorProfile, ColorSpacePreset  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.infra.adapters import color_profile_converter as converter_module  # noqa: E402
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter  # noqa: E402


class _FakeVipsImage:
    """Small pyvips.Image stand-in for CMS unit tests."""

    def __init__(self, array: np.ndarray) -> None:
        self.array = array
        self.icc_calls: list[dict[str, object]] = []

    def copy(self, **_kwargs: object) -> "_FakeVipsImage":
        return self

    def icc_transform(self, output_profile: str, **kwargs: object) -> "_FakeVipsImage":
        self.icc_calls.append({"output_profile": output_profile, **kwargs})
        return self

    def write_to_memory(self) -> bytes:
        return np.ascontiguousarray(self.array).tobytes()


class ColorProfileConverterTests(unittest.TestCase):
    """Validate pyvips-backed ICC color conversion behavior."""

    def test_module_does_not_import_pillow_imagecms(self) -> None:
        module = importlib.import_module("pic_viewer.infra.adapters.color_profile_converter")

        self.assertFalse(hasattr(module, "ImageCms"))

    def test_profile_display_name_reads_mluc_data_inside_desc_tag(self) -> None:
        converter = ColorProfileConverter()
        profile_bytes = self._icc_profile_with_text_tag(
            b"desc",
            self._mluc_tag_data("Display P3"),
        )

        display_name = converter._profile_display_name(profile_bytes)

        self.assertEqual("Display P3", display_name)

    def test_profile_display_name_reads_legacy_desc_tag(self) -> None:
        converter = ColorProfileConverter()
        profile_bytes = self._icc_profile_with_text_tag(
            b"desc",
            self._desc_tag_data("Camera RGB"),
        )

        display_name = converter._profile_display_name(profile_bytes)

        self.assertEqual("Camera RGB", display_name)

    def test_builtin_display_color_spaces_resolve_to_icc_profile_paths(self) -> None:
        converter = ColorProfileConverter()

        for color_space in ColorSpacePreset:
            with self.subTest(color_space=color_space):
                profile_path = converter.profile_for(color_space)

                self.assertTrue(profile_path.exists())
                self.assertEqual(".icc", profile_path.suffix.lower())

    def test_local_icc_file_loads_profile_spec_with_bytes_and_stable_key(self) -> None:
        converter = ColorProfileConverter()
        profile_bytes = converter.profile_bytes_for(ColorSpacePreset.SRGB)

        with TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "camera-profile.icc"
            profile_path.write_bytes(profile_bytes)
            with patch.object(converter, "_validate_profile_bytes"):
                profile = converter.load_local_profile(profile_path)

        self.assertIsInstance(profile, LocalColorProfile)
        self.assertEqual("camera-profile.icc", profile.path.name)
        self.assertEqual(profile_bytes, profile.profile_bytes)
        self.assertEqual("camera-profile", profile.display_name)
        self.assertTrue(profile.stable_key.startswith("local:"))

    def test_local_icc_file_rejects_non_icc_extension(self) -> None:
        converter = ColorProfileConverter()

        with TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "profile.txt"
            profile_path.write_bytes(converter.profile_bytes_for(ColorSpacePreset.SRGB))

            with self.assertRaises(ColorProfileLoadError) as ctx:
                converter.load_local_profile(profile_path)

        self.assertEqual("ICC profile files must use .icc or .icm extension", str(ctx.exception))

    def test_local_icc_validation_error_maps_to_color_profile_load_error(self) -> None:
        converter = ColorProfileConverter()

        with TemporaryDirectory() as tmp_dir:
            profile_path = Path(tmp_dir) / "profile.icc"
            profile_path.write_bytes(b"not-an-icc")
            with patch.object(converter, "_validate_profile_bytes", side_effect=RuntimeError("bad")):
                with self.assertRaises(ColorProfileLoadError) as ctx:
                    converter.load_local_profile(profile_path)

        self.assertEqual("Unable to load ICC profile", str(ctx.exception))

    def test_pyvips_conversion_receives_selected_depth_and_rendering_intent(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.array([[[1, 2, 3]]], dtype=np.uint16)
        fake_image = _FakeVipsImage(bgr[:, :, ::-1])

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=None),
            patch.object(converter, "_new_vips_image_from_rgb", return_value=fake_image),
        ):
            result, info, depth = converter.convert_file_bgr_to_display_space_with_depth(
                Path("/tmp/no-profile.tif"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
                bit_depth=ChannelBitDepth.SIXTEEN,
                rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
            )

        self.assertEqual(np.uint16, result.dtype)
        self.assertEqual(ChannelBitDepth.SIXTEEN, depth)
        self.assertEqual(ImageColorProfileStatus.MISSING, info.status)
        self.assertEqual("relative", fake_image.icc_calls[0]["intent"])
        self.assertEqual(16, fake_image.icc_calls[0]["depth"])
        self.assertIn("input_profile", fake_image.icc_calls[0])

    def test_embedded_profile_is_preferred_when_available(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.array([[[1, 2, 3]]], dtype=np.uint8)
        fake_image = _FakeVipsImage(bgr[:, :, ::-1])

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=converter.profile_bytes_for(ColorSpacePreset.SRGB)),
            patch.object(converter, "_validate_profile_bytes", return_value=None),
            patch.object(converter, "_new_vips_image_from_rgb", return_value=fake_image),
        ):
            _result, info, depth = converter.convert_file_bgr_to_display_space_with_depth(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
                bit_depth=ChannelBitDepth.EIGHT,
            )

        self.assertEqual(ImageColorProfileStatus.EMBEDDED, info.status)
        self.assertEqual(ChannelBitDepth.EIGHT, depth)
        self.assertTrue(fake_image.icc_calls[0]["embedded"])
        self.assertNotIn("input_profile", fake_image.icc_calls[0])

    def test_source_profile_override_skips_embedded_icc_and_uses_override_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.array([[[1, 2, 3]]], dtype=np.uint16)
        fake_image = _FakeVipsImage(bgr[:, :, ::-1])
        source_info = ImageColorProfileInfo(
            display_name="ProPhoto RGB",
            status=ImageColorProfileStatus.RAW_DECODED,
            uses_srgb_fallback=False,
            assumed_color_space=ColorSpacePreset.PROPHOTO_RGB,
        )

        with (
            patch.object(converter, "_read_embedded_icc_profile") as read_embedded,
            patch.object(converter, "_new_vips_image_from_rgb", return_value=fake_image),
        ):
            _result, info, depth = converter.convert_file_bgr_to_display_space_with_depth(
                Path("/tmp/camera.dng"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
                assumed_source_color_space=ColorSpacePreset.SRGB,
                rendering_intent=RenderingIntent.PERCEPTUAL,
                bit_depth=ChannelBitDepth.SIXTEEN,
                source_color_profile_override=source_info,
            )

        read_embedded.assert_not_called()
        self.assertEqual(source_info, info)
        self.assertEqual(ChannelBitDepth.SIXTEEN, depth)
        self.assertEqual(
            str(converter.profile_for(ColorSpacePreset.PROPHOTO_RGB)),
            fake_image.icc_calls[0]["input_profile"],
        )
        self.assertNotIn("embedded", fake_image.icc_calls[0])

    def test_embedded_transform_failure_retries_with_assumed_source_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.array([[[1, 2, 3]]], dtype=np.uint8)
        fake_image = _FakeVipsImage(bgr[:, :, ::-1])
        original_transform = fake_image.icc_transform
        calls = {"count": 0}

        def fail_once(output_profile: str, **kwargs: object) -> _FakeVipsImage:
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("bad embedded profile")
            return original_transform(output_profile, **kwargs)

        fake_image.icc_transform = fail_once  # type: ignore[method-assign]

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=b"bad-profile"),
            patch.object(converter, "_new_vips_image_from_rgb", return_value=fake_image),
            patch.object(converter, "_validate_profile_bytes", return_value=None),
        ):
            _result, info, _depth = converter.convert_file_bgr_to_display_space_with_depth(
                Path("/tmp/profiled.jpg"),
                bgr,
                ColorSpacePreset.DISPLAY_P3,
            )

        self.assertEqual(2, calls["count"])
        self.assertEqual(ImageColorProfileStatus.CONVERSION_FAILED, info.status)
        self.assertTrue(info.uses_srgb_fallback)
        self.assertIn("input_profile", fake_image.icc_calls[0])

    def test_missing_pyvips_dependency_raises_runtime_error_on_conversion(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.array([[[1, 2, 3]]], dtype=np.uint8)

        with (
            patch.object(converter, "_read_embedded_icc_profile", return_value=None),
            patch("pic_viewer.infra.adapters.color_profile_converter.pyvips", None),
        ):
            with self.assertRaises(RuntimeError):
                converter.convert_file_bgr_to_display_space_with_depth(
                    Path("/tmp/no-profile.jpg"),
                    bgr,
                    ColorSpacePreset.DISPLAY_P3,
                )

    @unittest.skipUnless(converter_module.pyvips is not None, "pyvips/libvips is not available")
    def test_actual_pyvips_conversion_preserves_eight_and_sixteen_bit_depth(self) -> None:
        converter = ColorProfileConverter()

        with TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "sample.png"

            Image.new("RGB", (2, 1), (20, 80, 140)).save(image_path)
            cases = (
                (
                    np.array([[[20, 80, 140], [180, 120, 60]]], dtype=np.uint8),
                    ChannelBitDepth.EIGHT,
                ),
                (
                    np.array([[[20, 80, 140], [180, 120, 60]]], dtype=np.uint16) * np.uint16(257),
                    ChannelBitDepth.SIXTEEN,
                ),
            )

            for bgr, bit_depth in cases:
                with self.subTest(bit_depth=bit_depth):
                    result, info, cms_depth = converter.convert_file_bgr_to_display_space_with_depth(
                        image_path,
                        bgr,
                        ColorSpacePreset.DISPLAY_P3,
                        bit_depth=bit_depth,
                    )

                    self.assertEqual(bit_depth.dtype, result.dtype)
                    self.assertEqual(bgr.shape, result.shape)
                    self.assertEqual(bit_depth, cms_depth)
                    self.assertEqual(ImageColorProfileStatus.MISSING, info.status)

    @unittest.skipUnless(converter_module.pyvips is not None, "pyvips/libvips is not available")
    def test_actual_pyvips_conversion_uses_embedded_icc_profile(self) -> None:
        converter = ColorProfileConverter()
        bgr = np.array([[[20, 80, 140], [180, 120, 60]]], dtype=np.uint16) * np.uint16(257)

        with TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "embedded.png"

            Image.new("RGB", (2, 1), (20, 80, 140)).save(
                image_path,
                icc_profile=converter.profile_bytes_for(ColorSpacePreset.SRGB),
            )

            result, info, cms_depth = converter.convert_file_bgr_to_display_space_with_depth(
                image_path,
                bgr,
                ColorSpacePreset.DISPLAY_P3,
                bit_depth=ChannelBitDepth.SIXTEEN,
            )

        self.assertEqual(np.uint16, result.dtype)
        self.assertEqual(bgr.shape, result.shape)
        self.assertEqual(ChannelBitDepth.SIXTEEN, cms_depth)
        self.assertEqual(ImageColorProfileStatus.EMBEDDED, info.status)
        self.assertFalse(info.uses_srgb_fallback)

    def _icc_profile_with_text_tag(self, signature: bytes, tag_data: bytes) -> bytes:
        header = bytearray(128)
        tag_table = bytearray()
        tag_table.extend((1).to_bytes(4, "big"))
        tag_offset = 128 + 4 + 12
        tag_table.extend(signature)
        tag_table.extend(tag_offset.to_bytes(4, "big"))
        tag_table.extend(len(tag_data).to_bytes(4, "big"))
        return bytes(header + tag_table + tag_data)

    def _desc_tag_data(self, label: str) -> bytes:
        text = label.encode("ascii") + b"\x00"
        return b"desc" + b"\x00" * 4 + len(text).to_bytes(4, "big") + text

    def _mluc_tag_data(self, label: str) -> bytes:
        text = label.encode("utf-16-be")
        text_offset = 28
        return (
            b"mluc"
            + b"\x00" * 4
            + (1).to_bytes(4, "big")
            + (12).to_bytes(4, "big")
            + b"enUS"
            + len(text).to_bytes(4, "big")
            + text_offset.to_bytes(4, "big")
            + text
        )


if __name__ == "__main__":
    unittest.main()
