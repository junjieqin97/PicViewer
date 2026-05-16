"""PicViewer application entry point."""

from __future__ import annotations

# Third-party dependencies:
# - PyQt5>=5.15
# - opencv-python>=4.7
# - numpy>=1.23
# - rawpy>=0.17 (optional, for RAW formats)

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from PyQt5 import QtCore, QtWidgets

if __name__ == "__main__" and __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.config.logging_config import configure_logging
from pic_viewer.config.settings import AppSettings, load_settings
from pic_viewer.domain.rules.analysis import ImageAnalyzer
from pic_viewer.infra.adapters.image_reader import ImageReader
from pic_viewer.infra.adapters.metadata_reader import MetadataReader
from pic_viewer.ui.i18n.runtime import install_translator, resolve_language
from pic_viewer.ui.resources.icons import load_app_icon
from pic_viewer.ui.windows.main_window import MainWindow


def parse_command_line(argv: Sequence[str]) -> tuple[bool, list[str]]:
    """Parse PicViewer CLI flags while preserving Qt arguments.

    Args:
        argv: Full process argument vector, including program name.

    Returns:
        tuple[bool, list[str]]: Developer mode flag and arguments for QApplication.
    """

    parser = argparse.ArgumentParser(prog=Path(argv[0]).name if argv else "picviewer")
    parser.add_argument(
        "--developer-mode",
        action="store_true",
        help="Write application logs to ~/.PicViewer/logs/picviewer.log.",
    )
    parsed_args, qt_args = parser.parse_known_args(list(argv[1:]))
    program_name = argv[0] if argv else "picviewer"
    return parsed_args.developer_mode, [program_name, *qt_args]


def build_services(settings: AppSettings) -> ImageService:
    """Wire application services and dependencies."""

    reader = ImageReader(allow_raw=settings.allow_raw)
    analyzer = ImageAnalyzer()
    metadata_reader = MetadataReader()
    return ImageService(reader=reader, analyzer=analyzer, metadata_reader=metadata_reader)


def main(argv: Sequence[str] | None = None) -> None:
    runtime_argv = list(sys.argv if argv is None else argv)
    developer_mode, qt_args = parse_command_line(runtime_argv)
    settings = load_settings(developer_mode=developer_mode)
    configure_logging(settings)

    # 必须在 QApplication 创建前启用 High-DPI 支持。
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    app = QtWidgets.QApplication(qt_args)
    app_icon = load_app_icon()
    app.setWindowIcon(app_icon)
    requested_language = resolve_language(settings.language_override)
    active_language, translator = install_translator(app, requested_language)
    if translator is not None:
        app._picviewer_translator = translator  # type: ignore[attr-defined]
    logging.getLogger(__name__).info("UI language: requested=%s, active=%s", requested_language, active_language)

    service = build_services(settings)
    view_service = AnalysisViewService()
    window = MainWindow(service, view_service)
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
