from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.filmstrip_filter import FilmstripFilterCriteria  # noqa: E402
from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
from pic_viewer.app.services.filmstrip_filter_service import (  # noqa: E402
    FilmstripFilterService,
    UNKNOWN_CAMERA_LABEL,
    UNKNOWN_LENS_LABEL,
)


class FilmstripFilterServiceTests(unittest.TestCase):
    """Validate Filmstrip filtering rules independently of Qt widgets."""

    def setUp(self) -> None:
        self.service = FilmstripFilterService()

    def test_extension_filter_is_case_insensitive(self) -> None:
        item = self.service.build_initial_item(Path("/tmp/IMG_0001.JPG"))

        self.assertEqual(".jpg", item.extension)
        self.assertTrue(self.service.matches(item, FilmstripFilterCriteria(extension=".JPG")))
        self.assertTrue(self.service.matches(item, FilmstripFilterCriteria(extension=".jpg")))
        self.assertFalse(self.service.matches(item, FilmstripFilterCriteria(extension=".png")))

    def test_filters_extension_camera_and_lens_with_and_semantics(self) -> None:
        item = self.service.build_item_from_metadata(
            Path("/tmp/portrait.JPG"),
            ImageMetadata(
                general=tuple(),
                exif=(
                    ("Make", "FUJIFILM"),
                    ("Model", "X-T5"),
                    ("LensModel", "XF 33mm F1.4"),
                ),
                iptc=tuple(),
                tiff=tuple(),
            ),
        )

        self.assertTrue(
            self.service.matches(
                item,
                FilmstripFilterCriteria(
                    extension=".jpg",
                    camera="FUJIFILM X-T5",
                    lens="XF 33mm F1.4",
                ),
            )
        )
        self.assertFalse(
            self.service.matches(
                item,
                FilmstripFilterCriteria(
                    extension=".jpg",
                    camera="FUJIFILM X-T5",
                    lens="XF 56mm F1.2",
                ),
            )
        )

    def test_candidates_are_deduplicated_sorted_and_include_unknown_values(self) -> None:
        first = self.service.build_item_from_metadata(
            Path("/tmp/a.JPG"),
            ImageMetadata(
                general=tuple(),
                exif=(
                    ("Make", "Canon"),
                    ("Model", "EOS R5"),
                    ("LensModel", "RF 50mm F1.2"),
                ),
                iptc=tuple(),
                tiff=tuple(),
            ),
        )
        duplicate = self.service.build_item_from_metadata(
            Path("/tmp/b.jpg"),
            ImageMetadata(
                general=tuple(),
                exif=(
                    ("Make", "Canon"),
                    ("Model", "EOS R5"),
                    ("LensModel", "RF 50mm F1.2"),
                ),
                iptc=tuple(),
                tiff=tuple(),
            ),
        )
        unknown = self.service.build_item_from_metadata(
            Path("/tmp/c.RAF"),
            ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple()),
        )

        options = self.service.build_options((unknown, duplicate, first))

        self.assertEqual((".jpg", ".raf"), options.extensions)
        self.assertEqual(("Canon EOS R5", UNKNOWN_CAMERA_LABEL), options.cameras)
        self.assertEqual(("RF 50mm F1.2", UNKNOWN_LENS_LABEL), options.lenses)

    def test_pending_metadata_does_not_match_camera_or_lens_specific_filters(self) -> None:
        pending = self.service.build_initial_item(Path("/tmp/pending.jpg"))

        self.assertTrue(self.service.matches(pending, FilmstripFilterCriteria()))
        self.assertTrue(self.service.matches(pending, FilmstripFilterCriteria(extension=".jpg")))
        self.assertFalse(self.service.matches(pending, FilmstripFilterCriteria(camera=UNKNOWN_CAMERA_LABEL)))
        self.assertFalse(self.service.matches(pending, FilmstripFilterCriteria(lens=UNKNOWN_LENS_LABEL)))


if __name__ == "__main__":
    unittest.main()
