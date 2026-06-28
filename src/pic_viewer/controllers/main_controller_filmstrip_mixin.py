"""Filmstrip behavior for main controller."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets

from pic_viewer.app.dto.filmstrip_filter import (
    FilmstripFilterCriteria,
    FilmstripFilterItem,
)
from pic_viewer.app.dto.metadata import ImageMetadata
from pic_viewer.app.services.filmstrip_filter_service import (
    FilmstripFilterService,
    UNKNOWN_CAMERA_LABEL,
    UNKNOWN_LENS_LABEL,
)
from pic_viewer.domain.models.color_space import ColorProfileSpec
from pic_viewer.ui.utils.image_qt import to_qpixmap
from pic_viewer.ui.utils.signal_blocker import block_signals
from pic_viewer.ui.workers.metadata_worker import MetadataLoadTask

logger = logging.getLogger(__name__)


class MainControllerFilmstripMixin:
    """Provide filmstrip sizing and thumbnail update helpers."""

    def _configure_filmstrip_resize(self) -> None:
        """Configure dynamic filmstrip icon resizing."""

        self._filmstrip_resize_timer.setSingleShot(True)
        self._filmstrip_resize_timer.setInterval(120)
        self._filmstrip_resize_timer.timeout.connect(self._apply_filmstrip_icon_size)

    def _configure_filmstrip_filtering(self) -> None:
        """Initialize Filmstrip filtering state and combo-box options."""

        self._ensure_filmstrip_filter_state()
        self._refresh_filmstrip_filter_options()

    def _ensure_filmstrip_filter_state(self) -> None:
        if not hasattr(self, "_filmstrip_filter_service"):
            self._filmstrip_filter_service = FilmstripFilterService()
        if not hasattr(self, "_filmstrip_filter_items_by_path"):
            self._filmstrip_filter_items_by_path = {}
        if not hasattr(self, "_filmstrip_filter_criteria"):
            self._filmstrip_filter_criteria = FilmstripFilterCriteria()
        if not hasattr(self, "_filmstrip_metadata_tasks_by_path"):
            self._filmstrip_metadata_tasks_by_path = {}
        if not hasattr(self, "_updating_filmstrip_filter_combos"):
            self._updating_filmstrip_filter_combos = False

    def _register_filmstrip_filter_path(self, path: Path) -> None:
        """Register an opened image path for Filmstrip filtering."""

        self._ensure_filmstrip_filter_state()
        key = str(path)
        if key not in self._filmstrip_filter_items_by_path:
            self._filmstrip_filter_items_by_path[key] = self._filmstrip_filter_service.build_initial_item(path)
        self._refresh_filmstrip_filter_options()
        self._apply_filmstrip_filter()
        self._ensure_filmstrip_metadata_scan(path)

    def _remove_filmstrip_filter_path(self, path: Path) -> None:
        """Forget filter metadata associated with a closed image path."""

        self._ensure_filmstrip_filter_state()
        key = str(path)
        self._filmstrip_filter_items_by_path.pop(key, None)
        self._filmstrip_metadata_tasks_by_path.pop(key, None)
        self._refresh_filmstrip_filter_options()
        self._apply_filmstrip_filter()

    def _ensure_filmstrip_metadata_scan(self, path: Path) -> None:
        """Start a low-priority metadata-only scan when dependencies are available."""

        self._ensure_filmstrip_filter_state()
        key = str(path)
        item = self._filmstrip_filter_items_by_path.get(key)
        if item is None or item.metadata_loaded:
            return
        if key in self._filmstrip_metadata_tasks_by_path:
            return
        if not hasattr(self, "_image_service") or not hasattr(self, "_thread_pool"):
            return

        task = MetadataLoadTask(self._image_service, path)
        task.signals.finished.connect(lambda metadata, p=path: self._on_filmstrip_metadata_loaded(p, metadata))
        task.signals.error.connect(lambda message, p=path: self._on_filmstrip_metadata_error(p, message))
        self._filmstrip_metadata_tasks_by_path[key] = task
        self._thread_pool.start(task, -2)

    def _on_filmstrip_metadata_loaded(self, path: Path, metadata: ImageMetadata) -> None:
        """Accept metadata-only scan output for Filmstrip filtering."""

        self._filmstrip_metadata_tasks_by_path.pop(str(path), None)
        self._update_filmstrip_filter_metadata(path, metadata)

    def _on_filmstrip_metadata_error(self, path: Path, message: str) -> None:
        """Treat metadata-only scan failures as unknown camera/lens values."""

        self._filmstrip_metadata_tasks_by_path.pop(str(path), None)
        logger.warning("Filmstrip metadata scan failed: %s, %s", path, message)
        self._update_filmstrip_filter_metadata(
            path,
            ImageMetadata(general=tuple(), exif=tuple(), iptc=tuple(), tiff=tuple()),
        )

    def _update_filmstrip_filter_metadata(self, path: Path, metadata: ImageMetadata) -> None:
        """Update filter metadata for a path after metadata or full load completes."""

        self._ensure_filmstrip_filter_state()
        key = str(path)
        if key not in self._filmstrip_filter_items_by_path and self._find_filmstrip_item_by_path(path) is None:
            return
        self._filmstrip_filter_items_by_path[key] = self._filmstrip_filter_service.build_item_from_metadata(
            path,
            metadata,
        )
        self._refresh_filmstrip_filter_options()
        self._apply_filmstrip_filter()

    def _on_filmstrip_filter_changed(self, *_args: object) -> None:
        """Apply Filmstrip filters when a filter combo-box selection changes."""

        self._ensure_filmstrip_filter_state()
        if self._updating_filmstrip_filter_combos:
            return
        self._filmstrip_filter_criteria = FilmstripFilterCriteria(
            extension=self._combo_filter_value(self._ui.comboFilmstripExtensionFilter),
            camera=self._combo_filter_value(self._ui.comboFilmstripCameraFilter),
            lens=self._combo_filter_value(self._ui.comboFilmstripLensFilter),
        )
        self._apply_filmstrip_filter()

    def _refresh_filmstrip_filter_options(self) -> None:
        """Refresh available combo-box options while preserving valid selections."""

        if not hasattr(self._ui, "comboFilmstripExtensionFilter"):
            return
        self._ensure_filmstrip_filter_state()
        options = self._filmstrip_filter_service.build_options(self._filmstrip_filter_items_by_path.values())
        criteria = self._filmstrip_filter_criteria
        self._updating_filmstrip_filter_combos = True
        try:
            self._populate_filter_combo(
                self._ui.comboFilmstripExtensionFilter,
                self._tr("All Extensions"),
                options.extensions,
                criteria.extension,
            )
            self._populate_filter_combo(
                self._ui.comboFilmstripCameraFilter,
                self._tr("All Cameras"),
                options.cameras,
                criteria.camera,
            )
            self._populate_filter_combo(
                self._ui.comboFilmstripLensFilter,
                self._tr("All Lenses"),
                options.lenses,
                criteria.lens,
            )
        finally:
            self._updating_filmstrip_filter_combos = False
        self._filmstrip_filter_criteria = FilmstripFilterCriteria(
            extension=self._combo_filter_value(self._ui.comboFilmstripExtensionFilter),
            camera=self._combo_filter_value(self._ui.comboFilmstripCameraFilter),
            lens=self._combo_filter_value(self._ui.comboFilmstripLensFilter),
        )

    def _populate_filter_combo(
        self,
        combo: QtWidgets.QComboBox,
        all_text: str,
        options: tuple[str, ...],
        current_value: str | None,
    ) -> None:
        """Populate one filter combo with an All entry and sorted options."""

        next_value = current_value if current_value in options else None
        with block_signals(combo):
            combo.clear()
            combo.addItem(all_text, None)
            combo.setItemData(
                combo.count() - 1,
                all_text,
                QtCore.Qt.ItemDataRole.ToolTipRole,
            )
            for option in options:
                display_text = self._filter_option_display_text(option)
                combo.addItem(display_text, option)
                combo.setItemData(
                    combo.count() - 1,
                    display_text,
                    QtCore.Qt.ItemDataRole.ToolTipRole,
                )
            index = combo.findData(next_value)
            combo.setCurrentIndex(index if index >= 0 else 0)

    def _filter_option_display_text(self, option: str) -> str:
        if option == UNKNOWN_CAMERA_LABEL:
            return self._tr("Unknown Camera")
        if option == UNKNOWN_LENS_LABEL:
            return self._tr("Unknown Lens")
        return option

    @staticmethod
    def _combo_filter_value(combo: QtWidgets.QComboBox) -> str | None:
        data = combo.currentData()
        if data is None:
            return None
        return str(data)

    def _apply_filmstrip_filter(self) -> None:
        """Hide non-matching Filmstrip items and keep selection coherent."""

        self._ensure_filmstrip_filter_state()
        visible_paths: list[Path] = []
        for row in range(self._ui.listFilmstrip.count()):
            item = self._ui.listFilmstrip.item(row)
            if item is None:
                continue
            path = self._path_for_filmstrip_item(item)
            filter_item = self._filter_item_for_path(path)
            visible = self._filmstrip_filter_service.matches(filter_item, self._filmstrip_filter_criteria)
            item.setHidden(not visible)
            if visible:
                visible_paths.append(path)
        self._sync_filtered_filmstrip_selection(visible_paths)
        self._sync_filmstrip_summary()

    def _sync_filtered_filmstrip_selection(self, visible_paths: list[Path]) -> None:
        current_path = self._current_image_path()
        if not visible_paths:
            self._set_filmstrip_current_row_without_signal(-1)
            return
        if current_path in visible_paths:
            row = self._find_filmstrip_row_by_path(current_path)
            if row is not None:
                self._set_filmstrip_current_row_without_signal(row)
            return
        first_path = visible_paths[0]
        row = self._find_filmstrip_row_by_path(first_path)
        if row is not None:
            self._set_filmstrip_current_row_without_signal(row)
        if current_path is not None:
            self._activate_existing_path(first_path)

    def _set_filmstrip_current_row_without_signal(self, row: int) -> None:
        with block_signals(self._ui.listFilmstrip):
            self._ui.listFilmstrip.setCurrentRow(row)

    def _filter_item_for_path(self, path: Path) -> FilmstripFilterItem:
        self._ensure_filmstrip_filter_state()
        key = str(path)
        item = self._filmstrip_filter_items_by_path.get(key)
        if item is not None:
            return item
        item = self._filmstrip_filter_service.build_initial_item(path)
        self._filmstrip_filter_items_by_path[key] = item
        return item

    @staticmethod
    def _path_for_filmstrip_item(item: QtWidgets.QListWidgetItem) -> Path:
        return Path(str(item.data(QtCore.Qt.ItemDataRole.UserRole)))

    def _visible_filmstrip_rows(self) -> list[int]:
        rows: list[int] = []
        for row in range(self._ui.listFilmstrip.count()):
            item = self._ui.listFilmstrip.item(row)
            if item is not None and not item.isHidden():
                rows.append(row)
        return rows

    def _update_filmstrip_icon(
        self,
        path: Path,
        preview_rgb: np.ndarray,
        display_color_space: ColorProfileSpec,
    ) -> None:
        item = self._find_filmstrip_item_by_path(path)
        if item is None:
            return
        icon_size = self._ui.listFilmstrip.iconSize()
        if icon_size.width() <= 0 or icon_size.height() <= 0:
            icon_size = QtCore.QSize(self._filmstrip_icon_side, self._filmstrip_icon_side)
        dpr = self._device_pixel_ratio_for(self._ui.listFilmstrip)
        pix = to_qpixmap(
            preview_rgb,
            icon_size,
            device_pixel_ratio=dpr,
            color_space=display_color_space,
        )
        item.setIcon(QtGui.QIcon(pix))

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
        if icon_side <= 0:
            return

        self._apply_filmstrip_item_size_hints(icon_side)
        if icon_side == self._filmstrip_icon_side:
            return

        self._filmstrip_icon_side = icon_side
        icon_size = QtCore.QSize(icon_side, icon_side)
        self._ui.listFilmstrip.setIconSize(icon_size)
        self._refresh_filmstrip_icons()

    def _calculate_filmstrip_icon_side(self) -> int:
        """Calculate the target side length for filmstrip thumbnails."""

        viewport_height = self._ui.listFilmstrip.viewport().height()
        if viewport_height <= 0:
            return self._filmstrip_icon_side

        font_height = self._ui.listFilmstrip.fontMetrics().height()
        vertical_padding = getattr(self._ui, "FILMSTRIP_ITEM_VERTICAL_PADDING", 18)
        available = viewport_height - font_height - vertical_padding
        if available <= 0:
            return self._filmstrip_icon_side
        min_side = getattr(self._ui, "FILMSTRIP_MIN_ICON_SIDE", 48)
        max_side = getattr(self._ui, "FILMSTRIP_ICON_SIDE", 72)
        return max(min_side, min(available, max_side))

    def _filmstrip_item_size(self, icon_side: int, text: str = "") -> QtCore.QSize:
        """Return the item size needed for a thumbnail and full file name."""

        if hasattr(self._ui, "filmstrip_item_size"):
            return self._ui.filmstrip_item_size(icon_side, text=text)
        font_metrics = self._ui.listFilmstrip.fontMetrics()
        font_height = font_metrics.height()
        text_width = font_metrics.horizontalAdvance(text) + 16 if hasattr(font_metrics, "horizontalAdvance") else 0
        width = max(icon_side + 36, text_width)
        height = icon_side + font_height + 18
        return QtCore.QSize(width, height)

    def _apply_filmstrip_item_size_hints(self, icon_side: int) -> None:
        """Apply per-item size hints so full file names stay visible."""

        for row in range(self._ui.listFilmstrip.count()):
            item = self._ui.listFilmstrip.item(row)
            if item is not None:
                item.setSizeHint(self._filmstrip_item_size(icon_side, item.text()))

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
            pix = to_qpixmap(
                data.analysis.preview_rgb,
                icon_size,
                device_pixel_ratio=dpr,
                color_space=data.analysis.display_color_space,
            )
            item.setIcon(QtGui.QIcon(pix))
