"""Rendered checks with tolerances for anti-aliasing, not screenshot baselines."""
from __future__ import annotations

import cv2
import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets


def pixels(image: QtGui.QImage) -> np.ndarray:
    """Copy physical RGB pixels, respecting Qt's padded scanlines."""
    converted = image.convertToFormat(QtGui.QImage.Format.Format_RGBA8888)
    rows = np.frombuffer(converted.constBits(), dtype=np.uint8).reshape(
        converted.height(), converted.bytesPerLine()
    )
    return rows[:, :converted.width() * 4].reshape(
        converted.height(), converted.width(), 4
    )[:, :, :3].copy()


def require_contained(inner: QtCore.QRect, outer: QtCore.QRect) -> None:
    """Reject empty or clipped logical geometry, including one-pixel clipping."""
    assert not inner.isEmpty() and outer.contains(inner), f"Clipped: {inner} in {outer}"


def require_visible(widget: QtWidgets.QWidget, ancestor: QtWidgets.QWidget) -> None:
    """Check every clipping ancestor, not just the final window bounds."""
    assert widget.isVisible(), f"Hidden: {widget.objectName()}"
    parent = widget.parentWidget()
    while parent is not None:
        rect = QtCore.QRect(widget.mapTo(parent, QtCore.QPoint()), widget.size())
        require_contained(rect, parent.rect())
        if parent is ancestor:
            return
        parent = parent.parentWidget()
    raise AssertionError(f"{ancestor.objectName()} is not an ancestor")


def require_contrast(foreground: QtGui.QColor, background: QtGui.QColor) -> None:
    """Require 4.5:1 contrast for normal state text, using sRGB luminance."""
    def luminance(color: QtGui.QColor) -> float:
        rgb = np.array(color.getRgbF()[:3])
        linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
        return float(linear @ np.array([0.2126, 0.7152, 0.0722]))

    values = sorted((luminance(foreground), luminance(background)))
    ratio = (values[1] + 0.05) / (values[0] + 0.05)
    assert ratio >= 4.5, f"Unreadable state contrast: {ratio:.2f}:1"


def require_text(label: QtWidgets.QLabel) -> None:
    """Check glyph availability, text fit, contrast and visible painted ink."""
    text = label.text()
    assert text.strip(), f"Missing state: {label.objectName()}"
    metrics = label.fontMetrics()
    for character in set(text):
        if not character.isspace():
            assert metrics.inFontUcs4(ord(character)), f"Missing glyph: {character!r}"
    rect = label.contentsRect().adjusted(label.margin(), label.margin(),
                                         -label.margin(), -label.margin())
    flags = int(label.alignment())
    if label.wordWrap():
        flags |= int(QtCore.Qt.TextFlag.TextWordWrap)
    bounds = metrics.boundingRect(rect, flags, text)
    require_contained(bounds, rect)
    # Transparent labels grabbed alone use Qt's fallback background. Sample the
    # composited window instead, so contrast reflects what the user actually sees.
    window = label.window()
    area = QtCore.QRect(label.mapTo(window, QtCore.QPoint()), label.size())
    image = pixels(window.grab(area).toImage())
    colors, counts = np.unique(image.reshape(-1, 3), axis=0, return_counts=True)
    background = QtGui.QColor(*map(int, colors[counts.argmax()]))
    foreground = label.palette().color(label.foregroundRole())
    require_contrast(foreground, background)
    distance = np.max(np.abs(image.astype(int) - np.array(foreground.getRgb()[:3])), axis=2)
    assert np.count_nonzero(distance <= 40) >= 5, f"No painted text: {label.objectName()}"


def focus_pixels(image: QtGui.QImage, color: str) -> int:
    """Count focus hue despite dashed-border blending at fractional coverage."""
    hsv = cv2.cvtColor(pixels(image), cv2.COLOR_RGB2HSV)
    target = QtGui.QColor(color).hue() / 2
    distance = np.abs(hsv[:, :, 0].astype(float) - target)
    return int(np.count_nonzero((np.minimum(distance, 180 - distance) < 4)
                               & (hsv[:, :, 1] > 38)))


def require_focus_delta(before: QtGui.QImage, after: QtGui.QImage, color: str) -> None:
    """Require extra focus-colored pixels, even on already selected items."""
    assert before.size() == after.size(), "Focus changed geometry"
    assert focus_pixels(after, color) > focus_pixels(before, color) + 4, "Missing focus indicator"


def require_canvas(image: QtGui.QImage, point: QtCore.QPoint, color: str) -> None:
    """Compare a small canvas patch in physical pixels to the documented color."""
    dpr = image.devicePixelRatio()
    x, y = round(point.x() * dpr), round(point.y() * dpr)
    rgb = pixels(image)
    patch = rgb[y:y + 2, x:x + 2]
    assert patch.shape == (2, 2, 3), "Canvas sample outside screenshot"
    expected = np.array(QtGui.QColor(color).getRgb()[:3])
    assert np.all(np.abs(patch.astype(int) - expected) <= 1), f"Canvas differs from {color}"
