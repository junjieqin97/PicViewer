"""Threaded image loading worker."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt5 import QtCore

from pic_viewer.app.services.image_service import ImageService
from pic_viewer.common.errors import ImageLoadError, ImageProcessError

logger = logging.getLogger(__name__)


class ImageLoadWorker(QtCore.QObject):
    """Run image loading and analysis in a worker thread."""

    # 需要跨线程（QueuedConnection）传递 Python 对象，必须使用 PyQt_PyObject。
    # 否则会出现信号无法排队传递，导致 UI 一直停留在“加载中”，线程也无法正常退出。
    finished = QtCore.pyqtSignal(object)
    error = QtCore.pyqtSignal(str)

    def __init__(self, service: ImageService, path: Path) -> None:
        super().__init__()
        self._service = service
        self._path = path

    @QtCore.pyqtSlot()
    def run(self) -> None:
        """Execute the load/analysis task."""

        try:
            result = self._service.load_and_analyze(self._path)
        except (ImageLoadError, ImageProcessError) as exc:
            self.error.emit(str(exc))
            return
        except Exception as exc:  # pragma: no cover - defensive safety net
            logger.exception("图像处理异常: %s", self._path)
            self.error.emit("处理图片时发生未知错误")
            return

        self.finished.emit(result)
