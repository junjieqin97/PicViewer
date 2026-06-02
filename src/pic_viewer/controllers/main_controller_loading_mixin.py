"""Background image loading behavior for main controller."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pic_viewer.app.dto.image_analysis import ImageLoadResult, PreviewLoadResult
from pic_viewer.ui.workers.image_worker import ImageLoadTask, PreviewLoadTask

logger = logging.getLogger(__name__)


class MainControllerLoadingMixin:
    """Provide async preview/full image loading helpers."""

    def _start_path_session(self, path: Path) -> int:
        """Start a new active session for a path to invalidate stale tasks."""

        key = str(path)
        session = self._session_counter_by_path.get(key, 0) + 1
        self._session_counter_by_path[key] = session
        self._active_session_by_path[key] = session
        return session

    def _is_session_active(self, path: Path, session: int) -> bool:
        return self._active_session_by_path.get(str(path)) == session

    def _activate_existing_path(self, path: Path) -> None:
        """Switch to an existing tab/filmstrip item and trigger lazy full load."""

        tab_index = self._find_tab_index_by_path(path)
        if tab_index is not None:
            self._ui.tabsImages.setCurrentIndex(tab_index)
        elif hasattr(self, "_activate_detached_image_window"):
            self._activate_detached_image_window(path)
        row = self._find_filmstrip_row_by_path(path)
        if row is not None:
            self._ui.listFilmstrip.setCurrentRow(row)
        self._ensure_full_load(path)

    def _ensure_preview_load(self, path: Path, session: Optional[int] = None) -> None:
        key = str(path)
        if key in self._load_error_by_path:
            return
        if key in self._images_by_path or key in self._preview_by_path or key in self._preview_tasks_by_path:
            return
        if session is None:
            session = self._active_session_by_path.get(key)
        if session is None:
            return

        self._show_tab_loading_state(
            path,
            self._tr("Loading preview"),
            self._tr("Loading preview: {name}").format(name=path.name),
        )
        task = PreviewLoadTask(
            self._image_service,
            path,
            self._working_color_space,
            self._assumed_source_color_space,
            self._rendering_intent,
        )
        task.signals.finished.connect(lambda result, p=path, s=session: self._on_preview_loaded(p, s, result))
        task.signals.error.connect(lambda message, p=path, s=session: self._on_preview_error(p, s, message))
        self._preview_tasks_by_path[key] = task
        self._thread_pool.start(task, -1)

    def _ensure_full_load(self, path: Optional[Path], session: Optional[int] = None) -> None:
        if path is None:
            return
        key = str(path)
        if key in self._load_error_by_path:
            return
        if key in self._images_by_path or key in self._load_tasks_by_path:
            return
        if session is None:
            session = self._active_session_by_path.get(key)
        if session is None:
            return

        self._main_window.statusBar().showMessage(self._tr("Loading image: {name}").format(name=path.name))
        if key not in self._preview_by_path:
            self._show_tab_loading_state(
                path,
                self._tr("Loading image"),
                self._tr("Loading image and generating analysis: {name}").format(name=path.name),
            )
        task = ImageLoadTask(
            self._image_service,
            path,
            self._working_color_space,
            self._assumed_source_color_space,
            self._rendering_intent,
        )
        task.signals.finished.connect(lambda result, p=path, s=session: self._on_loaded(p, s, result))
        task.signals.error.connect(lambda message, p=path, s=session: self._on_error(p, s, message))
        self._load_tasks_by_path[key] = task
        self._thread_pool.start(task, 1)
        if self._current_image_path() == path:
            self.update_info_for_image(path)

    def _cancel_tasks_for_path(self, path: Path) -> None:
        """Invalidate path session and forget pending task references."""

        key = str(path)
        self._active_session_by_path.pop(key, None)
        self._preview_tasks_by_path.pop(key, None)
        self._load_tasks_by_path.pop(key, None)

    def _on_preview_loaded(self, path: Path, session: int, result: PreviewLoadResult) -> None:
        key = str(path)
        self._preview_tasks_by_path.pop(key, None)
        if not self._is_session_active(path, session):
            return
        if result.working_color_space != self._working_color_space:
            return
        if result.assumed_source_color_space != self._assumed_source_color_space:
            return
        if result.rendering_intent != self._rendering_intent:
            return

        self._load_error_by_path.pop(key, None)
        self._preview_by_path[key] = result
        self._tab_preview_render_key_by_path.pop(key, None)
        self._update_filmstrip_icon(path, result.preview_rgb)
        if key in self._images_by_path:
            return
        if self._current_image_path() == path:
            self.update_info_for_image(path)
        else:
            self._refresh_tab_preview_pixmap(path, result.preview_rgb)

    def _on_preview_error(self, path: Path, session: int, message: str) -> None:
        self._preview_tasks_by_path.pop(str(path), None)
        if not self._is_session_active(path, session):
            return
        logger.warning("Failed to load preview image: %s, %s", path, message)
        if self._current_image_path() == path:
            self._main_window.statusBar().showMessage(
                self._tr("Preview failed, trying full image load: {name}").format(name=path.name)
            )
            self._ensure_full_load(path, session)

    def _on_loaded(self, path: Path, session: int, result: ImageLoadResult) -> None:
        key = str(path)
        self._load_tasks_by_path.pop(key, None)
        if not self._is_session_active(path, session):
            return
        if result.analysis.working_color_space != self._working_color_space:
            return
        if result.analysis.assumed_source_color_space != self._assumed_source_color_space:
            return
        if result.analysis.rendering_intent != self._rendering_intent:
            return

        self._load_error_by_path.pop(key, None)
        self._images_by_path[key] = result
        self._preview_by_path.pop(key, None)
        # 强制下一次刷新使用最新分析结果重渲染。
        self._analysis_render_key_by_path.pop(key, None)
        self._tab_preview_render_key_by_path.pop(key, None)
        self._update_filmstrip_icon(path, result.analysis.preview_rgb)

        if self._current_image_path() == path:
            self.update_info_for_image(path)
        else:
            self._refresh_tab_pixmap(path, result.analysis)

        self._main_window.statusBar().showMessage(self._tr("Loaded: {name}").format(name=path.name))

    def _on_error(self, path: Path, session: int, message: str) -> None:
        key = str(path)
        self._load_tasks_by_path.pop(key, None)
        if not self._is_session_active(path, session):
            return
        self._tab_preview_render_key_by_path.pop(key, None)

        logger.warning("Failed to load image: %s, %s", path, message)
        localized_message = self._localize_backend_error_message(message)
        self._load_error_by_path[key] = localized_message
        self._show_tab_error_state(path, localized_message)
        self._main_window.statusBar().showMessage(self._tr("Failed to load: {name}").format(name=path.name))

        if self._current_image_path() == path:
            self.update_info_for_image(path)

    def _is_path_loading(self, path: Path) -> bool:
        key = str(path)
        return key in self._preview_tasks_by_path or key in self._load_tasks_by_path

    def _localize_backend_error_message(self, message: str) -> str:
        mapping = {
            "Image file does not exist": self._tr("Image file does not exist"),
            "Unsupported image format": self._tr("Unsupported image format"),
            "Unable to read this image file": self._tr("Unable to read this image file"),
            "Image analysis failed": self._tr("Image analysis failed"),
            "An unknown error occurred while processing the image": self._tr(
                "An unknown error occurred while processing the image"
            ),
        }
        return mapping.get(message, self._tr("An unknown error occurred while processing the image"))
