"""Pointer and event interaction behavior for main controller."""

from __future__ import annotations

import logging
from html import escape
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from pic_viewer.app.services.app_metadata_service import AppMetadata, load_app_metadata
from pic_viewer.app.services.image_file_policy import filter_supported_image_paths
from pic_viewer.app.services.third_party_license_service import load_third_party_licenses
from pic_viewer.ui.resources.icons import load_app_icon
from pic_viewer.ui.windows.third_party_license_dialog import ThirdPartyLicenseDialog

logger = logging.getLogger(__name__)


class MainControllerInteractionMixin:
    """Provide cursor tracking, drag-to-pan, and context-menu helpers."""

    def _install_cursor_tracking(self) -> None:
        """Enable cursor hints near split boundaries."""

        self._set_splitter_handle_cursor()
        self._track_cursor_widget(self._ui.central)
        for widget in self._ui.central.findChildren(QtWidgets.QWidget):
            self._track_cursor_widget(widget)

    def _install_file_drop_handling(self) -> None:
        """Enable local image file drops in the central workspace."""

        self._track_file_drop_widget(self._ui.central)
        self._track_file_drop_widget(self._ui.splitMain)
        self._track_file_drop_widget(self._ui.tabsImages)
        for widget in self._ui.central.findChildren(QtWidgets.QWidget):
            self._track_file_drop_widget(widget)

    def _track_file_drop_widget(self, widget: QtWidgets.QWidget) -> None:
        if widget.property("_file_drop_area") is True:
            return
        widget.setProperty("_file_drop_area", True)
        widget.setAcceptDrops(True)
        if widget.property("_cursor_tracking") is not True:
            widget.installEventFilter(self)

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
        widget.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
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
        self._image_context_menu.exec(global_pos)

    def _show_current_image_in_folder(self) -> None:
        """Open the current image's parent directory in the platform file manager."""

        path = self._current_image_path()
        if path is None:
            logger.warning("Cannot show image in folder: no current image is active")
            self._show_in_folder_warning()
            return

        folder = path.parent
        if not folder.is_dir():
            logger.warning(
                "Cannot show image in folder: parent directory is unavailable path=%s folder=%s",
                path,
                folder,
            )
            self._show_in_folder_warning()
            return

        url = QtCore.QUrl.fromLocalFile(str(folder))
        try:
            opened = QtGui.QDesktopServices.openUrl(url)
        except Exception:
            logger.exception(
                "Cannot show image in folder: desktop service failed path=%s folder=%s",
                path,
                folder,
            )
            self._show_in_folder_warning()
            return

        if not opened:
            logger.warning(
                "Cannot show image in folder: desktop service rejected path=%s folder=%s",
                path,
                folder,
            )
            self._show_in_folder_warning()

    def _show_in_folder_warning(self) -> None:
        """Warn the user that the image folder could not be opened."""

        QtWidgets.QMessageBox.warning(
            self._main_window,
            self._tr("Warning"),
            self._tr("Unable to open the image folder."),
        )

    def _set_splitter_handle_cursor(self) -> None:
        self._set_splitter_cursor(self._ui.splitMain, QtCore.Qt.CursorShape.SplitHCursor)

    def _set_splitter_cursor(self, splitter: QtWidgets.QSplitter, cursor: QtCore.Qt.CursorShape) -> None:
        for index in range(1, splitter.count()):
            handle = splitter.handle(index)
            handle.setCursor(cursor)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if self._handle_file_drop_event(watched, event):
            return True
        if self._handle_image_wheel_zoom_event(watched, event):
            return True
        if self._handle_image_drag_event(watched, event):
            return True
        if event.type() in (QtCore.QEvent.Type.MouseMove, QtCore.QEvent.Type.Enter, QtCore.QEvent.Type.Leave):
            self._refresh_image_cursor(watched, event)
        try:
            return super().eventFilter(watched, event)
        except RuntimeError as exc:
            if "already deleted" in str(exc):
                return False
            raise

    def _handle_file_drop_event(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Accept and open supported local image files dropped on the workspace."""

        if not isinstance(watched, QtWidgets.QWidget):
            return False
        if watched.property("_file_drop_area") is not True:
            return False

        event_type = event.type()
        if event_type in (QtCore.QEvent.Type.DragEnter, QtCore.QEvent.Type.DragMove):
            if not hasattr(event, "mimeData"):
                return False
            if self._mime_data_has_supported_image_files(event.mimeData()):
                event.acceptProposedAction()
            else:
                event.ignore()
            return True

        if event_type == QtCore.QEvent.Type.Drop:
            if not hasattr(event, "mimeData"):
                return False
            has_supported = self._mime_data_has_supported_image_files(event.mimeData())
            self._open_dropped_images_from_mime_data(event.mimeData())
            if has_supported:
                event.acceptProposedAction()
            else:
                event.ignore()
            return True

        return False

    def _mime_data_has_supported_image_files(self, mime_data: QtCore.QMimeData) -> bool:
        return bool(self._supported_drop_paths(mime_data))

    def _supported_drop_paths(self, mime_data: QtCore.QMimeData) -> list[Path]:
        return filter_supported_image_paths(self._local_file_paths_from_mime_data(mime_data))

    def _local_file_paths_from_mime_data(self, mime_data: QtCore.QMimeData) -> list[Path]:
        if not mime_data.hasUrls():
            return []

        paths: list[Path] = []
        seen: set[str] = set()
        for url in mime_data.urls():
            if not url.isLocalFile():
                continue
            raw_path = url.toLocalFile()
            if not raw_path:
                continue
            path = Path(raw_path)
            key = self._drop_path_key(path)
            if key in seen:
                continue
            seen.add(key)
            paths.append(path)
        return paths

    def _drop_path_key(self, path: Path) -> str:
        try:
            return str(path.resolve())
        except OSError:
            return str(path)

    def _open_dropped_images_from_mime_data(self, mime_data: QtCore.QMimeData) -> None:
        local_paths = self._local_file_paths_from_mime_data(mime_data)
        supported_paths = filter_supported_image_paths(local_paths)
        if not supported_paths:
            self._show_no_supported_drop_files_message()
            return

        skipped_count = len(local_paths) - len(supported_paths)
        if skipped_count > 0:
            self._show_skipped_drop_files_message(skipped_count)
        self._open_image_paths(supported_paths)

    def _show_no_supported_drop_files_message(self) -> None:
        QtWidgets.QMessageBox.information(
            self._main_window,
            self._tr("Info"),
            self._tr("No supported image files were found in the dropped files."),
        )

    def _show_skipped_drop_files_message(self, skipped_count: int) -> None:
        if skipped_count <= 0:
            return
        if not hasattr(self, "_main_window"):
            return
        self._main_window.statusBar().showMessage(
            self._tr("Skipped {count} unsupported file(s).").format(count=skipped_count),
            5000,
        )

    def _handle_image_wheel_zoom_event(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Convert mouse-wheel events in the image preview area into zoom actions."""

        if not isinstance(watched, QtWidgets.QWidget):
            return False
        if watched.property("_image_zoom_area") is not True:
            return False
        if event.type() != QtCore.QEvent.Type.Wheel:
            return False
        if not hasattr(event, "angleDelta") or not hasattr(event, "pixelDelta"):
            return False

        delta_y = event.angleDelta().y()
        if delta_y == 0:
            delta_y = event.pixelDelta().y()
        if delta_y > 0:
            self._zoom_in()
        elif delta_y < 0:
            self._zoom_out()
        else:
            return False

        event.accept()
        return True

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
            QtCore.QEvent.Type.MouseButtonPress,
            QtCore.QEvent.Type.MouseButtonRelease,
            QtCore.QEvent.Type.MouseMove,
        ):
            if not isinstance(event, QtGui.QMouseEvent):
                return False

        if event_type == QtCore.QEvent.Type.MouseButtonPress:
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
                return False
            if not self._can_drag_image(scroll_area):
                return False
            self._image_dragging = True
            self._image_drag_start_pos = event.globalPosition().toPoint()
            self._image_drag_start_scroll = QtCore.QPoint(
                scroll_area.horizontalScrollBar().value(),
                scroll_area.verticalScrollBar().value(),
            )
            self._image_drag_scroll_area = scroll_area
            scroll_area.viewport().grabMouse()
            self._set_image_drag_cursor(scroll_area, True)
            return True

        if event_type == QtCore.QEvent.Type.MouseMove and self._image_dragging:
            if self._image_drag_scroll_area is None or self._image_drag_start_pos is None:
                return False
            delta = event.globalPosition().toPoint() - self._image_drag_start_pos
            hbar = self._image_drag_scroll_area.horizontalScrollBar()
            vbar = self._image_drag_scroll_area.verticalScrollBar()
            start = self._image_drag_start_scroll or QtCore.QPoint(hbar.value(), vbar.value())
            hbar.setValue(start.x() - delta.x())
            vbar.setValue(start.y() - delta.y())
            return True

        if event_type == QtCore.QEvent.Type.MouseButtonRelease and self._image_dragging:
            if event.button() != QtCore.Qt.MouseButton.LeftButton:
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
        if event.type() not in (QtCore.QEvent.Type.MouseMove, QtCore.QEvent.Type.Enter):
            return
        if not isinstance(watched, QtWidgets.QWidget):
            return
        if watched.property("_image_drag_area") is not True:
            return
        scroll_area = self._resolve_image_scroll_area(watched)
        if scroll_area is None:
            watched.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
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

        cursor = QtCore.Qt.CursorShape.ClosedHandCursor if dragging else QtCore.Qt.CursorShape.OpenHandCursor
        scroll_area.setCursor(cursor)
        scroll_area.viewport().setCursor(cursor)
        widget = scroll_area.widget()
        if widget is not None:
            widget.setCursor(cursor)

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
        metadata = load_app_metadata()
        message_box = QtWidgets.QMessageBox(self._main_window)
        message_box.setWindowTitle(self._tr("About"))
        message_box.setTextFormat(QtCore.Qt.TextFormat.RichText)
        message_box.setText(self._build_about_text(metadata))
        message_box.setIconPixmap(load_app_icon().pixmap(64, 64))
        message_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        message_box.exec()

    def _show_third_party_licenses(self) -> None:
        licenses = load_third_party_licenses()
        dialog = ThirdPartyLicenseDialog(licenses, self._main_window)
        dialog.exec()

    def _build_about_text(self, metadata: AppMetadata) -> str:
        return self._tr(
            '<div style="font-size: 12pt;">'
            '<p><strong>{name}</strong><br>'
            '<strong>Version {version}</strong></p>'
            '<p class="about-light" style="font-weight: 300;">'
            "A desktop photo viewer for common image formats and camera RAW files."
            "</p>"
            '<p class="about-light" style="font-weight: 300;">'
            "Copyright (c) {years} {owner}. All rights reserved."
            "</p>"
            "</div>"
        ).format(
            name=escape(metadata.name),
            version=escape(metadata.version),
            years=escape(metadata.copyright_years),
            owner=escape(metadata.copyright_owner),
        )
