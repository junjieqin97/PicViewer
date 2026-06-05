"""ICC profile conversion adapter backed by Pillow ImageCms."""

from __future__ import annotations

import io
import logging
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageCms, UnidentifiedImageError
from PySide6 import QtGui

from pic_viewer.common.errors import ColorProfileLoadError
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    ColorProfileSpec,
    LocalColorProfile,
    ColorSpacePreset,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent

logger = logging.getLogger(__name__)


class ColorProfileConverter:
    """Convert decoded image pixels from source ICC profiles into display profiles."""

    _QT_COLOR_SPACES: dict[ColorSpacePreset, QtGui.QColorSpace.NamedColorSpace] = {
        ColorSpacePreset.SRGB: QtGui.QColorSpace.NamedColorSpace.SRgb,
        ColorSpacePreset.DISPLAY_P3: QtGui.QColorSpace.NamedColorSpace.DisplayP3,
        ColorSpacePreset.ADOBE_RGB_1998: QtGui.QColorSpace.NamedColorSpace.AdobeRgb,
        ColorSpacePreset.PROPHOTO_RGB: QtGui.QColorSpace.NamedColorSpace.ProPhotoRgb,
    }
    _PILLOW_RENDERING_INTENTS: dict[RenderingIntent, ImageCms.Intent] = {
        RenderingIntent.PERCEPTUAL: ImageCms.Intent.PERCEPTUAL,
        RenderingIntent.RELATIVE_COLORIMETRIC: ImageCms.Intent.RELATIVE_COLORIMETRIC,
        RenderingIntent.SATURATION: ImageCms.Intent.SATURATION,
        RenderingIntent.ABSOLUTE_COLORIMETRIC: ImageCms.Intent.ABSOLUTE_COLORIMETRIC,
    }

    def __init__(self) -> None:
        self._profile_bytes_by_space: dict[ColorSpacePreset, bytes] = {}
        self._profiles_by_space: dict[ColorSpacePreset, ImageCms.ImageCmsProfile] = {}
        self._profiles_by_local_key: dict[str, ImageCms.ImageCmsProfile] = {}

    def profile_for(self, color_space: ColorProfileSpec) -> ImageCms.ImageCmsProfile:
        """Return a Pillow-open ICC profile for a supported color profile."""

        if isinstance(color_space, LocalColorProfile):
            cached_local = self._profiles_by_local_key.get(color_space.stable_key)
            if cached_local is not None:
                return cached_local
            local_profile = self._profile_from_bytes(color_space.profile_bytes)
            self._profiles_by_local_key[color_space.stable_key] = local_profile
            return local_profile

        cached = self._profiles_by_space.get(color_space)
        if cached is not None:
            return cached

        profile = self._profile_from_bytes(self.profile_bytes_for(color_space))
        self._profiles_by_space[color_space] = profile
        return profile

    def profile_bytes_for(self, color_space: ColorSpacePreset) -> bytes:
        """Return ICC profile bytes for a supported display color space."""

        cached = self._profile_bytes_by_space.get(color_space)
        if cached is not None:
            return cached

        qt_color_space = QtGui.QColorSpace(self._QT_COLOR_SPACES[color_space])
        if not qt_color_space.isValid():
            raise RuntimeError(f"Qt color space is invalid: {color_space.value}")
        profile_bytes = bytes(qt_color_space.iccProfile())
        if not profile_bytes:
            raise RuntimeError(f"Qt color space does not expose ICC bytes: {color_space.value}")
        self._profile_bytes_by_space[color_space] = profile_bytes
        return profile_bytes

    def qt_color_space_for(self, color_space: ColorProfileSpec) -> QtGui.QColorSpace:
        """Return a Qt color space for tagging display preview images.

        Args:
            color_space: Built-in preset or session-local ICC profile.

        Returns:
            QColorSpace: Valid Qt color space for QImage metadata.

        Raises:
            RuntimeError: If Qt cannot construct a color space from the ICC profile.
        """

        if isinstance(color_space, LocalColorProfile):
            qt_color_space = QtGui.QColorSpace.fromIccProfile(color_space.profile_bytes)
            label = color_space.stable_key
        else:
            qt_color_space = QtGui.QColorSpace(self._QT_COLOR_SPACES[color_space])
            label = color_space.value
        if not qt_color_space.isValid():
            raise RuntimeError(f"Qt color space is invalid: {label}")
        return qt_color_space

    def load_local_profile(self, path: Path) -> LocalColorProfile:
        """Load and validate a user-selected local ICC or ICM profile.

        Args:
            path: Path to the local ICC profile file.

        Returns:
            LocalColorProfile: Session-scoped local profile model.

        Raises:
            ColorProfileLoadError: If the path is not a readable ICC/ICM profile.
        """

        profile_path = Path(path).expanduser()
        if profile_path.suffix.lower() not in {".icc", ".icm"}:
            raise ColorProfileLoadError("ICC profile files must use .icc or .icm extension")
        if not profile_path.exists() or not profile_path.is_file():
            raise ColorProfileLoadError("ICC profile file does not exist")
        try:
            profile_bytes = profile_path.read_bytes()
        except OSError as exc:
            logger.exception("Unable to read local ICC profile: path=%s", profile_path)
            raise ColorProfileLoadError("Unable to read ICC profile file") from exc
        if not profile_bytes:
            raise ColorProfileLoadError("ICC profile file is empty")
        try:
            profile = self._profile_from_bytes(profile_bytes)
        except (ImageCms.PyCMSError, OSError, ValueError) as exc:
            logger.warning("Invalid local ICC profile: path=%s", profile_path)
            raise ColorProfileLoadError("Unable to load ICC profile") from exc
        return LocalColorProfile(
            display_name=self._local_profile_display_name(profile, profile_path),
            path=profile_path,
            profile_bytes=profile_bytes,
        )

    def convert_file_bgr_to_display_space(
        self,
        path: Path,
        bgr: np.ndarray,
        display_color_space: ColorProfileSpec,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> np.ndarray:
        """Convert decoded BGR pixels from embedded ICC profile to display space.

        Args:
            path: Source file path used only for ICC profile extraction.
            bgr: Decoded BGR image pixels.
            display_color_space: Target RGB display color space.
            assumed_source_color_space: Source color space to use when ICC is unavailable.
            rendering_intent: ICC rendering intent used for gamut mapping.

        Returns:
            A BGR uint8 array in the selected display color space. If profile
            extraction or conversion fails, the source is treated as sRGB.
        """

        converted_bgr, _profile_info = self.convert_file_bgr_to_display_space_with_info(
            path,
            bgr,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
        )
        return converted_bgr

    def convert_file_bgr_to_display_space_with_info(
        self,
        path: Path,
        bgr: np.ndarray,
        display_color_space: ColorProfileSpec,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Convert decoded BGR pixels and return source ICC status."""

        source_profile, source_info = self._source_profile_for_path(path, assumed_source_color_space)
        if self._is_empty_image(bgr):
            return bgr, source_info

        if source_info.uses_srgb_fallback and self._fallback_source_space(source_info) == display_color_space:
            return bgr.copy(), source_info

        target_profile = self.profile_for(display_color_space)
        rgb = self._bgr_to_rgb(bgr)
        converted_rgb = self._convert_rgb_with_profiles(
            rgb,
            source_profile,
            target_profile,
            source_path=path,
            target_label=self._profile_label(display_color_space),
            rendering_intent=rendering_intent,
        )
        if converted_rgb is None and not source_info.uses_srgb_fallback:
            source_info = self._fallback_profile_info(
                ImageColorProfileStatus.CONVERSION_FAILED,
                assumed_source_color_space,
            )
            if assumed_source_color_space == display_color_space:
                converted_rgb = rgb.copy()
            else:
                converted_rgb = self._convert_rgb_with_profiles(
                    rgb,
                    self.profile_for(assumed_source_color_space),
                    target_profile,
                    source_path=path,
                    target_label=self._profile_label(display_color_space),
                    rendering_intent=rendering_intent,
                )
        if converted_rgb is None:
            converted_rgb = rgb.copy()
        return self._rgb_to_bgr(converted_rgb), source_info

    def _source_profile_for_path(
        self,
        path: Path,
        assumed_source_color_space: ColorProfileSpec,
    ) -> tuple[ImageCms.ImageCmsProfile, ImageColorProfileInfo]:
        profile_bytes = self._read_embedded_icc_profile(path)
        if profile_bytes:
            try:
                profile = self._profile_from_bytes(profile_bytes)
                return profile, ImageColorProfileInfo(
                    display_name=self._profile_display_name(profile),
                    status=ImageColorProfileStatus.EMBEDDED,
                    uses_srgb_fallback=False,
                )
            except (ImageCms.PyCMSError, OSError, ValueError):
                logger.warning(
                    "Invalid embedded ICC profile, using assumed source color space: path=%s color_space=%s",
                    path,
                    self._profile_label(assumed_source_color_space),
                )
                return self.profile_for(assumed_source_color_space), self._fallback_profile_info(
                    ImageColorProfileStatus.INVALID,
                    assumed_source_color_space,
                )
        return self.profile_for(assumed_source_color_space), self._fallback_profile_info(
            ImageColorProfileStatus.MISSING,
            assumed_source_color_space,
        )

    def _fallback_profile_info(
        self,
        status: ImageColorProfileStatus,
        assumed_source_color_space: ColorProfileSpec,
    ) -> ImageColorProfileInfo:
        return ImageColorProfileInfo(
            display_name=self._profile_display_label(assumed_source_color_space),
            status=status,
            uses_srgb_fallback=True,
            assumed_color_space=assumed_source_color_space,
        )

    def _fallback_source_space(self, info: ImageColorProfileInfo) -> ColorProfileSpec:
        return info.assumed_color_space or ColorSpacePreset.SRGB

    def _profile_from_bytes(self, profile_bytes: bytes) -> ImageCms.ImageCmsProfile:
        return ImageCms.getOpenProfile(io.BytesIO(profile_bytes))

    def _profile_display_name(self, profile: ImageCms.ImageCmsProfile) -> str:
        for reader in (ImageCms.getProfileName, ImageCms.getProfileDescription):
            try:
                cleaned = self._clean_profile_name(reader(profile))
            except (ImageCms.PyCMSError, OSError, ValueError, TypeError):
                continue
            if cleaned:
                return cleaned
        return "Embedded ICC"

    def _local_profile_display_name(self, profile: ImageCms.ImageCmsProfile, path: Path) -> str:
        display_name = self._profile_display_name(profile)
        if display_name == "Embedded ICC":
            return path.name
        return display_name

    def _profile_display_label(self, color_space: ColorProfileSpec) -> str:
        return color_space.display_name

    def _profile_label(self, color_space: ColorProfileSpec) -> str:
        if isinstance(color_space, ColorSpacePreset):
            return color_space.value
        return color_space.stable_key

    def _clean_profile_name(self, profile_name: str | bytes | None) -> str:
        if profile_name is None:
            return ""
        if isinstance(profile_name, bytes):
            text = profile_name.decode("utf-8", errors="ignore")
        else:
            text = profile_name
        text = text.replace("\x00", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _read_embedded_icc_profile(self, path: Path) -> bytes | None:
        try:
            with Image.open(path) as image:
                profile = image.info.get("icc_profile")
        except (FileNotFoundError, OSError, UnidentifiedImageError, ValueError):
            logger.info("Unable to read embedded ICC profile, using sRGB: %s", path)
            return None

        if isinstance(profile, bytes) and profile:
            return profile
        return None

    def _convert_rgb_with_profiles(
        self,
        rgb: np.ndarray,
        source_profile: ImageCms.ImageCmsProfile,
        target_profile: ImageCms.ImageCmsProfile,
        source_path: Path | None,
        target_label: str,
        rendering_intent: RenderingIntent,
    ) -> np.ndarray | None:
        image = Image.fromarray(np.ascontiguousarray(rgb))
        try:
            converted = ImageCms.profileToProfile(
                image,
                source_profile,
                target_profile,
                renderingIntent=self._PILLOW_RENDERING_INTENTS[rendering_intent],
                outputMode="RGB",
            )
        except (ImageCms.PyCMSError, OSError, ValueError):
            logger.warning(
                "ICC conversion attempt failed: path=%s target=%s",
                source_path,
                target_label,
            )
            return None
        return np.asarray(converted.convert("RGB"), dtype=np.uint8).copy()

    def _bgr_to_rgb(self, bgr: np.ndarray) -> np.ndarray:
        return np.ascontiguousarray(bgr[:, :, ::-1])

    def _rgb_to_bgr(self, rgb: np.ndarray) -> np.ndarray:
        return np.ascontiguousarray(rgb[:, :, ::-1])

    def _is_empty_image(self, image: np.ndarray) -> bool:
        return getattr(image, "size", 0) == 0
