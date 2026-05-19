from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.rules.reference_lines import ReferenceLineSettings  # noqa: E402
from pic_viewer.ui.widgets.image_display_label import ImageDisplayLabel  # noqa: E402


class ImageDisplayLabelTests(unittest.TestCase):
    """Validate image display overlay rendering."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_reference_lines_render_as_pure_white(self) -> None:
        label = ImageDisplayLabel()
        self.addCleanup(label.deleteLater)
        label.resize(90, 60)
        pixmap = QtGui.QPixmap(90, 60)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        label.setPixmap(pixmap)
        label.set_reference_line_settings(ReferenceLineSettings(cross=True))

        image = QtGui.QImage(label.size(), QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor(0, 0, 0))
        label.render(image)

        self.assertEqual(QtGui.QColor(255, 255, 255), QtGui.QColor(image.pixel(45, 30)))

    def test_reference_lines_render_three_pixels_wide(self) -> None:
        label = ImageDisplayLabel()
        self.addCleanup(label.deleteLater)
        label.resize(90, 60)
        pixmap = QtGui.QPixmap(90, 60)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        label.setPixmap(pixmap)
        label.set_reference_line_settings(ReferenceLineSettings(cross=True))

        image = QtGui.QImage(label.size(), QtGui.QImage.Format_RGB32)
        image.fill(QtGui.QColor(0, 0, 0))
        label.render(image)

        white = QtGui.QColor(255, 255, 255)
        self.assertEqual(
            [white, white, white],
            [QtGui.QColor(image.pixel(x, 20)) for x in range(44, 47)],
        )
        self.assertNotEqual(white, QtGui.QColor(image.pixel(43, 20)))
        self.assertNotEqual(white, QtGui.QColor(image.pixel(47, 20)))

    def tearDown(self) -> None:
        self._app.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        self._app.processEvents()


if __name__ == "__main__":
    unittest.main()
