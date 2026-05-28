"""Detachable tab widgets with floating-window reattachment support."""

from __future__ import annotations

from dataclasses import dataclass
import itertools
import json
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets


DETACHED_TAB_MIME_TYPE = "application/x-picviewer-detached-tab"

_token_counter = itertools.count(1)
_floating_windows_by_token: dict[str, "FloatingTabWindow"] = {}


@dataclass(frozen=True)
class DetachedTabPayload:
    """Serializable drag payload for moving floating tabs back to a tab widget."""

    group: str
    token: str

    def to_mime_data(self) -> QtCore.QMimeData:
        """Return MIME data that can be carried by a Qt drag operation."""

        data = json.dumps({"group": self.group, "token": self.token}).encode("utf-8")
        mime_data = QtCore.QMimeData()
        mime_data.setData(DETACHED_TAB_MIME_TYPE, QtCore.QByteArray(data))
        return mime_data

    @classmethod
    def from_mime_data(cls, mime_data: QtCore.QMimeData) -> Optional["DetachedTabPayload"]:
        """Parse a detached-tab payload from MIME data if one is present."""

        if not mime_data.hasFormat(DETACHED_TAB_MIME_TYPE):
            return None
        raw = bytes(mime_data.data(DETACHED_TAB_MIME_TYPE)).decode("utf-8")
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        group = payload.get("group")
        token = payload.get("token")
        if not isinstance(group, str) or not isinstance(token, str):
            return None
        return cls(group=group, token=token)


@dataclass
class _DetachedTabRecord:
    group: str
    widget: QtWidgets.QWidget
    title: str
    icon: QtGui.QIcon
    tooltip: str
    enabled: bool
    original_index: int
    was_current: bool


class DetachableTabBar(QtWidgets.QTabBar):
    """Tab bar that detaches a tab when it is dragged outside the bar."""

    def __init__(self, owner: "DetachableTabWidget") -> None:
        super().__init__(owner)
        self._owner = owner
        self._drag_start_pos: Optional[QtCore.QPoint] = None
        self._drag_start_index = -1
        self.setAcceptDrops(True)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            self._drag_start_index = self.tabAt(self._drag_start_pos)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if self._should_detach_from_mouse_move(event):
            self._start_detach_drag(event)
            return
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        if self._owner.can_accept_detached_tab(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:  # type: ignore[override]
        if self._owner.can_accept_detached_tab(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:  # type: ignore[override]
        index = self._drop_insert_index(event.position().toPoint())
        if self._owner.drop_detached_tab(event.mimeData(), index):
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _should_detach_from_mouse_move(self, event: QtGui.QMouseEvent) -> bool:
        if self._drag_start_pos is None or self._drag_start_index < 0:
            return False
        if not event.buttons() & QtCore.Qt.MouseButton.LeftButton:
            return False
        delta = event.position().toPoint() - self._drag_start_pos
        if delta.manhattanLength() < QtWidgets.QApplication.startDragDistance():
            return False
        if self.rect().contains(event.position().toPoint()):
            return False
        return self._owner.is_tab_detachable(self._drag_start_index)

    def _start_detach_drag(self, event: QtGui.QMouseEvent) -> None:
        index = self._drag_start_index
        self._drag_start_pos = None
        self._drag_start_index = -1
        if index < 0:
            return
        floating = self._owner.detach_tab(index, event.globalPosition().toPoint(), show=False)
        drag = QtGui.QDrag(self)
        drag.setMimeData(floating.drag_payload().to_mime_data())
        drag.exec(QtCore.Qt.DropAction.MoveAction)
        if floating.content_widget() is not None:
            floating.move(event.globalPosition().toPoint() - QtCore.QPoint(48, 12))
            floating.show()
            floating.activateWindow()

    def _drop_insert_index(self, pos: QtCore.QPoint) -> int:
        index = self.tabAt(pos)
        if index < 0:
            return self._owner.count()
        tab_rect = self.tabRect(index)
        if pos.x() > tab_rect.center().x():
            return index + 1
        return index


class FloatingTabWindow(QtWidgets.QWidget):
    """Top-level window that owns one detached tab until it is returned."""

    activated = QtCore.Signal(object)

    def __init__(
        self,
        owner: "DetachableTabWidget",
        record: _DetachedTabRecord,
        token: str,
    ) -> None:
        super().__init__(None, QtCore.Qt.WindowType.Window)
        self._owner = owner
        self._record = record
        self._token = token
        self._content_widget: Optional[QtWidgets.QWidget] = record.widget
        self._return_on_close = True
        self.setObjectName("floatingTabWindow")
        self.setWindowTitle(record.title)
        self.resize(max(360, record.widget.width()), max(280, record.widget.height()))

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)

        self._content_host = QtWidgets.QWidget(self)
        self._content_host.setObjectName("floatingTabContent")
        self._content_layout = QtWidgets.QVBoxLayout(self._content_host)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._content_layout.addWidget(record.widget)
        record.widget.show()
        layout.addWidget(self._content_host, 1)

    def tab_group(self) -> str:
        """Return the compatible tab group for this floating window."""

        return self._record.group

    def parent_tab_widget(self) -> "DetachableTabWidget":
        """Return the tab widget that owns this floating window."""

        return self._owner

    def token(self) -> str:
        """Return this floating tab's in-process drag token."""

        return self._token

    def original_index(self) -> int:
        """Return the tab index this content had before it was detached."""

        return self._record.original_index

    def content_widget(self) -> Optional[QtWidgets.QWidget]:
        """Return the detached content widget while it is still floating."""

        return self._content_widget

    def drag_payload(self) -> DetachedTabPayload:
        """Return the drag payload used to dock this window into a tab widget."""

        return DetachedTabPayload(group=self._record.group, token=self._token)

    def return_to_tabs(self, index: Optional[int] = None) -> bool:
        """Dock this floating tab back into its owning tab widget."""

        return self._owner.reattach_floating_window(self, index)

    def take_content_for_close(self) -> Optional[QtWidgets.QWidget]:
        """Detach content for permanent close without returning to the tab bar."""

        self._return_on_close = False
        widget = self._take_content_widget()
        _floating_windows_by_token.pop(self._token, None)
        self.hide()
        self.deleteLater()
        return widget

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        if self._return_on_close and self._content_widget is not None:
            self.return_to_tabs()
        event.accept()

    def event(self, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if event.type() == QtCore.QEvent.Type.WindowActivate:
            self.activated.emit(self)
        return super().event(event)

    def _take_content_widget(self) -> Optional[QtWidgets.QWidget]:
        widget = self._content_widget
        if widget is None:
            return None
        self._content_layout.removeWidget(widget)
        widget.setParent(None)
        self._content_widget = None
        return widget

    def _mark_reattached(self) -> None:
        self._return_on_close = False
        _floating_windows_by_token.pop(self._token, None)
        self.hide()

    def detached_widget(self) -> QtWidgets.QWidget:
        """Return the tab content widget even after it has been reattached."""

        return self._record.widget


class DetachableTabWidget(QtWidgets.QTabWidget):
    """QTabWidget variant whose tabs can be detached into floating windows."""

    tab_detached = QtCore.Signal(object)
    tab_reattached = QtCore.Signal(object)
    floating_window_activated = QtCore.Signal(object)

    def __init__(self, tab_group: str, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._tab_group = tab_group
        self.setAcceptDrops(True)
        self.setTabBar(DetachableTabBar(self))

    def tab_group(self) -> str:
        """Return the group name used to prevent cross-container drops."""

        return self._tab_group

    def set_tab_detachable(self, index: int, detachable: bool) -> None:
        """Enable or disable detaching for a specific tab by index."""

        widget = self.widget(index)
        if widget is not None:
            widget.setProperty("_detachable_tab_enabled", detachable)

    def is_tab_detachable(self, index: int) -> bool:
        """Return whether the tab at index can be detached."""

        widget = self.widget(index)
        if widget is None:
            return False
        return widget.property("_detachable_tab_enabled") is not False

    def detach_tab(
        self,
        index: int,
        global_pos: Optional[QtCore.QPoint] = None,
        *,
        show: bool = True,
    ) -> FloatingTabWindow:
        """Detach a tab into a floating window and return the new window."""

        if index < 0 or index >= self.count():
            raise IndexError(f"Tab index out of range: {index}")
        if not self.is_tab_detachable(index):
            raise ValueError(f"Tab is not detachable: {index}")

        widget = self.widget(index)
        if widget is None:
            raise ValueError(f"Tab has no widget: {index}")
        record = _DetachedTabRecord(
            group=self._tab_group,
            widget=widget,
            title=self.tabText(index),
            icon=self.tabIcon(index),
            tooltip=self.tabToolTip(index),
            enabled=self.isTabEnabled(index),
            original_index=index,
            was_current=index == self.currentIndex(),
        )
        self.removeTab(index)
        widget.setParent(None)
        token = f"{self._tab_group}-{next(_token_counter)}"
        floating = FloatingTabWindow(self, record, token)
        floating.activated.connect(self.floating_window_activated.emit)
        floating.setStyleSheet(self.window().styleSheet())
        _floating_windows_by_token[token] = floating
        if global_pos is not None:
            floating.move(global_pos - QtCore.QPoint(48, 12))
        if show:
            floating.show()
            floating.activateWindow()
        self.tab_detached.emit(floating)
        return floating

    def can_accept_detached_tab(self, mime_data: QtCore.QMimeData) -> bool:
        """Return whether MIME data identifies a compatible floating tab."""

        payload = DetachedTabPayload.from_mime_data(mime_data)
        if payload is None or payload.group != self._tab_group:
            return False
        floating = _floating_windows_by_token.get(payload.token)
        return floating is not None and floating.content_widget() is not None

    def drop_detached_tab(self, mime_data: QtCore.QMimeData, index: Optional[int] = None) -> bool:
        """Dock the floating tab identified by MIME data into this widget."""

        payload = DetachedTabPayload.from_mime_data(mime_data)
        if payload is None or payload.group != self._tab_group:
            return False
        floating = _floating_windows_by_token.get(payload.token)
        if floating is None:
            return False
        return self.reattach_floating_window(floating, index)

    def reattach_floating_window(
        self,
        floating: FloatingTabWindow,
        index: Optional[int] = None,
    ) -> bool:
        """Reinsert a floating tab into this tab widget."""

        if floating.tab_group() != self._tab_group:
            return False
        widget = floating._take_content_widget()
        if widget is None:
            return False
        target_index = self._normalized_insert_index(index, floating.original_index())
        inserted = self.insertTab(target_index, widget, floating._record.icon, floating._record.title)
        self.setTabToolTip(inserted, floating._record.tooltip)
        self.setTabEnabled(inserted, floating._record.enabled)
        self.setCurrentIndex(inserted)
        floating._mark_reattached()
        self.tab_reattached.emit(floating)
        return True

    def apply_floating_stylesheet(self, style_sheet: str) -> None:
        """Apply the current app theme to floating windows owned by this widget."""

        for floating in _floating_windows_by_token.values():
            if floating.parent_tab_widget() is self:
                floating.setStyleSheet(style_sheet)

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        if self.can_accept_detached_tab(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QtGui.QDragMoveEvent) -> None:  # type: ignore[override]
        if self.can_accept_detached_tab(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QtGui.QDropEvent) -> None:  # type: ignore[override]
        if self.drop_detached_tab(event.mimeData(), self.count()):
            event.acceptProposedAction()
            return
        super().dropEvent(event)

    def _normalized_insert_index(self, index: Optional[int], fallback: int) -> int:
        if index is None:
            index = fallback
        return max(0, min(index, self.count()))
