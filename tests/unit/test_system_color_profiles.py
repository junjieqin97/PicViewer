from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.infra.system import color_profiles as color_profile_module  # noqa: E402
from pic_viewer.infra.system.color_profiles import discover_system_color_profile_paths  # noqa: E402


class SystemColorProfileDiscoveryTests(unittest.TestCase):
    """Validate platform-specific system ICC profile discovery."""

    def test_macos_discovers_root_and_first_level_icc_profiles_only(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            root_profile = root / "Root.icc"
            root_profile.write_bytes(b"profile")
            root_icm = root / "Monitor.ICM"
            root_icm.write_bytes(b"profile")
            ignored_text = root / "Notes.txt"
            ignored_text.write_text("ignore", encoding="utf-8")
            first_level = root / "Displays"
            first_level.mkdir()
            child_profile = first_level / "Display.icc"
            child_profile.write_bytes(b"profile")
            second_level = first_level / "Nested"
            second_level.mkdir()
            nested_profile = second_level / "Nested.icc"
            nested_profile.write_bytes(b"profile")

            with patch.object(color_profile_module, "MACOS_COLOR_PROFILE_ROOT", root):
                result = discover_system_color_profile_paths("Darwin")

        self.assertEqual([child_profile, root_icm, root_profile], result)

    def test_windows_discovers_color_driver_profiles(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            profile = root / "Camera.icc"
            profile.write_bytes(b"profile")
            child = root / "Vendor"
            child.mkdir()
            child_profile = child / "Printer.icm"
            child_profile.write_bytes(b"profile")

            with patch.object(color_profile_module, "WINDOWS_COLOR_PROFILE_ROOT", root):
                result = discover_system_color_profile_paths("Windows")

        self.assertEqual([profile, child_profile], result)

    def test_other_platforms_do_not_auto_discover_profiles(self) -> None:
        self.assertEqual([], discover_system_color_profile_paths("Linux"))


if __name__ == "__main__":
    unittest.main()
