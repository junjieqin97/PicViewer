"""Main window controller for wiring UI interactions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from PyQt5 import QtCore, QtGui, QtWidgets

from pic_viewer.app.dto.analysis_view import AnalysisViewSettings, LumaRgbMode, RgbChannel
from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult
from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection
from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.ui.utils.image_qt import to_qpixmap
from pic_viewer.ui.workers.image_worker import ImageLoadWorker

logger = logging.getLogger(__name__)


class MainController(QtCore.QObject):
    """负责主窗口信号槽与Tab-胶卷同步的控制器。"""

    def __init__(
        self,
        main_window: QtWidgets.QMainWindow,
        ui: "MainWindowUI",
        image_service: ImageService,
        view_service: AnalysisViewService,
    ) -> None:
        super().__init__(main_window)
        self._main_window = main_window
        self._ui = ui
        self._image_service = image_service
        self._view_service = view_service

        self._images_by_path: Dict[str, ImageLoadResult] = {}
        self._workers_by_path: Dict[str, ImageLoadWorker] = {}
        self._threads_by_path: Dict[str, QtCore.QThread] = {}
        self._syncing_selection = False
        self._view_settings = AnalysisViewSettings(mode=LumaRgbMode.LUMA, channel=RgbChannel.ALL)
        self._last_splitter_sizes: Optional[list[int]] = None
        self._last_metadata_path: Optional[str] = None
        self._cursor_boundary_margin = 4
        self._cursor_override_target: Optional[QtWidgets.QWidget] = None
        self._filmstrip_icon_side = self._ui.listFilmstrip.iconSize().width() or 96
        self._filmstrip_resize_timer = QtCore.QTimer(self)
        self._analysis_refresh_timer = QtCore.QTimer(self)
        self._analysis_resize_timer = QtCore.QTimer(self)
        self._analysis_resize_active = False
        self._analysis_resize_interval_ms = 180
        self._analysis_preview_scale = 0.6
        self._analysis_preview_min_side = 180
        hist_size = getattr(self._ui, "info_panel_histogram_size", self._ui.widgetHistogram.size())
        wave_size = getattr(self._ui, "info_panel_waveform_size", self._ui.widgetWaveform.size())
        self._analysis_histogram_size = QtCore.QSize(hist_size.width(), hist_size.height())
        self._analysis_waveform_size = QtCore.QSize(wave_size.width(), wave_size.height())
        self._zoom_by_path: Dict[str, float] = {}
        self._fit_to_window_by_path: Dict[str, bool] = {}
        self._analysis_render_key_by_path: Dict[str, tuple] = {}
        self._zoom_step = 1.25
        self._zoom_min = 0.1
        self._zoom_max = 6.0
        self._image_dragging = False
        self._image_drag_start_pos: Optional[QtCore.QPoint] = None
        self._image_drag_start_scroll: Optional[QtCore.QPoint] = None
        self._image_drag_scroll_area: Optional[QtWidgets.QScrollArea] = None
        self._image_context_menu = self._ui.menuImageContext

        self._connect_signals()
        self._install_cursor_tracking()
        self._configure_filmstrip_resize()
        self._configure_analysis_refresh()
        self._apply_initial_visibility()
        self._sync_view_actions()
        self._refresh_actions_state()
        self.update_info_for_image(None)

    def _connect_signals(self) -> None:
        self._ui.actOpenFile.triggered.connect(self._open_file)
        self._ui.actOpenFolder.triggered.connect(self._open_folder)
        self._ui.actCloseTab.triggered.connect(self.close_current_tab)
        self._ui.actExit.triggered.connect(self._main_window.close)
        self._ui.actAbout.triggered.connect(self._show_about)

        self._ui.actZoomIn.triggered.connect(self._zoom_in)
        self._ui.actZoomOut.triggered.connect(self._zoom_out)
        self._ui.actFitToWindow.triggered.connect(self._fit_to_window)

        self._ui.actToggleInfoPanel.toggled.connect(self._toggle_info_panel)
        self._ui.actToggleFilmstrip.toggled.connect(self._toggle_filmstrip)
        self._ui.actModeLuma.triggered.connect(lambda: self._change_view_mode(LumaRgbMode.LUMA))
        self._ui.actModeRgb.triggered.connect(lambda: self._change_view_mode(LumaRgbMode.RGB))
        self._ui.actChannelAll.triggered.connect(lambda: self._change_channel(RgbChannel.ALL))
        self._ui.actChannelRed.triggered.connect(lambda: self._change_channel(RgbChannel.RED))
        self._ui.actChannelGreen.triggered.connect(lambda: self._change_channel(RgbChannel.GREEN))
        self._ui.actChannelBlue.triggered.connect(lambda: self._change_channel(RgbChannel.BLUE))

        self._ui.tabsImages.currentChanged.connect(self._on_tab_changed)
        self._ui.tabsImages.tabCloseRequested.connect(self.close_tab)
        self._ui.listFilmstrip.currentRowChanged.connect(self._on_filmstrip_row_changed)
        self._ui.tabsInfo.currentChanged.connect(self._on_info_tab_changed)
        self._ui.splitMain.splitterMoved.connect(self._on_main_splitter_moved)

    def _configure_filmstrip_resize(self) -> None:
        """Configure dynamic filmstrip icon resizing."""

        self._filmstrip_resize_timer.setSingleShot(True)
        self._filmstrip_resize_timer.setInterval(120)
        self._filmstrip_resize_timer.timeout.connect(self._apply_filmstrip_icon_size)
        self._ui.splitVertical.splitterMoved.connect(self._on_vertical_splitter_moved)

    def _configure_analysis_refresh(self) -> None:
        """Debounce analysis panel refreshes until layout sizes stabilize."""

        self._analysis_refresh_timer.setSingleShot(True)
        # 轻量节流：避免在 splitter 拖动或 tab 切换时反复渲染。
        self._analysis_refresh_timer.setInterval(40)
        self._analysis_refresh_timer.timeout.connect(self._refresh_view_for_current_image)

        self._analysis_resize_timer.setSingleShot(True)
        self._analysis_resize_timer.setInterval(self._analysis_resize_interval_ms)
        self._analysis_resize_timer.timeout.connect(self._finish_analysis_resize)

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

    def _apply_initial_visibility(self) -> None:
        """Sync initial panel visibility with menu action states."""

        self._toggle_info_panel(self._ui.actToggleInfoPanel.isChecked())
        self._toggle_filmstrip(self._ui.actToggleFilmstrip.isChecked())

    def _zoom_in(self) -> None:
        """Zoom in the current image by a fixed step."""

        self._adjust_zoom(self._zoom_step)

    def _zoom_out(self) -> None:
        """Zoom out the current image by a fixed step."""

        self._adjust_zoom(1 / self._zoom_step)

    def _fit_to_window(self) -> None:
        """Fit the current image to the available view size."""

        path = self._current_image_path()
        if path is None:
            return
        self._set_zoom_state(path, 1.0, True)
        self._refresh_current_image_pixmap()

    def _adjust_zoom(self, factor: float) -> None:
        """Apply a zoom factor for the current image."""

        path = self._current_image_path()
        if path is None:
            return
        zoom, fit = self._get_zoom_state(path)
        if fit:
            zoom = 1.0
        zoom = max(self._zoom_min, min(self._zoom_max, zoom * factor))
        self._set_zoom_state(path, zoom, False)
        self._refresh_current_image_pixmap()

    def _todo_not_implemented(self) -> None:
        QtWidgets.QMessageBox.information(self._main_window, "提示", "该功能尚未实现（TODO）")

    def _show_about(self) -> None:
        QtWidgets.QMessageBox.information(self._main_window, "关于", "PicViewer\n一个简单的图片预览工具 Demo。")

    def _toggle_info_panel(self, visible: bool) -> None:
        splitter = self._ui.splitMain
        info_widget = self._ui.scrollInfo

        if visible:
            info_widget.setVisible(True)
            splitter.setSizes(self._last_splitter_sizes or [1, 380])
            return

        self._last_splitter_sizes = splitter.sizes()
        info_widget.setVisible(False)
        splitter.setSizes([1, 0])

    def _toggle_filmstrip(self, visible: bool) -> None:
        self._ui.frameFilmstrip.setVisible(visible)
        self._update_boundary_cursor()
        if visible:
            self._schedule_filmstrip_resize()

    def _change_view_mode(self, mode: LumaRgbMode) -> None:
        if self._view_settings.mode == mode:
            return
        self._view_settings = AnalysisViewSettings(mode=mode, channel=self._view_settings.channel)
        self._sync_view_actions()
        self._refresh_view_for_current_image()

    def _change_channel(self, channel: RgbChannel) -> None:
        if self._view_settings.mode != LumaRgbMode.RGB:
            return
        if self._view_settings.channel == channel:
            return
        self._view_settings = AnalysisViewSettings(mode=LumaRgbMode.RGB, channel=channel)
        self._sync_view_actions()
        self._refresh_view_for_current_image()

    def _sync_view_actions(self) -> None:
        """Keep menu actions aligned with the current view settings."""

        rgb_mode = self._view_settings.mode == LumaRgbMode.RGB
        mode_pairs = [
            (self._ui.actModeLuma, self._view_settings.mode == LumaRgbMode.LUMA),
            (self._ui.actModeRgb, rgb_mode),
        ]
        channel_pairs = [
            (self._ui.actChannelAll, self._view_settings.channel == RgbChannel.ALL),
            (self._ui.actChannelRed, self._view_settings.channel == RgbChannel.RED),
            (self._ui.actChannelGreen, self._view_settings.channel == RgbChannel.GREEN),
            (self._ui.actChannelBlue, self._view_settings.channel == RgbChannel.BLUE),
        ]

        for action, checked in mode_pairs + channel_pairs:
            with QtCore.QSignalBlocker(action):
                action.setChecked(checked)

        for action, _ in channel_pairs:
            action.setEnabled(rgb_mode)

        if not rgb_mode:
            with QtCore.QSignalBlocker(self._ui.actChannelAll):
                self._ui.actChannelAll.setChecked(True)

    def _refresh_view_for_current_image(self) -> None:
        path = self._current_image_path()
        if path is None:
            return
        self.update_info_for_image(path)

    def _open_file(self) -> None:
        filter_text = (
            "Images (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.dng *.nef *.cr2 *.arw *.raf);;"
            "All Files (*)"
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._main_window,
            "打开图片",
            "",
            filter_text,
        )
        if not path:
            return
        self.open_image(Path(path))

    def _open_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self._main_window, "打开文件夹", "")
        if not folder:
            return

        root = Path(folder)
        supported = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".dng", ".nef", ".cr2", ".arw", ".raf"}
        paths = sorted([p for p in root.iterdir() if p.is_file() and p.suffix.lower() in supported])
        if not paths:
            QtWidgets.QMessageBox.information(self._main_window, "提示", "该文件夹未找到可打开的图片文件")
            return

        for path in paths:
            self.open_image(path)

    def open_image(self, path: Path) -> None:
        """打开图片：新增Tab + 新增胶卷Item + 自动切换到该Tab。"""

        existing_tab = self._find_tab_index_by_path(path)
        if existing_tab is not None:
            self._update_tab_title(existing_tab, path)
            self._update_filmstrip_text(path)
            self._ui.tabsImages.setCurrentIndex(existing_tab)
            return

        tab_container = QtWidgets.QWidget()
        tab_container.setProperty("image_path", str(path))
        layout = QtWidgets.QVBoxLayout(tab_container)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QtWidgets.QScrollArea(tab_container)
        scroll_area.setObjectName("scrollImage")
        scroll_area.setWidgetResizable(False)
        scroll_area.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustIgnored)
        scroll_area.setAlignment(QtCore.Qt.AlignCenter)
        scroll_area.setCursor(QtCore.Qt.OpenHandCursor)
        scroll_area.setProperty("_image_drag_area", True)
        layout.addWidget(scroll_area)

        lbl_image = QtWidgets.QLabel("加载中…")
        lbl_image.setObjectName("lblImage")
        lbl_image.setAlignment(QtCore.Qt.AlignCenter)
        lbl_image.setStyleSheet("background:#222;color:#ddd;")
        lbl_image.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        lbl_image.setCursor(QtCore.Qt.OpenHandCursor)
        lbl_image.setProperty("_image_drag_area", True)
        scroll_area.setWidget(lbl_image)
        scroll_area.viewport().setCursor(QtCore.Qt.OpenHandCursor)
        scroll_area.viewport().setProperty("_image_drag_area", True)
        self._track_cursor_widget(scroll_area)
        self._track_cursor_widget(scroll_area.viewport())
        self._track_cursor_widget(lbl_image)
        self._install_image_context_menu(scroll_area)
        self._install_image_context_menu(scroll_area.viewport())
        self._install_image_context_menu(lbl_image)

        tab_index = self._ui.tabsImages.addTab(tab_container, "")
        self._update_tab_title(tab_index, path)
        self._ui.tabsImages.setCurrentIndex(tab_index)
        self._set_zoom_state(path, 1.0, True)

        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.UserRole, str(path))
        self._apply_display_name_to_item(item, path)
        item.setIcon(self._placeholder_icon())
        self._ui.listFilmstrip.addItem(item)
        self._ui.listFilmstrip.setCurrentRow(self._ui.listFilmstrip.count() - 1)

        self._start_load(path)
        self._refresh_actions_state()

    def close_current_tab(self) -> None:
        index = self._ui.tabsImages.currentIndex()
        if index >= 0:
            self.close_tab(index)

    def close_tab(self, index: int) -> None:
        """关闭Tab：同步移除胶卷Item；如果关闭当前Tab则自动切换到相邻Tab。"""

        tab = self._ui.tabsImages.widget(index)
        if tab is None:
            return

        path = self._tab_path(tab)
        self._ui.tabsImages.removeTab(index)

        if path is not None:
            self._remove_filmstrip_item(path)
            self._images_by_path.pop(str(path), None)
            self._stop_thread_if_running(path)
            self._zoom_by_path.pop(str(path), None)
            self._fit_to_window_by_path.pop(str(path), None)
            self._analysis_render_key_by_path.pop(str(path), None)

        self._refresh_actions_state()
        self.update_info_for_image(self._current_image_path())

    def _on_tab_changed(self, _: int) -> None:
        path = self._current_image_path()
        self.update_info_for_image(path)
        self._sync_filmstrip_selection_from_tab(path)
        self._refresh_actions_state()

    def _on_filmstrip_row_changed(self, row: int) -> None:
        if self._syncing_selection:
            return
        item = self._ui.listFilmstrip.item(row)
        if item is None:
            return
        path_str = item.data(QtCore.Qt.UserRole)
        if not path_str:
            return
        tab_index = self._find_tab_index_by_path(Path(str(path_str)))
        if tab_index is not None:
            self._ui.tabsImages.setCurrentIndex(tab_index)

    def _on_info_tab_changed(self, _: int) -> None:
        """Info tabs use fixed-size renders; no resize refresh needed."""
        return

    def _on_main_splitter_moved(self, _: int, __: int) -> None:
        """Info panel uses fixed sizes; avoid refresh during splitter drag."""
        return

    def _schedule_analysis_refresh(self) -> None:
        """Schedule a debounced refresh for histogram and waveform views."""

        path = self._current_image_path()
        if path is None:
            return
        if str(path) not in self._images_by_path:
            return
        # 重启 single-shot timer：保证在布局稳定后再渲染。
        self._analysis_refresh_timer.stop()
        self._analysis_refresh_timer.start()

    def _mark_analysis_resizing(self) -> None:
        """Flag active resizing to trigger lightweight analysis renders."""

        self._analysis_resize_active = True
        self._analysis_resize_timer.stop()
        self._analysis_resize_timer.start()

    def _finish_analysis_resize(self) -> None:
        """Restore full-quality analysis renders after resizing stops."""

        if not self._analysis_resize_active:
            return
        self._analysis_resize_active = False
        self._schedule_analysis_refresh()

    def update_info_for_image(self, image_path: Optional[Path]) -> None:
        """右侧信息区刷新接口（本版允许占位刷新）。"""

        if image_path is None:
            self._set_info_placeholders()
            self._clear_metadata_tables()
            self._last_metadata_path = None
            return

        data = self._images_by_path.get(str(image_path))
        if data is None:
            self._set_info_placeholders()
            self._clear_metadata_tables()
            self._last_metadata_path = None
            return

        if str(image_path) != self._last_metadata_path:
            self._ui.tabsMetadata.setCurrentIndex(0)
        self._last_metadata_path = str(image_path)

        hist_logical = self._analysis_histogram_size
        wave_logical = self._analysis_waveform_size
        dpr = self._device_pixel_ratio_for(self._ui.widgetHistogram)
        hist_size = self._analysis_render_size(hist_logical, dpr)
        wave_size = self._analysis_render_size(wave_logical, dpr)
        render_key = (
            hist_size,
            wave_size,
            round(dpr, 2),
            self._view_settings.mode.value,
            self._view_settings.channel.value,
        )
        path_key = str(image_path)
        if self._analysis_render_key_by_path.get(path_key) == render_key and self._has_analysis_pixmaps():
            self._fill_metadata_tables(data.metadata)
            self._refresh_tab_pixmap(image_path, data.analysis)
            return

        fallback_view = self._view_service.build_view(data.analysis, self._view_settings)
        self._ui.widgetHistogram.setText("")
        self._ui.widgetWaveform.setText("")
        if hist_logical.width() <= 0 or hist_logical.height() <= 0:
            view = fallback_view
        elif wave_logical.width() <= 0 or wave_logical.height() <= 0:
            view = fallback_view
        else:
            view = self._image_service.render_analysis_view(
                data.analysis,
                self._view_settings,
                hist_size,
                wave_size,
                dpr,
            )
        self._ui.widgetHistogram.setPixmap(to_qpixmap(view.histogram_rgb, hist_logical, device_pixel_ratio=dpr))
        self._ui.widgetWaveform.setPixmap(to_qpixmap(view.waveform_rgb, wave_logical, device_pixel_ratio=dpr))
        self._analysis_render_key_by_path[path_key] = render_key
        self._fill_metadata_tables(data.metadata)
        self._refresh_tab_pixmap(image_path, data.analysis)

    def on_main_window_resized(self) -> None:
        self._schedule_filmstrip_resize()
        path = self._current_image_path()
        if path is None:
            return
        if str(path) not in self._images_by_path:
            return

    def _set_info_placeholders(self) -> None:
        self._ui.widgetHistogram.setText("Histogram Placeholder")
        self._ui.widgetWaveform.setText("Waveform Placeholder")
        self._ui.widgetHistogram.setPixmap(QtGui.QPixmap())
        self._ui.widgetWaveform.setPixmap(QtGui.QPixmap())

    def _clear_metadata_tables(self) -> None:
        self._populate_metadata_table(self._ui.tableMetadataGeneral, tuple(), "暂无通用信息")
        self._populate_metadata_table(self._ui.tableMetadataExif, tuple(), "暂无 Exif 信息")
        self._populate_metadata_table(self._ui.tableMetadataIptc, tuple(), "暂无 IPTC 信息")
        self._populate_metadata_table(self._ui.tableMetadataTiff, tuple(), "暂无 TIFF 信息")
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _fill_metadata_tables(self, metadata: ImageMetadata) -> None:
        self._populate_metadata_table(self._ui.tableMetadataGeneral, metadata.general, "暂无通用信息")
        self._populate_metadata_table(self._ui.tableMetadataExif, metadata.exif, "暂无 Exif 信息")
        self._populate_metadata_table(self._ui.tableMetadataIptc, metadata.iptc, "暂无 IPTC 信息")
        self._populate_metadata_table(self._ui.tableMetadataTiff, metadata.tiff, "暂无 TIFF 信息")

    def _populate_metadata_table(
        self, table: QtWidgets.QTableWidget, entries: MetadataSection, empty_message: str
    ) -> None:
        if entries:
            table.setRowCount(len(entries))
            for row, (key, value) in enumerate(entries):
                table.setItem(row, 0, QtWidgets.QTableWidgetItem(key))
                table.setItem(row, 1, QtWidgets.QTableWidgetItem(value))
        else:
            table.setRowCount(1)
            table.setItem(0, 0, QtWidgets.QTableWidgetItem(empty_message))
            table.setItem(0, 1, QtWidgets.QTableWidgetItem(""))
        table.resizeColumnsToContents()

    def _refresh_current_image_pixmap(self) -> None:
        """Refresh the current image pixmap using the stored zoom settings."""

        path = self._current_image_path()
        if path is None:
            return
        data = self._images_by_path.get(str(path))
        if data is None:
            return
        self._refresh_tab_pixmap(path, data.analysis)

    def _refresh_tab_pixmap(self, path: Path, analysis: ImageAnalysis) -> None:
        """Render the image preview inside the tab for the given path."""

        tab_index = self._find_tab_index_by_path(path)
        if tab_index is None:
            return
        tab = self._ui.tabsImages.widget(tab_index)
        if tab is None:
            return
        scroll_area = tab.findChild(QtWidgets.QScrollArea, "scrollImage")
        lbl = tab.findChild(QtWidgets.QLabel, "lblImage")
        if lbl is None:
            return
        base_size = lbl.size()
        if scroll_area is not None:
            base_size = scroll_area.viewport().size()
        target_size = self._target_pixmap_size(path, base_size)
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        dpr = self._device_pixel_ratio_for(lbl)
        existing = lbl.pixmap()
        if existing is not None and self._pixmap_matches_target(existing, target_size, dpr):
            return
        pixmap = to_qpixmap(analysis.preview_rgb, target_size, device_pixel_ratio=dpr)
        lbl.setPixmap(pixmap)
        lbl.setText("")
        if not pixmap.isNull():
            lbl.resize(self._pixmap_logical_size(pixmap))

    def _target_pixmap_size(self, path: Path, base_size: QtCore.QSize) -> QtCore.QSize:
        """Calculate the target pixmap size based on zoom settings."""

        if base_size.width() <= 0 or base_size.height() <= 0:
            return base_size
        zoom, fit_to_window = self._get_zoom_state(path)
        if fit_to_window:
            return base_size
        return QtCore.QSize(
            max(1, int(base_size.width() * zoom)),
            max(1, int(base_size.height() * zoom)),
        )

    def _device_pixel_ratio_for(self, widget: QtWidgets.QWidget) -> float:
        """Best-effort device pixel ratio resolution for the widget's screen."""

        screen: Optional[QtGui.QScreen] = None
        window = widget.window().windowHandle()
        if window is not None:
            screen = window.screen()
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return 1.0
        dpr = getattr(screen, "devicePixelRatioF", screen.devicePixelRatio)()
        try:
            return max(1.0, float(dpr))
        except (TypeError, ValueError):
            return 1.0

    def _physical_size(self, logical_size: QtCore.QSize, dpr: float) -> QtCore.QSize:
        """Scale a logical size into physical pixels using DPR."""

        return QtCore.QSize(
            max(1, int(round(logical_size.width() * dpr))),
            max(1, int(round(logical_size.height() * dpr))),
        )

    def _analysis_size(self, logical_size: QtCore.QSize, dpr: float) -> tuple[int, int]:
        """Convert a logical QSize into (height, width) physical pixels."""

        physical = self._physical_size(logical_size, dpr)
        return (physical.height(), physical.width())

    def _analysis_render_size(self, logical_size: QtCore.QSize, dpr: float) -> tuple[int, int]:
        """Return the render size, downsampled during active resizing."""

        size = self._analysis_size(logical_size, dpr)
        if not self._analysis_resize_active:
            return size
        return self._scale_analysis_size(size, self._analysis_preview_scale)

    def _scale_analysis_size(self, size: tuple[int, int], scale: float) -> tuple[int, int]:
        """Scale the analysis render size while keeping a minimum readable size."""

        height, width = size
        if scale <= 0 or scale >= 1:
            return size

        scaled_height = max(1, int(round(height * scale)))
        scaled_width = max(1, int(round(width * scale)))
        min_side = self._analysis_preview_min_side

        if height > min_side:
            scaled_height = max(min_side, scaled_height)
        else:
            scaled_height = height
        if width > min_side:
            scaled_width = max(min_side, scaled_width)
        else:
            scaled_width = width

        return (scaled_height, scaled_width)

    def _has_analysis_pixmaps(self) -> bool:
        """Return True when histogram and waveform pixmaps are present."""

        hist_pix = self._ui.widgetHistogram.pixmap()
        wave_pix = self._ui.widgetWaveform.pixmap()
        if hist_pix is None or hist_pix.isNull():
            return False
        if wave_pix is None or wave_pix.isNull():
            return False
        return True

    def _pixmap_logical_size(self, pixmap: QtGui.QPixmap) -> QtCore.QSize:
        """Return pixmap size in device-independent pixels."""

        dpr = pixmap.devicePixelRatio()
        dpr = dpr if dpr and dpr > 0 else 1.0
        return QtCore.QSize(
            max(1, int(round(pixmap.width() / dpr))),
            max(1, int(round(pixmap.height() / dpr))),
        )

    def _pixmap_matches_target(
        self,
        pixmap: QtGui.QPixmap,
        target_size: QtCore.QSize,
        dpr: float,
    ) -> bool:
        """Check whether an existing pixmap already matches the logical target."""

        if pixmap.isNull():
            return False
        logical_size = self._pixmap_logical_size(pixmap)
        if logical_size != target_size:
            return False
        existing_dpr = pixmap.devicePixelRatio()
        existing_dpr = existing_dpr if existing_dpr and existing_dpr > 0 else 1.0
        return abs(existing_dpr - max(1.0, dpr)) < 0.01

    def _get_zoom_state(self, path: Path) -> tuple[float, bool]:
        """Return zoom factor and fit flag for the given image path."""

        key = str(path)
        zoom = self._zoom_by_path.get(key)
        fit = self._fit_to_window_by_path.get(key)
        if zoom is None:
            zoom = 1.0
            self._zoom_by_path[key] = zoom
        if fit is None:
            fit = True
            self._fit_to_window_by_path[key] = fit
        return zoom, fit

    def _set_zoom_state(self, path: Path, zoom: float, fit_to_window: bool) -> None:
        """Persist zoom state for the given image path."""

        key = str(path)
        self._zoom_by_path[key] = zoom
        self._fit_to_window_by_path[key] = fit_to_window

    def _start_load(self, path: Path) -> None:
        if str(path) in self._threads_by_path:
            return

        self._main_window.statusBar().showMessage(f"正在读取图片：{path.name}")

        worker = ImageLoadWorker(self._image_service, path)
        thread = QtCore.QThread(self._main_window)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(lambda result, p=path: self._on_loaded(p, result))
        worker.error.connect(lambda message, p=path: self._on_error(p, message))

        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.error.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda p=path: self._threads_by_path.pop(str(p), None))
        thread.finished.connect(lambda p=path: self._workers_by_path.pop(str(p), None))

        # 必须持有 worker 的 Python 引用，否则函数返回后对象可能被 GC，
        # 导致 started->run/finished 信号都无法触发，表现为一直“加载中”。
        self._workers_by_path[str(path)] = worker
        self._threads_by_path[str(path)] = thread
        thread.start()

    def _stop_thread_if_running(self, path: Path) -> None:
        thread = self._threads_by_path.pop(str(path), None)
        if thread is None:
            return
        if thread.isRunning():
            thread.requestInterruption()
            thread.quit()

    def _on_loaded(self, path: Path, result: ImageLoadResult) -> None:
        self._images_by_path[str(path)] = result
        # 强制下一次刷新使用最新分析结果重渲染。
        self._analysis_render_key_by_path.pop(str(path), None)
        self._update_filmstrip_icon(path, result.analysis)

        if self._current_image_path() == path:
            self.update_info_for_image(path)
        else:
            self._refresh_tab_pixmap(path, result.analysis)

        self._main_window.statusBar().showMessage(f"加载完成：{path.name}")

    def _on_error(self, path: Path, message: str) -> None:
        logger.warning("加载图片失败: %s, %s", path, message)
        QtWidgets.QMessageBox.warning(self._main_window, "错误", message)
        self._main_window.statusBar().showMessage(f"加载失败：{path.name}")

        tab_index = self._find_tab_index_by_path(path)
        if tab_index is None:
            return
        tab = self._ui.tabsImages.widget(tab_index)
        if tab is None:
            return
        lbl = tab.findChild(QtWidgets.QLabel, "lblImage")
        if lbl is not None:
            lbl.setText("加载失败")
            lbl.setPixmap(QtGui.QPixmap())

        if self._current_image_path() == path:
            self.update_info_for_image(path)

    def _update_filmstrip_icon(self, path: Path, analysis: ImageAnalysis) -> None:
        item = self._find_filmstrip_item_by_path(path)
        if item is None:
            return
        icon_size = self._ui.listFilmstrip.iconSize()
        if icon_size.width() <= 0 or icon_size.height() <= 0:
            icon_size = QtCore.QSize(self._filmstrip_icon_side, self._filmstrip_icon_side)
        dpr = self._device_pixel_ratio_for(self._ui.listFilmstrip)
        pix = to_qpixmap(analysis.preview_rgb, icon_size, device_pixel_ratio=dpr)
        item.setIcon(QtGui.QIcon(pix))

    def _sync_filmstrip_selection_from_tab(self, path: Optional[Path]) -> None:
        self._syncing_selection = True
        try:
            if path is None:
                self._ui.listFilmstrip.setCurrentRow(-1)
                return
            row = self._find_filmstrip_row_by_path(path)
            if row is not None and row != self._ui.listFilmstrip.currentRow():
                self._ui.listFilmstrip.setCurrentRow(row)
        finally:
            self._syncing_selection = False

    def _remove_filmstrip_item(self, path: Path) -> None:
        row = self._find_filmstrip_row_by_path(path)
        if row is None:
            return
        self._syncing_selection = True
        self._ui.listFilmstrip.blockSignals(True)
        try:
            item = self._ui.listFilmstrip.takeItem(row)
            del item
        finally:
            self._ui.listFilmstrip.blockSignals(False)
            self._syncing_selection = False

    def _placeholder_icon(self) -> QtGui.QIcon:
        return self._main_window.style().standardIcon(QtWidgets.QStyle.SP_FileIcon)

    def _current_image_path(self) -> Optional[Path]:
        tab = self._ui.tabsImages.currentWidget()
        if tab is None:
            return None
        return self._tab_path(tab)

    def _tab_path(self, tab_widget: QtWidgets.QWidget) -> Optional[Path]:
        raw = tab_widget.property("image_path")
        if not raw:
            return None
        return Path(str(raw))

    def _find_tab_index_by_path(self, path: Path) -> Optional[int]:
        target = str(path)
        for i in range(self._ui.tabsImages.count()):
            tab = self._ui.tabsImages.widget(i)
            if tab is None:
                continue
            if str(tab.property("image_path")) == target:
                return i
        return None

    def _find_filmstrip_row_by_path(self, path: Path) -> Optional[int]:
        target = str(path)
        for i in range(self._ui.listFilmstrip.count()):
            item = self._ui.listFilmstrip.item(i)
            if item is None:
                continue
            if str(item.data(QtCore.Qt.UserRole)) == target:
                return i
        return None

    def _find_filmstrip_item_by_path(self, path: Path) -> Optional[QtWidgets.QListWidgetItem]:
        row = self._find_filmstrip_row_by_path(path)
        if row is None:
            return None
        return self._ui.listFilmstrip.item(row)

    def _refresh_actions_state(self) -> None:
        has_tab = self._ui.tabsImages.count() > 0
        self._ui.actCloseTab.setEnabled(has_tab)
        self._ui.actZoomIn.setEnabled(has_tab)
        self._ui.actZoomOut.setEnabled(has_tab)
        self._ui.actFitToWindow.setEnabled(has_tab)

    def _format_display_name(self, filename: str) -> str:
        """Shorten long filenames for tab and filmstrip display."""

        if len(filename) <= 15:
            return filename
        return f"{filename[:5]}...{filename[-5:]}"

    def _update_tab_title(self, tab_index: int, path: Path) -> None:
        if tab_index < 0 or tab_index >= self._ui.tabsImages.count():
            return
        display_name = self._format_display_name(path.name)
        self._ui.tabsImages.setTabText(tab_index, display_name)
        self._ui.tabsImages.setTabToolTip(tab_index, path.name)

    def _apply_display_name_to_item(self, item: QtWidgets.QListWidgetItem, path: Path) -> None:
        item.setText(self._format_display_name(path.name))
        item.setToolTip(path.name)

    def _update_filmstrip_text(self, path: Path) -> None:
        item = self._find_filmstrip_item_by_path(path)
        if item is None:
            return
        self._apply_display_name_to_item(item, path)

    def _on_vertical_splitter_moved(self, _: int, __: int) -> None:
        """Handle vertical splitter changes for filmstrip resizing."""

        self._schedule_filmstrip_resize()

    def _schedule_filmstrip_resize(self) -> None:
        """Debounce filmstrip icon size updates during resize."""

        if not self._ui.frameFilmstrip.isVisible():
            return
        self._filmstrip_resize_timer.stop()
        self._filmstrip_resize_timer.start()

    def _apply_filmstrip_icon_size(self) -> None:
        """Resize filmstrip thumbnails based on available height."""

        if not self._ui.frameFilmstrip.isVisible():
            return
        icon_side = self._calculate_filmstrip_icon_side()
        if icon_side <= 0 or icon_side == self._filmstrip_icon_side:
            return

        self._filmstrip_icon_side = icon_side
        icon_size = QtCore.QSize(icon_side, icon_side)
        self._ui.listFilmstrip.setIconSize(icon_size)

        font_height = self._ui.listFilmstrip.fontMetrics().height()
        grid_height = icon_side + font_height + 16
        grid_width = icon_side + 20
        self._ui.listFilmstrip.setGridSize(QtCore.QSize(grid_width, grid_height))
        self._refresh_filmstrip_icons()

    def _calculate_filmstrip_icon_side(self) -> int:
        """Calculate the target side length for filmstrip thumbnails."""

        viewport_height = self._ui.listFilmstrip.viewport().height()
        if viewport_height <= 0:
            return self._filmstrip_icon_side

        font_height = self._ui.listFilmstrip.fontMetrics().height()
        available = viewport_height - font_height - 12
        if available <= 0:
            return self._filmstrip_icon_side
        return max(24, min(available, 256))

    def _refresh_filmstrip_icons(self) -> None:
        """Regenerate filmstrip icons using the current thumbnail size."""

        icon_size = self._ui.listFilmstrip.iconSize()
        if icon_size.width() <= 0 or icon_size.height() <= 0:
            return
        dpr = self._device_pixel_ratio_for(self._ui.listFilmstrip)

        for path_str, data in self._images_by_path.items():
            item = self._find_filmstrip_item_by_path(Path(path_str))
            if item is None:
                continue
            pix = to_qpixmap(data.analysis.preview_rgb, icon_size, device_pixel_ratio=dpr)
            item.setIcon(QtGui.QIcon(pix))


if TYPE_CHECKING:  # pragma: no cover
    from pic_viewer.ui.windows.main_window import MainWindowUI
