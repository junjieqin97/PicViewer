from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def load_script(relative_path: str):
    script_path = PROJECT_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(script_path.stem, script_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackagingScriptsTests(unittest.TestCase):
    """Validate release scripts without running external packaging tools."""

    def test_build_qm_invokes_lrelease_for_each_translation_file(self) -> None:
        build_qm = load_script("scripts/i18n/build_qm.py")
        commands: list[list[str]] = []

        def fake_runner(command: list[str], **_: object) -> None:
            commands.append(command)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ts_dir = root / "i18n"
            out_dir = root / "out"
            ts_dir.mkdir()
            (ts_dir / "picviewer_en.ts").write_text("<TS/>", encoding="utf-8")
            (ts_dir / "picviewer_zh_CN.ts").write_text("<TS/>", encoding="utf-8")

            generated = build_qm.build_qm(
                ts_dir=ts_dir,
                out_dir=out_dir,
                lrelease="lrelease-test",
                runner=fake_runner,
            )

        self.assertEqual(
            [
                ["lrelease-test", str(ts_dir / "picviewer_en.ts"), "-qm", str(out_dir / "picviewer_en.qm")],
                ["lrelease-test", str(ts_dir / "picviewer_zh_CN.ts"), "-qm", str(out_dir / "picviewer_zh_CN.qm")],
            ],
            commands,
        )
        self.assertEqual(
            [out_dir / "picviewer_en.qm", out_dir / "picviewer_zh_CN.qm"],
            generated,
        )

    def test_build_qm_reports_missing_lrelease_clearly(self) -> None:
        build_qm = load_script("scripts/i18n/build_qm.py")

        with self.assertRaisesRegex(RuntimeError, "lrelease"):
            build_qm.find_lrelease(explicit=None, path_lookup=lambda _: None)

    def test_build_python_package_checks_conda_environment(self) -> None:
        build_package = load_script("scripts/packaging/build_python_package.py")

        with self.assertRaisesRegex(RuntimeError, "PicViewer"):
            build_package.ensure_conda_environment({"CONDA_DEFAULT_ENV": "base"})

        build_package.ensure_conda_environment({"CONDA_DEFAULT_ENV": "PicViewer"})

    def test_build_app_uses_pyinstaller_spec(self) -> None:
        build_app = load_script("scripts/packaging/build_app.py")
        commands: list[list[str]] = []

        def fake_runner(command: list[str], **_: object) -> None:
            commands.append(command)

        build_app.build_app(
            project_root=PROJECT_ROOT,
            env={"CONDA_DEFAULT_ENV": "PicViewer"},
            runner=fake_runner,
        )

        self.assertIn(
            [
                build_app.python_executable(),
                str(PROJECT_ROOT / "scripts" / "i18n" / "build_qm.py"),
            ],
            commands,
        )
        self.assertIn(
            [
                build_app.python_executable(),
                "-m",
                "PyInstaller",
                "--noconfirm",
                "--clean",
                str(PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec"),
            ],
            commands,
        )

    def test_build_app_uses_project_local_pyinstaller_cache(self) -> None:
        build_app = load_script("scripts/packaging/build_app.py")
        pyinstaller_envs: list[dict[str, str]] = []

        def fake_runner(command: list[str], **kwargs: object) -> None:
            if "-m" in command and "PyInstaller" in command:
                pyinstaller_envs.append(kwargs["env"])  # type: ignore[arg-type]

        build_app.build_app(
            project_root=PROJECT_ROOT,
            env={"CONDA_DEFAULT_ENV": "PicViewer"},
            runner=fake_runner,
        )

        self.assertEqual(
            str(PROJECT_ROOT / "build" / "pyinstaller-cache"),
            pyinstaller_envs[0]["PYINSTALLER_CONFIG_DIR"],
        )
