from __future__ import annotations

import sys
from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.main import parse_command_line


class MainCliTests(unittest.TestCase):
    """Validate PicViewer startup argument parsing."""

    def test_developer_mode_is_parsed_and_removed_from_qt_arguments(self) -> None:
        developer_mode, qt_args = parse_command_line(["picviewer", "--developer-mode", "-style", "Fusion"])

        self.assertTrue(developer_mode)
        self.assertEqual(["picviewer", "-style", "Fusion"], qt_args)

    def test_unknown_arguments_are_preserved_for_qt(self) -> None:
        developer_mode, qt_args = parse_command_line(["picviewer", "-platform", "offscreen"])

        self.assertFalse(developer_mode)
        self.assertEqual(["picviewer", "-platform", "offscreen"], qt_args)


if __name__ == "__main__":
    unittest.main()
