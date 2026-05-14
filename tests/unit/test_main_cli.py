from __future__ import annotations

import os
import subprocess
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

    def test_package_module_help_exits_before_qapplication_startup(self) -> None:
        env = os.environ.copy()
        existing_pythonpath = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(SRC_ROOT)
            if not existing_pythonpath
            else f"{SRC_ROOT}{os.pathsep}{existing_pythonpath}"
        )

        result = subprocess.run(
            [sys.executable, "-m", "pic_viewer", "--help"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--developer-mode", result.stdout)
        self.assertNotIn("QApplication", result.stderr)


if __name__ == "__main__":
    unittest.main()
