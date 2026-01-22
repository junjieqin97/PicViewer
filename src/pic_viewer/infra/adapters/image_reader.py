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

        if not path.exists() or not path.is_file():
            raise ImageLoadError("图片文件不存在")

        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is not None:
            return image

        if not self._allow_raw:
            raise ImageLoadError("不支持该图片格式")

        raw_image = self._read_raw(path)
        if raw_image is None:
            raise ImageLoadError("无法读取该图片文件")
        return raw_image

    def _read_raw(self, path: Path) -> Optional[np.ndarray]:
        """Attempt to load RAW image using rawpy."""

        try:
            import rawpy  # type: ignore
        except Exception:
            logger.warning("RAW解码库未安装，跳过RAW读取")
            return None

        try:
            with rawpy.imread(str(path)) as raw:
                rgb = raw.postprocess()
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        except Exception:
            logger.exception("RAW图像读取失败")
            return None
