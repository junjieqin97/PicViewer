from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
from pic_viewer.app.services.metadata_overlay_service import (  # noqa: E402
    build_metadata_overlay_lines,
)


class MetadataOverlayServiceTests(unittest.TestCase):
    """Validate the three-line image metadata overlay summary."""

    def test_complete_exif_metadata_formats_three_overlay_lines(self) -> None:
        metadata = ImageMetadata(
            general=(("Resolution", "6000 x 4000"),),
            exif=(
                ("Model", "X-T5"),
                ("LensModel", "XF 33mm F1.4"),
                ("FNumber", "2.8"),
                ("ExposureTime", "1/125"),
                ("ISOSpeedRatings", "400"),
            ),
            iptc=tuple(),
            tiff=tuple(),
        )

        lines = build_metadata_overlay_lines(metadata, source_size=(4000, 6000))

        self.assertEqual(
            (
                "X-T5 XF 33mm F1.4",
                "f/2.8 1/125s ISO 400",
                "6000 x 4000",
            ),
            lines,
        )

    def test_missing_metadata_uses_unknown_and_resolution_fallback(self) -> None:
        metadata = ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple())

        lines = build_metadata_overlay_lines(metadata, source_size=(1080, 1920))

        self.assertEqual(
            (
                "Unknown Unknown",
                "f/Unknown Unknowns ISO Unknown",
                "1920 x 1080",
            ),
            lines,
        )

    def test_decimal_exposure_time_is_rendered_as_fraction_when_under_one_second(self) -> None:
        metadata = ImageMetadata(
            general=tuple(),
            exif=(
                ("Model", "EOS R5"),
                ("LensModel", "RF 50mm"),
                ("FNumber", "4/1"),
                ("ExposureTime", "0.008"),
                ("PhotographicSensitivity", "800"),
            ),
            iptc=tuple(),
            tiff=tuple(),
        )

        lines = build_metadata_overlay_lines(metadata, source_size=(3000, 4500))

        self.assertEqual("f/4 1/125s ISO 800", lines[1])


if __name__ == "__main__":
    unittest.main()
