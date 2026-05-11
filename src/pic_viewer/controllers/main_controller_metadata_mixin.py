"""Metadata table behavior for main controller."""

from __future__ import annotations

from PyQt5 import QtWidgets

from pic_viewer.app.dto.metadata import ImageMetadata, MetadataSection


class MainControllerMetadataMixin:
    """Provide metadata table rendering helpers."""

    def _clear_metadata_tables(self) -> None:
        self._populate_metadata_table(self._ui.tableMetadataGeneral, tuple(), self._tr("暂无通用信息"))
        self._populate_metadata_table(self._ui.tableMetadataExif, tuple(), self._tr("暂无 Exif 信息"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, tuple(), self._tr("暂无 IPTC 信息"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, tuple(), self._tr("暂无 TIFF 信息"))
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _set_metadata_loading_state(self) -> None:
        self._populate_metadata_table(self._ui.tableMetadataGeneral, tuple(), self._tr("正在读取元数据…"))
        self._populate_metadata_table(self._ui.tableMetadataExif, tuple(), self._tr("等待图片加载完成"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, tuple(), self._tr("等待图片加载完成"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, tuple(), self._tr("等待图片加载完成"))
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _set_metadata_error_state(self, reason: str) -> None:
        entries = (
            (self._tr("加载状态"), self._tr("失败")),
            (self._tr("失败原因"), reason),
        )
        self._populate_metadata_table(
            self._ui.tableMetadataGeneral,
            entries,
            self._tr("图片加载失败，暂无元数据"),
        )
        self._populate_metadata_table(self._ui.tableMetadataExif, tuple(), self._tr("图片加载失败，暂无元数据"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, tuple(), self._tr("图片加载失败，暂无元数据"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, tuple(), self._tr("图片加载失败，暂无元数据"))
        self._ui.tabsMetadata.setCurrentIndex(0)

    def _fill_metadata_tables(self, metadata: ImageMetadata) -> None:
        self._populate_metadata_table(
            self._ui.tableMetadataGeneral,
            self._localize_general_metadata_entries(metadata.general),
            self._tr("暂无通用信息"),
        )
        self._populate_metadata_table(self._ui.tableMetadataExif, metadata.exif, self._tr("暂无 Exif 信息"))
        self._populate_metadata_table(self._ui.tableMetadataIptc, metadata.iptc, self._tr("暂无 IPTC 信息"))
        self._populate_metadata_table(self._ui.tableMetadataTiff, metadata.tiff, self._tr("暂无 TIFF 信息"))

    def _localize_general_metadata_entries(self, entries: MetadataSection) -> MetadataSection:
        key_map = {
            "文件名": self._tr("文件名"),
            "路径": self._tr("路径"),
            "大小": self._tr("大小"),
            "分辨率": self._tr("分辨率"),
        }
        value_map = {
            "未知": self._tr("未知"),
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
