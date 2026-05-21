"""Dialog for displaying third-party dependency license information."""

from __future__ import annotations

from collections.abc import Sequence

from PySide2 import QtCore, QtWidgets

from pic_viewer.app.services.third_party_license_service import (
    NOT_INSTALLED_VERSION,
    ThirdPartyLicenseInfo,
)


class ThirdPartyLicenseDialog(QtWidgets.QDialog):
    """Read-only table dialog for runtime dependency license metadata."""

    def __init__(
        self,
        licenses: Sequence[ThirdPartyLicenseInfo],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._licenses = list(licenses)
        self.setObjectName("dialogThirdPartyLicenses")
        self.resize(720, 360)
        self._setup_ui()
        self._populate_table()

    def _tr(self, text: str) -> str:
        return QtCore.QCoreApplication.translate("ThirdPartyLicenseDialog", text)

    def _setup_ui(self) -> None:
        self.setWindowTitle(self._tr("Third-Party License Information"))

        layout = QtWidgets.QVBoxLayout(self)
        self.tableThirdPartyLicenses = QtWidgets.QTableWidget(self)
        self.tableThirdPartyLicenses.setObjectName("tableThirdPartyLicenses")
        self.tableThirdPartyLicenses.setColumnCount(4)
        self.tableThirdPartyLicenses.setHorizontalHeaderLabels(
            [
                self._tr("Library"),
                self._tr("Version"),
                self._tr("License"),
                self._tr("Notes"),
            ]
        )
        self.tableThirdPartyLicenses.verticalHeader().setVisible(False)
        self.tableThirdPartyLicenses.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tableThirdPartyLicenses.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableThirdPartyLicenses.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableThirdPartyLicenses.setWordWrap(True)
        header = self.tableThirdPartyLicenses.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        layout.addWidget(self.tableThirdPartyLicenses)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, self)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _populate_table(self) -> None:
        self.tableThirdPartyLicenses.setRowCount(len(self._licenses))
        for row, license_info in enumerate(self._licenses):
            values = (
                license_info.display_name,
                self._translate_version(license_info.version),
                license_info.license_text,
                self._translate_notes(license_info.notes),
            )
            for column, value in enumerate(values):
                self.tableThirdPartyLicenses.setItem(row, column, self._create_item(value))
        self.tableThirdPartyLicenses.resizeRowsToContents()

    def _create_item(self, text: str) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem(text)
        item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
        return item

    def _translate_version(self, version: str) -> str:
        if version == NOT_INSTALLED_VERSION:
            return self._tr("Not installed")
        return version

    def _translate_notes(self, notes: str) -> str:
        if notes == "LGPL v3, GPL v2, or commercial license depending on distribution.":
            return self._tr("LGPL v3, GPL v2, or commercial license depending on distribution.")
        if notes == "Includes OpenCV and bundled third-party components.":
            return self._tr("Includes OpenCV and bundled third-party components.")
        if notes == "Optional RAW image support.":
            return self._tr("Optional RAW image support.")
        return notes
