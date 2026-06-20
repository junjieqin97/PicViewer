"""Thread-pool metadata-only loading tasks."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore

from pic_viewer.app.services.image_service import ImageService

logger = logging.getLogger(__name__)


class MetadataTaskSignals(QtCore.QObject):
    """Signals emitted by background metadata tasks."""

    finished = QtCore.Signal(object)
    error = QtCore.Signal(str)


class MetadataLoadTask(QtCore.QRunnable):
    """Load image metadata in a thread-pool worker without decoding pixels."""

    def __init__(self, service: ImageService, path: Path) -> None:
        super().__init__()
        self._service = service
        self._path = path
        self.signals = MetadataTaskSignals()
        self.setAutoDelete(True)

    @QtCore.Slot()
    def run(self) -> None:
        """Execute metadata-only loading."""

        try:
            metadata = self._service.read_metadata(self._path)
        except Exception:  # pragma: no cover - defensive safety net
            logger.exception("Metadata-only loading failed: %s", self._path)
            self.signals.error.emit("An unknown error occurred while reading metadata")
            return

        self.signals.finished.emit(metadata)
