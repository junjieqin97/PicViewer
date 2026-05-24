"""Filmstrip behavior for main controller."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtGui

from pic_viewer.ui.utils.image_qt import to_qpixmap


class MainControllerFilmstripMixin:
    """Provide filmstrip sizing and thumbnail update helpers."""

    def _configure_filmstrip_resize(self) -> None:
        """Configure dynamic filmstrip icon resizing."""

        self._filmstrip_resize_timer.setSingleShot(True)
        self._filmstrip_resize_timer.setInterval(120)
        self._filmstrip_resize_timer.timeout.connect(self._apply_filmstrip_icon_size)

    def _update_filmstrip_icon(self, path: Path, preview_rgb: np.ndarray) -> None:
        item = self._find_filmstrip_item_by_path(path)
        if item is None:
            return
        icon_size = self._ui.listFilmstrip.iconSize()
        if icon_size.width() <= 0 or icon_size.height() <= 0:
            icon_size = QtCore.QSize(self._filmstrip_icon_side, self._filmstrip_icon_side)
        dpr = self._device_pixel_ratio_for(self._ui.listFilmstrip)
        pix = to_qpixmap(preview_rgb, icon_size, device_pixel_ratio=dpr)
        item.setIcon(QtGui.QIcon(pix))

    def _schedule_filmstrip_resize(self) -> None:
        """Debounce filmstrip icon size updates during resize."""

        if not self._ui.frameFilmstrip.isVisible():
            return
        self._filmstrip_resize_timer.stop()
        self._filmstrip_resize_timer.start()

    def _apply_filmstrip_icon_size(self) -> None:
        """Resize filmstrip thumbnails based on available height."""

        if not self._ui.frameFilmstrip.isVisible():
            return
        icon_side = self._calculate_filmstrip_icon_side()
        if icon_side <= 0:
            return

        item_size = self._filmstrip_item_size(icon_side)
        self._ui.listFilmstrip.setGridSize(item_size)
        self._apply_filmstrip_item_size_hints(item_size)
        if icon_side == self._filmstrip_icon_side:
            return

        self._filmstrip_icon_side = icon_side
        icon_size = QtCore.QSize(icon_side, icon_side)
        self._ui.listFilmstrip.setIconSize(icon_size)
        self._refresh_filmstrip_icons()

    def _calculate_filmstrip_icon_side(self) -> int:
        """Calculate the target side length for filmstrip thumbnails."""

        viewport_height = self._ui.listFilmstrip.viewport().height()
        if viewport_height <= 0:
            return self._filmstrip_icon_side

        font_height = self._ui.listFilmstrip.fontMetrics().height()
        vertical_padding = getattr(self._ui, "FILMSTRIP_ITEM_VERTICAL_PADDING", 18)
        available = viewport_height - font_height - vertical_padding
        if available <= 0:
            return self._filmstrip_icon_side
        min_side = getattr(self._ui, "FILMSTRIP_MIN_ICON_SIDE", 48)
        max_side = getattr(self._ui, "FILMSTRIP_ICON_SIDE", 72)
        return max(min_side, min(available, max_side))

    def _filmstrip_item_size(self, icon_side: int) -> QtCore.QSize:
        """Return the fixed item size for the current filmstrip thumbnail side."""

        if hasattr(self._ui, "filmstrip_item_size"):
            return self._ui.filmstrip_item_size(icon_side)
        font_height = self._ui.listFilmstrip.fontMetrics().height()
        width = icon_side + 36
        height = icon_side + font_height + 18
        return QtCore.QSize(width, height)

    def _apply_filmstrip_item_size_hints(self, item_size: QtCore.QSize) -> None:
        """Apply fixed filmstrip size hints to all existing items."""

        for row in range(self._ui.listFilmstrip.count()):
            item = self._ui.listFilmstrip.item(row)
            if item is not None:
                item.setSizeHint(item_size)

    def _refresh_filmstrip_icons(self) -> None:
        """Regenerate filmstrip icons using the current thumbnail size."""

        icon_size = self._ui.listFilmstrip.iconSize()
        if icon_size.width() <= 0 or icon_size.height() <= 0:
            return
        dpr = self._device_pixel_ratio_for(self._ui.listFilmstrip)

        for path_str, data in self._images_by_path.items():
            item = self._find_filmstrip_item_by_path(Path(path_str))
            if item is None:
                continue
            pix = to_qpixmap(data.analysis.preview_rgb, icon_size, device_pixel_ratio=dpr)
            item.setIcon(QtGui.QIcon(pix))
