"""Thread-pool image loading tasks."""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore

from pic_viewer.app.services.image_service import ImageService
from pic_viewer.common.errors import ImageLoadError, ImageProcessError
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    DEFAULT_WORKING_COLOR_SPACE,
    WorkingColorSpace,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent

logger = logging.getLogger(__name__)


class ImageTaskSignals(QtCore.QObject):
    """Signals emitted by background image tasks."""

    finished = QtCore.Signal(object)
    error = QtCore.Signal(str)


class PreviewLoadTask(QtCore.QRunnable):
    """Load preview payload in a thread-pool worker."""

    def __init__(
        self,
        service: ImageService,
        path: Path,
        working_color_space: WorkingColorSpace = DEFAULT_WORKING_COLOR_SPACE,
        assumed_source_color_space: WorkingColorSpace = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> None:
        super().__init__()
        self._service = service
        self._path = path
        self._working_color_space = working_color_space
        self._assumed_source_color_space = assumed_source_color_space
        self._rendering_intent = rendering_intent
        self.signals = ImageTaskSignals()
        self.setAutoDelete(True)

    @QtCore.Slot()
    def run(self) -> None:
        """Execute lightweight preview loading."""

        try:
            result = self._service.load_preview(
                self._path,
                self._working_color_space,
                self._assumed_source_color_space,
                self._rendering_intent,
            )
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

    def __init__(
        self,
        service: ImageService,
        path: Path,
        working_color_space: WorkingColorSpace = DEFAULT_WORKING_COLOR_SPACE,
        assumed_source_color_space: WorkingColorSpace = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> None:
        super().__init__()
        self._service = service
        self._path = path
        self._working_color_space = working_color_space
        self._assumed_source_color_space = assumed_source_color_space
        self._rendering_intent = rendering_intent
        self.signals = ImageTaskSignals()
        self.setAutoDelete(True)

    @QtCore.Slot()
    def run(self) -> None:
        """Execute full load + analysis task."""

        try:
            result = self._service.load_and_analyze(
                self._path,
                self._working_color_space,
                self._assumed_source_color_space,
                self._rendering_intent,
            )
        except (ImageLoadError, ImageProcessError) as exc:
            self.signals.error.emit(str(exc))
            return
        except Exception:  # pragma: no cover - defensive safety net
            logger.exception("Image processing failed: %s", self._path)
            self.signals.error.emit("An unknown error occurred while processing the image")
            return

        self.signals.finished.emit(result)
