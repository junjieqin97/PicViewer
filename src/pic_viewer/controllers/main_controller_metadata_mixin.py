"""Metadata table behavior for main controller."""

from __future__ import annotations

from PyQt5 import QtCore, QtWidgets

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection


class MainControllerMetadataMixin:
    """Provide metadata table rendering helpers."""

    METADATA_TOOLTIP_VALUE_LENGTH = 48

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
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsSelectable)
        return item

    def _should_show_metadata_tooltip(self, text: str) -> bool:
        return "\n" in text or len(text) > self.METADATA_TOOLTIP_VALUE_LENGTH
