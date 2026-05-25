"""Metadata table behavior for main controller."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtWidgets

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection
from pic_viewer.app.services.metadata_overlay_service import build_metadata_overlay_lines
from pic_viewer.ui.utils.signal_blocker import block_signals
from pic_viewer.ui.widgets.image_display_label import ImageDisplayLabel


class MainControllerMetadataMixin:
    """Provide metadata table rendering helpers."""

    METADATA_TOOLTIP_VALUE_LENGTH = 48

    def _on_metadata_overlay_toggled(self, active: bool) -> None:
        """Handle metadata overlay visibility changes from shared actions."""

        if self._show_metadata_overlay == active:
            self._sync_metadata_overlay_action()
            return
        self._show_metadata_overlay = active
        self._sync_metadata_overlay_action()
        if active:
            self._sync_metadata_overlay_for_current_image()
        else:
            self._clear_metadata_overlay_for_all_images()

    def _sync_metadata_overlay_action(self) -> None:
        if not hasattr(self._ui, "actToggleMetadataOverlay"):
            return
        with block_signals(self._ui.actToggleMetadataOverlay):
            self._ui.actToggleMetadataOverlay.setChecked(self._show_metadata_overlay)

    def _sync_metadata_overlay_for_current_image(self) -> None:
        self._sync_metadata_overlay_for_path(self._current_image_path())

    def _sync_metadata_overlay_for_path(self, image_path: Path | None) -> None:
        """Update metadata overlay text for a loaded image or hide it otherwise."""

        if image_path is None:
            self._clear_metadata_overlay_for_all_images()
            return

        label = self._metadata_overlay_label_for_path(image_path)
        if label is None:
            return
        data = self._images_by_path.get(str(image_path))
        if not self._show_metadata_overlay or data is None or str(image_path) in self._load_error_by_path:
            label.set_metadata_overlay(tuple(), False)
            return

        lines = build_metadata_overlay_lines(data.metadata, data.analysis.source_size)
        label.set_metadata_overlay(lines, True)

    def _metadata_overlay_label_for_path(self, image_path: Path) -> ImageDisplayLabel | None:
        tab = self._tab_widget_for_path(image_path)
        if tab is None:
            return None
        return tab.findChild(ImageDisplayLabel, "lblImage")

    def _clear_metadata_overlay_for_all_images(self) -> None:
        for label in self._ui.tabsImages.findChildren(ImageDisplayLabel, "lblImage"):
            label.set_metadata_overlay(tuple(), False)

    def _clear_metadata_tables(self) -> None:
        self._populate_metadata_table(self._ui.tableMetadataGeneral, tuple(), self._tr("No general metadata"))
        self._populate_metadata_table(self._ui.tableMetadataExif, tuple(), self._tr("No Exif metadata"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, tuple(), self._tr("No IPTC metadata"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, tuple(), self._tr("No TIFF metadata"))
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _set_metadata_loading_state(self) -> None:
        self._populate_metadata_table(self._ui.tableMetadataGeneral, tuple(), self._tr("Reading metadata..."))
        self._populate_metadata_table(self._ui.tableMetadataExif, tuple(), self._tr("Waiting for image load to finish"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, tuple(), self._tr("Waiting for image load to finish"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, tuple(), self._tr("Waiting for image load to finish"))
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _set_metadata_error_state(self, reason: str) -> None:
        entries = (
            (self._tr("Load Status"), self._tr("Failed")),
            (self._tr("Failure Reason"), reason),
        )
        self._populate_metadata_table(
            self._ui.tableMetadataGeneral,
            entries,
            self._tr("Image failed to load. No metadata is available."),
        )
        self._populate_metadata_table(
            self._ui.tableMetadataExif,
            tuple(),
            self._tr("Image failed to load. No metadata is available."),
        )
        self._populate_metadata_table(
            self._ui.tableMetadataIptc,
            tuple(),
            self._tr("Image failed to load. No metadata is available."),
        )
        self._populate_metadata_table(
            self._ui.tableMetadataTiff,
            tuple(),
            self._tr("Image failed to load. No metadata is available."),
        )
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _fill_metadata_tables(self, metadata: ImageMetadata) -> None:
        self._populate_metadata_table(
            self._ui.tableMetadataGeneral,
            self._localize_general_metadata_entries(metadata.general),
            self._tr("No general metadata"),
        )
        self._populate_metadata_table(self._ui.tableMetadataExif, metadata.exif, self._tr("No Exif metadata"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, metadata.iptc, self._tr("No IPTC metadata"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, metadata.tiff, self._tr("No TIFF metadata"))

    def _localize_general_metadata_entries(self, entries: MetadataSection) -> MetadataSection:
        key_map = {
            "File Name": self._tr("File Name"),
            "Path": self._tr("Path"),
            "Size": self._tr("Size"),
            "Resolution": self._tr("Resolution"),
        }
        value_map = {
            "Unknown": self._tr("Unknown"),
        }
        localized: list[tuple[str, str]] = []
        for key, value in entries:
            localized_key = key_map.get(key, key)
            localized_value = value_map.get(value, value)
            localized.append((localized_key, localized_value))
        return tuple(localized)

    def _populate_metadata_table(
        self, table: QtWidgets.QTableWidget, entries: MetadataSection, empty_message: str
    ) -> None:
        table.clearSpans()
        table.clearContents()
        if entries:
            table.setRowCount(len(entries))
            for row, (key, value) in enumerate(entries):
                table.setItem(row, 0, self._create_metadata_item(key))
                table.setItem(row, 1, self._create_metadata_item(value, tooltip_if_long=True))
        else:
            table.setRowCount(1)
            table.setItem(0, 0, self._create_metadata_state_item(empty_message))
            table.setSpan(0, 0, 1, 2)

    def _create_metadata_item(
        self, text: str, tooltip_if_long: bool = False
    ) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem(text)
        if tooltip_if_long and self._should_show_metadata_tooltip(text):
            item.setToolTip(text)
        return item

    def _create_metadata_state_item(self, text: str) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem(text)
        item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsSelectable)
        return item

    def _should_show_metadata_tooltip(self, text: str) -> bool:
        return "\n" in text or len(text) > self.METADATA_TOOLTIP_VALUE_LENGTH
