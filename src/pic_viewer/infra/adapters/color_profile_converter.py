"""ICC profile conversion adapter backed by pyvips/libvips."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import re
import tempfile
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError
from PySide6 import QtGui

from pic_viewer.common.errors import ColorProfileLoadError
from pic_viewer.domain.models.bit_depth import ChannelBitDepth
from pic_viewer.domain.models.color_profile import ImageColorProfileInfo, ImageColorProfileStatus
from pic_viewer.domain.models.color_space import (
    DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
    ColorProfileSpec,
    LocalColorProfile,
    ColorSpacePreset,
)
from pic_viewer.domain.models.rendering_intent import DEFAULT_RENDERING_INTENT, RenderingIntent
from pic_viewer.infra.adapters.pillow_image_plugins import register_optional_pillow_image_plugins

try:  # pragma: no cover - exercised in environments with pyvips installed
    import pyvips
except Exception:  # pragma: no cover - dependency availability is environment-specific
    pyvips = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class ColorProfileConverter:
    """Convert decoded image pixels from source ICC profiles into display profiles."""

    _QT_COLOR_SPACES: dict[ColorSpacePreset, QtGui.QColorSpace.NamedColorSpace] = {
        ColorSpacePreset.SRGB: QtGui.QColorSpace.NamedColorSpace.SRgb,
        ColorSpacePreset.DISPLAY_P3: QtGui.QColorSpace.NamedColorSpace.DisplayP3,
        ColorSpacePreset.ADOBE_RGB_1998: QtGui.QColorSpace.NamedColorSpace.AdobeRgb,
        ColorSpacePreset.PROPHOTO_RGB: QtGui.QColorSpace.NamedColorSpace.ProPhotoRgb,
    }
    _PYVIPS_RENDERING_INTENTS: dict[RenderingIntent, str] = {
        RenderingIntent.PERCEPTUAL: "perceptual",
        RenderingIntent.RELATIVE_COLORIMETRIC: "relative",
        RenderingIntent.SATURATION: "saturation",
        RenderingIntent.ABSOLUTE_COLORIMETRIC: "absolute",
    }

    def __init__(self) -> None:
        self._profile_bytes_by_space: dict[ColorSpacePreset, bytes] = {}
        self._profile_path_by_key: dict[str, Path] = {}
        self._profile_temp_dir = tempfile.TemporaryDirectory(prefix="picviewer-icc-")

    def __del__(self) -> None:
        try:
            self._profile_temp_dir.cleanup()
        except Exception:
            pass

    def profile_for(self, color_space: ColorProfileSpec) -> Path:
        """Return an ICC profile file path for a supported color profile."""

        if isinstance(color_space, LocalColorProfile):
            key = color_space.stable_key
            profile_bytes = color_space.profile_bytes
        else:
            key = color_space.value
            profile_bytes = self.profile_bytes_for(color_space)

        cached = self._profile_path_by_key.get(key)
        if cached is not None and cached.exists():
            return cached

        digest = hashlib.sha256(profile_bytes).hexdigest()[:16]
        safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
        profile_path = Path(self._profile_temp_dir.name) / f"{safe_key}-{digest}.icc"
        profile_path.write_bytes(profile_bytes)
        self._profile_path_by_key[key] = profile_path
        return profile_path

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
        """Return a Qt color space for tagging display preview images."""

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
        """Load and validate a user-selected local ICC or ICM profile."""

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
            self._validate_profile_bytes(profile_bytes)
        except Exception as exc:
            logger.warning("Invalid local ICC profile: path=%s", profile_path)
            raise ColorProfileLoadError("Unable to load ICC profile") from exc
        return LocalColorProfile(
            display_name=profile_path.stem,
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
        bit_depth: ChannelBitDepth | None = None,
    ) -> np.ndarray:
        """Convert decoded BGR pixels from source ICC profile to display space."""

        converted_bgr, _profile_info, _cms_bit_depth = self.convert_file_bgr_to_display_space_with_depth(
            path,
            bgr,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
            bit_depth=bit_depth,
        )
        return converted_bgr

    def convert_file_bgr_to_display_space_with_info(
        self,
        path: Path,
        bgr: np.ndarray,
        display_color_space: ColorProfileSpec,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
        bit_depth: ChannelBitDepth | None = None,
    ) -> tuple[np.ndarray, ImageColorProfileInfo]:
        """Convert decoded BGR pixels and return source ICC status."""

        converted_bgr, source_info, _cms_bit_depth = self.convert_file_bgr_to_display_space_with_depth(
            path,
            bgr,
            display_color_space,
            assumed_source_color_space,
            rendering_intent,
            bit_depth=bit_depth,
        )
        return converted_bgr, source_info

    def convert_file_bgr_to_display_space_with_depth(
        self,
        path: Path,
        bgr: np.ndarray,
        display_color_space: ColorProfileSpec,
        assumed_source_color_space: ColorProfileSpec = DEFAULT_ASSUMED_IMAGE_COLOR_SPACE,
        rendering_intent: RenderingIntent = DEFAULT_RENDERING_INTENT,
        bit_depth: ChannelBitDepth | None = None,
        *,
        source_color_profile_override: ImageColorProfileInfo | None = None,
    ) -> tuple[np.ndarray, ImageColorProfileInfo, ChannelBitDepth]:
        """Convert BGR pixels and return source ICC status plus CMS bit depth."""

        cms_bit_depth = bit_depth or ChannelBitDepth.from_dtype(bgr.dtype)
        if source_color_profile_override is None:
            source_info, embedded_profile_bytes = self._source_profile_info_for_path(
                path,
                assumed_source_color_space,
            )
        else:
            source_info = source_color_profile_override
            embedded_profile_bytes = None
        if self._is_empty_image(bgr):
            return bgr, source_info, cms_bit_depth

        if source_info.uses_srgb_fallback and self._fallback_source_space(source_info) == display_color_space:
            return np.ascontiguousarray(bgr.copy()), source_info, cms_bit_depth
        if (
            source_color_profile_override is not None
            and source_info.assumed_color_space is not None
            and source_info.assumed_color_space == display_color_space
        ):
            return np.ascontiguousarray(bgr.copy()), source_info, cms_bit_depth

        target_profile = self.profile_for(display_color_space)
        rgb = self._bgr_to_rgb(bgr)
        source_profile = self._source_profile_for_conversion(
            source_info,
            assumed_source_color_space,
            source_color_profile_override is not None,
        )
        converted_rgb = self._convert_rgb(
            rgb,
            target_profile=target_profile,
            rendering_intent=rendering_intent,
            cms_bit_depth=cms_bit_depth,
            embedded_profile_bytes=embedded_profile_bytes if not source_info.uses_srgb_fallback else None,
            source_profile=source_profile,
            source_path=path,
            target_label=self._profile_label(display_color_space),
        )

        if converted_rgb is None and source_color_profile_override is not None:
            converted_rgb = rgb.copy()
        elif converted_rgb is None and not source_info.uses_srgb_fallback:
            source_info = self._fallback_profile_info(
                ImageColorProfileStatus.CONVERSION_FAILED,
                assumed_source_color_space,
            )
            if assumed_source_color_space == display_color_space:
                converted_rgb = rgb.copy()
            else:
                converted_rgb = self._convert_rgb(
                    rgb,
                    target_profile=target_profile,
                    rendering_intent=rendering_intent,
                    cms_bit_depth=cms_bit_depth,
                    source_profile=self.profile_for(assumed_source_color_space),
                    embedded_profile_bytes=None,
                    source_path=path,
                    target_label=self._profile_label(display_color_space),
                )
        if converted_rgb is None:
            converted_rgb = rgb.copy()
        return self._rgb_to_bgr(converted_rgb), source_info, cms_bit_depth

    def _source_profile_info_for_path(
        self,
        path: Path,
        assumed_source_color_space: ColorProfileSpec,
    ) -> tuple[ImageColorProfileInfo, bytes | None]:
        profile_bytes = self._read_embedded_icc_profile(path)
        if profile_bytes:
            try:
                self._validate_profile_bytes(profile_bytes)
                return ImageColorProfileInfo(
                    display_name=self._profile_display_name(profile_bytes),
                    status=ImageColorProfileStatus.EMBEDDED,
                    uses_srgb_fallback=False,
                ), profile_bytes
            except Exception:
                logger.warning(
                    "Invalid embedded ICC profile, using assumed source color space: path=%s color_space=%s",
                    path,
                    self._profile_label(assumed_source_color_space),
                )
                return self._fallback_profile_info(
                    ImageColorProfileStatus.INVALID,
                    assumed_source_color_space,
                ), None
        return self._fallback_profile_info(
            ImageColorProfileStatus.MISSING,
            assumed_source_color_space,
        ), None

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

    def _source_profile_for_conversion(
        self,
        info: ImageColorProfileInfo,
        assumed_source_color_space: ColorProfileSpec,
        has_profile_override: bool,
    ) -> Path | None:
        if has_profile_override:
            return self.profile_for(info.assumed_color_space or assumed_source_color_space)
        if info.uses_srgb_fallback:
            return self.profile_for(assumed_source_color_space)
        return None

    def _profile_display_label(self, color_space: ColorProfileSpec) -> str:
        return color_space.display_name

    def _profile_label(self, color_space: ColorProfileSpec) -> str:
        if isinstance(color_space, ColorSpacePreset):
            return color_space.value
        return color_space.stable_key

    def _read_embedded_icc_profile(self, path: Path) -> bytes | None:
        register_optional_pillow_image_plugins()
        try:
            with Image.open(path) as image:
                profile = image.info.get("icc_profile")
        except (FileNotFoundError, OSError, UnidentifiedImageError, ValueError):
            logger.info("Unable to read embedded ICC profile, using fallback source space: %s", path)
            return None

        if isinstance(profile, bytes) and profile:
            return profile
        return None

    def _validate_profile_bytes(self, profile_bytes: bytes) -> None:
        self._require_pyvips()
        profile_path = self._profile_path_for_bytes("validate", profile_bytes)
        srgb_profile = self.profile_for(ColorSpacePreset.SRGB)
        test_rgb = np.zeros((1, 1, 3), dtype=np.uint8)
        test_image = self._new_vips_image_from_rgb(test_rgb, ChannelBitDepth.EIGHT)
        test_image.icc_transform(
            str(srgb_profile),
            input_profile=str(profile_path),
            intent="perceptual",
            depth=8,
        )

    def _profile_path_for_bytes(self, key_prefix: str, profile_bytes: bytes) -> Path:
        digest = hashlib.sha256(profile_bytes).hexdigest()
        key = f"{key_prefix}:{digest}"
        cached = self._profile_path_by_key.get(key)
        if cached is not None and cached.exists():
            return cached
        profile_path = Path(self._profile_temp_dir.name) / f"{key_prefix}-{digest[:16]}.icc"
        profile_path.write_bytes(profile_bytes)
        self._profile_path_by_key[key] = profile_path
        return profile_path

    def _profile_display_name(self, profile_bytes: bytes) -> str:
        for tag in (b"desc", b"mluc"):
            text = self._read_icc_text_tag(profile_bytes, tag)
            if text:
                return text
        return "Embedded ICC"

    def _read_icc_text_tag(self, profile_bytes: bytes, tag_signature: bytes) -> str:
        if len(profile_bytes) < 132:
            return ""
        try:
            tag_count = int.from_bytes(profile_bytes[128:132], "big")
            for index in range(tag_count):
                record_start = 132 + index * 12
                record_end = record_start + 12
                if record_end > len(profile_bytes):
                    return ""
                signature = profile_bytes[record_start : record_start + 4]
                if signature != tag_signature:
                    continue
                offset = int.from_bytes(profile_bytes[record_start + 4 : record_start + 8], "big")
                size = int.from_bytes(profile_bytes[record_start + 8 : record_start + 12], "big")
                tag_data = profile_bytes[offset : offset + size]
                tag_type = tag_data[:4]
                if tag_type == b"desc":
                    return self._read_desc_tag(tag_data)
                if tag_type == b"mluc":
                    return self._read_mluc_tag(tag_data)
        except (IndexError, ValueError):
            return ""
        return ""

    def _read_desc_tag(self, tag_data: bytes) -> str:
        if len(tag_data) < 12 or tag_data[:4] != b"desc":
            return ""
        text_len = int.from_bytes(tag_data[8:12], "big")
        if text_len <= 0:
            return ""
        return self._clean_profile_name(tag_data[12 : 12 + max(0, text_len - 1)])

    def _read_mluc_tag(self, tag_data: bytes) -> str:
        if len(tag_data) < 28 or tag_data[:4] != b"mluc":
            return ""
        record_count = int.from_bytes(tag_data[8:12], "big")
        record_size = int.from_bytes(tag_data[12:16], "big")
        if record_count <= 0 or record_size < 12:
            return ""
        first_record = tag_data[16 : 16 + record_size]
        if len(first_record) < 12:
            return ""
        text_len = int.from_bytes(first_record[4:8], "big")
        text_offset = int.from_bytes(first_record[8:12], "big")
        text = tag_data[text_offset : text_offset + text_len]
        try:
            return self._clean_profile_name(text.decode("utf-16-be", errors="ignore"))
        except (AttributeError, UnicodeError):
            return ""

    def _clean_profile_name(self, profile_name: str | bytes | None) -> str:
        if profile_name is None:
            return ""
        if isinstance(profile_name, bytes):
            text = profile_name.decode("utf-8", errors="ignore")
        else:
            text = profile_name
        text = text.replace("\x00", " ")
        return re.sub(r"\s+", " ", text).strip()

    def _convert_rgb(
        self,
        rgb: np.ndarray,
        target_profile: Path,
        rendering_intent: RenderingIntent,
        cms_bit_depth: ChannelBitDepth,
        source_profile: Path | None,
        embedded_profile_bytes: bytes | None,
        source_path: Path | None,
        target_label: str,
    ) -> np.ndarray | None:
        vips_image = self._new_vips_image_from_rgb(rgb, cms_bit_depth)
        kwargs: dict[str, Any] = {
            "intent": self._PYVIPS_RENDERING_INTENTS[rendering_intent],
            "depth": cms_bit_depth.value,
        }
        if embedded_profile_bytes is not None:
            self._attach_embedded_profile(vips_image, embedded_profile_bytes)
            kwargs["embedded"] = True
        elif source_profile is not None:
            kwargs["input_profile"] = str(source_profile)
        else:
            kwargs["input_profile"] = str(self.profile_for(DEFAULT_ASSUMED_IMAGE_COLOR_SPACE))

        try:
            converted = vips_image.icc_transform(str(target_profile), **kwargs)
        except Exception:
            logger.warning(
                "ICC conversion attempt failed: path=%s target=%s",
                source_path,
                target_label,
                exc_info=True,
            )
            return None
        return self._rgb_from_vips_image(converted, rgb.shape, cms_bit_depth)

    def _new_vips_image_from_rgb(self, rgb: np.ndarray, bit_depth: ChannelBitDepth):
        self._require_pyvips()
        contiguous = np.ascontiguousarray(rgb.astype(bit_depth.dtype, copy=False))
        height, width, bands = contiguous.shape
        format_name = "ushort" if bit_depth is ChannelBitDepth.SIXTEEN else "uchar"
        return pyvips.Image.new_from_memory(contiguous.tobytes(), width, height, bands, format_name)

    def _attach_embedded_profile(self, image: Any, profile_bytes: bytes) -> None:
        if pyvips is None or not hasattr(image, "set_type"):
            return
        try:
            image.set_type(pyvips.GValue.blob_type, "icc-profile-data", profile_bytes)
        except Exception:
            logger.info("Unable to attach embedded ICC bytes to pyvips image", exc_info=True)

    def _rgb_from_vips_image(
        self,
        image: Any,
        shape: tuple[int, int, int],
        bit_depth: ChannelBitDepth,
    ) -> np.ndarray:
        height, width, bands = shape
        memory = image.write_to_memory()
        rgb = np.frombuffer(memory, dtype=bit_depth.dtype).reshape((height, width, bands))
        return np.ascontiguousarray(rgb.copy())

    def _bgr_to_rgb(self, bgr: np.ndarray) -> np.ndarray:
        return np.ascontiguousarray(bgr[:, :, ::-1])

    def _rgb_to_bgr(self, rgb: np.ndarray) -> np.ndarray:
        return np.ascontiguousarray(rgb[:, :, ::-1])

    def _is_empty_image(self, image: np.ndarray) -> bool:
        return getattr(image, "size", 0) == 0

    def _require_pyvips(self) -> None:
        if pyvips is None:
            raise RuntimeError("pyvips/libvips is required for ICC color conversion")
