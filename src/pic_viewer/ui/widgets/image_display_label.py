"""Image display label with optional reference line overlays."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from pic_viewer.domain.rules.pixel_sample import ColorReadout
from pic_viewer.domain.rules.reference_lines import (
    ReferenceLineSettings,
    build_reference_line_segments,
)
from pic_viewer.ui.resources import styles


class ImageDisplayLabel(QtWidgets.QLabel):
    """QLabel-compatible image display widget that draws reference overlays."""

    _REFERENCE_LINE_COLOR = QtGui.QColor(255, 255, 255)
    _REFERENCE_LINE_WIDTH = 3
    _METADATA_OVERLAY_COLOR = QtGui.QColor(255, 255, 255, 185)
    _METADATA_OVERLAY_MARGIN = 8
    _COLOR_READOUT_PADDING_X = 6
    _COLOR_READOUT_PADDING_Y = 4
    _COLOR_READOUT_MARGIN = 6
    _COLOR_READOUT_RADIUS = 4
    _COLOR_READOUT_MARKER_RADIUS = 5
    _COLOR_READOUT_VALUE_GAP = 8

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
        self._color_readouts: tuple[ColorReadout, ...] = tuple()
        self._color_readout_image_size: tuple[int, int] | None = None
        self._color_readout_theme = styles.AppearanceTheme.DARK

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

    def set_color_readouts(
        self,
        readouts: tuple[ColorReadout, ...],
        image_size: tuple[int, int] | None = None,
    ) -> None:
        """Apply persistent color readout overlays for this image label."""

        normalized = tuple(readouts)
        normalized_size = self._normalize_image_size(image_size, normalized)
        if self._color_readouts == normalized and self._color_readout_image_size == normalized_size:
            return
        self._color_readouts = normalized
        self._color_readout_image_size = normalized_size
        self.update()

    def color_readouts(self) -> tuple[ColorReadout, ...]:
        """Return the currently configured persistent color readouts."""

        return self._color_readouts

    def set_color_readout_theme(self, theme: styles.AppearanceTheme) -> None:
        """Apply the theme used to paint persistent color readout labels."""

        if self._color_readout_theme == theme:
            return
        self._color_readout_theme = theme
        self.update()

    def color_readout_theme(self) -> styles.AppearanceTheme:
        """Return the theme used for persistent color readout labels."""

        return self._color_readout_theme

    def color_readout_id_at(self, pos: QtCore.QPoint) -> int | None:
        """Return the topmost color readout id at a widget-local position."""

        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return None
        pixmap_rect = self._pixmap_logical_rect(pixmap)
        for readout in reversed(self._color_readouts):
            anchor = self._color_readout_anchor(readout, pixmap_rect)
            if anchor is None:
                continue
            marker_rect = QtCore.QRect(
                anchor.x() - self._COLOR_READOUT_MARKER_RADIUS,
                anchor.y() - self._COLOR_READOUT_MARKER_RADIUS,
                self._COLOR_READOUT_MARKER_RADIUS * 2 + 1,
                self._COLOR_READOUT_MARKER_RADIUS * 2 + 1,
            )
            if marker_rect.contains(pos):
                return readout.readout_id
        for readout in reversed(self._color_readouts):
            anchor = self._color_readout_anchor(readout, pixmap_rect)
            if anchor is None:
                continue
            if self._color_readout_label_rect(readout, anchor, pixmap_rect).contains(pos):
                return readout.readout_id
        return None

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        super().paintEvent(event)
        self._paint_reference_lines()
        self._paint_metadata_overlay()
        self._paint_color_readouts()

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
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
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
            text = font_metrics.elidedText(line, QtCore.Qt.TextElideMode.ElideRight, max_width)
            painter.drawText(left, baseline, text)
            baseline += font_metrics.lineSpacing()
        painter.end()

    def _paint_color_readouts(self) -> None:
        if not self._color_readouts:
            return
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return

        pixmap_rect = self._pixmap_logical_rect(pixmap)
        colors = self._color_readout_colors()
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)
        for readout in self._color_readouts:
            anchor = self._color_readout_anchor(readout, pixmap_rect)
            if anchor is None:
                continue
            text_rect = self._color_readout_label_rect(readout, anchor, pixmap_rect)
            painter.setPen(QtGui.QPen(colors["border"], 1))
            painter.setBrush(colors["background"])
            painter.drawRoundedRect(text_rect, self._COLOR_READOUT_RADIUS, self._COLOR_READOUT_RADIUS)
            self._draw_color_readout_values(painter, readout, text_rect, colors)
            painter.setBrush(colors["marker"])
            painter.setPen(QtGui.QPen(colors["border"], 1))
            painter.drawEllipse(anchor, self._COLOR_READOUT_MARKER_RADIUS, self._COLOR_READOUT_MARKER_RADIUS)
        painter.end()

    def _draw_color_readout_values(
        self,
        painter: QtGui.QPainter,
        readout: ColorReadout,
        text_rect: QtCore.QRect,
        colors: dict[str, QtGui.QColor],
    ) -> None:
        metrics = painter.fontMetrics()
        left = text_rect.left() + self._COLOR_READOUT_PADDING_X
        baseline = text_rect.top() + self._COLOR_READOUT_PADDING_Y + metrics.ascent()
        for text, color_name in self.color_readout_text_runs(readout):
            painter.setPen(colors[color_name])
            painter.drawText(left, baseline, text)
            left += metrics.horizontalAdvance(text) + self._COLOR_READOUT_VALUE_GAP

    def color_readout_text_runs(self, readout: ColorReadout) -> tuple[tuple[str, str], ...]:
        """Return display values with their color keys in visual order."""

        red, green, blue, luma = readout.display_values()
        return (
            (red, "red"),
            (green, "green"),
            (blue, "blue"),
            (luma, "luma"),
        )

    def color_readout_text_colors(self) -> dict[str, QtGui.QColor]:
        """Return channel colors for readout text in the active theme."""

        luma = QtGui.QColor(0, 0, 0)
        if self._color_readout_theme == styles.AppearanceTheme.DARK:
            luma = QtGui.QColor(255, 255, 255)
        return {
            "red": QtGui.QColor(255, 77, 77),
            "green": QtGui.QColor(72, 199, 116),
            "blue": QtGui.QColor(77, 163, 255),
            "luma": luma,
        }

    def _color_readout_label_rect(
        self,
        readout: ColorReadout,
        anchor: QtCore.QPoint,
        pixmap_rect: QtCore.QRect,
    ) -> QtCore.QRect:
        metrics = self.fontMetrics()
        value_widths = [
            metrics.horizontalAdvance(text)
            for text, _color_name in self.color_readout_text_runs(readout)
        ]
        width = (
            sum(value_widths)
            + self._COLOR_READOUT_VALUE_GAP * (len(value_widths) - 1)
            + self._COLOR_READOUT_PADDING_X * 2
        )
        height = metrics.height() + self._COLOR_READOUT_PADDING_Y * 2
        left = anchor.x() + self._COLOR_READOUT_MARGIN
        top = anchor.y() - height - self._COLOR_READOUT_MARGIN
        if left + width > pixmap_rect.right():
            left = anchor.x() - width - self._COLOR_READOUT_MARGIN
        if top < pixmap_rect.top():
            top = anchor.y() + self._COLOR_READOUT_MARGIN
        left = min(max(pixmap_rect.left(), left), max(pixmap_rect.left(), pixmap_rect.right() - width + 1))
        top = min(max(pixmap_rect.top(), top), max(pixmap_rect.top(), pixmap_rect.bottom() - height + 1))
        return QtCore.QRect(left, top, width, height)

    def _color_readout_anchor(
        self,
        readout: ColorReadout,
        pixmap_rect: QtCore.QRect,
    ) -> QtCore.QPoint | None:
        image_size = self._color_readout_image_size
        if image_size is None:
            return None
        image_height, image_width = image_size
        if image_height <= 0 or image_width <= 0:
            return None
        x = pixmap_rect.left() + int(round((readout.x + 0.5) * pixmap_rect.width() / image_width))
        y = pixmap_rect.top() + int(round((readout.y + 0.5) * pixmap_rect.height() / image_height))
        return QtCore.QPoint(
            min(pixmap_rect.right(), max(pixmap_rect.left(), x)),
            min(pixmap_rect.bottom(), max(pixmap_rect.top(), y)),
        )

    def _color_readout_colors(self) -> dict[str, QtGui.QColor]:
        if self._color_readout_theme == styles.AppearanceTheme.LIGHT:
            return {
                "background": QtGui.QColor(255, 255, 255, 235),
                "border": QtGui.QColor(77, 143, 211),
                "marker": QtGui.QColor(77, 143, 211),
                **self.color_readout_text_colors(),
            }
        return {
            "background": QtGui.QColor(43, 48, 54, 235),
            "border": QtGui.QColor(142, 180, 223),
            "marker": QtGui.QColor(142, 180, 223),
            **self.color_readout_text_colors(),
        }

    def _normalize_image_size(
        self,
        image_size: tuple[int, int] | None,
        readouts: tuple[ColorReadout, ...],
    ) -> tuple[int, int] | None:
        if image_size is not None:
            height, width = image_size
            if height > 0 and width > 0:
                return (int(height), int(width))
            return None
        if not readouts:
            return None
        max_x = max(readout.x for readout in readouts)
        max_y = max(readout.y for readout in readouts)
        return (max_y + 1, max_x + 1)

    def image_pixel_position_at(
        self,
        pos: QtCore.QPoint,
        image_size: tuple[int, int],
    ) -> tuple[int, int] | None:
        """Map a widget-local position to image pixel coordinates.

        Args:
            pos: Position in this label's coordinate system.
            image_size: Source image size as (height, width).

        Returns:
            tuple[int, int] | None: (x, y) image coordinates, or None when the
            position is outside the displayed pixmap.
        """

        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull():
            return None
        image_height, image_width = image_size
        if image_height <= 0 or image_width <= 0:
            return None

        pixmap_rect = self._pixmap_logical_rect(pixmap)
        if pixmap_rect.width() <= 0 or pixmap_rect.height() <= 0:
            return None
        if not pixmap_rect.contains(pos):
            return None

        relative_x = pos.x() - pixmap_rect.left()
        relative_y = pos.y() - pixmap_rect.top()
        image_x = int(relative_x * image_width / pixmap_rect.width())
        image_y = int(relative_y * image_height / pixmap_rect.height())
        return (
            min(image_width - 1, max(0, image_x)),
            min(image_height - 1, max(0, image_y)),
        )

    def _pixmap_logical_rect(self, pixmap: QtGui.QPixmap) -> QtCore.QRect:
        dpr = pixmap.devicePixelRatio()
        dpr = dpr if dpr and dpr > 0 else 1.0
        width = max(1, int(round(pixmap.width() / dpr)))
        height = max(1, int(round(pixmap.height() / dpr)))
        contents = self.contentsRect()
        left = contents.left() + max(0, (contents.width() - width) // 2)
        top = contents.top() + max(0, (contents.height() - height) // 2)
        return QtCore.QRect(left, top, width, height)
