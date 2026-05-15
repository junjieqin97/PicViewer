"""Thread-pool image loading tasks."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt5 import QtCore

from pic_viewer.app.services.image_service import ImageService
from pic_viewer.common.errors import ImageLoadError, ImageProcessError

logger = logging.getLogger(__name__)


class ImageTaskSignals(QtCore.QObject):
    """Signals emitted by background image tasks."""

    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)


class PreviewLoadTask(QtCore.QRunnable):
    """Load preview payload in a thread-pool worker."""

    def __init__(self, service: ImageService, path: Path) -> None:
        super().__init__()
        self._service = service
        self._path = path
        self.signals = ImageTaskSignals()
        self.setAutoDelete(True)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        """Execute lightweight preview loading."""

        try:
            result = self._service.load_preview(self._path)
        except (ImageLoadError, ImageProcessError) as exc:
            self.signals.error.emit(str(exc))
            return
        except Exception:  # pragma: no cover - defensive safety net
            logger.exception("Preview processing failed: %s", self._path)
            self.signals.error.emit("An unknown error occurred while processing the image")
            return

        self.signals.finished.emit(result)


class ImageLoadTask(QtCore.QRunnable):
    """Load full analysis payload in a thread-pool worker."""

    def __init__(self, service: ImageService, path: Path) -> None:
        super().__init__()
        self._service = service
        self._path = path
        self.signals = ImageTaskSignals()
        self.setAutoDelete(True)

    @QtCore.pyqtSlot()
    def run(self) -> None:
        """Execute full load + analysis task."""

        try:
            result = self._service.load_and_analyze(self._path)
        except (ImageLoadError, ImageProcessError) as exc:
            self.signals.error.emit(str(exc))
            return
        except Exception:  # pragma: no cover - defensive safety net
            logger.exception("Image processing failed: %s", self._path)
            self.signals.error.emit("An unknown error occurred while processing the image")
            return

        self.signals.finished.emit(result)
