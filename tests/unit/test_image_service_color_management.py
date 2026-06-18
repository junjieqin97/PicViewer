from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
from pic_viewer.app.services.image_service import ImageService  # noqa: E402
from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import LocalColorProfile, ColorSpacePreset  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.domain.rules.analysis import AnalysisResult  # noqa: E402
from pic_viewer.infra.adapters.image_reader import ImageReadResult  # noqa: E402


class ImageServiceColorManagementTests(unittest.TestCase):
    """Validate color-managed full image loading."""

    def test_load_local_color_profile_delegates_to_color_converter(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )
        local_profile = self._local_profile()
        color_converter.load_local_profile.return_value = local_profile
        path = Path("/tmp/local.icc")

        result = service.load_local_color_profile(path)

        color_converter.load_local_profile.assert_called_once_with(path)
        self.assertEqual(local_profile, result)

    def test_warm_up_optional_backends_delegates_to_metadata_reader(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )

        service.warm_up_optional_backends()

        metadata_reader.warm_up.assert_called_once_with()

    def test_read_metadata_delegates_to_metadata_reader_without_image_loading(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )
        expected = ImageMetadata(
            general=tuple(),
            exif=(("Model", "X-T5"),),
            iptc=tuple(),
            tiff=tuple(),
        )
        metadata_reader.read.return_value = expected
        path = Path("/tmp/sample.jpg")

        result = service.read_metadata(path)

        self.assertEqual(expected, result)
        metadata_reader.read.assert_called_once_with(path)
        reader.read_with_profile_and_depth.assert_not_called()
        analyzer.analyze.assert_not_called()

    def test_full_load_analyzes_display_space_pixels_and_uses_display_space_preview(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )
        display_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        analysis_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="ProPhoto RGB",
            status=ImageColorProfileStatus.EMBEDDED,
            uses_srgb_fallback=False,
        )
        analysis_result = self._analysis_result(display_bgr, analysis_preview_rgb)
        reader.read_with_profile_and_depth.return_value = self._read_result(display_bgr, source_profile)
        analyzer.analyze.return_value = analysis_result
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
        result = service.load_and_analyze(path, ColorSpacePreset.PROPHOTO_RGB)

        reader.read_with_profile_and_depth.assert_called_once_with(
            path,
            display_color_space=ColorSpacePreset.PROPHOTO_RGB,
            assumed_source_color_space=ColorSpacePreset.SRGB,
            rendering_intent=RenderingIntent.PERCEPTUAL,
        )
        analyzer.analyze.assert_called_once_with(display_bgr, analysis_bit_depth=ChannelBitDepth.EIGHT)
        self.assertEqual([], color_converter.method_calls)
        self.assertEqual(ColorSpacePreset.PROPHOTO_RGB, result.analysis.display_color_space)
        self.assertEqual(ColorSpacePreset.SRGB, result.analysis.assumed_source_color_space)
        self.assertEqual(RenderingIntent.PERCEPTUAL, result.analysis.rendering_intent)
        self.assertEqual(source_profile, result.analysis.source_color_profile)
        np.testing.assert_array_equal(result.analysis.analysis_bgr, display_bgr)
        np.testing.assert_array_equal(result.analysis.preview_rgb, analysis_preview_rgb)

    def test_full_load_defaults_to_app_display_color_space(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )
        display_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        analysis_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        reader.read_with_profile_and_depth.return_value = self._read_result(display_bgr, source_profile)
        analyzer.analyze.return_value = self._analysis_result(display_bgr, analysis_preview_rgb)
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
            result = service.load_and_analyze(path)

        reader.read_with_profile_and_depth.assert_called_once_with(
            path,
            display_color_space=ColorSpacePreset.SRGB,
            assumed_source_color_space=ColorSpacePreset.SRGB,
            rendering_intent=RenderingIntent.PERCEPTUAL,
        )
        self.assertEqual([], color_converter.method_calls)
        self.assertEqual(ColorSpacePreset.SRGB, result.analysis.display_color_space)

    def test_full_load_passes_specified_source_color_space(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )
        display_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        analysis_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="Display P3",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        reader.read_with_profile_and_depth.return_value = self._read_result(display_bgr, source_profile)
        analyzer.analyze.return_value = self._analysis_result(display_bgr, analysis_preview_rgb)
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
        result = service.load_and_analyze(
            path,
            ColorSpacePreset.PROPHOTO_RGB,
            ColorSpacePreset.DISPLAY_P3,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )

        reader.read_with_profile_and_depth.assert_called_once_with(
            path,
            display_color_space=ColorSpacePreset.PROPHOTO_RGB,
            assumed_source_color_space=ColorSpacePreset.DISPLAY_P3,
            rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        self.assertEqual([], color_converter.method_calls)
        self.assertEqual(ColorSpacePreset.PROPHOTO_RGB, result.analysis.display_color_space)
        self.assertEqual(ColorSpacePreset.DISPLAY_P3, result.analysis.assumed_source_color_space)
        self.assertEqual(RenderingIntent.RELATIVE_COLORIMETRIC, result.analysis.rendering_intent)

    def test_full_load_passes_local_color_profiles(self) -> None:
        reader = MagicMock()
        analyzer = MagicMock()
        metadata_reader = MagicMock()
        color_converter = MagicMock()
        service = ImageService(
            reader=reader,
            analyzer=analyzer,
            metadata_reader=metadata_reader,
            color_converter=color_converter,
        )
        display_profile = self._local_profile(name="Local Display", file_name="display.icc")
        source_profile_spec = self._local_profile(name="Local Source", file_name="source.icc")
        display_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        analysis_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="Local Source",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
            assumed_color_space=source_profile_spec,
        )
        reader.read_with_profile_and_depth.return_value = self._read_result(display_bgr, source_profile)
        analyzer.analyze.return_value = self._analysis_result(display_bgr, analysis_preview_rgb)
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
            result = service.load_and_analyze(
                path,
                display_profile,
                source_profile_spec,
                RenderingIntent.RELATIVE_COLORIMETRIC,
            )

        reader.read_with_profile_and_depth.assert_called_once_with(
            path,
            display_color_space=display_profile,
            assumed_source_color_space=source_profile_spec,
            rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        self.assertEqual([], color_converter.method_calls)
        self.assertEqual(display_profile, result.analysis.display_color_space)
        self.assertEqual(source_profile_spec, result.analysis.assumed_source_color_space)

    def _local_profile(self, name: str = "Local Profile", file_name: str = "local.icc") -> LocalColorProfile:
        return LocalColorProfile(
            display_name=name,
            path=Path("/tmp") / file_name,
            profile_bytes=b"fake-profile-bytes",
        )

    def _analysis_result(self, bgr: np.ndarray, preview_rgb: np.ndarray) -> AnalysisResult:
        plot = np.zeros((2, 2, 3), dtype=np.uint8)
        return AnalysisResult(
            analysis_bgr=bgr,
            preview_rgb=preview_rgb,
            source_size=(bgr.shape[0], bgr.shape[1]),
            histogram_rgb=plot,
            histogram_luma=plot,
            histogram_r=plot,
            histogram_g=plot,
            histogram_b=plot,
            waveform_rgb=plot,
            waveform_luma=plot,
            waveform_r=plot,
            waveform_g=plot,
            waveform_b=plot,
        )

    def _read_result(
        self,
        bgr: np.ndarray,
        source_profile: ImageColorProfileInfo,
        bit_depth: ChannelBitDepth = ChannelBitDepth.EIGHT,
    ) -> ImageReadResult:
        return ImageReadResult(
            bgr=bgr,
            source_color_profile=source_profile,
            source_bit_depth=bit_depth,
            cms_bit_depth=bit_depth,
            is_raw=False,
        )


if __name__ == "__main__":
    unittest.main()
