from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets  # noqa: E402


class QtWidgetTestCase(unittest.TestCase):
    """Base test case for Qt widget tests.

    It ensures a QApplication exists and flushes DeferredDelete events after
    unittest cleanups have scheduled widgets for deletion.
    """

    def setUp(self) -> None:
        super().setUp()
        self._app = self._ensure_application()
        self.addCleanup(self._flush_deferred_deletes)

    @staticmethod
    def _ensure_application() -> QtWidgets.QApplication:
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])
        return app

    @staticmethod
    def _flush_deferred_deletes() -> None:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        app.processEvents()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
