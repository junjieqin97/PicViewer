"""Filmstrip behavior for main controller."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PyQt5 import QtCore, QtGui

from pic_viewer.ui.utils.image_qt import to_qpixmap


class MainControllerFilmstripMixin:
    """Provide filmstrip sizing and thumbnail update helpers."""

    def _configure_filmstrip_resize(self) -> None:
        """Configure dynamic filmstrip icon resizing."""

        self._filmstrip_resize_timer.setSingleShot(True)
        self._filmstrip_resize_timer.setInterval(120)
        self._filmstrip_resize_timer.timeout.connect(self._apply_filmstrip_icon_size)
        self._ui.splitVertical.splitterMoved.connect(self._on_vertical_splitter_moved)

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

    def _on_vertical_splitter_moved(self, _: int, __: int) -> None:
        """Handle vertical splitter changes for filmstrip resizing."""

        self._schedule_filmstrip_resize()

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
        if icon_side <= 0 or icon_side == self._filmstrip_icon_side:
            return

        self._filmstrip_icon_side = icon_side
        icon_size = QtCore.QSize(icon_side, icon_side)
        self._ui.listFilmstrip.setIconSize(icon_size)

        font_height = self._ui.listFilmstrip.fontMetrics().height()
        grid_height = icon_side + font_height + 16
        grid_width = icon_side + 20
        self._ui.listFilmstrip.setGridSize(QtCore.QSize(grid_width, grid_height))
        self._refresh_filmstrip_icons()

    def _calculate_filmstrip_icon_side(self) -> int:
        """Calculate the target side length for filmstrip thumbnails."""

        viewport_height = self._ui.listFilmstrip.viewport().height()
        if viewport_height <= 0:
            return self._filmstrip_icon_side

        font_height = self._ui.listFilmstrip.fontMetrics().height()
        available = viewport_height - font_height - 12
        if available <= 0:
            return self._filmstrip_icon_side
        return max(24, min(available, 256))

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
