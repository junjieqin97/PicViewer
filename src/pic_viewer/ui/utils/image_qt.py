"""Qt helpers for image conversion."""

from __future__ import annotations

import numpy as np
from PySide6 import QtCore, QtGui

from pic_viewer.domain.models.color_space import ColorProfileSpec, ColorSpacePreset, LocalColorProfile

_QT_COLOR_SPACES: dict[ColorSpacePreset, QtGui.QColorSpace.NamedColorSpace] = {
    ColorSpacePreset.SRGB: QtGui.QColorSpace.NamedColorSpace.SRgb,
    ColorSpacePreset.DISPLAY_P3: QtGui.QColorSpace.NamedColorSpace.DisplayP3,
    ColorSpacePreset.ADOBE_RGB_1998: QtGui.QColorSpace.NamedColorSpace.AdobeRgb,
    ColorSpacePreset.PROPHOTO_RGB: QtGui.QColorSpace.NamedColorSpace.ProPhotoRgb,
}

QColorSpaceInput = QtGui.QColorSpace | ColorProfileSpec


def to_qpixmap(
    rgb: np.ndarray,
    target_size: QtCore.QSize,
    device_pixel_ratio: float = 1.0,
    color_space: QColorSpaceInput | None = None,
) -> QtGui.QPixmap:
    """Convert RGB array to a DPR-aware scaled QPixmap.

    Args:
        rgb: RGB image array.
        target_size: Target widget size in device-independent pixels.
        device_pixel_ratio: Device pixel ratio (DPR) for High-DPI displays.
        color_space: Optional color space metadata for display preview pixels.

    Returns:
        QPixmap: Scaled pixmap for display.
    """

    if rgb.size == 0:
        return QtGui.QPixmap()

    if target_size.width() <= 0 or target_size.height() <= 0:
        return QtGui.QPixmap()

    rgb8 = _to_rgb888(rgb)
    h, w, _ = rgb8.shape
    bytes_per_line = w * 3
    image = QtGui.QImage(rgb8.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
    qt_color_space = _to_qt_color_space(color_space)
    if qt_color_space is not None and qt_color_space.isValid():
        image.setColorSpace(qt_color_space)
    pixmap = QtGui.QPixmap.fromImage(image)

    dpr = max(1.0, float(device_pixel_ratio))
    physical_size = QtCore.QSize(
        max(1, int(round(target_size.width() * dpr))),
        max(1, int(round(target_size.height() * dpr))),
    )
    scaled = pixmap.scaled(
        physical_size,
        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    scaled.setDevicePixelRatio(dpr)
    return scaled


def _to_rgb888(rgb: np.ndarray) -> np.ndarray:
    """Return a contiguous uint8 RGB buffer suitable for QImage."""

    if rgb.dtype == np.dtype(np.uint8):
        return np.ascontiguousarray(rgb)
    if rgb.dtype == np.dtype(np.uint16):
        return np.ascontiguousarray((rgb.astype(np.uint32) >> 8).astype(np.uint8))
    return np.ascontiguousarray(np.clip(rgb, 0, 255).astype(np.uint8))


def _to_qt_color_space(color_space: QColorSpaceInput | None) -> QtGui.QColorSpace | None:
    """Convert project color profile specs to Qt color spaces."""

    if color_space is None:
        return None
    if isinstance(color_space, QtGui.QColorSpace):
        return color_space
    if isinstance(color_space, LocalColorProfile):
        return QtGui.QColorSpace.fromIccProfile(color_space.profile_bytes)
    return QtGui.QColorSpace(_QT_COLOR_SPACES[color_space])
