"""Image display label with optional reference line overlays."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from pic_viewer.domain.rules.reference_lines import (
    ReferenceLineSettings,
    build_reference_line_segments,
)


class ImageDisplayLabel(QtWidgets.QLabel):
    """QLabel-compatible image display widget that draws reference overlays."""

    _REFERENCE_LINE_COLOR = QtGui.QColor(255, 255, 255)
    _REFERENCE_LINE_WIDTH = 3

    def __init__(
        self,
        text: str | QtWidgets.QWidget = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        if isinstance(text, QtWidgets.QWidget) and parent is None:
            parent = text
            text = ""
        super().__init__(text, parent)
        self._reference_line_settings = ReferenceLineSettings()

    def set_reference_line_settings(self, settings: ReferenceLineSettings) -> None:
        """Apply reference line settings and repaint without changing the pixmap."""

        if self._reference_line_settings == settings:
            return
        self._reference_line_settings = settings
        self.update()

    def reference_line_settings(self) -> ReferenceLineSettings:
        """Return the currently applied reference line settings."""

        return self._reference_line_settings

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        super().paintEvent(event)
        self._paint_reference_lines()

    def _paint_reference_lines(self) -> None:
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return

        pixmap_rect = self._pixmap_logical_rect(pixmap)
        lines = build_reference_line_segments(
            pixmap_rect.width(),
            pixmap_rect.height(),
            self._reference_line_settings,
        )
        if not lines:
            return

        painter = QtGui.QPainter(self)
        pen = QtGui.QPen(self._REFERENCE_LINE_COLOR)
        pen.setWidth(self._REFERENCE_LINE_WIDTH)
        pen.setCosmetic(True)
        painter.setPen(pen)
        for line in lines:
            painter.drawLine(
                QtCore.QPointF(pixmap_rect.left() + line.start[0], pixmap_rect.top() + line.start[1]),
                QtCore.QPointF(pixmap_rect.left() + line.end[0], pixmap_rect.top() + line.end[1]),
            )
        painter.end()

    def _pixmap_logical_rect(self, pixmap: QtGui.QPixmap) -> QtCore.QRect:
        dpr = pixmap.devicePixelRatio()
        dpr = dpr if dpr and dpr > 0 else 1.0
        width = max(1, int(round(pixmap.width() / dpr)))
        height = max(1, int(round(pixmap.height() / dpr)))
        contents = self.contentsRect()
        left = contents.left() + max(0, (contents.width() - width) // 2)
        top = contents.top() + max(0, (contents.height() - height) // 2)
        return QtCore.QRect(left, top, width, height)
