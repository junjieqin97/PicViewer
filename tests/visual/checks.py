"""Principal layout, content, focus and canvas acceptance checks."""
from __future__ import annotations

from itertools import combinations

from PySide6 import QtCore, QtGui, QtWidgets

from pic_viewer.ui.resources.styles import AppearanceTheme, CanvasColor
from pic_viewer.ui.widgets.elided_fields import ElidedLabel
from tests.visual.assertions import (
    require_canvas, require_contained, require_focus_delta, require_text, require_visible,
)
from tests.visual.scene import Scene, settle


class SceneChecks:
    """Track the current widget so failures include a useful close-up."""

    def __init__(self, scene: Scene) -> None:
        self.scene = scene
        self.current: QtWidgets.QWidget = scene.window

    def visible(self, widget: QtWidgets.QWidget) -> None:
        """Check one widget after bringing Analysis content into view if needed."""
        self.current = widget
        ui = self.scene.ui
        if ui.analysisScrollContent.isAncestorOf(widget):
            ui.scrollAnalysis.ensureWidgetVisible(widget, 0, 0)
            QtWidgets.QApplication.processEvents()
        require_visible(widget, self.scene.window)

    def layout(self) -> None:
        """Validate fixed chrome and scroll-reachable Analysis content."""
        ui = self.scene.ui
        assert ui.widgetAnalysisToolbar.height() == 30
        assert ui.frameFilmstrip.height() == 140
        groups = (
            ui.widgetAnalysisToolbar.findChildren(QtWidgets.QToolButton),
            ui.widgetFilmstripFilterToolbar.findChildren(QtWidgets.QComboBox),
            [ui.widgetAnalysisToolbar, ui.splitMain, ui.frameFilmstrip],
        )
        for group in groups:
            for widget in group:
                self.visible(widget)
            for first, second in combinations(group, 2):
                a = QtCore.QRect(first.mapTo(self.scene.window, QtCore.QPoint()), first.size())
                b = QtCore.QRect(second.mapTo(self.scene.window, QtCore.QPoint()), second.size())
                assert not a.intersects(b), f'Overlap: {first.objectName()}, {second.objectName()}'
        assert ui.analysisScrollContent.width() <= ui.scrollAnalysis.viewport().width()
        controls = ui.analysisScrollContent.findChildren(QtWidgets.QComboBox)
        labels = ui.analysisScrollContent.findChildren(QtWidgets.QLabel)
        for widget in [*controls, *labels]:
            self.visible(widget)
            if isinstance(widget, QtWidgets.QLabel) and widget.text():
                if isinstance(widget, ElidedLabel):
                    assert widget.toolTip() == widget.text()
                elif widget.objectName().startswith('labelPixel'):
                    require_contained(widget.fontMetrics().boundingRect(widget.text()),
                                      QtCore.QRect(0, -widget.fontMetrics().ascent(),
                                                   widget.width(), widget.height()))
                else:
                    require_text(widget)
        for chart, size in ((ui.widgetHistogram, (256, 100)), (ui.widgetWaveform, (256, 256))):
            self.visible(chart)
            assert (chart.width(), chart.height()) == size
        left = ui.comboFilmstripExtensionFilter.mapTo(ui.frameFilmstrip, QtCore.QPoint()).x()
        assert left == ui.listFilmstrip.mapTo(ui.frameFilmstrip, QtCore.QPoint()).x()

    def content(self, loaded: bool, language: str, dpr: int) -> None:
        """Require actual localized states or DPR-tagged image and chart pixels."""
        ui = self.scene.ui
        assert ui.tabsInfo.tabText(0) == ('分析' if language == 'zh_CN' else 'Analysis')
        if loaded:
            labels = [ui.widgetHistogram, ui.widgetWaveform,
                      self.scene.window.findChild(QtWidgets.QLabel, 'lblImage')]
            for label in labels:
                self.current = label
                pixmap = label.pixmap()
                assert pixmap and not pixmap.isNull(), 'Missing loaded rendering'
                assert pixmap.devicePixelRatio() == dpr, 'Incorrect loaded pixmap DPR'
        else:
            for label in ui.tabsImages.findChildren(QtWidgets.QLabel):
                if label.isVisible() and label.text():
                    self.visible(label)
                    require_text(label)

    def long_fields(self) -> None:
        """Exercise elision without changing controller color-space selections."""
        ui = self.scene.ui
        label = ui.labelImageColorSpaceValue
        original = label.text()
        long_text = 'VeryLongICCProfileNameWithoutSpaces' * 8
        try:
            label.setText(long_text)
            self.visible(label)
            assert label.text() == label.toolTip() == long_text
            assert label.fontMetrics().horizontalAdvance(long_text) > label.width()
            for combo in ui.analysisScrollContent.findChildren(QtWidgets.QComboBox):
                index = combo.currentIndex()
                assert index >= 0, 'Fixture requires an active fallback profile'
                text, data = combo.currentText(), combo.currentData()
                try:
                    combo.setItemText(index, long_text)
                    self.visible(combo)
                    assert combo.currentText() == combo.toolTip() == long_text
                    assert combo.currentData() == data
                finally:
                    combo.setItemText(index, text)
        finally:
            label.setText(original)
            ui.scrollAnalysis.verticalScrollBar().setValue(0)

    def focus(self, loaded: bool, theme: str) -> None:
        """Check all six control families, including focused table/list items."""
        ui = self.scene.ui
        ui.tabsInfo.setCurrentWidget(ui.tabMetadata)
        settle()
        widgets = [ui.buttonToolbarUnderexposed, ui.comboFilmstripExtensionFilter,
                   ui.tabsInfo.tabBar(), ui.tabsMetadata.tabBar()]
        if loaded:
            ui.tableMetadataGeneral.setCurrentCell(0, 0)
            ui.listFilmstrip.setCurrentRow(0)
            widgets.extend([ui.tabsImages.tabBar(), ui.tableMetadataGeneral, ui.listFilmstrip])
        else:
            widgets.append(self.scene.window.findChild(QtWidgets.QPushButton, 'buttonEmptyOpenFile'))
        color = '#ffd166' if theme == 'dark' else '#805000'
        for widget in widgets:
            self.visible(widget)
            ui.buttonToolbarModeLuma.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
            QtWidgets.QApplication.processEvents()
            before = widget.grab().toImage()
            item_before = self._item_image(widget)
            geometry = widget.geometry()
            widget.setFocus(QtCore.Qt.FocusReason.TabFocusReason)
            QtWidgets.QApplication.processEvents()
            assert widget.hasFocus(), f'Cannot focus {widget.objectName()}'
            require_focus_delta(before, widget.grab().toImage(), color)
            if item_before is not None:
                require_focus_delta(item_before, self._item_image(widget), color)
            assert widget.geometry() == geometry, 'Focus moved control'
        ui.tabsInfo.setCurrentWidget(ui.tabAnalysis)
        ui.scrollAnalysis.verticalScrollBar().setValue(0)
        settle()

    @staticmethod
    def _item_image(widget: QtWidgets.QWidget) -> QtGui.QImage | None:
        """Capture only the selected item, excluding container focus borders."""
        if isinstance(widget, QtWidgets.QAbstractItemView):
            return widget.viewport().grab(widget.visualRect(widget.currentIndex())).toImage()
        return None

    def canvas(self, theme: str) -> None:
        """Probe documented colors outside the portrait before/after theme changes."""
        ui = self.scene.ui
        viewport = self.scene.window.findChild(QtWidgets.QScrollArea, 'scrollImage').viewport()
        self.current = viewport
        # A portrait fixture leaves a wide strip at the left of the fitted image.
        point = QtCore.QPoint(4, viewport.height() // 2)
        require_canvas(viewport.grab().toImage(), point, '#202020')
        expected = {
            CanvasColor.PURE_WHITE: '#ffffff', CanvasColor.MIDDLE_GRAY_18: '#777777',
            CanvasColor.DEEP_NEUTRAL: '#202020', CanvasColor.NEAR_BLACK: '#101010',
            CanvasColor.PURE_BLACK: '#000000',
        }
        for canvas, color in expected.items():
            ui.apply_canvas_color(canvas)
            for appearance in AppearanceTheme:
                ui.apply_appearance_theme(appearance)
                QtWidgets.QApplication.processEvents()
                require_canvas(viewport.grab().toImage(), point, color)
        ui.apply_canvas_color(CanvasColor.DEEP_NEUTRAL)
        ui.apply_appearance_theme(AppearanceTheme(theme))
        settle()
