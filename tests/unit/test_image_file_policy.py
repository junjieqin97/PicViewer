from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.image_file_policy import (  # noqa: E402
    SUPPORTED_IMAGE_SUFFIXES,
    filter_supported_image_paths,
    is_supported_image_path,
)


class ImageFilePolicyTests(unittest.TestCase):
    def test_supported_suffixes_include_current_open_formats(self) -> None:
        self.assertIn(".jpg", SUPPORTED_IMAGE_SUFFIXES)
        self.assertIn(".jpeg", SUPPORTED_IMAGE_SUFFIXES)
        self.assertIn(".png", SUPPORTED_IMAGE_SUFFIXES)
        self.assertIn(".tiff", SUPPORTED_IMAGE_SUFFIXES)
        self.assertIn(".dng", SUPPORTED_IMAGE_SUFFIXES)
        self.assertIn(".raf", SUPPORTED_IMAGE_SUFFIXES)

    def test_filter_supported_image_paths_is_case_insensitive_and_excludes_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            upper_case = root / "sample.JPG"
            raw_file = root / "camera.NEF"
            text_file = root / "notes.txt"
            directory = root / "folder.png"
            missing = root / "missing.png"
            upper_case.write_bytes(b"image")
            raw_file.write_bytes(b"raw")
            text_file.write_text("not an image", encoding="utf-8")
            directory.mkdir()

            self.assertTrue(is_supported_image_path(upper_case))
            self.assertFalse(is_supported_image_path(text_file))
            self.assertFalse(is_supported_image_path(directory))
            self.assertFalse(is_supported_image_path(missing))

            filtered = filter_supported_image_paths([upper_case, text_file, directory, raw_file, missing])

        self.assertEqual([upper_case, raw_file], filtered)


if __name__ == "__main__":
    unittest.main()
