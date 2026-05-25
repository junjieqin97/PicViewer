"""Dialog for displaying third-party dependency license information."""

from __future__ import annotations

from collections.abc import Sequence
from html import escape

from PySide6 import QtCore, QtWidgets

from pic_viewer.app.services.third_party_license_service import (
    LicenseTextPart,
    NOT_INSTALLED_VERSION,
    ThirdPartyLicenseInfo,
    load_license_document,
    split_license_text,
)


class LicenseDocumentDialog(QtWidgets.QDialog):
    """Read-only dialog for one full third-party license document."""

    def __init__(
        self,
        title: str,
        body: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("dialogLicenseDocument")
        self.resize(760, 520)
        self._setup_ui(title, body)

    def _setup_ui(self, title: str, body: str) -> None:
        self.setWindowTitle(title)

        layout = QtWidgets.QVBoxLayout(self)
        self.textLicenseDocument = QtWidgets.QPlainTextEdit(self)
        self.textLicenseDocument.setObjectName("textLicenseDocument")
        self.textLicenseDocument.setReadOnly(True)
        self.textLicenseDocument.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.textLicenseDocument.setPlainText(body)
        layout.addWidget(self.textLicenseDocument)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class ThirdPartyLicenseDialog(QtWidgets.QDialog):
    """Read-only rich text dialog for runtime dependency license metadata."""

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
        self.textThirdPartyLicenses = QtWidgets.QTextBrowser(self)
        self.textThirdPartyLicenses.setObjectName("textThirdPartyLicenses")
        self.textThirdPartyLicenses.setReadOnly(True)
        self.textThirdPartyLicenses.setOpenExternalLinks(False)
        self.textThirdPartyLicenses.setOpenLinks(False)
        self.textThirdPartyLicenses.anchorClicked.connect(self._open_license_url)
        layout.addWidget(self.textThirdPartyLicenses)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok, self)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    def _populate_text(self) -> None:
        self.textThirdPartyLicenses.setHtml(
            "<html><body>"
            + "".join(self._format_license_row_html(license_info) for license_info in self._licenses)
            + "</body></html>"
        )

    def _format_license_row_html(self, license_info: ThirdPartyLicenseInfo) -> str:
        version = self._translate_version(license_info.version)
        license_html = "".join(
            self._format_license_part_html(part) for part in split_license_text(license_info.license_text)
        )
        return (
            "<p>"
            f"<strong>{escape(license_info.display_name)}</strong> "
            f"{escape(version)} "
            f"{license_html}"
            "</p>"
        )

    def _format_license_part_html(self, part: LicenseTextPart) -> str:
        if part.document_key is None:
            return escape(part.text)
        document_key = escape(part.document_key, quote=True)
        return f'<a href="license:{document_key}">{escape(part.text)}</a>'

    def _open_license_url(self, url: QtCore.QUrl) -> None:
        url_text = url.toString()
        if not url_text.startswith("license:"):
            return

        document_key = url_text[len("license:") :]
        document = load_license_document(document_key)
        if document is None:
            QtWidgets.QMessageBox.warning(
                self,
                self._tr("Third-Party License Information"),
                self._tr("License text is not available."),
            )
            return

        dialog = LicenseDocumentDialog(document.title, document.body, self)
        dialog.exec()

    def _translate_version(self, version: str) -> str:
        if version == NOT_INSTALLED_VERSION:
            return self._tr("Not installed")
        return version
