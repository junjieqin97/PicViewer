from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer import main as main_module
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

    def test_main_loads_system_color_profiles_before_showing_window(self) -> None:
        events: list[str] = []

        class FakeApp:
            def setWindowIcon(self, _icon: object) -> None:
                pass

            def exec(self) -> int:
                return 0

        class FakeWindow:
            def setWindowIcon(self, _icon: object) -> None:
                pass

            def show(self) -> None:
                events.append("show")

        service = SimpleNamespace(
            warm_up_optional_backends=lambda: events.append("warm"),
            load_system_color_profiles=lambda: events.append("profiles") or ["profile"],
        )

        def build_window(*_args: object, **kwargs: object) -> FakeWindow:
            events.append(f"window:{len(kwargs.get('system_color_profiles', []))}")
            return FakeWindow()

        with (
            patch.object(main_module, "load_settings", return_value=SimpleNamespace(language_override=None)),
            patch.object(main_module, "configure_logging"),
            patch.object(main_module.QtWidgets, "QApplication", return_value=FakeApp()),
            patch.object(main_module, "load_app_icon", return_value=object()),
            patch.object(main_module, "resolve_language", return_value="en"),
            patch.object(main_module, "install_translator", return_value=("en", None)),
            patch.object(main_module, "build_services", return_value=service),
            patch.object(main_module, "AnalysisViewService", return_value=object()),
            patch.object(main_module, "MainWindow", side_effect=build_window),
        ):
            with self.assertRaises(SystemExit) as exit_context:
                main_module.main(["picviewer"])

        self.assertEqual(0, exit_context.exception.code)
        self.assertEqual(["warm", "profiles", "window:1", "show"], events)


if __name__ == "__main__":
    unittest.main()
