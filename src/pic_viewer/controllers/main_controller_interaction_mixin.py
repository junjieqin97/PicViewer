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
from pic_viewer.domain.rules.pixel_sample import (
    DEFAULT_COLOR_READOUT_TYPE,
    ColorReadout,
    ColorReadoutType,
    INVALID_PIXEL_SAMPLE,
    PixelSample,
    sample_analysis_pixel,
)
from pic_viewer.domain.models.bit_depth import ChannelBitDepth
from pic_viewer.ui.resources import styles
from pic_viewer.ui.resources.icons import load_app_icon
from pic_viewer.ui.utils.signal_blocker import block_signals
from pic_viewer.ui.widgets.image_display_label import ImageDisplayLabel
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
        if self._handle_image_viewport_resize_event(watched, event):
            return False
        if self._handle_file_drop_event(watched, event):
            return True
        if self._handle_color_readout_event(watched, event):
            return True
        if self._handle_image_wheel_zoom_event(watched, event):
            return True
        if self._handle_image_drag_event(watched, event):
            return True
        self._handle_pixel_sample_event(watched, event)
        if event.type() in (QtCore.QEvent.Type.MouseMove, QtCore.QEvent.Type.Enter, QtCore.QEvent.Type.Leave):
            self._refresh_image_cursor(watched, event)
        try:
            return super().eventFilter(watched, event)
        except RuntimeError as exc:
            if "already deleted" in str(exc):
                return False
            raise

    def _handle_image_viewport_resize_event(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Refresh the current full image when its viewport changes size."""

        if event.type() != QtCore.QEvent.Type.Resize:
            return False
        if not isinstance(watched, QtWidgets.QWidget):
            return False
        if watched.property("_image_viewport_refresh") is not True:
            return False
        path = self._current_image_path()
        if path is None:
            return False
        if str(path) not in getattr(self, "_images_by_path", {}):
            return False
        self._refresh_current_image_pixmap()
        return False

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

    def _on_add_color_readout_triggered(self, checked: bool = False) -> None:
        """Toggle the persistent color readout add interaction mode."""

        self._set_color_readout_mode("add" if checked else None)

    def _on_delete_color_readout_triggered(self, checked: bool = False) -> None:
        """Toggle the persistent color readout delete interaction mode."""

        self._set_color_readout_mode("delete" if checked else None)

    def _on_delete_all_color_readouts_triggered(self, _checked: bool = False) -> None:
        """Remove all persistent color readouts from the current image."""

        current_path = self._current_image_path()
        if current_path is None:
            self._sync_color_readout_actions()
            return
        readouts_by_path = getattr(self, "_color_readouts_by_path", None)
        if readouts_by_path is None:
            self._color_readouts_by_path = {}
            self._sync_color_readout_actions()
            return
        key = str(current_path)
        if not readouts_by_path.get(key):
            self._sync_color_readout_actions()
            return
        readouts_by_path[key] = []
        self._sync_color_readouts_for_path(current_path)
        self._sync_color_readout_actions()
        self._sync_color_readout_cursors()

    def _set_color_readout_mode(self, mode: str | None) -> None:
        if mode not in (None, "add", "delete"):
            return
        self._color_readout_mode = mode
        self._sync_color_readout_actions()
        self._sync_color_readout_cursors()

    def _handle_color_readout_event(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        """Add or delete fixed color readouts in the active readout mode."""

        mode = getattr(self, "_color_readout_mode", None)
        if mode is None:
            return False
        if event.type() != QtCore.QEvent.Type.MouseButtonPress:
            return False
        if not isinstance(event, QtGui.QMouseEvent):
            return False
        if event.button() != QtCore.Qt.MouseButton.LeftButton:
            return False
        if not isinstance(watched, QtWidgets.QWidget):
            return False

        label = self._image_label_for_widget(watched)
        if label is None:
            return False
        path = self._image_path_for_widget(label)
        current_path = self._current_image_path()
        if path is None or current_path is None or path != current_path:
            return True
        data = self._images_by_path.get(str(path))
        if data is None:
            return True

        label_pos = label.mapFrom(watched, event.position().toPoint())
        if mode == "add":
            self._add_color_readout_at(label, path, data.analysis.analysis_bgr, label_pos)
            return True
        if mode == "delete":
            self._delete_color_readout_at(label, path, label_pos)
            return True
        return False

    def _add_color_readout_at(
        self,
        label: ImageDisplayLabel,
        path: Path,
        analysis_bgr,
        label_pos: QtCore.QPoint,
    ) -> None:
        pixel_pos = label.image_pixel_position_at(label_pos, analysis_bgr.shape[:2])
        if pixel_pos is None:
            return
        x, y = pixel_pos
        sample = sample_analysis_pixel(analysis_bgr, x, y)
        if sample == INVALID_PIXEL_SAMPLE:
            return
        readout = ColorReadout(
            readout_id=self._next_color_readout_id,
            x=x,
            y=y,
            sample=sample,
            bit_depth=ChannelBitDepth.from_dtype(analysis_bgr.dtype),
        )
        self._next_color_readout_id += 1
        key = str(path)
        self._color_readouts_by_path.setdefault(key, []).append(readout)
        self._sync_color_readouts_for_path(path)
        self._sync_color_readout_actions()

    def _delete_color_readout_at(
        self,
        label: ImageDisplayLabel,
        path: Path,
        label_pos: QtCore.QPoint,
    ) -> None:
        readout_id = label.color_readout_id_at(label_pos)
        if readout_id is None:
            return
        key = str(path)
        current = self._color_readouts_by_path.get(key, [])
        self._color_readouts_by_path[key] = [readout for readout in current if readout.readout_id != readout_id]
        self._sync_color_readouts_for_path(path)
        self._sync_color_readout_actions()
        self._sync_color_readout_cursors()

    def _refresh_color_readouts_for_path(self, path: Path, analysis_bgr) -> None:
        """Resample stored color readouts when analysis data changes."""

        key = str(path)
        readouts_by_path = getattr(self, "_color_readouts_by_path", None)
        if readouts_by_path is None:
            self._color_readouts_by_path = {}
            readouts_by_path = self._color_readouts_by_path
        current = readouts_by_path.get(key)
        if not current:
            self._sync_color_readouts_for_path(path)
            self._sync_color_readout_actions()
            return
        if not hasattr(analysis_bgr, "shape") or len(analysis_bgr.shape) < 2:
            return
        height, width = analysis_bgr.shape[:2]
        if height <= 0 or width <= 0:
            return
        refreshed: list[ColorReadout] = []
        for readout in current:
            x = min(width - 1, max(0, readout.x))
            y = min(height - 1, max(0, readout.y))
            refreshed.append(
                ColorReadout(
                    readout_id=readout.readout_id,
                    x=x,
                    y=y,
                    sample=sample_analysis_pixel(analysis_bgr, x, y),
                    bit_depth=ChannelBitDepth.from_dtype(analysis_bgr.dtype),
                )
            )
        readouts_by_path[key] = refreshed
        self._sync_color_readouts_for_path(path)
        self._sync_color_readout_actions()

    def _sync_color_readouts_for_path(self, path: Path) -> None:
        """Apply one image path's readout list to every matching image label."""

        key = str(path)
        readouts = tuple(getattr(self, "_color_readouts_by_path", {}).get(key, []))
        data = getattr(self, "_images_by_path", {}).get(key)
        image_size = data.analysis.analysis_bgr.shape[:2] if data is not None else None
        theme = getattr(self._ui, "_appearance_theme", styles.AppearanceTheme.DARK)
        readout_type = getattr(self, "_color_readout_type", DEFAULT_COLOR_READOUT_TYPE)
        for tab in self._all_image_tab_widgets():
            if self._tab_path(tab) != path:
                continue
            for label in tab.findChildren(ImageDisplayLabel, "lblImage"):
                label.set_color_readout_theme(theme)
                label.set_color_readout_type(readout_type)
                label.set_color_readouts(readouts, image_size)

    def _apply_color_readouts_to_label(self, label: QtWidgets.QLabel) -> None:
        """Apply current color readouts to a newly created image label."""

        if not isinstance(label, ImageDisplayLabel):
            return
        path = self._image_path_for_widget(label)
        if path is None:
            return
        key = str(path)
        data = getattr(self, "_images_by_path", {}).get(key)
        image_size = data.analysis.analysis_bgr.shape[:2] if data is not None else None
        theme = getattr(self._ui, "_appearance_theme", styles.AppearanceTheme.DARK)
        readout_type = getattr(self, "_color_readout_type", DEFAULT_COLOR_READOUT_TYPE)
        label.set_color_readout_theme(theme)
        label.set_color_readout_type(readout_type)
        label.set_color_readouts(tuple(getattr(self, "_color_readouts_by_path", {}).get(key, [])), image_size)

    def _set_color_readout_type(self, readout_type: ColorReadoutType) -> None:
        """Set the global fixed color readout format and repaint every label."""

        if not isinstance(readout_type, ColorReadoutType):
            return
        self._color_readout_type = readout_type
        self._sync_color_readout_type_actions()
        for tab in self._all_image_tab_widgets():
            for label in tab.findChildren(ImageDisplayLabel, "lblImage"):
                label.set_color_readout_type(readout_type)

    def _sync_color_readout_type_actions(self) -> None:
        """Keep the global color readout type actions mutually synchronized."""

        readout_type = getattr(self, "_color_readout_type", DEFAULT_COLOR_READOUT_TYPE)
        action_state = (
            ("actColorReadoutTypeRgbl", readout_type is ColorReadoutType.RGBL),
            ("actColorReadoutTypeHsb", readout_type is ColorReadoutType.HSB),
            ("actColorReadoutTypeHsl", readout_type is ColorReadoutType.HSL),
            ("actColorReadoutTypeLab", readout_type is ColorReadoutType.LAB),
        )
        for action_name, checked in action_state:
            action = getattr(self._ui, action_name, None)
            if action is None:
                continue
            with block_signals(action):
                action.setChecked(checked)

    def _sync_color_readout_actions(self) -> None:
        """Keep color readout tool actions enabled and checked consistently."""

        current_path = self._current_image_path()
        readouts_by_path = getattr(self, "_color_readouts_by_path", {})
        can_add = current_path is not None and str(current_path) in getattr(self, "_images_by_path", {})
        can_delete = can_add and bool(readouts_by_path.get(str(current_path)))
        mode = getattr(self, "_color_readout_mode", None)
        if mode == "add" and not can_add:
            mode = None
        if mode == "delete" and not can_delete:
            mode = None
        self._color_readout_mode = mode

        action_state = (
            ("actAddColorReadout", can_add, mode == "add"),
            ("actDeleteColorReadout", can_delete, mode == "delete"),
            ("actDeleteAllColorReadouts", can_delete, False),
        )
        for action_name, enabled, checked in action_state:
            action = getattr(self._ui, action_name, None)
            if action is None:
                continue
            with block_signals(action):
                action.setEnabled(enabled)
                if action.isCheckable():
                    action.setChecked(checked)

    def _sync_color_readout_cursors(self) -> None:
        """Update image-area cursors for the active color readout mode."""

        mode = getattr(self, "_color_readout_mode", None)
        if mode == "add":
            cursor = self._add_color_readout_cursor()
        elif mode == "delete":
            cursor = self._delete_color_readout_cursor()
        else:
            cursor = QtGui.QCursor(QtCore.Qt.CursorShape.OpenHandCursor)
        for tab in self._all_image_tab_widgets():
            for scroll_area in tab.findChildren(QtWidgets.QScrollArea, "scrollImage"):
                scroll_area.setCursor(cursor)
                scroll_area.viewport().setCursor(cursor)
                widget = scroll_area.widget()
                if widget is not None:
                    widget.setCursor(cursor)

    def _sync_color_readout_themes_for_all_labels(self) -> None:
        """Apply the current appearance theme to all existing readout labels."""

        theme = getattr(self._ui, "_appearance_theme", styles.AppearanceTheme.DARK)
        for tab in self._all_image_tab_widgets():
            for label in tab.findChildren(ImageDisplayLabel, "lblImage"):
                label.set_color_readout_theme(theme)
        self._sync_color_readout_cursors()

    def _add_color_readout_cursor(self) -> QtGui.QCursor:
        """Return a circular cursor containing a plus sign."""

        return self._color_readout_cursor(include_vertical_stroke=True)

    def _delete_color_readout_cursor(self) -> QtGui.QCursor:
        """Return a circular cursor containing a minus sign."""

        return self._color_readout_cursor(include_vertical_stroke=False)

    def _color_readout_cursor(self, *, include_vertical_stroke: bool) -> QtGui.QCursor:
        """Build a high-contrast circular cursor for a color readout tool."""

        size = 24
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        theme = getattr(self._ui, "_appearance_theme", styles.AppearanceTheme.DARK)
        foreground = (
            QtGui.QColor(31, 37, 45)
            if theme == styles.AppearanceTheme.LIGHT
            else QtGui.QColor(237, 241, 245)
        )
        halo = (
            QtGui.QColor(255, 255, 255, 220)
            if theme == styles.AppearanceTheme.LIGHT
            else QtGui.QColor(0, 0, 0, 220)
        )
        circle = QtCore.QRectF(4, 4, 16, 16)
        horizontal = QtCore.QLineF(8, 12, 16, 12)
        vertical = QtCore.QLineF(12, 8, 12, 16)
        for color, width in ((halo, 4.0), (foreground, 2.0)):
            painter.setPen(
                QtGui.QPen(
                    color,
                    width,
                    QtCore.Qt.PenStyle.SolidLine,
                    QtCore.Qt.PenCapStyle.RoundCap,
                )
            )
            painter.drawEllipse(circle)
            painter.drawLine(horizontal)
            if include_vertical_stroke:
                painter.drawLine(vertical)
        painter.end()
        return QtGui.QCursor(pixmap, 12, 12)

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

    def _handle_pixel_sample_event(self, watched: QtCore.QObject, event: QtCore.QEvent) -> None:
        """Update RGB/luma sample readouts for image hover events."""

        if event.type() == QtCore.QEvent.Type.Leave:
            if isinstance(watched, QtWidgets.QWidget) and self._image_label_for_widget(watched) is not None:
                self._reset_pixel_sample_display()
            return
        if event.type() != QtCore.QEvent.Type.MouseMove:
            return
        if not isinstance(event, QtGui.QMouseEvent):
            return
        if not isinstance(watched, QtWidgets.QWidget):
            return

        label = self._image_label_for_widget(watched)
        if label is None:
            return
        path = self._image_path_for_widget(label)
        current_path = self._current_image_path()
        if path is None or current_path is None or path != current_path:
            self._reset_pixel_sample_display()
            return

        data = self._images_by_path.get(str(path))
        if data is None:
            self._reset_pixel_sample_display()
            return

        analysis_bgr = data.analysis.analysis_bgr
        if not hasattr(label, "image_pixel_position_at"):
            self._reset_pixel_sample_display()
            return

        label_pos = label.mapFrom(watched, event.position().toPoint())
        pixel_pos = label.image_pixel_position_at(label_pos, analysis_bgr.shape[:2])
        if pixel_pos is None:
            self._reset_pixel_sample_display()
            return

        x, y = pixel_pos
        sample = sample_analysis_pixel(analysis_bgr, x, y)
        self._set_pixel_sample_display(sample, str(path), id(analysis_bgr))

    def _image_label_for_widget(self, widget: QtWidgets.QWidget) -> ImageDisplayLabel | None:
        """Resolve the image display label from an image widget or viewport."""

        if isinstance(widget, ImageDisplayLabel) and widget.objectName() == "lblImage":
            return widget
        scroll_area = self._resolve_image_scroll_area(widget)
        if scroll_area is None:
            return None
        label = scroll_area.widget()
        if isinstance(label, ImageDisplayLabel):
            return label
        return None

    def _image_path_for_widget(self, widget: QtWidgets.QWidget) -> Optional[Path]:
        """Return the image path associated with a widget's tab container."""

        current: Optional[QtWidgets.QWidget] = widget
        while current is not None:
            raw = current.property("image_path")
            if raw:
                return Path(str(raw))
            current = current.parentWidget()
        return None

    def _set_pixel_sample_display(
        self,
        sample: PixelSample,
        path_key: str | None = None,
        analysis_id: int | None = None,
    ) -> None:
        """Show one pixel sample in the analysis panel."""

        for attr, value in (
            ("labelPixelRedValue", sample.red),
            ("labelPixelGreenValue", sample.green),
            ("labelPixelBlueValue", sample.blue),
            ("labelPixelLumaValue", sample.luma),
        ):
            label = getattr(self._ui, attr, None)
            if isinstance(label, QtWidgets.QLabel):
                label.setText(str(value))

        histogram = getattr(self._ui, "widgetHistogram", None)
        if hasattr(histogram, "set_luma_marker_value"):
            max_value = ChannelBitDepth.EIGHT.max_value
            if path_key is not None:
                loaded = self._images_by_path.get(path_key)
                if loaded is not None:
                    max_value = loaded.analysis.analysis_bit_depth.max_value
            histogram.set_luma_marker_value(sample.luma, max_value=max_value)
        if sample == INVALID_PIXEL_SAMPLE:
            self._pixel_sample_analysis_key = None
        elif path_key is not None and analysis_id is not None:
            self._pixel_sample_analysis_key = (path_key, analysis_id)

    def _reset_pixel_sample_display(self) -> None:
        """Reset analysis pixel readouts and hide the histogram marker."""

        self._set_pixel_sample_display(INVALID_PIXEL_SAMPLE)

    def _refresh_image_cursor(self, watched: QtCore.QObject, event: QtCore.QEvent) -> None:
        """Ensure the hand cursor appears over the image area."""

        if self._image_dragging:
            return
        if getattr(self, "_color_readout_mode", None) is not None:
            self._sync_color_readout_cursors()
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
