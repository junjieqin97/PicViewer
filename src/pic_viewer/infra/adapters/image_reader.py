"""Image loading adapter for files and RAW formats."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from pic_viewer.common.errors import ImageLoadError
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    DEFAULT_WORKING_COLOR_SPACE,
    WorkingColorSpace,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter

logger = logging.getLogger(__name__)


class ImageReader:
    """Read images from disk with optional RAW support."""

    def __init__(self, allow_raw: bool, color_converter: ColorProfileConverter | None = None) -> None:
        self._allow_raw = allow_raw
        self._color_converter = color_converter or ColorProfileConverter()

    def read(
        self,
        path: Path,
        working_color_space: WorkingColorSpace = DEFAULT_WORKING_COLOR_SPACE,
        assumed_source_color_space: WorkingColorSpace = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> np.ndarray:
        """Read image file into BGR array in the selected working space.

        Args:
            path: File path to load.
            working_color_space: Target RGB working color space.
            assumed_source_color_space: Source color space to use when ICC is unavailable.
            rendering_intent: ICC rendering intent used for gamut mapping.

        Returns:
            numpy.ndarray: BGR image array in the working color space.

        Raises:
            ImageLoadError: If the file cannot be loaded.
        """

        self._validate_path(path)

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            return self._convert_to_working_space(
                path,
                image,
                working_color_space,
                assumed_source_color_space,
                rendering_intent,
            )

        if not self._allow_raw:
            raise ImageLoadError("Unsupported image format")

        raw_image = self._read_raw(path, preview=False)
        if raw_image is None:
            raise ImageLoadError("Unable to read this image file")
        return self._convert_to_working_space(
            path,
            raw_image,
            working_color_space,
            DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
            rendering_intent,
        )

    def read_with_color_profile_info(
        self,
        path: Path,
        working_color_space: WorkingColorSpace = DEFAULT_WORKING_COLOR_SPACE,
        assumed_source_color_space: WorkingColorSpace = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Read image file into BGR array and return source ICC status."""

        self._validate_path(path)

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            return self._convert_to_working_space_with_info(
                path,
                image,
                working_color_space,
                assumed_source_color_space,
                rendering_intent,
            )

        if not self._allow_raw:
            raise ImageLoadError("Unsupported image format")

        raw_image = self._read_raw(path, preview=False)
        if raw_image is None:
            raise ImageLoadError("Unable to read this image file")
        return self._convert_to_working_space_with_info(
            path,
            raw_image,
            working_color_space,
            DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
            rendering_intent,
        )

    def read_preview(
        self,
        path: Path,
        max_edge: int = 1920,
        working_color_space: WorkingColorSpace = DEFAULT_WORKING_COLOR_SPACE,
        assumed_source_color_space: WorkingColorSpace = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> np.ndarray:
        """Read a faster low-cost preview for incremental UI updates."""

        self._validate_path(path)
        max_edge = max(1, int(max_edge))
        reduced_flags = (
            cv2.IMREAD_REDUCED_COLOR_8,
            cv2.IMREAD_REDUCED_COLOR_4,
            cv2.IMREAD_REDUCED_COLOR_2,
        )

        for flag in reduced_flags:
            image = cv2.imread(str(path), flag)
            if image is not None:
                preview = self._resize_if_needed(image, max_edge)
                return self._convert_to_working_space(
                    path,
                    preview,
                    working_color_space,
                    assumed_source_color_space,
                    rendering_intent,
                )

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            preview = self._resize_if_needed(image, max_edge)
            return self._convert_to_working_space(
                path,
                preview,
                working_color_space,
                assumed_source_color_space,
                rendering_intent,
            )

        if not self._allow_raw:
            raise ImageLoadError("Unsupported image format")

        raw_image = self._read_raw(path, preview=True)
        if raw_image is None:
            raise ImageLoadError("Unable to read this image file")
        preview = self._resize_if_needed(raw_image, max_edge)
        return self._convert_to_working_space(
            path,
            preview,
            working_color_space,
            DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
            rendering_intent,
        )

    def read_preview_with_color_profile_info(
        self,
        path: Path,
        max_edge: int = 1920,
        working_color_space: WorkingColorSpace = DEFAULT_WORKING_COLOR_SPACE,
        assumed_source_color_space: WorkingColorSpace = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Read a faster preview and return source ICC status."""

        self._validate_path(path)
        max_edge = max(1, int(max_edge))
        reduced_flags = (
            cv2.IMREAD_REDUCED_COLOR_8,
            cv2.IMREAD_REDUCED_COLOR_4,
            cv2.IMREAD_REDUCED_COLOR_2,
        )

        for flag in reduced_flags:
            image = cv2.imread(str(path), flag)
            if image is not None:
                preview = self._resize_if_needed(image, max_edge)
                return self._convert_to_working_space_with_info(
                    path,
                    preview,
                    working_color_space,
                    assumed_source_color_space,
                    rendering_intent,
                )

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            preview = self._resize_if_needed(image, max_edge)
            return self._convert_to_working_space_with_info(
                path,
                preview,
                working_color_space,
                assumed_source_color_space,
                rendering_intent,
            )

        if not self._allow_raw:
            raise ImageLoadError("Unsupported image format")

        raw_image = self._read_raw(path, preview=True)
        if raw_image is None:
            raise ImageLoadError("Unable to read this image file")
        preview = self._resize_if_needed(raw_image, max_edge)
        return self._convert_to_working_space_with_info(
            path,
            preview,
            working_color_space,
            DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
            rendering_intent,
        )

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise ImageLoadError("Image file does not exist")

    def _resize_if_needed(self, bgr: np.ndarray, max_edge: int) -> np.ndarray:
        height, width = bgr.shape[:2]
        edge = max(height, width)
        if edge <= max_edge:
            return bgr
        scale = max_edge / float(edge)
        resized = (
            max(1, int(round(width * scale))),
            max(1, int(round(height * scale))),
        )
        return cv2.resize(bgr, resized, interpolation=cv2.INTER_AREA)

    def _convert_to_working_space(
        self,
        path: Path,
        bgr: np.ndarray,
        working_color_space: WorkingColorSpace,
        assumed_source_color_space: WorkingColorSpace,
        rendering_intent: RenderingIntent,
    ) -> np.ndarray:
        return self._color_converter.convert_file_bgr_to_working_space(
            path,
            bgr,
            working_color_space,
            assumed_source_color_space,
            rendering_intent,
        )

    def _convert_to_working_space_with_info(
        self,
        path: Path,
        bgr: np.ndarray,
        working_color_space: WorkingColorSpace,
        assumed_source_color_space: WorkingColorSpace,
        rendering_intent: RenderingIntent,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        return self._color_converter.convert_file_bgr_to_working_space_with_info(
            path,
            bgr,
            working_color_space,
            assumed_source_color_space,
            rendering_intent,
        )

    def _read_raw(self, path: Path, preview: bool) -> Optional[np.ndarray]:
        """Attempt to load RAW image using rawpy."""

        try:
            import rawpy  # type: ignore
        except Exception:
            logger.warning("RAW decoder is not installed, skipping RAW read")
            return None

        try:
            with rawpy.imread(str(path)) as raw:
                if preview:
                    rgb = raw.postprocess(
                        half_size=True,
                        output_bps=8,
                        output_color=rawpy.ColorSpace.sRGB,
                    )
                else:
                    rgb = raw.postprocess(output_color=rawpy.ColorSpace.sRGB)
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            logger.exception("Failed to read RAW image")
            return None
