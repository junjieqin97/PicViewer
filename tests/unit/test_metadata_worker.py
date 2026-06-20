from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.dto.metadata import ImageMetadata  # noqa: E402
from pic_viewer.ui.workers.metadata_worker import MetadataLoadTask  # noqa: E402


class MetadataWorkerTests(unittest.TestCase):
    """Validate the lightweight metadata-only worker."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_metadata_load_task_reads_metadata_without_full_image_load(self) -> None:
        service = MagicMock()
        path = Path("/tmp/sample.jpg")
        metadata = ImageMetadata(
            general=tuple(),
            exif=(("Model", "X-T5"),),
            iptc=tuple(),
            tiff=tuple(),
        )
        service.read_metadata.return_value = metadata
        task = MetadataLoadTask(service, path)
        results: list[ImageMetadata] = []
        errors: list[str] = []
        task.signals.finished.connect(results.append)
        task.signals.error.connect(errors.append)

        task.run()

        service.read_metadata.assert_called_once_with(path)
        self.assertEqual([metadata], results)
        self.assertEqual([], errors)


if __name__ == "__main__":
    unittest.main()
