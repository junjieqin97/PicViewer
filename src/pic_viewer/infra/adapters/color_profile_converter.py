"""ICC profile conversion adapter backed by Pillow ImageCms."""

from __future__ import annotations

import io
import logging
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageCms, UnidentifiedImageError
from PySide6 import QtGui

from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus
from pic_viewer.domain.models.color_space import WorkingColorSpace

logger = logging.getLogger(__name__)


class ColorProfileConverter:
    """Convert decoded image pixels between embedded and working ICC profiles."""

    _QT_COLOR_SPACES: dict[WorkingColorSpace, QtGui.QColorSpace.NamedColorSpace] = {
        WorkingColorSpace.SRGB: QtGui.QColorSpace.NamedColorSpace.SRgb,
        WorkingColorSpace.DISPLAY_P3: QtGui.QColorSpace.NamedColorSpace.DisplayP3,
        WorkingColorSpace.ADOBE_RGB_1998: QtGui.QColorSpace.NamedColorSpace.AdobeRgb,
        WorkingColorSpace.PROPHOTO_RGB: QtGui.QColorSpace.NamedColorSpace.ProPhotoRgb,
    }

    def __init__(self) -> None:
        self._profile_bytes_by_space: dict[WorkingColorSpace, bytes] = {}
        self._profiles_by_space: dict[WorkingColorSpace, ImageCms.ImageCmsProfile] = {}

    def profile_for(self, color_space: WorkingColorSpace) -> ImageCms.ImageCmsProfile:
        """Return a Pillow-open ICC profile for a supported working color space."""

        cached = self._profiles_by_space.get(color_space)
        if cached is not None:
            return cached

        profile = self._profile_from_bytes(self.profile_bytes_for(color_space))
        self._profiles_by_space[color_space] = profile
        return profile

    def profile_bytes_for(self, color_space: WorkingColorSpace) -> bytes:
        """Return ICC profile bytes for a supported working color space."""

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

    def convert_file_bgr_to_working_space(
        self,
        path: Path,
        bgr: np.ndarray,
        working_color_space: WorkingColorSpace,
    ) -> np.ndarray:
        """Convert decoded BGR pixels from embedded ICC profile to working space.

        Args:
            path: Source file path used only for ICC profile extraction.
            bgr: Decoded BGR image pixels.
            working_color_space: Target RGB working color space.

        Returns:
            A BGR uint8 array in the selected working color space. If profile
            extraction or conversion fails, the source is treated as sRGB.
        """

        converted_bgr, _profile_info = self.convert_file_bgr_to_working_space_with_info(
            path,
            bgr,
            working_color_space,
        )
        return converted_bgr

    def convert_file_bgr_to_working_space_with_info(
        self,
        path: Path,
        bgr: np.ndarray,
        working_color_space: WorkingColorSpace,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Convert decoded BGR pixels and return source ICC status."""

        source_profile, source_info = self._source_profile_for_path(path)
        if self._is_empty_image(bgr):
            return bgr, source_info

        if source_info.uses_srgb_fallback and working_color_space == WorkingColorSpace.SRGB:
            return bgr.copy(), source_info

        target_profile = self.profile_for(working_color_space)
        rgb = self._bgr_to_rgb(bgr)
        converted_rgb = self._convert_rgb_with_profiles(
            rgb,
            source_profile,
            target_profile,
            source_path=path,
            target_label=working_color_space.value,
        )
        if converted_rgb is None and not source_info.uses_srgb_fallback:
            source_info = ImageColorProfileInfo(
                display_name="sRGB",
                status=ImageColorProfileStatus.CONVERSION_FAILED,
                uses_srgb_fallback=True,
            )
            converted_rgb = self._convert_rgb_with_profiles(
                rgb,
                self.profile_for(WorkingColorSpace.SRGB),
                target_profile,
                source_path=path,
                target_label=working_color_space.value,
            )
        if converted_rgb is None:
            converted_rgb = rgb.copy()
        return self._rgb_to_bgr(converted_rgb), source_info

    def convert_working_rgb_to_srgb(
        self,
        rgb: np.ndarray,
        working_color_space: WorkingColorSpace,
    ) -> np.ndarray:
        """Convert preview RGB pixels from the working color space to sRGB."""

        if self._is_empty_image(rgb) or working_color_space == WorkingColorSpace.SRGB:
            return rgb.copy()

        converted = self._convert_rgb_with_profiles(
            rgb,
            self.profile_for(working_color_space),
            self.profile_for(WorkingColorSpace.SRGB),
            source_path=None,
            target_label=WorkingColorSpace.SRGB.value,
        )
        if converted is None:
            return rgb.copy()
        return converted

    def _source_profile_for_path(self, path: Path) -> tuple[ImageCms.ImageCmsProfile, ImageColorProfileInfo]:
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
                logger.warning("Invalid embedded ICC profile, falling back to sRGB: %s", path)
                return self.profile_for(WorkingColorSpace.SRGB), ImageColorProfileInfo(
                    display_name="sRGB",
                    status=ImageColorProfileStatus.INVALID,
                    uses_srgb_fallback=True,
                )
        return self.profile_for(WorkingColorSpace.SRGB), ImageColorProfileInfo(
            display_name="sRGB",
            status=ImageColorProfileStatus.MISSING,
            uses_srgb_fallback=True,
        )

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
    ) -> np.ndarray | None:
        image = Image.fromarray(np.ascontiguousarray(rgb))
        try:
            converted = ImageCms.profileToProfile(
                image,
                source_profile,
                target_profile,
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
