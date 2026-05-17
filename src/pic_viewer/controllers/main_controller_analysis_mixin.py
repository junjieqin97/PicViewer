"""Analysis panel and image render behavior for main controller."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

from pic_viewer.app.dto.analysis_view import AnalysisViewSettings, LumaRgbMode, RgbChannel
from pic_viewer.app.dto.image_analysis import ImageAnalysis
from pic_viewer.domain.rules.focus_peaking import FocusPeakLevel
from pic_viewer.ui.utils.image_qt import to_qpixmap


class MainControllerAnalysisMixin:
    """Provide zoom, analysis view, and pixmap rendering helpers."""

    def _configure_analysis_refresh(self) -> None:
        """Debounce analysis panel refreshes until layout sizes stabilize."""

        self._analysis_refresh_timer.setSingleShot(True)
        # 轻量节流：避免在 splitter 拖动或 tab 切换时反复渲染。
        self._analysis_refresh_timer.setInterval(40)
        self._analysis_refresh_timer.timeout.connect(self._refresh_view_for_current_image)

        self._analysis_resize_timer.setSingleShot(True)
        self._analysis_resize_timer.setInterval(self._analysis_resize_interval_ms)
        self._analysis_resize_timer.timeout.connect(self._finish_analysis_resize)

    def _zoom_in(self) -> None:
        """Zoom in the current image by a fixed step."""

        self._adjust_zoom(self._zoom_step)

    def _zoom_out(self) -> None:
        """Zoom out the current image by a fixed step."""

        self._adjust_zoom(1 / self._zoom_step)

    def _fit_to_window(self) -> None:
        """Fit the current image to the available view size."""

        path = self._current_image_path()
        if path is None:
            return
        self._set_zoom_state(path, 1.0, True)
        self._refresh_current_image_pixmap()
        self._show_zoom_status(path)

    def _adjust_zoom(self, factor: float) -> None:
        """Apply a zoom factor for the current image."""

        path = self._current_image_path()
        if path is None:
            return
        zoom, fit = self._get_zoom_state(path)
        if fit:
            zoom = 1.0
        zoom = max(self._zoom_min, min(self._zoom_max, zoom * factor))
        self._set_zoom_state(path, zoom, False)
        self._refresh_current_image_pixmap()
        self._show_zoom_status(path)

    def _format_zoom_status(self, zoom: float, fit_to_window: bool) -> str:
        """Return the status-bar text for the current zoom state."""

        if fit_to_window:
            return self._tr("Zoom: Fit to Window")
        return self._tr("Zoom: {percent}%").format(percent=round(zoom * 100))

    def _show_zoom_status(self, path: Path) -> None:
        """Show the persisted zoom state for the given image in the status bar."""

        zoom, fit_to_window = self._get_zoom_state(path)
        self._main_window.statusBar().showMessage(
            self._format_zoom_status(zoom, fit_to_window)
        )

    def _toggle_info_panel(self, visible: bool) -> None:
        splitter = self._ui.splitMain
        info_widget = self._ui.scrollInfo

        if visible:
            info_widget.setVisible(True)
            if self._last_splitter_sizes:
                splitter.setSizes(self._last_splitter_sizes)
            else:
                splitter.setSizes(self._ui.default_split_main_sizes(splitter.width()))
            return

        self._last_splitter_sizes = splitter.sizes()
        info_widget.setVisible(False)
        splitter.setSizes([1, 0])

    def _toggle_filmstrip(self, visible: bool) -> None:
        self._ui.frameFilmstrip.setVisible(visible)
        if visible:
            self._schedule_filmstrip_resize()

    def _change_view_mode(self, mode: LumaRgbMode) -> None:
        if self._view_settings.mode == mode:
            if mode == LumaRgbMode.RGB and self._view_settings.channel != RgbChannel.ALL:
                self._change_channel(RgbChannel.ALL)
            return
        self._view_settings = AnalysisViewSettings(mode=mode, channel=self._view_settings.channel)
        self._sync_view_actions()
        self._refresh_view_for_current_image()

    def _change_channel(self, channel: RgbChannel) -> None:
        if self._view_settings.mode != LumaRgbMode.RGB:
            self._view_settings = AnalysisViewSettings(mode=LumaRgbMode.RGB, channel=channel)
            self._sync_view_actions()
            self._refresh_view_for_current_image()
            return
        if self._view_settings.channel == channel:
            return
        self._view_settings = AnalysisViewSettings(mode=LumaRgbMode.RGB, channel=channel)
        self._sync_view_actions()
        self._refresh_view_for_current_image()

    def _sync_view_actions(self) -> None:
        """Keep menu actions aligned with the current view settings."""

        rgb_mode = self._view_settings.mode == LumaRgbMode.RGB
        mode_pairs = [
            (self._ui.actModeLuma, self._view_settings.mode == LumaRgbMode.LUMA),
            (self._ui.actModeRgb, rgb_mode),
        ]
        channel_pairs = [
            (self._ui.actChannelAll, self._view_settings.channel == RgbChannel.ALL),
            (self._ui.actChannelRed, self._view_settings.channel == RgbChannel.RED),
            (self._ui.actChannelGreen, self._view_settings.channel == RgbChannel.GREEN),
            (self._ui.actChannelBlue, self._view_settings.channel == RgbChannel.BLUE),
        ]

        for action, checked in mode_pairs + channel_pairs:
            with QtCore.QSignalBlocker(action):
                action.setChecked(checked)

        if not rgb_mode:
            with QtCore.QSignalBlocker(self._ui.actChannelAll):
                self._ui.actChannelAll.setChecked(True)
        self._sync_analysis_mode_summary()

    def _sync_analysis_mode_summary(self) -> None:
        """Update the visible analysis mode summary from current settings."""

        if not hasattr(self._ui, "labelAnalysisModeValue"):
            return

        if self._view_settings.mode == LumaRgbMode.LUMA:
            mode_text = self._tr("Luma Mode")
            channel_text = self._tr("Not Applicable")
        else:
            mode_text = self._tr("RGB Mode")
            channel_text_by_channel = {
                RgbChannel.ALL: self._tr("All"),
                RgbChannel.RED: self._tr("Red"),
                RgbChannel.GREEN: self._tr("Green"),
                RgbChannel.BLUE: self._tr("Blue"),
            }
            channel_text = channel_text_by_channel[self._view_settings.channel]

        self._ui.labelAnalysisModeValue.setText(mode_text)
        self._ui.labelAnalysisChannelValue.setText(channel_text)

    def _on_underexposed_toggled(self, active: bool) -> None:
        """Handle underexposed clipping toggle changes."""

        if self._show_underexposed == active:
            return
        self._show_underexposed = active
        self._sync_histogram_overlay_state()
        self._refresh_overlay_for_current_image()

    def _on_overexposed_toggled(self, active: bool) -> None:
        """Handle overexposed clipping toggle changes."""

        if self._show_overexposed == active:
            return
        self._show_overexposed = active
        self._sync_histogram_overlay_state()
        self._refresh_overlay_for_current_image()

    def _on_focus_peak_level_triggered(self, level: FocusPeakLevel) -> None:
        """Handle focus peaking level menu changes."""

        next_level = None if self._focus_peak_level == level else level
        if self._focus_peak_level == next_level:
            return
        self._focus_peak_level = next_level
        self._sync_histogram_overlay_state()
        self._refresh_overlay_for_current_image()

    def _sync_histogram_overlay_state(self) -> None:
        """Keep histogram clipping widget state in sync with controller flags."""

        if hasattr(self._ui, "actToggleUnderexposed"):
            with QtCore.QSignalBlocker(self._ui.actToggleUnderexposed):
                self._ui.actToggleUnderexposed.setChecked(self._show_underexposed)
        if hasattr(self._ui, "actToggleOverexposed"):
            with QtCore.QSignalBlocker(self._ui.actToggleOverexposed):
                self._ui.actToggleOverexposed.setChecked(self._show_overexposed)
        self._sync_focus_peak_actions()

        self._sync_pseudo_color_summary()

        histogram_widget = self._ui.widgetHistogram
        if not hasattr(histogram_widget, "set_clipping_state"):
            return
        with QtCore.QSignalBlocker(histogram_widget):
            histogram_widget.set_clipping_state(
                self._show_underexposed,
                self._show_overexposed,
            )

    def _sync_pseudo_color_summary(self) -> None:
        """Update the visible pseudo-color toggle summary from controller state."""

        if not hasattr(self._ui, "labelPseudoColorValue"):
            return

        enabled_text = self._tr("On")
        disabled_text = self._tr("Off")
        under_text = enabled_text if self._show_underexposed else disabled_text
        over_text = enabled_text if self._show_overexposed else disabled_text
        peak_text = self._focus_peak_level_summary_text()
        self._ui.labelPseudoColorValue.setText(
            self._tr("Underexposed: {under} / Overexposed: {over} / Peaks: {peaks}").format(
                under=under_text,
                over=over_text,
                peaks=peak_text,
            )
        )

    def _sync_focus_peak_actions(self) -> None:
        """Keep focus peaking menu actions aligned with controller state."""

        action_pairs = (
            ("actPeakHigh", FocusPeakLevel.HIGH),
            ("actPeakMedium", FocusPeakLevel.MEDIUM),
            ("actPeakLow", FocusPeakLevel.LOW),
        )
        current_level = getattr(self, "_focus_peak_level", None)
        for action_name, level in action_pairs:
            if not hasattr(self._ui, action_name):
                continue
            action = getattr(self._ui, action_name)
            with QtCore.QSignalBlocker(action):
                action.setChecked(current_level == level)

    def _focus_peak_level_summary_text(self) -> str:
        """Return localized focus peaking status text."""

        level = getattr(self, "_focus_peak_level", None)
        if level is None:
            return self._tr("Off")
        labels = {
            FocusPeakLevel.HIGH: self._tr("High"),
            FocusPeakLevel.MEDIUM: self._tr("Medium"),
            FocusPeakLevel.LOW: self._tr("Low"),
        }
        return labels[level]

    def _refresh_overlay_for_current_image(self) -> None:
        """Refresh current image pixmap when clipping overlay state changes."""

        path = self._current_image_path()
        if path is None:
            return
        self._tab_preview_render_key_by_path.pop(str(path), None)
        self._refresh_current_image_pixmap()

    def _refresh_view_for_current_image(self) -> None:
        path = self._current_image_path()
        if path is None:
            return
        self.update_info_for_image(path)

    def _on_info_tab_changed(self, _: int) -> None:
        """Info tabs use fixed-size renders; no resize refresh needed."""
        return

    def _on_main_splitter_moved(self, _: int, __: int) -> None:
        """Info panel uses fixed sizes; avoid refresh during splitter drag."""
        return

    def _schedule_analysis_refresh(self) -> None:
        """Schedule a debounced refresh for histogram and waveform views."""

        path = self._current_image_path()
        if path is None:
            return
        if str(path) not in self._images_by_path:
            return
        # 重启 single-shot timer：保证在布局稳定后再渲染。
        self._analysis_refresh_timer.stop()
        self._analysis_refresh_timer.start()

    def _mark_analysis_resizing(self) -> None:
        """Flag active resizing to trigger lightweight analysis renders."""

        self._analysis_resize_active = True
        self._analysis_resize_timer.stop()
        self._analysis_resize_timer.start()

    def _finish_analysis_resize(self) -> None:
        """Restore full-quality analysis renders after resizing stops."""

        if not self._analysis_resize_active:
            return
        self._analysis_resize_active = False
        self._schedule_analysis_refresh()

    def update_info_for_image(self, image_path: Optional[Path]) -> None:
        """右侧信息区刷新接口（本版允许占位刷新）。"""

        if image_path is None:
            self._set_info_placeholders()
            self._clear_metadata_tables()
            self._last_metadata_path = None
            return

        data = self._images_by_path.get(str(image_path))
        if data is None:
            error_message = self._load_error_by_path.get(str(image_path))
            if error_message:
                self._set_info_error_placeholders()
                self._set_metadata_error_state(error_message)
                self._last_metadata_path = None
                return

            if self._is_path_loading(image_path):
                self._set_info_loading_placeholders()
                self._set_metadata_loading_state()
            else:
                self._set_info_placeholders()
                self._clear_metadata_tables()
            self._last_metadata_path = None
            preview = self._preview_by_path.get(str(image_path))
            if preview is not None:
                self._refresh_tab_preview_pixmap(image_path, preview.preview_rgb)
            return

        if str(image_path) != self._last_metadata_path:
            self._ui.tabsMetadata.setCurrentIndex(0)
        self._last_metadata_path = str(image_path)

        hist_logical = self._analysis_histogram_size
        wave_logical = self._analysis_waveform_size
        dpr = self._device_pixel_ratio_for(self._ui.widgetHistogram)
        hist_size = self._analysis_render_size(hist_logical, dpr)
        wave_size = self._analysis_render_size(wave_logical, dpr)
        render_key = (
            hist_size,
            wave_size,
            round(dpr, 2),
            self._view_settings.mode.value,
            self._view_settings.channel.value,
        )
        path_key = str(image_path)
        current_render_key = (path_key, render_key)
        if self._current_analysis_render_key == current_render_key and self._has_analysis_pixmaps():
            self._fill_metadata_tables(data.metadata)
            self._refresh_tab_pixmap(image_path, data.analysis)
            return

        fallback_view = self._view_service.build_view(data.analysis, self._view_settings)
        self._ui.widgetHistogram.setText("")
        self._ui.widgetWaveform.setText("")
        if hist_logical.width() <= 0 or hist_logical.height() <= 0:
            view = fallback_view
        elif wave_logical.width() <= 0 or wave_logical.height() <= 0:
            view = fallback_view
        else:
            view = self._image_service.render_analysis_view(
                data.analysis,
                self._view_settings,
                hist_size,
                wave_size,
                dpr,
            )
        self._ui.widgetHistogram.setPixmap(to_qpixmap(view.histogram_rgb, hist_logical, device_pixel_ratio=dpr))
        self._ui.widgetWaveform.setPixmap(to_qpixmap(view.waveform_rgb, wave_logical, device_pixel_ratio=dpr))
        self._analysis_render_key_by_path[path_key] = render_key
        self._current_analysis_render_key = current_render_key
        self._fill_metadata_tables(data.metadata)
        self._refresh_tab_pixmap(image_path, data.analysis)

    def on_main_window_resized(self) -> None:
        self._schedule_filmstrip_resize()
        path = self._current_image_path()
        if path is None:
            return
        if str(path) not in self._images_by_path:
            return

    def _set_info_placeholders(self) -> None:
        self._current_analysis_render_key = None
        self._ui.widgetHistogram.setPixmap(QtGui.QPixmap())
        self._ui.widgetWaveform.setPixmap(QtGui.QPixmap())
        self._ui.widgetHistogram.setText(self._tr("Histogram Placeholder"))
        self._ui.widgetWaveform.setText(self._tr("Waveform Placeholder"))

    def _set_info_loading_placeholders(self) -> None:
        self._current_analysis_render_key = None
        self._ui.widgetHistogram.setPixmap(QtGui.QPixmap())
        self._ui.widgetWaveform.setPixmap(QtGui.QPixmap())
        self._ui.widgetHistogram.setText(self._tr("Generating histogram..."))
        self._ui.widgetWaveform.setText(self._tr("Generating waveform..."))

    def _set_info_error_placeholders(self) -> None:
        self._current_analysis_render_key = None
        message = self._tr("Image failed to load. Analysis is unavailable.")
        self._ui.widgetHistogram.setPixmap(QtGui.QPixmap())
        self._ui.widgetWaveform.setPixmap(QtGui.QPixmap())
        self._ui.widgetHistogram.setText(message)
        self._ui.widgetWaveform.setText(message)

    def _refresh_current_image_pixmap(self) -> None:
        """Refresh the current image pixmap using the stored zoom settings."""

        path = self._current_image_path()
        if path is None:
            return
        if str(path) in self._load_error_by_path:
            return
        data = self._images_by_path.get(str(path))
        if data is None:
            preview = self._preview_by_path.get(str(path))
            if preview is not None:
                self._refresh_tab_preview_pixmap(path, preview.preview_rgb)
            return
        self._refresh_tab_pixmap(path, data.analysis)

    def _refresh_tab_pixmap(self, path: Path, analysis: ImageAnalysis) -> None:
        """Render the image preview inside the tab for the given path."""

        self._set_tab_pixmap(path, analysis.preview_rgb)

    def _refresh_tab_preview_pixmap(self, path: Path, preview_rgb: np.ndarray) -> None:
        """Render a lightweight preview before full analysis completes."""

        self._set_tab_pixmap(path, preview_rgb)

    def _set_tab_pixmap(self, path: Path, preview_rgb: np.ndarray) -> None:
        """Render an RGB preview inside the tab for the given path."""

        tab_index = self._find_tab_index_by_path(path)
        if tab_index is None:
            return
        tab = self._ui.tabsImages.widget(tab_index)
        if tab is None:
            return
        scroll_area = tab.findChild(QtWidgets.QScrollArea, "scrollImage")
        lbl = tab.findChild(QtWidgets.QLabel, "lblImage")
        if lbl is None:
            return
        base_size = lbl.size()
        if scroll_area is not None:
            base_size = scroll_area.viewport().size()
        target_size = self._target_pixmap_size(path, base_size)
        if target_size.width() <= 0 or target_size.height() <= 0:
            return
        dpr = self._device_pixel_ratio_for(lbl)
        existing = lbl.pixmap()
        path_key = str(path)
        render_key = (
            target_size.width(),
            target_size.height(),
            round(dpr, 2),
            self._show_underexposed,
            self._show_overexposed,
            self._focus_peak_level.value if self._focus_peak_level is not None else None,
            id(preview_rgb),
        )
        if (
            existing is not None
            and self._tab_preview_render_key_by_path.get(path_key) == render_key
            and self._pixmap_matches_target(existing, target_size, dpr)
        ):
            return
        display_rgb = self._image_service.build_preview_with_pseudo_color_overlay(
            preview_rgb,
            show_underexposed=self._show_underexposed,
            show_overexposed=self._show_overexposed,
            focus_peak_level=self._focus_peak_level,
        )
        pixmap = to_qpixmap(display_rgb, target_size, device_pixel_ratio=dpr)
        lbl.setPixmap(pixmap)
        lbl.setText("")
        if not pixmap.isNull():
            lbl.resize(self._pixmap_logical_size(pixmap))
            self._show_tab_image_state(path)
        self._tab_preview_render_key_by_path[path_key] = render_key

    def _target_pixmap_size(self, path: Path, base_size: QtCore.QSize) -> QtCore.QSize:
        """Calculate the target pixmap size based on zoom settings."""

        if base_size.width() <= 0 or base_size.height() <= 0:
            return base_size
        zoom, fit_to_window = self._get_zoom_state(path)
        if fit_to_window:
            return base_size
        return QtCore.QSize(
            max(1, int(base_size.width() * zoom)),
            max(1, int(base_size.height() * zoom)),
        )

    def _device_pixel_ratio_for(self, widget: QtWidgets.QWidget) -> float:
        """Best-effort device pixel ratio resolution for the widget's screen."""

        screen: Optional[QtGui.QScreen] = None
        window = widget.window().windowHandle()
        if window is not None:
            screen = window.screen()
        if screen is None:
            screen = QtWidgets.QApplication.primaryScreen()
        if screen is None:
            return 1.0
        dpr = getattr(screen, "devicePixelRatioF", screen.devicePixelRatio)()
        try:
            return max(1.0, float(dpr))
        except (TypeError, ValueError):
            return 1.0

    def _physical_size(self, logical_size: QtCore.QSize, dpr: float) -> QtCore.QSize:
        """Scale a logical size into physical pixels using DPR."""

        return QtCore.QSize(
            max(1, int(round(logical_size.width() * dpr))),
            max(1, int(round(logical_size.height() * dpr))),
        )

    def _analysis_size(self, logical_size: QtCore.QSize, dpr: float) -> tuple[int, int]:
        """Convert a logical QSize into (height, width) physical pixels."""

        physical = self._physical_size(logical_size, dpr)
        return (physical.height(), physical.width())

    def _analysis_render_size(self, logical_size: QtCore.QSize, dpr: float) -> tuple[int, int]:
        """Return the render size, downsampled during active resizing."""

        size = self._analysis_size(logical_size, dpr)
        if not self._analysis_resize_active:
            return size
        return self._scale_analysis_size(size, self._analysis_preview_scale)

    def _scale_analysis_size(self, size: tuple[int, int], scale: float) -> tuple[int, int]:
        """Scale the analysis render size while keeping a minimum readable size."""

        height, width = size
        if scale <= 0 or scale >= 1:
            return size

        scaled_height = max(1, int(round(height * scale)))
        scaled_width = max(1, int(round(width * scale)))
        min_side = self._analysis_preview_min_side

        if height > min_side:
            scaled_height = max(min_side, scaled_height)
        else:
            scaled_height = height
        if width > min_side:
            scaled_width = max(min_side, scaled_width)
        else:
            scaled_width = width

        return (scaled_height, scaled_width)

    def _has_analysis_pixmaps(self) -> bool:
        """Return True when histogram and waveform pixmaps are present."""

        hist_pix = self._ui.widgetHistogram.pixmap()
        wave_pix = self._ui.widgetWaveform.pixmap()
        if hist_pix is None or hist_pix.isNull():
            return False
        if wave_pix is None or wave_pix.isNull():
            return False
        return True

    def _pixmap_logical_size(self, pixmap: QtGui.QPixmap) -> QtCore.QSize:
        """Return pixmap size in device-independent pixels."""

        dpr = pixmap.devicePixelRatio()
        dpr = dpr if dpr and dpr > 0 else 1.0
        return QtCore.QSize(
            max(1, int(round(pixmap.width() / dpr))),
            max(1, int(round(pixmap.height() / dpr))),
        )

    def _pixmap_matches_target(
        self,
        pixmap: QtGui.QPixmap,
        target_size: QtCore.QSize,
        dpr: float,
    ) -> bool:
        """Check whether an existing pixmap already matches the logical target."""

        if pixmap.isNull():
            return False
        logical_size = self._pixmap_logical_size(pixmap)
        if logical_size != target_size:
            return False
        existing_dpr = pixmap.devicePixelRatio()
        existing_dpr = existing_dpr if existing_dpr and existing_dpr > 0 else 1.0
        return abs(existing_dpr - max(1.0, dpr)) < 0.01

    def _get_zoom_state(self, path: Path) -> tuple[float, bool]:
        """Return zoom factor and fit flag for the given image path."""

        key = str(path)
        zoom = self._zoom_by_path.get(key)
        fit = self._fit_to_window_by_path.get(key)
        if zoom is None:
            zoom = 1.0
            self._zoom_by_path[key] = zoom
        if fit is None:
            fit = True
            self._fit_to_window_by_path[key] = fit
        return zoom, fit

    def _set_zoom_state(self, path: Path, zoom: float, fit_to_window: bool) -> None:
        """Persist zoom state for the given image path."""

        key = str(path)
        self._zoom_by_path[key] = zoom
        self._fit_to_window_by_path[key] = fit_to_window
