from __future__ import annotations

import sys
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.infra.adapters.metadata_reader import MetadataReader  # noqa: E402


class _FakePyexiv2Image:
    def __init__(
        self,
        exif: dict[str, object] | None = None,
        iptc: dict[str, object] | None = None,
        read_error: Exception | None = None,
    ) -> None:
        self.exif = exif or {}
        self.iptc = iptc or {}
        self.read_error = read_error
        self.closed = False

    def __enter__(self) -> "_FakePyexiv2Image":
        return self

    def __exit__(self, *_args: object) -> None:
        self.closed = True

    def read_exif(self, encoding: str = "utf-8") -> dict[str, object]:
        if self.read_error is not None:
            raise self.read_error
        return self.exif

    def read_iptc(self, encoding: str = "utf-8") -> dict[str, object]:
        if self.read_error is not None:
            raise self.read_error
        return self.iptc


class MetadataReaderTests(unittest.TestCase):
    """Validate the pyexiv2 metadata adapter."""

    def test_warm_up_loads_optional_pyexiv2_backend(self) -> None:
        reader = MetadataReader()

        with patch.object(reader, "_load_pyexiv2", return_value=object()) as load_backend:
            reader.warm_up()

        load_backend.assert_called_once_with()

    def test_warm_up_import_failure_is_non_fatal(self) -> None:
        reader = MetadataReader()

        with (
            patch.object(reader, "_load_pyexiv2", side_effect=ImportError("missing")),
            self.assertLogs("pic_viewer.infra.adapters.metadata_reader", level="WARNING") as logs,
        ):
            reader.warm_up()

        self.assertTrue(any("metadata warm-up skipped" in message for message in logs.output))

    def test_reads_pyexiv2_metadata_into_existing_sections(self) -> None:
        fake_image = _FakePyexiv2Image(
            exif={
                "Exif.Image.Make": "FUJIFILM",
                "Exif.Image.DateTime": "2026:05:20 10:11:12",
                "Exif.Photo.FNumber": "4/1",
                "Exif.Photo.MakerNote": b"\xff\x00",
                "Exif.Thumbnail.Compression": "JPEG",
            },
            iptc={
                "Iptc.Application2.Keywords": ["landscape", "raw"],
                "Iptc.Envelope.CharacterSet": {"encoding": "utf-8", "source": "iptc"},
            },
        )
        fake_module = SimpleNamespace(Image=lambda *_args, **_kwargs: fake_image)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.jpg"
            path.write_bytes(b"not a real image")
            with patch("importlib.import_module", return_value=fake_module):
                metadata = MetadataReader().read(path)

        self.assertIn(("Make", "FUJIFILM"), metadata.exif)
        self.assertIn(("FNumber", "4/1"), metadata.exif)
        self.assertIn(("MakerNote", "ff00"), metadata.exif)
        self.assertIn(("Keywords", "landscape, raw"), metadata.iptc)
        self.assertIn(("CharacterSet", "encoding: utf-8, source: iptc"), metadata.iptc)
        self.assertEqual(
            (
                ("Compression", "JPEG"),
                ("DateTime", "2026:05:20 10:11:12"),
                ("Make", "FUJIFILM"),
            ),
            metadata.tiff,
        )
        self.assertTrue(fake_image.closed)

    def test_missing_file_returns_empty_metadata(self) -> None:
        metadata = MetadataReader().read(Path("/tmp/does-not-exist-picviewer.jpg"))

        self.assertEqual(tuple(), metadata.general)
        self.assertEqual(tuple(), metadata.exif)
        self.assertEqual(tuple(), metadata.iptc)
        self.assertEqual(tuple(), metadata.tiff)

    def test_import_failure_returns_empty_metadata_without_blocking_image_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.jpg"
            path.write_bytes(b"not a real image")
            with (
                patch("importlib.import_module", side_effect=ImportError("pyexiv2 missing")),
                self.assertLogs("pic_viewer.infra.adapters.metadata_reader", level="WARNING") as logs,
            ):
                metadata = MetadataReader().read(path)

        self.assertEqual(tuple(), metadata.exif)
        self.assertTrue(any("pyexiv2 is not available" in message for message in logs.output))

    def test_native_read_failure_returns_empty_metadata_and_closes_image(self) -> None:
        fake_image = _FakePyexiv2Image(read_error=RuntimeError("native read failed"))
        fake_module = SimpleNamespace(Image=lambda *_args, **_kwargs: fake_image)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.jpg"
            path.write_bytes(b"not a real image")
            with (
                patch("importlib.import_module", return_value=fake_module),
                self.assertLogs("pic_viewer.infra.adapters.metadata_reader", level="ERROR") as logs,
            ):
                metadata = MetadataReader().read(path)

        self.assertEqual(tuple(), metadata.exif)
        self.assertEqual(tuple(), metadata.iptc)
        self.assertEqual(tuple(), metadata.tiff)
        self.assertTrue(fake_image.closed)
        self.assertTrue(any("Error extracting metadata" in message for message in logs.output))


if __name__ == "__main__":
    unittest.main()
