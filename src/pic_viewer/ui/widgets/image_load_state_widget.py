"""Inline loading and failure state widget for image tabs."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class ImageLoadStateWidget(QtWidgets.QWidget):
    """Show image loading progress or a recoverable load failure."""

    retry_requested = QtCore.Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("widgetImageLoadState")
        self._setup_ui()

    def set_loading(self, title: str, detail: str) -> None:
        """Render a loading state.

        Args:
            title: Short state title.
            detail: Ignored for loading states; kept for API compatibility.
        """

        self.label_title.setText(title)
        self.label_detail.setText("")
        self.label_detail.setVisible(False)
        self.label_reason.setText("")
        self.label_reason.setVisible(False)
        self.label_file_name.setText("")
        self.label_file_name.setVisible(False)
        self.progress.setVisible(False)
        self.button_retry.setVisible(False)

    def set_error(self, title: str, reason: str, file_name: str, retry_text: str) -> None:
        """Render a failure state with a retry action.

        Args:
            title: Short failure title.
            reason: User-readable failure reason.
            file_name: Name of the file that failed to load.
            retry_text: Localized retry button text.
        """

        self.label_title.setText(title)
        self.label_detail.setText("")
        self.label_detail.setVisible(False)
        self.label_reason.setText(reason)
        self.label_reason.setVisible(True)
        self.label_file_name.setText(file_name)
        self.label_file_name.setVisible(True)
        self.progress.setVisible(False)
        self.button_retry.setText(retry_text)
        self.button_retry.setVisible(True)

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addStretch(1)

        content = QtWidgets.QWidget(self)
        content.setObjectName("imageLoadStateContent")
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        self.label_title = QtWidgets.QLabel(content)
        self.label_title.setObjectName("labelImageLoadStateTitle")
        self.label_title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title_font = self.label_title.font()
        title_font.setPointSize(title_font.pointSize() + 3)
        title_font.setBold(True)
        self.label_title.setFont(title_font)
        content_layout.addWidget(self.label_title)

        self.label_detail = QtWidgets.QLabel(content)
        self.label_detail.setObjectName("labelImageLoadStateDetail")
        self.label_detail.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_detail.setWordWrap(True)
        content_layout.addWidget(self.label_detail)

        self.label_reason = QtWidgets.QLabel(content)
        self.label_reason.setObjectName("labelImageLoadStateReason")
        self.label_reason.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_reason.setWordWrap(True)
        content_layout.addWidget(self.label_reason)

        self.label_file_name = QtWidgets.QLabel(content)
        self.label_file_name.setObjectName("labelImageLoadStateFileName")
        self.label_file_name.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label_file_name.setWordWrap(True)
        content_layout.addWidget(self.label_file_name)

        self.progress = QtWidgets.QProgressBar(content)
        self.progress.setObjectName("progressImageLoadState")
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(220)
        content_layout.addWidget(self.progress, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)

        self.button_retry = QtWidgets.QPushButton(content)
        self.button_retry.setObjectName("buttonImageLoadRetry")
        self.button_retry.setMinimumWidth(120)
        self.button_retry.clicked.connect(self.retry_requested)
        content_layout.addWidget(self.button_retry, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(content, 0, QtCore.Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
