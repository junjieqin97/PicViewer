"""Image loading adapter for files and RAW formats."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from pic_viewer.common.errors import ImageLoadError

logger = logging.getLogger(__name__)


class ImageReader:
    """Read images from disk with optional RAW support."""

    def __init__(self, allow_raw: bool) -> None:
        self._allow_raw = allow_raw

    def read(self, path: Path) -> np.ndarray:
        """Read image file into BGR array.

        Args:
            path: File path to load.

        Returns:
            numpy.ndarray: BGR image array.

        Raises:
            ImageLoadError: If the file cannot be loaded.
        """

        self._validate_path(path)

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            return image

        if not self._allow_raw:
            raise ImageLoadError("不支持该图片格式")

        raw_image = self._read_raw(path, preview=False)
        if raw_image is None:
            raise ImageLoadError("无法读取该图片文件")
        return raw_image

    def read_preview(self, path: Path, max_edge: int = 1920) -> np.ndarray:
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
                return self._resize_if_needed(image, max_edge)

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            return self._resize_if_needed(image, max_edge)

        if not self._allow_raw:
            raise ImageLoadError("不支持该图片格式")

        raw_image = self._read_raw(path, preview=True)
        if raw_image is None:
            raise ImageLoadError("无法读取该图片文件")
        return self._resize_if_needed(raw_image, max_edge)

    def _validate_path(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            raise ImageLoadError("图片文件不存在")

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

    def _read_raw(self, path: Path, preview: bool) -> Optional[np.ndarray]:
        """Attempt to load RAW image using rawpy."""

        try:
            import rawpy  # type: ignore
        except Exception:
            logger.warning("RAW解码库未安装，跳过RAW读取")
            return None

        try:
            with rawpy.imread(str(path)) as raw:
                if preview:
                    rgb = raw.postprocess(half_size=True, output_bps=8)
                else:
                    rgb = raw.postprocess()
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            logger.exception("RAW图像读取失败")
            return None
