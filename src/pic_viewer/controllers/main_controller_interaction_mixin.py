"""Pointer and event interaction behavior for main controller."""

from __future__ import annotations

from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class MainControllerInteractionMixin:
    """Provide cursor tracking, drag-to-pan, and context-menu helpers."""

    def _install_cursor_tracking(self) -> None:
        """Enable cursor hints near split boundaries."""

        self._set_splitter_handle_cursor()
        self._track_cursor_widget(self._ui.central)
        for widget in self._ui.central.findChildren(QtWidgets.QWidget):
            self._track_cursor_widget(widget)

    def _track_cursor_widget(self, widget: QtWidgets.QWidget) -> None:
        if widget.property("_cursor_tracking") is True:
            return
        widget.setProperty("_cursor_tracking", True)
        widget.setMouseTracking(True)
        widget.installEventFilter(self)

    def _install_image_context_menu(self, widget: QtWidgets.QWidget) -> None:
        """Enable custom context menu on the image display widgets."""

        if widget.property("_image_context_menu") is True:
            return
        widget.setProperty("_image_context_menu", True)
        widget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(self._show_image_context_menu)

    def _show_image_context_menu(self, pos: QtCore.QPoint) -> None:
        """Show the image context menu at the requested position."""

        if self._image_context_menu is None:
            return
        sender = self.sender()
        if isinstance(sender, QtWidgets.QWidget):
            global_pos = sender.mapToGlobal(pos)
        else:
            global_pos = QtGui.QCursor.pos()
        self._refresh_actions_state()
        self._image_context_menu.exec_(global_pos)

    def _set_splitter_handle_cursor(self) -> None:
        self._set_splitter_cursor(self._ui.splitMain, QtCore.Qt.SplitHCursor)
        self._set_splitter_cursor(self._ui.splitVertical, QtCore.Qt.SplitVCursor)

    def _set_splitter_cursor(self, splitter: QtWidgets.QSplitter, cursor: QtCore.Qt.CursorShape) -> None:
        for index in range(1, splitter.count()):
            handle = splitter.handle(index)
            handle.setCursor(cursor)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if self._handle_image_drag_event(watched, event):
            return True
        if event.type() in (QtCore.QEvent.MouseMove, QtCore.QEvent.Enter, QtCore.QEvent.Leave):
            self._update_boundary_cursor()
            self._refresh_image_cursor(watched, event)
        return super().eventFilter(watched, event)

    def _handle_image_drag_event(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Handle drag-to-pan interactions inside image scroll areas."""

        if not isinstance(watched, QtWidgets.QWidget):
            return False
        if watched.property("_image_drag_area") is not True:
            return False
        scroll_area = self._resolve_image_scroll_area(watched)
        if scroll_area is None:
            return False

        event_type = event.type()
        if event_type in (
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.MouseMove,
        ):
            if not isinstance(event, QtGui.QMouseEvent):
                return False

        if event_type == QtCore.QEvent.MouseButtonPress:
            if event.button() != QtCore.Qt.LeftButton:
                return False
            if not self._can_drag_image(scroll_area):
                return False
            self._image_dragging = True
            self._image_drag_start_pos = event.globalPos()
            self._image_drag_start_scroll = QtCore.QPoint(
                scroll_area.horizontalScrollBar().value(),
                scroll_area.verticalScrollBar().value(),
            )
            self._image_drag_scroll_area = scroll_area
            scroll_area.viewport().grabMouse()
            self._set_image_drag_cursor(scroll_area, True)
            return True

        if event_type == QtCore.QEvent.MouseMove and self._image_dragging:
            if self._image_drag_scroll_area is None or self._image_drag_start_pos is None:
                return False
            delta = event.globalPos() - self._image_drag_start_pos
            hbar = self._image_drag_scroll_area.horizontalScrollBar()
            vbar = self._image_drag_scroll_area.verticalScrollBar()
            start = self._image_drag_start_scroll or QtCore.QPoint(hbar.value(), vbar.value())
            hbar.setValue(start.x() - delta.x())
            vbar.setValue(start.y() - delta.y())
            return True

        if event_type == QtCore.QEvent.MouseButtonRelease and self._image_dragging:
            if event.button() != QtCore.Qt.LeftButton:
                return False
            self._image_dragging = False
            if self._image_drag_scroll_area is not None:
                self._image_drag_scroll_area.viewport().releaseMouse()
                self._set_image_drag_cursor(self._image_drag_scroll_area, False)
            self._image_drag_start_pos = None
            self._image_drag_start_scroll = None
            self._image_drag_scroll_area = None
            return True

        return False

    def _refresh_image_cursor(self, watched: QtCore.QObject, event: QtCore.QEvent) -> None:
        """Ensure the hand cursor appears over the image area."""

        if self._image_dragging:
            return
        if self._cursor_override_target is not None:
            return
        if event.type() not in (QtCore.QEvent.MouseMove, QtCore.QEvent.Enter):
            return
        if not isinstance(watched, QtWidgets.QWidget):
            return
        if watched.property("_image_drag_area") is not True:
            return
        scroll_area = self._resolve_image_scroll_area(watched)
        if scroll_area is None:
            watched.setCursor(QtCore.Qt.OpenHandCursor)
            return
        self._set_image_drag_cursor(scroll_area, False)

    def _resolve_image_scroll_area(self, widget: QtWidgets.QWidget) -> Optional[QtWidgets.QScrollArea]:
        """Resolve the image scroll area from any child widget."""

        current: Optional[QtWidgets.QWidget] = widget
        while current is not None:
            if isinstance(current, QtWidgets.QScrollArea) and current.objectName() == "scrollImage":
                return current
            current = current.parentWidget()
        return None

    def _can_drag_image(self, scroll_area: QtWidgets.QScrollArea) -> bool:
        """Return True when the image is larger than the viewport."""

        hbar = scroll_area.horizontalScrollBar()
        vbar = scroll_area.verticalScrollBar()
        return hbar.maximum() > 0 or vbar.maximum() > 0

    def _set_image_drag_cursor(self, scroll_area: QtWidgets.QScrollArea, dragging: bool) -> None:
        """Update the cursor for image drag interactions."""

        cursor = QtCore.Qt.ClosedHandCursor if dragging else QtCore.Qt.OpenHandCursor
        scroll_area.setCursor(cursor)
        scroll_area.viewport().setCursor(cursor)
        widget = scroll_area.widget()
        if widget is not None:
            widget.setCursor(cursor)

    def _update_boundary_cursor(self) -> None:
        """Show resize cursor when hovering over the filmstrip boundary."""

        if not self._ui.frameFilmstrip.isVisible():
            self._clear_cursor_override()
            return

        global_pos = QtGui.QCursor.pos()
        if not self._is_near_filmstrip_boundary(global_pos):
            self._clear_cursor_override()
            return

        target = QtWidgets.QApplication.widgetAt(global_pos)
        if target is None or target.window() is not self._main_window:
            self._clear_cursor_override()
            return

        self._apply_cursor_override(target, QtCore.Qt.SplitVCursor)

    def _is_near_filmstrip_boundary(self, global_pos: QtCore.QPoint) -> bool:
        """Return True when the cursor is near the top edge of the filmstrip."""

        split_bottom = self._ui.splitMain.mapToGlobal(
            QtCore.QPoint(0, self._ui.splitMain.height())
        ).y()
        film_top = self._ui.frameFilmstrip.mapToGlobal(QtCore.QPoint(0, 0)).y()
        y = global_pos.y()
        if y < split_bottom - self._cursor_boundary_margin:
            return False
        if y > film_top + self._cursor_boundary_margin:
            return False

        left = self._ui.central.mapToGlobal(QtCore.QPoint(0, 0)).x()
        right = left + self._ui.central.width()
        return left <= global_pos.x() <= right

    def _apply_cursor_override(self, widget: QtWidgets.QWidget, cursor: QtCore.Qt.CursorShape) -> None:
        if self._cursor_override_target is widget and widget.cursor().shape() == cursor:
            return
        self._clear_cursor_override()
        widget.setCursor(cursor)
        self._cursor_override_target = widget

    def _clear_cursor_override(self) -> None:
        if self._cursor_override_target is None:
            return
        self._cursor_override_target.unsetCursor()
        self._cursor_override_target = None

    def _todo_not_implemented(self) -> None:
        QtWidgets.QMessageBox.information(
            self._main_window,
            self._tr("Info"),
            self._tr("This feature is not implemented yet (TODO)."),
        )

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.information(
            self._main_window,
            self._tr("About"),
            self._tr("PicViewer\nA simple image viewer demo."),
        )
