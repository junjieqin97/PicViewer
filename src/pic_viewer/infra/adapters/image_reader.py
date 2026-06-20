"""Image loading adapter for files and RAW formats."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from pic_viewer.app.services.image_file_policy import RAW_IMAGE_SUFFIXES
from pic_viewer.common.errors import ImageLoadError
from pic_viewer.domain.models.bit_depth import ChannelBitDepth
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    DEFAULT_DISPLAY_COLOR_SPACE,
    ColorProfileSpec,
    ColorSpacePreset,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent
from pic_viewer.infra.adapters.color_profile_converter import ColorProfileConverter
from pic_viewer.infra.adapters.pillow_image_plugins import register_optional_pillow_image_plugins

try:  # pragma: no cover - exercised in environments with pyvips installed
    import pyvips
except Exception:  # pragma: no cover - dependency availability is environment-specific
    pyvips = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)
RAW_SOURCE_COLOR_SPACE = ColorSpacePreset.PROPHOTO_RGB
RAW_SOURCE_COLOR_PROFILE = ImageColorProfileInfo(
    display_name=RAW_SOURCE_COLOR_SPACE.display_name,
    status=ImageColorProfileStatus.RAW_DECODED,
    uses_srgb_fallback=False,
    assumed_color_space=RAW_SOURCE_COLOR_SPACE,
)


@dataclass(frozen=True)
class ImageReadResult:
    """Decoded and color-managed image payload with precision metadata."""

    bgr: np.ndarray
    source_color_profile: ImageColorProfileInfo
    source_bit_depth: ChannelBitDepth
    cms_bit_depth: ChannelBitDepth
    is_raw: bool


class ImageReader:
    """Read images from disk with optional RAW support."""

    def __init__(self, allow_raw: bool, color_converter: ColorProfileConverter | None = None) -> None:
        self._allow_raw = allow_raw
        self._color_converter = color_converter or ColorProfileConverter()

    def read(
        self,
        path: Path,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> np.ndarray:
        """Read image file into BGR array in the selected display space."""

        return self.read_with_profile_and_depth(
            path,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
        ).bgr

    def read_with_color_profile_info(
        self,
        path: Path,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Read image file into BGR array and return source ICC status."""

        result = self.read_with_profile_and_depth(
            path,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
        )
        return result.bgr, result.source_color_profile

    def read_with_profile_and_depth(
        self,
        path: Path,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> ImageReadResult:
        """Read full image data and return color/profile/bit-depth metadata."""

        self._validate_path(path)
        is_raw = self._is_raw_path(path)
        if is_raw:
            if not self._allow_raw:
                raise ImageLoadError("Unsupported image format")
            raw_image = self._read_raw(path, preview=False)
            if raw_image is None:
                raise ImageLoadError("Unable to read this image file")
            return self._convert_to_read_result(
                path,
                raw_image,
                display_color_space,
                RAW_SOURCE_COLOR_SPACE,
                rendering_intent,
                is_raw=True,
                source_color_profile_override=RAW_SOURCE_COLOR_PROFILE,
            )

        image = self._read_pyvips_non_raw(path)
        if image is None:
            image = self._read_opencv_unchanged(path)
        if image is None:
            image = self._read_pillow(path)
        if image is None:
            raise ImageLoadError("Unsupported image format" if not self._allow_raw else "Unable to read this image file")

        return self._convert_to_read_result(
            path,
            image,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
            is_raw=False,
        )

    def read_preview(
        self,
        path: Path,
        max_edge: int = 1920,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> np.ndarray:
        """Read a faster low-cost preview for incremental UI updates."""

        return self.read_preview_with_profile_and_depth(
            path,
            max_edge,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
        ).bgr

    def read_preview_with_color_profile_info(
        self,
        path: Path,
        max_edge: int = 1920,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Read a faster preview and return source ICC status."""

        result = self.read_preview_with_profile_and_depth(
            path,
            max_edge,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
        )
        return result.bgr, result.source_color_profile

    def read_preview_with_profile_and_depth(
        self,
        path: Path,
        max_edge: int = 1920,
        display_color_space: ColorProfileSpec = DEFAULT_DISPLAY_COLOR_SPACE,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> ImageReadResult:
        """Read a faster preview with color/profile/bit-depth metadata."""

        self._validate_path(path)
        max_edge = max(1, int(max_edge))
        is_raw = self._is_raw_path(path)
        if is_raw:
            if not self._allow_raw:
                raise ImageLoadError("Unsupported image format")
            raw_image = self._read_raw(path, preview=True)
            if raw_image is None:
                raise ImageLoadError("Unable to read this image file")
            preview = self._resize_if_needed(raw_image, max_edge)
            return self._convert_to_read_result(
                path,
                preview,
                display_color_space,
                RAW_SOURCE_COLOR_SPACE,
                rendering_intent,
                is_raw=True,
                source_color_profile_override=RAW_SOURCE_COLOR_PROFILE,
            )

        image = self._read_reduced_opencv_preview(path, max_edge)
        if image is None:
            image = self._read_pyvips_non_raw(path)
            if image is not None:
                image = self._resize_if_needed(image, max_edge)
        if image is None:
            image = self._read_opencv_unchanged(path)
            if image is not None:
                image = self._resize_if_needed(image, max_edge)
        if image is None:
            image = self._read_pillow(path)
            if image is not None:
                image = self._resize_if_needed(image, max_edge)
        if image is None:
            raise ImageLoadError("Unsupported image format" if not self._allow_raw else "Unable to read this image file")

        return self._convert_to_read_result(
            path,
            image,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
            is_raw=False,
        )

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise ImageLoadError("Image file does not exist")

    def _is_raw_path(self, path: Path) -> bool:
        return path.suffix.lower() in RAW_IMAGE_SUFFIXES

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

    def _read_reduced_opencv_preview(self, path: Path, max_edge: int) -> np.ndarray | None:
        reduced_flags = (
            cv2.IMREAD_REDUCED_COLOR_8,
            cv2.IMREAD_REDUCED_COLOR_4,
            cv2.IMREAD_REDUCED_COLOR_2,
        )
        for flag in reduced_flags:
            image = cv2.imread(str(path), flag)
            if image is not None:
                return self._resize_if_needed(self._normalize_decoded_bgr(image), max_edge)
        return None

    def _read_pyvips_non_raw(self, path: Path) -> Optional[np.ndarray]:
        """Attempt to decode a non-RAW image through pyvips while preserving bit depth."""

        if pyvips is None:
            return None
        try:
            image = pyvips.Image.new_from_file(str(path), access="sequential")
            if hasattr(image, "autorot"):
                image = image.autorot()
            if image.bands < 3:
                return None
            if image.bands > 3:
                image = image.extract_band(0, n=3)
            if image.format not in {"uchar", "ushort"}:
                image = image.cast("ushort" if "ushort" in str(image.format) else "uchar")
            dtype = np.uint16 if image.format == "ushort" else np.uint8
            memory = image.write_to_memory()
            rgb = np.frombuffer(memory, dtype=dtype).reshape((image.height, image.width, image.bands))
            return np.ascontiguousarray(rgb[:, :, ::-1].copy())
        except Exception:
            logger.info("pyvips image decoder could not read file: %s", path, exc_info=True)
            return None

    def _read_opencv_unchanged(self, path: Path) -> Optional[np.ndarray]:
        image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if image is None:
            return None
        return self._normalize_decoded_bgr(image)

    def _normalize_decoded_bgr(self, image: np.ndarray) -> np.ndarray:
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif image.ndim == 3 and image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        elif image.ndim != 3 or image.shape[2] != 3:
            raise ImageLoadError("Unsupported image channel layout")

        if image.dtype == np.dtype(np.uint16):
            return np.ascontiguousarray(image)
        if image.dtype == np.dtype(np.uint8):
            return np.ascontiguousarray(image)
        return np.ascontiguousarray(np.clip(image, 0, 255).astype(np.uint8))

    def _read_pillow(self, path: Path) -> Optional[np.ndarray]:
        """Attempt to decode a non-RAW image through Pillow plugins."""

        register_optional_pillow_image_plugins()
        try:
            with Image.open(path) as image:
                transposed = ImageOps.exif_transpose(image)
                rgb = np.asarray(transposed.convert("RGB"), dtype=np.uint8).copy()
        except (FileNotFoundError, OSError, UnidentifiedImageError, ValueError):
            logger.info("Pillow image decoder could not read file: %s", path, exc_info=True)
            return None
        except Exception:
            logger.exception("Unexpected Pillow image decoder failure: %s", path)
            return None
        return np.ascontiguousarray(rgb[:, :, ::-1])

    def _convert_to_read_result(
        self,
        path: Path,
        bgr: np.ndarray,
        display_color_space: ColorProfileSpec,
        assumed_source_color_space: ColorProfileSpec,
        rendering_intent: RenderingIntent,
        is_raw: bool,
        source_color_profile_override: ImageColorProfileInfo | None = None,
    ) -> ImageReadResult:
        source_bit_depth = ChannelBitDepth.SIXTEEN if is_raw else ChannelBitDepth.from_dtype(bgr.dtype)
        bgr = np.ascontiguousarray(bgr.astype(source_bit_depth.dtype, copy=False))
        converted, source_color_profile, cms_bit_depth = self._convert_bgr_with_depth(
            path,
            bgr,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
            source_bit_depth,
            source_color_profile_override,
        )
        converted = np.ascontiguousarray(converted.astype(cms_bit_depth.dtype, copy=False))
        return ImageReadResult(
            bgr=converted,
            source_color_profile=source_color_profile,
            source_bit_depth=source_bit_depth,
            cms_bit_depth=cms_bit_depth,
            is_raw=is_raw,
        )

    def _convert_bgr_with_depth(
        self,
        path: Path,
        bgr: np.ndarray,
        display_color_space: ColorProfileSpec,
        assumed_source_color_space: ColorProfileSpec,
        rendering_intent: RenderingIntent,
        source_bit_depth: ChannelBitDepth,
        source_color_profile_override: ImageColorProfileInfo | None = None,
    ) -> tuple[np.ndarray, ImageColorProfileInfo, ChannelBitDepth]:
        new_method = getattr(self._color_converter, "convert_file_bgr_to_display_space_with_depth", None)
        if new_method is not None:
            kwargs = {"bit_depth": source_bit_depth}
            if source_color_profile_override is not None:
                kwargs["source_color_profile_override"] = source_color_profile_override
            converted = new_method(
                path,
                bgr,
                display_color_space,
                assumed_source_color_space,
                rendering_intent,
                **kwargs,
            )
            if isinstance(converted, tuple) and len(converted) == 3:
                return converted

        info_method = getattr(self._color_converter, "convert_file_bgr_to_display_space_with_info", None)
        if info_method is not None:
            converted_with_info = info_method(
                path,
                bgr,
                display_color_space,
                assumed_source_color_space,
                rendering_intent,
            )
            if isinstance(converted_with_info, tuple) and len(converted_with_info) == 2:
                converted_bgr, source_color_profile = converted_with_info
                return converted_bgr, source_color_profile, source_bit_depth

        legacy_method = getattr(self._color_converter, "convert_file_bgr_to_display_space")
        converted_bgr = legacy_method(
            path,
            bgr,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
        )
        fallback_info = ImageColorProfileInfo(
            display_name=assumed_source_color_space.display_name,
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
            assumed_color_space=assumed_source_color_space,
        )
        return converted_bgr, fallback_info, source_bit_depth

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
                        output_bps=16,
                        output_color=rawpy.ColorSpace.ProPhoto,
                    )
                else:
                    rgb = raw.postprocess(
                        output_bps=16,
                        output_color=rawpy.ColorSpace.ProPhoto,
                    )
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            logger.exception("Failed to read RAW image")
            return None
