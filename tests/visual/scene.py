"""Deterministic scenes using production presentation and analysis code."""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PySide6 import QtCore, QtTest, QtWidgets

from pic_viewer.app.dto.image_analysis import ImageAnalysis, ImageLoadResult
from pic_viewer.app.dto.metadata import ImageMetadata
from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.controllers.main_controller import MainController
from pic_viewer.domain.rules.analysis import ImageAnalyzer
from pic_viewer.ui.resources.styles import AppearanceTheme
from pic_viewer.ui.windows.main_window import MainWindowUI


def settle() -> None:
    """Drain layout events and the controller's bounded resize debounce."""
    QtWidgets.QApplication.processEvents()
    QtTest.QTest.qWait(220)
    QtWidgets.QApplication.processEvents()


class Scene:
    """Own a complete controller, but never schedule image or metadata I/O."""

    def __init__(self, width: int, height: int, theme: str, loaded: bool) -> None:
        self.window = QtWidgets.QMainWindow()
        self.window.setObjectName('visualMainWindow')
        self.ui = MainWindowUI()
        self.ui.setup_ui(self.window)
        self.window.menuBar().setNativeMenuBar(False)
        self.analyzer = ImageAnalyzer()
        # Keep production rendering; any unexpected I/O dependency fails immediately.
        forbidden_io = ForbiddenIO()
        service = ImageService(forbidden_io, self.analyzer, forbidden_io, forbidden_io)
        self.controller = MainController(self.window, self.ui, service, AnalysisViewService())
        self.ui.apply_appearance_theme(AppearanceTheme(theme))
        self.window.resize(width, height)
        self.window.show()
        self.window.activateWindow()
        settle()
        if loaded:
            self.load()
        self.ui.splitMain.setSizes([width, self.ui.info_panel_min_width])
        settle()

    def load(self) -> None:
        """Deliver an analyzed, synthetic portrait through the worker-result slot."""
        y, x = np.indices((240, 160))
        bgr = np.stack(((x * 2) % 256, y % 256, (x + y) % 256), axis=2).astype(np.uint8)
        metadata = ImageMetadata(
            general=(('File Name', 'visual-sample.png'), ('Resolution', '160 x 240')),
            exif=(('Make', 'Example'), ('Model', 'Camera'), ('LensModel', '35mm')),
            iptc=(), tiff=(),
        )
        analyzed = self.analyzer.analyze(bgr)
        analysis = ImageAnalysis(**{field.name: getattr(analyzed, field.name)
                                    for field in fields(analyzed)})
        result = ImageLoadResult(analysis, metadata)
        path = Path('visual-sample.png').resolve()
        with patch.object(self.controller, '_ensure_preview_load'), \
                patch.object(self.controller, '_ensure_full_load'), \
                patch.object(self.controller, '_ensure_filmstrip_metadata_scan'):
            self.controller.open_image(path)
            session = self.controller._active_session_by_path[str(path)]
            self.controller._on_loaded(path, session, result)
            settle()
        assert str(path) in self.controller._images_by_path, 'Fixture result was rejected'
        assert not self.ui.listFilmstrip.item(0).icon().isNull(), 'Missing thumbnail'
        assert self.ui.tableMetadataGeneral.rowCount() >= 2, 'Missing metadata'

    def close(self) -> None:
        """Release timers and widgets before the next scene."""
        self.window.close()
        self.window.deleteLater()
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        QtWidgets.QApplication.processEvents()


class ForbiddenIO:
    """Fail immediately if production rendering unexpectedly requests I/O."""

    def __getattr__(self, name: str) -> None:
        raise AssertionError(f'Unexpected visual fixture I/O: {name}')
