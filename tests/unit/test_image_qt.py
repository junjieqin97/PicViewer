from __future__ import annotations

import os
import sys
from pathlib import Path
import unittest

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.unit.qt_test_utils import QtWidgetTestCase
from PySide6 import QtCore, QtWidgets  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.models.color_space import ColorSpacePreset, LocalColorProfile  # noqa: E402
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter  # noqa: E402
from pic_viewer.ui.utils.image_qt import to_qpixmap  # noqa: E402


class ImageQtColorSpaceTests(QtWidgetTestCase):
    """Validate Qt image conversion preserves display color space metadata."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance()
        if cls._app is None:
            cls._app = QtWidgets.QApplication([])

    def test_to_qpixmap_attaches_builtin_display_color_space(self) -> None:
        converter = ColorProfileConverter()
        color_space = converter.qt_color_space_for(ColorSpacePreset.DISPLAY_P3)
        rgb = np.zeros((4, 4, 3), dtype=np.uint8)

        pixmap = to_qpixmap(rgb, QtCore.QSize(4, 4), color_space=color_space)

        self.assertTrue(pixmap.toImage().colorSpace().isValid())

    def test_to_qpixmap_attaches_local_display_color_space(self) -> None:
        converter = ColorProfileConverter()
        local_profile = LocalColorProfile(
            display_name="Local Display",
            path=Path("/tmp/local-display.icc"),
            profile_bytes=converter.profile_bytes_for(ColorSpacePreset.SRGB),
        )
        color_space = converter.qt_color_space_for(local_profile)
        rgb = np.zeros((4, 4, 3), dtype=np.uint8)

        pixmap = to_qpixmap(rgb, QtCore.QSize(4, 4), color_space=color_space)

        self.assertTrue(pixmap.toImage().colorSpace().isValid())


if __name__ == "__main__":
    unittest.main()
