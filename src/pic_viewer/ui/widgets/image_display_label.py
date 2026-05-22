"""Image display label with optional reference line overlays."""

from __future__ import annotations

from PySide2 import QtCore, QtGui, QtWidgets

from pic_viewer.domain.rules.reference_lines import (
    ReferenceLineSettings,
    build_reference_line_segments,
)


class ImageDisplayLabel(QtWidgets.QLabel):
    """QLabel-compatible image display widget that draws reference overlays."""

    _REFERENCE_LINE_COLOR = QtGui.QColor(255, 255, 255)
    _REFERENCE_LINE_WIDTH = 3
    _METADATA_OVERLAY_COLOR = QtGui.QColor(255, 255, 255, 185)
    _METADATA_OVERLAY_MARGIN = 8

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
        self._metadata_overlay_lines: tuple[str, ...] = tuple()
        self._metadata_overlay_visible = False

    def set_reference_line_settings(self, settings: ReferenceLineSettings) -> None:
        """Apply reference line settings and repaint without changing the pixmap."""

        if self._reference_line_settings == settings:
            return
        self._reference_line_settings = settings
        self.update()

    def reference_line_settings(self) -> ReferenceLineSettings:
        """Return the currently applied reference line settings."""

        return self._reference_line_settings

    def set_metadata_overlay(self, lines: tuple[str, ...], visible: bool) -> None:
        """Apply metadata overlay text and visibility, then repaint."""

        normalized_lines = tuple(line for line in lines if line)
        if self._metadata_overlay_lines == normalized_lines and self._metadata_overlay_visible == visible:
            return
        self._metadata_overlay_lines = normalized_lines
        self._metadata_overlay_visible = visible
        self.update()

    def metadata_overlay_lines(self) -> tuple[str, ...]:
        """Return the currently configured metadata overlay lines."""

        return self._metadata_overlay_lines

    def is_metadata_overlay_visible(self) -> bool:
        """Return True when the metadata overlay is enabled for painting."""

        return self._metadata_overlay_visible

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        super().paintEvent(event)
        self._paint_reference_lines()
        self._paint_metadata_overlay()

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

    def _paint_metadata_overlay(self) -> None:
        if not self._metadata_overlay_visible or not self._metadata_overlay_lines:
            return
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return

        pixmap_rect = self._pixmap_logical_rect(pixmap)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        painter.setPen(self._METADATA_OVERLAY_COLOR)
        font_metrics = painter.fontMetrics()
        left = pixmap_rect.left() + self._METADATA_OVERLAY_MARGIN
        top = pixmap_rect.top() + self._METADATA_OVERLAY_MARGIN
        max_width = max(1, pixmap_rect.width() - self._METADATA_OVERLAY_MARGIN * 2)
        clip_rect = QtCore.QRect(
            left,
            top,
            max_width,
            max(1, pixmap_rect.height() - self._METADATA_OVERLAY_MARGIN * 2),
        )
        painter.setClipRect(clip_rect)
        baseline = top + font_metrics.ascent()
        for line in self._metadata_overlay_lines[:3]:
            text = font_metrics.elidedText(line, QtCore.Qt.ElideRight, max_width)
            painter.drawText(left, baseline, text)
            baseline += font_metrics.lineSpacing()
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
