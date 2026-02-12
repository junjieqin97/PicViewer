"""Histogram label with clickable clipping warning triangles."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets


class HistogramClippingLabel(QtWidgets.QLabel):
    """QLabel variant that renders and toggles histogram clipping markers."""

    underexposed_toggled = QtCore.pyqtSignal(bool)
    overexposed_toggled = QtCore.pyqtSignal(bool)

    def __init__(self, text: str = "", parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._underexposed_active = False
        self._overexposed_active = False
        self._triangle_size = 12
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
            active_color=QtGui.QColor(0, 200, 0),
        )
        self._paint_triangle(
            painter,
            self._right_triangle(),
            active=self._overexposed_active,
            active_color=QtGui.QColor(220, 40, 40),
        )
        painter.end()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        """Toggle clipping marker state when a triangle is clicked."""

        if event.button() == QtCore.Qt.LeftButton:
            pos = event.pos()
            if self._left_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill):
                self._underexposed_active = not self._underexposed_active
                self.underexposed_toggled.emit(self._underexposed_active)
                self.update()
                event.accept()
                return
            if self._right_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill):
                self._overexposed_active = not self._overexposed_active
                self.overexposed_toggled.emit(self._overexposed_active)
                self.update()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        """Show hand cursor when hovering clipping triangles."""

        pos = event.pos()
        if self._left_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill) or self._right_triangle().containsPoint(
            pos, QtCore.Qt.OddEvenFill
        ):
            self.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self.unsetCursor()
        super().mouseMoveEvent(event)

    def event(self, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        """Handle tooltip events for clipping triangles."""

        if event.type() == QtCore.QEvent.ToolTip and isinstance(event, QtGui.QHelpEvent):
            pos = event.pos()
            if self._left_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill):
                QtWidgets.QToolTip.showText(event.globalPos(), self._underexposed_tooltip, self)
                return True
            if self._right_triangle().containsPoint(pos, QtCore.Qt.OddEvenFill):
                QtWidgets.QToolTip.showText(event.globalPos(), self._overexposed_tooltip, self)
                return True
            QtWidgets.QToolTip.hideText()
            event.ignore()
            return True
        return super().event(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:  # type: ignore[override]
        """Clear cursor override and hide tooltip on leave."""

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

    def _paint_triangle(
        self,
        painter: QtGui.QPainter,
        polygon: QtGui.QPolygon,
        active: bool,
        active_color: QtGui.QColor,
    ) -> None:
        """Draw a clipping indicator triangle."""

        color = active_color if active else QtGui.QColor(120, 120, 120)
        painter.setBrush(QtGui.QBrush(color))
        painter.setPen(QtGui.QPen(QtGui.QColor(30, 30, 30), 1))
        painter.drawPolygon(polygon)
