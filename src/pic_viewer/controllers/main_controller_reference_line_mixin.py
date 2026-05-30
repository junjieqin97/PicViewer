"""Reference line overlay state synchronization for the main controller."""

from __future__ import annotations

from dataclasses import replace

from PySide6 import QtCore, QtWidgets

from pic_viewer.domain.rules.reference_lines import ReferenceLineSettings
from pic_viewer.ui.utils.signal_blocker import block_signals
from pic_viewer.ui.widgets.image_display_label import ImageDisplayLabel


class MainControllerReferenceLineMixin:
    """Provide global reference line toggle state and widget synchronization."""

    def _on_cross_reference_line_toggled(self, active: bool) -> None:
        """Toggle cross reference lines without changing other reference types."""

        self._set_reference_line_settings(cross=active)

    def _on_diagonal_reference_line_toggled(self, active: bool) -> None:
        """Toggle diagonal reference lines without changing other reference types."""

        self._set_reference_line_settings(diagonal=active)

    def _on_thirds_reference_line_toggled(self, active: bool) -> None:
        """Toggle rule-of-thirds reference lines without changing other types."""

        self._set_reference_line_settings(thirds=active)

    def _set_reference_line_settings(
        self,
        *,
        cross: bool | None = None,
        diagonal: bool | None = None,
        thirds: bool | None = None,
    ) -> None:
        current = getattr(self, "_reference_line_settings", ReferenceLineSettings())
        next_settings = replace(
            current,
            cross=current.cross if cross is None else cross,
            diagonal=current.diagonal if diagonal is None else diagonal,
            thirds=current.thirds if thirds is None else thirds,
        )
        if current == next_settings:
            return
        self._reference_line_settings = next_settings
        self._sync_reference_line_actions()
        self._sync_reference_line_widgets()

    def _sync_reference_line_actions(self) -> None:
        """Keep reference line menu actions aligned with controller state."""

        settings = getattr(self, "_reference_line_settings", ReferenceLineSettings())
        action_pairs = (
            ("actToggleCrossReferenceLine", settings.cross),
            ("actToggleDiagonalReferenceLine", settings.diagonal),
            ("actToggleThirdsReferenceLine", settings.thirds),
        )
        for action_name, checked in action_pairs:
            if not hasattr(self._ui, action_name):
                continue
            action = getattr(self._ui, action_name)
            with block_signals(action):
                action.setChecked(checked)

    def _sync_reference_line_widgets(self) -> None:
        """Apply the current reference line settings to all open image labels."""

        settings = getattr(self, "_reference_line_settings", ReferenceLineSettings())
        tab_widget = getattr(self._ui, "tabsImages", None)
        if not isinstance(tab_widget, QtWidgets.QTabWidget):
            return
        tabs = [tab_widget.widget(index) for index in range(tab_widget.count())]
        for floating in getattr(self, "_detached_image_windows", {}).values():
            if hasattr(floating, "content_widget"):
                tabs.append(floating.content_widget())

        for tab in tabs:
            if tab is None:
                continue
            for label in tab.findChildren(ImageDisplayLabel, "lblImage"):
                label.set_reference_line_settings(settings)

    def _apply_reference_line_settings_to_label(self, label: QtWidgets.QLabel) -> None:
        """Apply current reference line settings to a newly created image label."""

        if not hasattr(label, "set_reference_line_settings"):
            return
        settings = getattr(self, "_reference_line_settings", ReferenceLineSettings())
        label.set_reference_line_settings(settings)
