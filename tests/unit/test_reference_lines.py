from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _reference_lines_module():
    spec = importlib.util.find_spec("pic_viewer.domain.rules.reference_lines")
    assert spec is not None, "reference_lines module should exist"
    return importlib.import_module("pic_viewer.domain.rules.reference_lines")


class ReferenceLineRuleTests(unittest.TestCase):
    """Validate GUI-free reference line geometry."""

    def test_cross_reference_lines_are_centered(self) -> None:
        module = _reference_lines_module()
        settings = module.ReferenceLineSettings(cross=True)

        lines = module.build_reference_line_segments(300, 150, settings)

        self.assertEqual(
            (
                module.ReferenceLineSegment((150.0, 0.0), (150.0, 150.0)),
                module.ReferenceLineSegment((0.0, 75.0), (300.0, 75.0)),
            ),
            lines,
        )

    def test_diagonal_reference_lines_connect_corners(self) -> None:
        module = _reference_lines_module()
        settings = module.ReferenceLineSettings(diagonal=True)

        lines = module.build_reference_line_segments(300, 150, settings)

        self.assertEqual(
            (
                module.ReferenceLineSegment((0.0, 0.0), (300.0, 150.0)),
                module.ReferenceLineSegment((300.0, 0.0), (0.0, 150.0)),
            ),
            lines,
        )

    def test_thirds_reference_lines_use_one_and_two_thirds(self) -> None:
        module = _reference_lines_module()
        settings = module.ReferenceLineSettings(thirds=True)

        lines = module.build_reference_line_segments(300, 150, settings)

        self.assertEqual(
            (
                module.ReferenceLineSegment((100.0, 0.0), (100.0, 150.0)),
                module.ReferenceLineSegment((200.0, 0.0), (200.0, 150.0)),
                module.ReferenceLineSegment((0.0, 50.0), (300.0, 50.0)),
                module.ReferenceLineSegment((0.0, 100.0), (300.0, 100.0)),
            ),
            lines,
        )

    def test_enabled_reference_line_types_are_additive(self) -> None:
        module = _reference_lines_module()
        settings = module.ReferenceLineSettings(cross=True, diagonal=True, thirds=True)

        lines = module.build_reference_line_segments(300, 150, settings)

        self.assertEqual(8, len(lines))


if __name__ == "__main__":
    unittest.main()
