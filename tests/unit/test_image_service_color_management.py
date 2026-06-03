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
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus  # noqa: E402
from pic_viewer.domain.models.color_space import LocalColorProfile, WorkingColorSpace  # noqa: E402
from pic_viewer.domain.models.rendering_intent import RenderingIntent  # noqa: E402
from pic_viewer.domain.rules.analysis import AnalysisResult  # noqa: E402


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

    def test_full_load_analyzes_working_space_pixels_and_displays_srgb_preview(self) -> None:
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
        working_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        working_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        display_preview_rgb = np.full((4, 4, 3), 32, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="ProPhoto RGB",
            status=ImageColorProfileStatus.EMBEDDED,
            uses_srgb_fallback=False,
        )
        analysis_result = self._analysis_result(working_bgr, working_preview_rgb)
        reader.read_with_color_profile_info.return_value = (working_bgr, source_profile)
        analyzer.analyze.return_value = analysis_result
        color_converter.convert_working_rgb_to_srgb.return_value = display_preview_rgb
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
        result = service.load_and_analyze(path, WorkingColorSpace.PROPHOTO_RGB)

        reader.read_with_color_profile_info.assert_called_once_with(
            path,
            working_color_space=WorkingColorSpace.PROPHOTO_RGB,
            assumed_source_color_space=WorkingColorSpace.SRGB,
            rendering_intent=RenderingIntent.PERCEPTUAL,
        )
        analyzer.analyze.assert_called_once_with(working_bgr)
        color_converter.convert_working_rgb_to_srgb.assert_called_once_with(
            working_preview_rgb,
            WorkingColorSpace.PROPHOTO_RGB,
            RenderingIntent.PERCEPTUAL,
        )
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, result.analysis.working_color_space)
        self.assertEqual(WorkingColorSpace.SRGB, result.analysis.assumed_source_color_space)
        self.assertEqual(RenderingIntent.PERCEPTUAL, result.analysis.rendering_intent)
        self.assertEqual(source_profile, result.analysis.source_color_profile)
        np.testing.assert_array_equal(result.analysis.analysis_bgr, working_bgr)
        np.testing.assert_array_equal(result.analysis.preview_rgb, display_preview_rgb)

    def test_full_load_defaults_to_app_working_color_space(self) -> None:
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
        working_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        working_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        display_preview_rgb = np.full((4, 4, 3), 32, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        reader.read_with_color_profile_info.return_value = (working_bgr, source_profile)
        analyzer.analyze.return_value = self._analysis_result(working_bgr, working_preview_rgb)
        color_converter.convert_working_rgb_to_srgb.return_value = display_preview_rgb
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
            result = service.load_and_analyze(path)

        reader.read_with_color_profile_info.assert_called_once_with(
            path,
            working_color_space=WorkingColorSpace.PROPHOTO_RGB,
            assumed_source_color_space=WorkingColorSpace.SRGB,
            rendering_intent=RenderingIntent.PERCEPTUAL,
        )
        color_converter.convert_working_rgb_to_srgb.assert_called_once_with(
            working_preview_rgb,
            WorkingColorSpace.PROPHOTO_RGB,
            RenderingIntent.PERCEPTUAL,
        )
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, result.analysis.working_color_space)

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
        working_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        working_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        display_preview_rgb = np.full((4, 4, 3), 32, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="Display P3",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )
        reader.read_with_color_profile_info.return_value = (working_bgr, source_profile)
        analyzer.analyze.return_value = self._analysis_result(working_bgr, working_preview_rgb)
        color_converter.convert_working_rgb_to_srgb.return_value = display_preview_rgb
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
        result = service.load_and_analyze(
            path,
            WorkingColorSpace.PROPHOTO_RGB,
            WorkingColorSpace.DISPLAY_P3,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )

        reader.read_with_color_profile_info.assert_called_once_with(
            path,
            working_color_space=WorkingColorSpace.PROPHOTO_RGB,
            assumed_source_color_space=WorkingColorSpace.DISPLAY_P3,
            rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        color_converter.convert_working_rgb_to_srgb.assert_called_once_with(
            working_preview_rgb,
            WorkingColorSpace.PROPHOTO_RGB,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        self.assertEqual(WorkingColorSpace.PROPHOTO_RGB, result.analysis.working_color_space)
        self.assertEqual(WorkingColorSpace.DISPLAY_P3, result.analysis.assumed_source_color_space)
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
        working_profile = self._local_profile(name="Local Working", file_name="working.icc")
        source_profile_spec = self._local_profile(name="Local Source", file_name="source.icc")
        working_bgr = np.full((4, 4, 3), 8, dtype=np.uint8)
        working_preview_rgb = np.full((4, 4, 3), 16, dtype=np.uint8)
        display_preview_rgb = np.full((4, 4, 3), 32, dtype=np.uint8)
        source_profile = ImageColorProfileInfo(
            display_name="Local Source",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
            assumed_color_space=source_profile_spec,
        )
        reader.read_with_color_profile_info.return_value = (working_bgr, source_profile)
        analyzer.analyze.return_value = self._analysis_result(working_bgr, working_preview_rgb)
        color_converter.convert_working_rgb_to_srgb.return_value = display_preview_rgb
        metadata_reader.read.return_value = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        with TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "profiled.jpg"
            path.write_bytes(b"stub")
            result = service.load_and_analyze(
                path,
                working_profile,
                source_profile_spec,
                RenderingIntent.RELATIVE_COLORIMETRIC,
            )

        reader.read_with_color_profile_info.assert_called_once_with(
            path,
            working_color_space=working_profile,
            assumed_source_color_space=source_profile_spec,
            rendering_intent=RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        color_converter.convert_working_rgb_to_srgb.assert_called_once_with(
            working_preview_rgb,
            working_profile,
            RenderingIntent.RELATIVE_COLORIMETRIC,
        )
        self.assertEqual(working_profile, result.analysis.working_color_space)
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


if __name__ == "__main__":
    unittest.main()
