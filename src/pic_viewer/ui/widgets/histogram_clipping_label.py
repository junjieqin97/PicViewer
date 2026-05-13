"""Histogram label with clickable clipping warning triangles."""

from __future__ import annotations

from typing import Literal

from PyQt5 import QtCore, QtGui, QtWidgets

TriangleName = Literal["underexposed", "overexposed"] | None


class HistogramClippingLabel(QtWidgets.QLabel):
    """QLabel variant that renders and toggles histogram clipping markers."""

    underexposed_toggled = QtCore.pyqtSignal(bool)
    overexposed_toggled = QtCore.pyqtSignal(bool)

    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._underexposed_active = False
        self._overexposed_active = False
        self._hovered_triangle: TriangleName = None
        self._triangle_size = 14
        self._triangle_margin = 6
        self._underexposed_tooltip = ""
        self._overexposed_tooltip = ""
        self.setMouseTracking(True)

    def set_clipping_state(self, underexposed: bool, overexposed: bool) -> None:
        """Set clipping marker states without emitting signals."""

        updated = False
        if self._underexposed_active != underexposed:
            self._underexposed_active = underexposed
            updated = True
        if self._overexposed_active != overexposed:
            self._overexposed_active = overexposed
            updated = True
        if updated:
            self.update()

    def underexposed_active(self) -> bool:
        """Return whether the underexposed marker is active."""

        return self._underexposed_active

    def overexposed_active(self) -> bool:
        """Return whether the overexposed marker is active."""

        return self._overexposed_active

    def set_triangle_tooltips(self, underexposed: str, overexposed: str) -> None:
        """Set hover tooltips for left/right triangles."""

        self._underexposed_tooltip = underexposed
        self._overexposed_tooltip = overexposed

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        """Draw base label and clipping indicator triangles."""

        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        self._paint_triangle(
            painter,
            self._left_triangle(),
            active=self._underexposed_active,
            hovered=self._hovered_triangle == "underexposed",
            semantic_color=QtGui.QColor(48, 180, 88),
        )
        self._paint_triangle(
            painter,
            self._right_triangle(),
            active=self._overexposed_active,
            hovered=self._hovered_triangle == "overexposed",
            semantic_color=QtGui.QColor(224, 68, 68),
        )
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        """Toggle clipping marker state when a triangle is clicked."""

        if event.button() == QtCore.Qt.LeftButton:
            triangle = self._triangle_at(event.pos())
            if triangle == "underexposed":
                self._underexposed_active = not self._underexposed_active
                self.underexposed_toggled.emit(self._underexposed_active)
                self.update()
                event.accept()
                return
            if triangle == "overexposed":
                self._overexposed_active = not self._overexposed_active
                self.overexposed_toggled.emit(self._overexposed_active)
                self.update()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        """Show hand cursor when hovering clipping triangles."""

        triangle = self._triangle_at(event.pos())
        self._set_hovered_triangle(triangle)
        if triangle is not None:
            self.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def event(self, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        """Handle tooltip events for clipping triangles."""

        if event.type() == QtCore.QEvent.ToolTip and isinstance(event, QtGui.QHelpEvent):
            triangle = self._triangle_at(event.pos())
            if triangle == "underexposed":
                QtWidgets.QToolTip.showText(event.globalPos(), self._underexposed_tooltip, self)
                return True
            if triangle == "overexposed":
                QtWidgets.QToolTip.showText(event.globalPos(), self._overexposed_tooltip, self)
                return True
            QtWidgets.QToolTip.hideText()
            event.ignore()
            return True
        return super().event(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # type: ignore[override]
        """Clear cursor override and hide tooltip on leave."""

        self._set_hovered_triangle(None)
        self.unsetCursor()
        QtWidgets.QToolTip.hideText()
        super().leaveEvent(event)

    def _left_triangle(self) -> QtGui.QPolygon:
        """Build polygon for the top-left clipping triangle."""

        x = self._triangle_margin
        y = self._triangle_margin
        side = self._triangle_size
        return QtGui.QPolygon(
            [
                QtCore.QPoint(x, y),
                QtCore.QPoint(x + side, y),
                QtCore.QPoint(x, y + side),
            ]
        )

    def _right_triangle(self) -> QtGui.QPolygon:
        """Build polygon for the top-right clipping triangle."""

        side = self._triangle_size
        max_x = max(0, self.width() - 1)
        desired_x = self.width() - self._triangle_margin - 1
        min_x = self._triangle_margin + side
        x_right = min(max(desired_x, min_x), max_x)
        y = self._triangle_margin
        return QtGui.QPolygon(
            [
                QtCore.QPoint(x_right, y),
                QtCore.QPoint(x_right - side, y),
                QtCore.QPoint(x_right, y + side),
            ]
        )

    def _triangle_at(self, pos: QtCore.QPoint) -> TriangleName:
        """Return the clipping triangle under the given widget position."""

        if self._left_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill):
            return "underexposed"
        if self._right_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill):
            return "overexposed"
        return None

    def _set_hovered_triangle(self, value: TriangleName) -> None:
        """Update hovered clipping marker and repaint only when it changes."""

        if self._hovered_triangle == value:
            return
        self._hovered_triangle = value
        self.update()

    def _paint_triangle(
        self,
        painter: QtGui.QPainter,
        polygon: QtGui.QPolygon,
        active: bool,
        hovered: bool,
        semantic_color: QtGui.QColor,
    ) -> None:
        """Draw a clipping indicator triangle."""

        fill_color = QtGui.QColor(semantic_color)
        fill_color.setAlpha(230 if active else 92)
        if hovered and not active:
            fill_color.setAlpha(128)

        outline_color = semantic_color.lighter(145 if hovered else 115)
        outline_width = 2 if hovered else 1

        if hovered:
            glow_color = QtGui.QColor(semantic_color)
            glow_color.setAlpha(72)
            glow_pen = QtGui.QPen(glow_color, 5)
            glow_pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(glow_pen)
            painter.drawPolygon(polygon)

        painter.setBrush(QtGui.QBrush(fill_color))
        painter.setPen(QtGui.QPen(outline_color, outline_width))
        painter.drawPolygon(polygon)

        if active:
            highlight_color = semantic_color.lighter(160)
            highlight_color.setAlpha(150)
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.setPen(QtGui.QPen(highlight_color, 1))
            painter.drawPolyline(polygon)
