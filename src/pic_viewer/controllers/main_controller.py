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

        self._connect_signals()
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

        self._ui.actZoomIn.triggered.connect(self._todo_not_implemented)
        self._ui.actZoomOut.triggered.connect(self._todo_not_implemented)
        self._ui.actFitToWindow.triggered.connect(self._todo_not_implemented)

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

    def _apply_initial_visibility(self) -> None:
        """Sync initial panel visibility with menu action states."""

        self._toggle_info_panel(self._ui.actToggleInfoPanel.isChecked())
        self._toggle_filmstrip(self._ui.actToggleFilmstrip.isChecked())

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

        lbl_image = QtWidgets.QLabel("加载中…", tab_container)
        lbl_image.setObjectName("lblImage")
        lbl_image.setAlignment(QtCore.Qt.AlignCenter)
        lbl_image.setStyleSheet("background:#222;color:#ddd;")
        layout.addWidget(lbl_image)

        tab_index = self._ui.tabsImages.addTab(tab_container, "")
        self._update_tab_title(tab_index, path)
        self._ui.tabsImages.setCurrentIndex(tab_index)

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

        view = self._view_service.build_view(data.analysis, self._view_settings)
        self._ui.widgetHistogram.setText("")
        self._ui.widgetWaveform.setText("")
        self._ui.widgetHistogram.setPixmap(to_qpixmap(view.histogram_rgb, self._ui.widgetHistogram.size()))
        self._ui.widgetWaveform.setPixmap(to_qpixmap(view.waveform_rgb, self._ui.widgetWaveform.size()))
        self._fill_metadata_tables(data.metadata)
        self._refresh_tab_pixmap(image_path, data.analysis)

    def on_main_window_resized(self) -> None:
        path = self._current_image_path()
        if path is None:
            return
        if str(path) not in self._images_by_path:
            return
        self.update_info_for_image(path)

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

    def _refresh_tab_pixmap(self, path: Path, analysis: ImageAnalysis) -> None:
        tab_index = self._find_tab_index_by_path(path)
        if tab_index is None:
            return
        tab = self._ui.tabsImages.widget(tab_index)
        if tab is None:
            return
        lbl = tab.findChild(QtWidgets.QLabel, "lblImage")
        if lbl is None:
            return
        target_size = lbl.size()
        existing = lbl.pixmap()
        if existing is not None and existing.size() == target_size:
            return
        lbl.setPixmap(to_qpixmap(analysis.preview_rgb, target_size))

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
        pix = to_qpixmap(analysis.preview_rgb, QtCore.QSize(96, 96))
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
        self._ui.actCloseTab.setEnabled(self._ui.tabsImages.count() > 0)

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


if TYPE_CHECKING:  # pragma: no cover
    from pic_viewer.ui.main_window import MainWindowUI
