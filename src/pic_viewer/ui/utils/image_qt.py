"""Qt helpers for image conversion."""

from __future__ import annotations

import numpy as np
from PyQt5 import QtCore, QtGui


def to_qpixmap(rgb: np.ndarray, target_size: QtCore.QSize) -> QtGui.QPixmap:
    """Convert RGB array to scaled QPixmap.

    Args:
        rgb: RGB image array.
        target_size: Target widget size.

    Returns:
        QPixmap: Scaled pixmap for display.
    """

    if rgb.size == 0:
        return QtGui.QPixmap()

    h, w, _ = rgb.shape
    bytes_per_line = w * 3
    image = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
    pixmap = QtGui.QPixmap.fromImage(image)
    return pixmap.scaled(target_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
