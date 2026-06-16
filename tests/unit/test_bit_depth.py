from __future__ import annotations

import sys
from pathlib import Path
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.domain.models.bit_depth import ChannelBitDepth  # noqa: E402


class ChannelBitDepthTests(unittest.TestCase):
    """Validate shared per-channel bit-depth metadata."""

    def test_eight_bit_metadata(self) -> None:
        self.assertEqual(255, ChannelBitDepth.EIGHT.max_value)
        self.assertEqual(np.uint8, ChannelBitDepth.EIGHT.dtype)
        self.assertEqual("8-bit/channel", ChannelBitDepth.EIGHT.display_name)

    def test_sixteen_bit_metadata(self) -> None:
        self.assertEqual(65535, ChannelBitDepth.SIXTEEN.max_value)
        self.assertEqual(np.uint16, ChannelBitDepth.SIXTEEN.dtype)
        self.assertEqual("16-bit/channel", ChannelBitDepth.SIXTEEN.display_name)

    def test_from_dtype_resolves_supported_numpy_dtypes(self) -> None:
        self.assertEqual(ChannelBitDepth.EIGHT, ChannelBitDepth.from_dtype(np.dtype(np.uint8)))
        self.assertEqual(ChannelBitDepth.SIXTEEN, ChannelBitDepth.from_dtype(np.dtype(np.uint16)))


if __name__ == "__main__":
    unittest.main()
