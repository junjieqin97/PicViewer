from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtGui, QtWidgets

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.rules.reference_lines import ReferenceLineSettings  # noqa: E402
from pic_viewer.ui.widgets.image_display_label import ImageDisplayLabel  # noqa: E402


class ImageDisplayLabelTests(QtWidgetTestCase):
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

        image = QtGui.QImage(label.size(), QtGui.QImage.Format.Format_RGB32)
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

        image = QtGui.QImage(label.size(), QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor(0, 0, 0))
        label.render(image)

        white = QtGui.QColor(255, 255, 255)
        self.assertEqual(
            [white, white, white],
            [QtGui.QColor(image.pixel(x, 20)) for x in range(44, 47)],
        )
        self.assertNotEqual(white, QtGui.QColor(image.pixel(43, 20)))
        self.assertNotEqual(white, QtGui.QColor(image.pixel(47, 20)))

    def test_metadata_overlay_state_can_be_set_and_hidden(self) -> None:
        label = ImageDisplayLabel()
        self.addCleanup(label.deleteLater)

        label.set_metadata_overlay(("Camera Lens", "f/2.8 1/125s ISO 400", "6000 x 4000"), True)

        self.assertEqual(
            ("Camera Lens", "f/2.8 1/125s ISO 400", "6000 x 4000"),
            label.metadata_overlay_lines(),
        )
        self.assertTrue(label.is_metadata_overlay_visible())

        label.set_metadata_overlay(tuple(), False)

        self.assertEqual(tuple(), label.metadata_overlay_lines())
        self.assertFalse(label.is_metadata_overlay_visible())

    def test_metadata_overlay_renders_at_pixmap_top_left(self) -> None:
        label = ImageDisplayLabel()
        self.addCleanup(label.deleteLater)
        self._use_black_label_background(label)
        label.resize(120, 80)
        pixmap = QtGui.QPixmap(80, 40)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        label.setPixmap(pixmap)
        label.set_metadata_overlay(("INFO", "f/2.8 1/125s ISO 400", "6000 x 4000"), True)

        image = QtGui.QImage(label.size(), QtGui.QImage.Format.Format_RGB32)
        image.fill(QtGui.QColor(0, 0, 0))
        label.render(image)

        self.assertFalse(self._has_light_pixel(image, QtCore.QRect(0, 0, 18, 18)))
        self.assertTrue(self._has_light_pixel(image, QtCore.QRect(20, 20, 80, 32)))

    def test_image_pixel_position_maps_label_position_to_image_pixel(self) -> None:
        label = ImageDisplayLabel()
        self.addCleanup(label.deleteLater)
        label.resize(100, 60)
        pixmap = QtGui.QPixmap(80, 40)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        label.setPixmap(pixmap)

        self.assertTrue(hasattr(label, "image_pixel_position_at"))
        self.assertEqual((0, 0), label.image_pixel_position_at(QtCore.QPoint(10, 10), (4, 8)))
        self.assertEqual((4, 2), label.image_pixel_position_at(QtCore.QPoint(50, 30), (4, 8)))
        self.assertEqual((7, 3), label.image_pixel_position_at(QtCore.QPoint(89, 49), (4, 8)))

    def test_image_pixel_position_returns_none_outside_pixmap(self) -> None:
        label = ImageDisplayLabel()
        self.addCleanup(label.deleteLater)
        label.resize(100, 60)
        pixmap = QtGui.QPixmap(80, 40)
        pixmap.fill(QtGui.QColor(0, 0, 0))
        label.setPixmap(pixmap)

        self.assertTrue(hasattr(label, "image_pixel_position_at"))
        self.assertIsNone(label.image_pixel_position_at(QtCore.QPoint(9, 10), (4, 8)))
        self.assertIsNone(label.image_pixel_position_at(QtCore.QPoint(90, 49), (4, 8)))
        self.assertIsNone(label.image_pixel_position_at(QtCore.QPoint(10, 50), (4, 8)))

    def _has_light_pixel(self, image: QtGui.QImage, rect: QtCore.QRect) -> bool:
        for y in range(rect.top(), rect.bottom() + 1):
            for x in range(rect.left(), rect.right() + 1):
                color = QtGui.QColor(image.pixel(x, y))
                if color.red() > 120 and color.green() > 120 and color.blue() > 120:
                    return True
        return False

    def _use_black_label_background(self, label: ImageDisplayLabel) -> None:
        palette = label.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        label.setPalette(palette)
        label.setAutoFillBackground(True)

    def tearDown(self) -> None:
        self._app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self._app.processEvents()


if __name__ == "__main__":
    unittest.main()
