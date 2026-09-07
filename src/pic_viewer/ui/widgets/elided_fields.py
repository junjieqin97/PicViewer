"""Width-independent form fields that retain their complete source text."""

from PySide6 import QtCore, QtGui, QtWidgets


class ElidedLabel(QtWidgets.QLabel):
    """Display a single status line without letting long text widen its layout."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTextFormat(QtCore.Qt.TextFormat.PlainText)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Ignored,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )

    def setText(self, text: str) -> None:
        """Keep the full status available to callers and tooltip users."""
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Elide at paint time so resizing never changes the stored status."""
        QtWidgets.QFrame.paintEvent(self, event)
        painter = QtGui.QPainter(self)
        rect = self.contentsRect().adjusted(
            self.margin(), self.margin(), -self.margin(), -self.margin()
        )
        text = self.fontMetrics().elidedText(
            self.text(), QtCore.Qt.TextElideMode.ElideRight, rect.width()
        )
        self.style().drawItemText(
            painter, rect, self.alignment(), self.palette(),
            self.isEnabled(), text, self.foregroundRole(),
        )


class ElidedComboBox(QtWidgets.QComboBox):
    """Use the available field width while retaining native combo interactions."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSizeAdjustPolicy(
            QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.setMinimumContentsLength(0)
        self.currentTextChanged.connect(self.setToolTip)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        """Paint native chrome and elide only the selected option's display text."""
        option = QtWidgets.QStyleOptionComboBox()
        self.initStyleOption(option)
        rect = self.style().subControlRect(
            QtWidgets.QStyle.ComplexControl.CC_ComboBox, option,
            QtWidgets.QStyle.SubControl.SC_ComboBoxEditField, self,
        )
        option.currentText = option.fontMetrics.elidedText(
            option.currentText, QtCore.Qt.TextElideMode.ElideRight, rect.width()
        )
        painter = QtWidgets.QStylePainter(self)
        painter.drawComplexControl(QtWidgets.QStyle.ComplexControl.CC_ComboBox, option)
        painter.drawControl(QtWidgets.QStyle.ControlElement.CE_ComboBoxLabel, option)
