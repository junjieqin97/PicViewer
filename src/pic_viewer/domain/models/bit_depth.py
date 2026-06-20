"""Per-channel bit-depth metadata shared by image processing layers."""

from __future__ import annotations

from enum import Enum

import numpy as np


class ChannelBitDepth(Enum):
    """Supported integer precision per color channel."""

    EIGHT = 8
    SIXTEEN = 16

    @property
    def max_value(self) -> int:
        """Return the maximum representable channel value."""

        return (1 << self.value) - 1

    @property
    def dtype(self) -> type[np.uint8] | type[np.uint16]:
        """Return the NumPy dtype for this precision."""

        if self is ChannelBitDepth.SIXTEEN:
            return np.uint16
        return np.uint8

    @property
    def display_name(self) -> str:
        """Return user-facing precision text."""

        return f"{self.value}-bit/channel"

    @classmethod
    def from_dtype(cls, dtype: np.dtype | type[np.generic]) -> "ChannelBitDepth":
        """Resolve supported unsigned integer image dtype to bit depth."""

        resolved = np.dtype(dtype)
        if resolved == np.dtype(np.uint16):
            return cls.SIXTEEN
        return cls.EIGHT
