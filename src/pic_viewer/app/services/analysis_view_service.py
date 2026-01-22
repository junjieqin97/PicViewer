"""Application service for selecting analysis preview images."""

from __future__ import annotations

from pic_viewer.app.dto.analysis_view import (
    AnalysisView,
    AnalysisViewSettings,
    LumaRgbMode,
    RgbChannel,
)
from pic_viewer.app.dto.image_analysis import ImageAnalysis


class AnalysisViewService:
    """Select histogram and waveform previews based on view settings."""

    def build_view(self, analysis: ImageAnalysis, settings: AnalysisViewSettings) -> AnalysisView:
        """Return preview images based on the current settings.

        Args:
            analysis: Precomputed analysis artifacts.
            settings: View settings for histogram/waveform.

        Returns:
            AnalysisView: Preview images to render.
        """

        if settings.mode == LumaRgbMode.LUMA:
            return AnalysisView(
                histogram_rgb=analysis.histogram_luma,
                waveform_rgb=analysis.waveform_luma,
            )

        if settings.channel == RgbChannel.RED:
            return AnalysisView(
                histogram_rgb=analysis.histogram_r,
                waveform_rgb=analysis.waveform_r,
            )
        if settings.channel == RgbChannel.GREEN:
            return AnalysisView(
                histogram_rgb=analysis.histogram_g,
                waveform_rgb=analysis.waveform_g,
            )
        if settings.channel == RgbChannel.BLUE:
            return AnalysisView(
                histogram_rgb=analysis.histogram_b,
                waveform_rgb=analysis.waveform_b,
            )

        return AnalysisView(
            histogram_rgb=analysis.histogram_rgb,
            waveform_rgb=analysis.waveform_rgb,
        )
