"""Main window controller for wiring UI interactions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional

from PySide6 import QtCore, QtWidgets

from pic_viewer.app.dto.analysis_view import AnalysisViewSettings, LumaRgbMode, RgbChannel
from pic_viewer.app.dto.image_analysis import ImageLoadResult, PreviewLoadResult
from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.controllers.main_controller_analysis_mixin import MainControllerAnalysisMixin
from pic_viewer.controllers.main_controller_filmstrip_mixin import MainControllerFilmstripMixin
from pic_viewer.controllers.main_controller_interaction_mixin import MainControllerInteractionMixin
from pic_viewer.controllers.main_controller_loading_mixin import MainControllerLoadingMixin
from pic_viewer.controllers.main_controller_metadata_mixin import MainControllerMetadataMixin
from pic_viewer.controllers.main_controller_reference_line_mixin import MainControllerReferenceLineMixin
from pic_viewer.controllers.main_controller_tabs_mixin import MainControllerTabsMixin
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    DEFAULT_DISPLAY_COLOR_SPACE,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT
from pic_viewer.domain.rules.focus_peaking import FocusPeakLevel
from pic_viewer.domain.rules.reference_lines import ReferenceLineSettings
from pic_viewer.ui.workers.image_worker import ImageLoadTask, PreviewLoadTask

MAX_IMAGE_LOAD_CONCURRENCY = 8
TRANSLATION_CONTEXTS = (
    "MainController",
    "MainControllerAnalysisMixin",
    "MainControllerInteractionMixin",
    "MainControllerLoadingMixin",
    "MainControllerMetadataMixin",
    "MainControllerTabsMixin",
)


class MainController(
    MainControllerInteractionMixin,
    MainControllerAnalysisMixin,
    MainControllerReferenceLineMixin,
    MainControllerTabsMixin,
    MainControllerLoadingMixin,
    MainControllerFilmstripMixin,
    MainControllerMetadataMixin,
    QtCore.QObject,
):
    """负责主窗口信号槽与Tab-胶卷同步的控制器。"""

    def __init__(
        self,
        main_window: QtWidgets.QMainWindow,
        ui: "MainWindowUI",
        image_service: ImageService,
        view_service: AnalysisViewService,
    ) -> None:
        QtCore.QObject.__init__(self, main_window)
        self._main_window = main_window
        self._ui = ui
        self._image_service = image_service
        self._view_service = view_service

        self._images_by_path: Dict[str, ImageLoadResult] = {}
        self._preview_by_path: Dict[str, PreviewLoadResult] = {}
        self._preview_tasks_by_path: Dict[str, PreviewLoadTask] = {}
        self._load_tasks_by_path: Dict[str, ImageLoadTask] = {}
        self._load_error_by_path: Dict[str, str] = {}
        self._active_session_by_path: Dict[str, int] = {}
        self._session_counter_by_path: Dict[str, int] = {}
        self._thread_pool = QtCore.QThreadPool(self._main_window)
        self._thread_pool.setMaxThreadCount(MAX_IMAGE_LOAD_CONCURRENCY)
        self._syncing_selection = False
        self._active_image_path: Optional[Path] = None
        self._detached_image_windows: Dict[str, QtWidgets.QWidget] = {}
        self._detached_info_windows: Dict[str, QtWidgets.QWidget] = {}
        self._view_settings = AnalysisViewSettings(mode=LumaRgbMode.LUMA, channel=RgbChannel.ALL)
        self._display_color_space = DEFAULT_DISPLAY_COLOR_SPACE
        self._assumed_source_color_space = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE
        self._rendering_intent = DEFAULT_RENDERING_INTENT
        self._last_splitter_sizes: Optional[list[int]] = None
        self._last_metadata_path: Optional[str] = None
        self._cursor_boundary_margin = 4
        self._cursor_override_target: Optional[QtWidgets.QWidget] = None
        self._filmstrip_icon_side = self._ui.listFilmstrip.iconSize().width() or 96
        self._filmstrip_resize_timer = QtCore.QTimer(self)
        self._analysis_refresh_timer = QtCore.QTimer(self)
        self._analysis_resize_timer = QtCore.QTimer(self)
        self._analysis_resize_active = False
        self._analysis_resize_interval_ms = 180
        self._analysis_preview_scale = 0.6
        self._analysis_preview_min_side = 180
        hist_size = getattr(self._ui, "info_panel_histogram_size", self._ui.widgetHistogram.size())
        wave_size = getattr(self._ui, "info_panel_waveform_size", self._ui.widgetWaveform.size())
        self._analysis_histogram_size = QtCore.QSize(hist_size.width(), hist_size.height())
        self._analysis_waveform_size = QtCore.QSize(wave_size.width(), wave_size.height())
        self._zoom_by_path: Dict[str, float] = {}
        self._fit_to_window_by_path: Dict[str, bool] = {}
        self._analysis_render_key_by_path: Dict[str, tuple] = {}
        self._current_analysis_render_key: Optional[tuple[str, tuple]] = None
        self._tab_preview_render_key_by_path: Dict[str, tuple] = {}
        self._show_underexposed = False
        self._show_overexposed = False
        self._focus_peak_level: FocusPeakLevel | None = None
        self._show_metadata_overlay = self._ui.actToggleMetadataOverlay.isChecked()
        self._reference_line_settings = ReferenceLineSettings()
        self._zoom_step = 1.25
        self._zoom_min = 0.1
        self._zoom_max = 6.0
        self._image_dragging = False
        self._image_drag_start_pos: Optional[QtCore.QPoint] = None
        self._image_drag_start_scroll: Optional[QtCore.QPoint] = None
        self._image_drag_scroll_area: Optional[QtWidgets.QScrollArea] = None
        self._image_context_menu = self._ui.menuImageContext
        self._pixel_sample_analysis_key: Optional[tuple[str, int]] = None

        self._connect_signals()
        self._install_cursor_tracking()
        self._install_file_drop_handling()
        self._configure_filmstrip_resize()
        self._configure_analysis_refresh()
        self._apply_initial_visibility()
        self._sync_view_actions()
        self._sync_histogram_overlay_state()
        self._sync_reference_line_actions()
        self._sync_reference_line_widgets()
        self._refresh_actions_state()
        self.update_info_for_image(None)
        self._ensure_empty_image_placeholder()

    def _tr(self, text: str) -> str:
        for context in TRANSLATION_CONTEXTS:
            translated = QtCore.QCoreApplication.translate(context, text)
            if translated != text:
                return translated
        return QtCore.QCoreApplication.translate("MainController", text)

    def _connect_signals(self) -> None:
        self._ui.actOpenFile.triggered.connect(self._open_file)
        self._ui.actOpenFolder.triggered.connect(self._open_folder)
        self._ui.actCloseTab.triggered.connect(self.close_current_tab)
        self._ui.actExit.triggered.connect(self._main_window.close)
        self._ui.actAbout.triggered.connect(self._show_about)
        self._ui.actThirdPartyLicenses.triggered.connect(self._show_third_party_licenses)

        self._ui.actZoomIn.triggered.connect(self._zoom_in)
        self._ui.actZoomOut.triggered.connect(self._zoom_out)
        self._ui.actFitToWindow.triggered.connect(self._fit_to_window)
        self._ui.actShowInFolder.triggered.connect(self._show_current_image_in_folder)

        self._ui.actToggleInfoPanel.toggled.connect(self._toggle_info_panel)
        self._ui.actToggleAnalysisToolbar.toggled.connect(self._toggle_analysis_toolbar)
        self._ui.actToggleFilmstrip.toggled.connect(self._toggle_filmstrip)
        self._ui.actModeLuma.triggered.connect(lambda: self._change_view_mode(LumaRgbMode.LUMA))
        self._ui.actModeRgb.triggered.connect(lambda: self._change_view_mode(LumaRgbMode.RGB))
        self._ui.actChannelAll.triggered.connect(lambda: self._change_channel(RgbChannel.ALL))
        self._ui.actChannelRed.triggered.connect(lambda: self._change_channel(RgbChannel.RED))
        self._ui.actChannelGreen.triggered.connect(lambda: self._change_channel(RgbChannel.GREEN))
        self._ui.actChannelBlue.triggered.connect(lambda: self._change_channel(RgbChannel.BLUE))
        self._ui.comboSpecifiedImageColorSpace.currentIndexChanged.connect(
            self._on_assumed_source_color_space_changed
        )
        self._ui.comboRenderingIntent.currentIndexChanged.connect(self._on_rendering_intent_changed)
        self._ui.comboDisplayColorSpace.currentIndexChanged.connect(self._on_display_color_space_changed)
        if hasattr(self._ui, "actToggleUnderexposed"):
            self._ui.actToggleUnderexposed.toggled.connect(self._on_underexposed_toggled)
        if hasattr(self._ui, "actToggleOverexposed"):
            self._ui.actToggleOverexposed.toggled.connect(self._on_overexposed_toggled)
        if hasattr(self._ui, "actPeakHigh"):
            self._ui.actPeakHigh.triggered.connect(
                lambda _checked=False: self._on_focus_peak_level_triggered(FocusPeakLevel.HIGH)
            )
        if hasattr(self._ui, "actPeakMedium"):
            self._ui.actPeakMedium.triggered.connect(
                lambda _checked=False: self._on_focus_peak_level_triggered(FocusPeakLevel.MEDIUM)
            )
        if hasattr(self._ui, "actPeakLow"):
            self._ui.actPeakLow.triggered.connect(
                lambda _checked=False: self._on_focus_peak_level_triggered(FocusPeakLevel.LOW)
            )
        if hasattr(self._ui, "actToggleCrossReferenceLine"):
            self._ui.actToggleCrossReferenceLine.toggled.connect(self._on_cross_reference_line_toggled)
        if hasattr(self._ui, "actToggleDiagonalReferenceLine"):
            self._ui.actToggleDiagonalReferenceLine.toggled.connect(self._on_diagonal_reference_line_toggled)
        if hasattr(self._ui, "actToggleThirdsReferenceLine"):
            self._ui.actToggleThirdsReferenceLine.toggled.connect(self._on_thirds_reference_line_toggled)
        if hasattr(self._ui, "actToggleMetadataOverlay"):
            self._ui.actToggleMetadataOverlay.toggled.connect(self._on_metadata_overlay_toggled)

        self._ui.tabsImages.currentChanged.connect(self._on_tab_changed)
        self._ui.tabsImages.tabCloseRequested.connect(self.close_tab)
        if hasattr(self._ui.tabsImages, "tab_detached"):
            self._ui.tabsImages.tab_detached.connect(self._on_image_tab_detached)
            self._ui.tabsImages.tab_reattached.connect(self._on_image_tab_reattached)
            self._ui.tabsImages.floating_window_activated.connect(self._on_image_floating_window_activated)
        self._ui.listFilmstrip.currentRowChanged.connect(self._on_filmstrip_row_changed)
        self._ui.tabsInfo.currentChanged.connect(self._on_info_tab_changed)
        if hasattr(self._ui.tabsInfo, "tab_detached"):
            self._ui.tabsInfo.tab_detached.connect(self._on_info_tab_detached)
            self._ui.tabsInfo.tab_reattached.connect(self._on_info_tab_reattached)
        self._ui.splitMain.splitterMoved.connect(self._on_main_splitter_moved)
        if hasattr(self._ui.widgetHistogram, "underexposed_toggled"):
            self._ui.widgetHistogram.underexposed_toggled.connect(self._on_underexposed_toggled)
        if hasattr(self._ui.widgetHistogram, "overexposed_toggled"):
            self._ui.widgetHistogram.overexposed_toggled.connect(self._on_overexposed_toggled)


if TYPE_CHECKING:  # pragma: no cover
    from pic_viewer.ui.windows.main_window import MainWindowUI
