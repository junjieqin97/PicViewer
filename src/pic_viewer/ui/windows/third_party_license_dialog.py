"""Dialog for displaying third-party dependency license information."""

from __future__ import annotations

from collections.abc import Sequence

from PySide2 import QtCore, QtWidgets

from pic_viewer.app.services.third_party_license_service import (
    NOT_INSTALLED_VERSION,
    ThirdPartyLicenseInfo,
)


class ThirdPartyLicenseDialog(QtWidgets.QDialog):
    """Read-only plain text dialog for runtime dependency license metadata."""

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
        self._populate_text()

    def _tr(self, text: str) -> str:
        return QtCore.QCoreApplication.translate("ThirdPartyLicenseDialog", text)

    def _setup_ui(self) -> None:
        self.setWindowTitle(self._tr("Third-Party License Information"))

        layout = QtWidgets.QVBoxLayout(self)
        self.textThirdPartyLicenses = QtWidgets.QPlainTextEdit(self)
        self.textThirdPartyLicenses.setObjectName("textThirdPartyLicenses")
        self.textThirdPartyLicenses.setReadOnly(True)
        self.textThirdPartyLicenses.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        layout.addWidget(self.textThirdPartyLicenses)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok, self)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _populate_text(self) -> None:
        self.textThirdPartyLicenses.setPlainText(
            "\n".join(self._format_license_line(license_info) for license_info in self._licenses)
        )

    def _format_license_line(self, license_info: ThirdPartyLicenseInfo) -> str:
        version = self._translate_version(license_info.version)
        return f"{license_info.display_name} {version} {license_info.license_text}"

    def _translate_version(self, version: str) -> str:
        if version == NOT_INSTALLED_VERSION:
            return self._tr("Not installed")
        return version
