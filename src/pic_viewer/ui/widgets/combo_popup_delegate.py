"""Item delegate for theme-aware combo box popup rows."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class ComboPopupItemDelegate(QtWidgets.QStyledItemDelegate):
    """Paint combo popup rows using the view palette for reliable highlighting."""

    def paint(
        self,
        painter: QtGui.QPainter,
        option: QtWidgets.QStyleOptionViewItem,
        index: QtCore.QModelIndex,
    ) -> None:
        """Draw one popup row with full-row hover and selected backgrounds."""

        view_option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(view_option, index)
        highlighted = bool(
            view_option.state
            & (
                QtWidgets.QStyle.StateFlag.State_MouseOver
                | QtWidgets.QStyle.StateFlag.State_Selected
            )
        )
        background_role = (
            QtGui.QPalette.ColorRole.Highlight
            if highlighted
            else QtGui.QPalette.ColorRole.Base
        )
        text_role = (
            QtGui.QPalette.ColorRole.HighlightedText
            if highlighted
            else QtGui.QPalette.ColorRole.Text
        )

        painter.save()
        try:
            painter.fillRect(view_option.rect, view_option.palette.color(background_role))
            painter.setPen(view_option.palette.color(text_role))
            painter.setFont(view_option.font)
            text_rect = view_option.rect.adjusted(8, 0, -8, 0)
            elided_text = view_option.fontMetrics.elidedText(
                view_option.text,
                QtCore.Qt.TextElideMode.ElideRight,
                text_rect.width(),
            )
            painter.drawText(
                text_rect,
                QtCore.Qt.AlignmentFlag.AlignLeft
                | QtCore.Qt.AlignmentFlag.AlignVCenter,
                elided_text,
            )
        finally:
            painter.restore()
