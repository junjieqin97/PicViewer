"""PicViewer application entry point."""

from __future__ import annotations

# Third-party dependencies:
# - PyQt5>=5.15
# - opencv-python>=4.7
# - numpy>=1.23
# - rawpy>=0.17 (optional, for RAW formats)

import logging
import sys
from pathlib import Path

from PyQt5 import QtCore, QtWidgets

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.config.settings import AppSettings, load_settings
from pic_viewer.domain.rules.analysis import ImageAnalyzer
from pic_viewer.infra.adapters.image_reader import ImageReader
from pic_viewer.infra.adapters.metadata_reader import MetadataReader
from pic_viewer.ui.i18n.runtime import install_translator, resolve_language
from pic_viewer.ui.windows.main_window import MainWindow


def configure_logging(settings: AppSettings) -> None:
    """Configure application logging."""

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_services(settings: AppSettings) -> ImageService:
    """Wire application services and dependencies."""

    reader = ImageReader(allow_raw=settings.allow_raw)
    analyzer = ImageAnalyzer()
    metadata_reader = MetadataReader()
    return ImageService(reader=reader, analyzer=analyzer, metadata_reader=metadata_reader)


def main() -> None:
    settings = load_settings()
    configure_logging(settings)

    # 必须在 QApplication 创建前启用 High-DPI 支持。
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(sys.argv)
    requested_language = resolve_language(settings.language_override)
    active_language, translator = install_translator(app, requested_language)
    if translator is not None:
        app._picviewer_translator = translator  # type: ignore[attr-defined]
    logging.getLogger(__name__).info("UI language: requested=%s, active=%s", requested_language, active_language)

    service = build_services(settings)
    view_service = AnalysisViewService()
    window = MainWindow(service, view_service)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
