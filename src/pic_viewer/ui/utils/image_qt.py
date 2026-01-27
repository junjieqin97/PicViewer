"""Qt helpers for image conversion."""

from __future__ import annotations

import numpy as np
from PyQt5 import QtCore, QtGui


def to_qpixmap(
    rgb: np.ndarray,
    target_size: QtCore.QSize,
    device_pixel_ratio: float = 1.0,
) -> QtGui.QPixmap:
    """Convert RGB array to a DPR-aware scaled QPixmap.

    Args:
        rgb: RGB image array.
        target_size: Target widget size in device-independent pixels.
        device_pixel_ratio: Device pixel ratio (DPR) for High-DPI displays.

    Returns:
        QPixmap: Scaled pixmap for display.
    """

    if rgb.size == 0:
        return QtGui.QPixmap()

    if target_size.width() <= 0 or target_size.height() <= 0:
        return QtGui.QPixmap()

    h, w, _ = rgb.shape
    bytes_per_line = w * 3
    image = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
    pixmap = QtGui.QPixmap.fromImage(image)

    dpr = max(1.0, float(device_pixel_ratio))
    physical_size = QtCore.QSize(
        max(1, int(round(target_size.width() * dpr))),
        max(1, int(round(target_size.height() * dpr))),
    )
    scaled = pixmap.scaled(
        physical_size,
        QtCore.Qt.KeepAspectRatio,
        QtCore.Qt.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(dpr)
    return scaled
