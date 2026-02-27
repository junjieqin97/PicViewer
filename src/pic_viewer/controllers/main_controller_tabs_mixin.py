"""Tab and filmstrip synchronization behavior for main controller."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PyQt5 import QtCore, QtGui, QtWidgets


class MainControllerTabsMixin:
    """Provide image tab lifecycle and selection sync helpers."""

    def _apply_initial_visibility(self) -> None:
        """Sync initial panel visibility with menu action states."""

        self._toggle_info_panel(self._ui.actToggleInfoPanel.isChecked())
        self._toggle_filmstrip(self._ui.actToggleFilmstrip.isChecked())

    def _open_file(self) -> None:
        image_filter_label = self._tr("图片文件")
        all_files_label = self._tr("所有文件")
        filter_text = (
            f"{image_filter_label} (*.jpg *.jpeg *.png *.tif *.tiff *.bmp *.dng *.nef *.cr2 *.arw *.raf);;"
            f"{all_files_label} (*)"
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self._main_window,
            self._tr("打开图片"),
            "",
            filter_text,
        )
        if not path:
            return
        self.open_image(Path(path))

    def _open_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self._main_window, self._tr("打开文件夹"), "")
        if not folder:
            return

        root = Path(folder)
        supported = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".dng", ".nef", ".cr2", ".arw", ".raf"}
        paths = sorted([p for p in root.iterdir() if p.is_file() and p.suffix.lower() in supported])
        if not paths:
            QtWidgets.QMessageBox.information(
                self._main_window,
                self._tr("提示"),
                self._tr("该文件夹未找到可打开的图片文件"),
            )
            return

        last_path: Optional[Path] = None
        with QtCore.QSignalBlocker(self._ui.tabsImages), QtCore.QSignalBlocker(self._ui.listFilmstrip):
            for path in paths:
                self.open_image(path, activate=False)
                last_path = path

        if last_path is not None:
            self._activate_existing_path(last_path)

    def open_image(self, path: Path, activate: bool = True) -> None:
        """打开图片：新增Tab + 新增胶卷Item；可选激活该Tab。"""

        existing_tab = self._find_tab_index_by_path(path)
        if existing_tab is not None:
            self._update_tab_title(existing_tab, path)
            self._update_filmstrip_text(path)
            if activate:
                self._ui.tabsImages.setCurrentIndex(existing_tab)
            self._ensure_preview_load(path)
            if activate:
                self._ensure_full_load(path)
            return

        self._remove_empty_image_placeholder()
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

        lbl_image = QtWidgets.QLabel(self._tr("加载中…"))
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
        self._set_zoom_state(path, 1.0, True)

        item = QtWidgets.QListWidgetItem()
        item.setData(QtCore.Qt.UserRole, str(path))
        self._apply_display_name_to_item(item, path)
        item.setIcon(self._placeholder_icon())
        self._ui.listFilmstrip.addItem(item)
        session = self._start_path_session(path)
        self._ensure_preview_load(path, session)
        if activate:
            self._ui.tabsImages.setCurrentIndex(tab_index)
            self._ui.listFilmstrip.setCurrentRow(self._ui.listFilmstrip.count() - 1)
            self._ensure_full_load(path, session)
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
        if tab.property("_image_placeholder") is True:
            return

        path = self._tab_path(tab)
        self._ui.tabsImages.removeTab(index)

        if path is not None:
            self._remove_filmstrip_item(path)
            self._images_by_path.pop(str(path), None)
            self._preview_by_path.pop(str(path), None)
            self._cancel_tasks_for_path(path)
            self._zoom_by_path.pop(str(path), None)
            self._fit_to_window_by_path.pop(str(path), None)
            self._analysis_render_key_by_path.pop(str(path), None)
            self._tab_preview_render_key_by_path.pop(str(path), None)

        self._refresh_actions_state()
        self.update_info_for_image(self._current_image_path())
        self._ensure_empty_image_placeholder()

    def _on_tab_changed(self, _: int) -> None:
        path = self._current_image_path()
        self.update_info_for_image(path)
        self._sync_filmstrip_selection_from_tab(path)
        self._refresh_actions_state()
        self._ensure_full_load(path)

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

    def _ensure_empty_image_placeholder(self) -> None:
        if self._has_image_tabs():
            self._ui.tabsImages.tabBar().setVisible(True)
            return
        if self._has_placeholder_tab():
            self._ui.tabsImages.tabBar().setVisible(False)
            return
        placeholder = self._build_empty_image_placeholder()
        tab_index = self._ui.tabsImages.addTab(placeholder, "")
        tab_bar = self._ui.tabsImages.tabBar()
        tab_bar.setTabButton(tab_index, QtWidgets.QTabBar.LeftSide, None)
        tab_bar.setTabButton(tab_index, QtWidgets.QTabBar.RightSide, None)
        tab_bar.setVisible(False)
        self._ui.tabsImages.setCurrentIndex(tab_index)

    def _remove_empty_image_placeholder(self) -> None:
        tab_index = self._placeholder_tab_index()
        if tab_index is None:
            return
        self._ui.tabsImages.removeTab(tab_index)
        self._ui.tabsImages.tabBar().setVisible(True)

    def _build_empty_image_placeholder(self) -> QtWidgets.QWidget:
        placeholder = QtWidgets.QWidget()
        placeholder.setObjectName("tabImagePlaceholder")
        placeholder.setProperty("_image_placeholder", True)
        layout = QtWidgets.QVBoxLayout(placeholder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        open_file_text = self._ui.actOpenFile.text()
        open_file_shortcut = self._shortcut_text(self._ui.actOpenFile)
        open_folder_text = self._ui.actOpenFolder.text()
        open_folder_shortcut = self._shortcut_text(self._ui.actOpenFolder)

        label_open_file = QtWidgets.QLabel(open_file_text)
        label_open_file.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label_open_file_shortcut = QtWidgets.QLabel(open_file_shortcut)
        label_open_file_shortcut.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        label_open_folder = QtWidgets.QLabel(open_folder_text)
        label_open_folder.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
        label_open_folder_shortcut = QtWidgets.QLabel(open_folder_shortcut)
        label_open_folder_shortcut.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        grid.addWidget(label_open_file, 0, 0)
        grid.addWidget(label_open_file_shortcut, 0, 1)
        grid.addWidget(label_open_folder, 1, 0)
        grid.addWidget(label_open_folder_shortcut, 1, 1)

        grid_container = QtWidgets.QWidget()
        grid_container.setLayout(grid)
        grid_container.setStyleSheet("color: #777;")
        layout.addWidget(grid_container, 0, QtCore.Qt.AlignHCenter)
        layout.addStretch(1)
        return placeholder

    def _shortcut_text(self, action: QtWidgets.QAction) -> str:
        sequence = action.shortcut()
        if sequence.isEmpty():
            return ""
        return sequence.toString(QtGui.QKeySequence.NativeText)

    def _has_image_tabs(self) -> bool:
        for i in range(self._ui.tabsImages.count()):
            tab = self._ui.tabsImages.widget(i)
            if tab is None:
                continue
            if self._tab_path(tab) is not None:
                return True
        return False

    def _has_placeholder_tab(self) -> bool:
        return self._placeholder_tab_index() is not None

    def _placeholder_tab_index(self) -> Optional[int]:
        for i in range(self._ui.tabsImages.count()):
            tab = self._ui.tabsImages.widget(i)
            if tab is not None and tab.property("_image_placeholder") is True:
                return i
        return None

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
        has_image_tab = self._has_image_tabs()
        self._ui.actCloseTab.setEnabled(has_image_tab)
        self._ui.actZoomIn.setEnabled(has_image_tab)
        self._ui.actZoomOut.setEnabled(has_image_tab)
        self._ui.actFitToWindow.setEnabled(has_image_tab)

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
