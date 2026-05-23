from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
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


def fake_applications_linker(link_path: Path) -> None:
    """Create a test marker instead of a platform-specific macOS symlink."""

    link_path.write_text("/Applications", encoding="utf-8")


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
            build_qm.find_lrelease(
                explicit=None,
                path_lookup=lambda _: None,
                pyside2_tools_dir=Path("missing"),
            )

    def test_find_lrelease_falls_back_to_pyside2_tools_dir(self) -> None:
        build_qm = load_script("scripts/i18n/build_qm.py")

        with tempfile.TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / "PySide2"
            tools_dir.mkdir()
            lrelease = tools_dir / "lrelease"
            lrelease.write_text("tool", encoding="utf-8")

            self.assertEqual(
                str(lrelease),
                build_qm.find_lrelease(
                    explicit=None,
                    path_lookup=lambda _: None,
                    pyside2_tools_dir=tools_dir,
                ),
            )

    def test_find_lrelease_falls_back_to_pyside2_lrelease_qt5(self) -> None:
        build_qm = load_script("scripts/i18n/build_qm.py")

        with tempfile.TemporaryDirectory() as tmp:
            tools_dir = Path(tmp) / "PySide2"
            tools_dir.mkdir()
            lrelease_qt5 = tools_dir / "lrelease-qt5"
            lrelease_qt5.write_text("tool", encoding="utf-8")

            self.assertEqual(
                str(lrelease_qt5),
                build_qm.find_lrelease(
                    explicit=None,
                    path_lookup=lambda _: None,
                    pyside2_tools_dir=tools_dir,
                ),
            )

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

    def test_build_dmg_creates_compressed_image_from_existing_app(self) -> None:
        build_dmg = load_script("scripts/packaging/build_dmg.py")
        commands: list[list[str]] = []

        def fake_runner(command: list[str], **_: object) -> None:
            commands.append(command)
            Path(command[-1]).write_bytes(b"dmg bytes")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist_dir = root / "dist"
            app_dir = dist_dir / "PicViewer.app"
            app_dir.mkdir(parents=True)
            (app_dir / "Contents").mkdir()
            (app_dir / "Contents" / "Info.plist").write_text("plist", encoding="utf-8")
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )

            dmg_path = build_dmg.build_dmg(
                project_root=root,
                env={"CONDA_DEFAULT_ENV": "PicViewer"},
                runner=fake_runner,
                platform="darwin",
                applications_linker=fake_applications_linker,
            )

            staging_dir = root / "build" / "dmg" / "staging"
            applications_link = staging_dir / "Applications"

            self.assertEqual(dist_dir / "PicViewer-1.2.3.dmg", dmg_path)
            self.assertTrue((staging_dir / "PicViewer.app" / "Contents" / "Info.plist").exists())
            self.assertEqual("/Applications", applications_link.read_text(encoding="utf-8"))
            self.assertEqual(
                [
                    "hdiutil",
                    "create",
                    "-volname",
                    "PicViewer",
                    "-srcfolder",
                    str(staging_dir),
                    "-ov",
                    "-format",
                    "UDZO",
                    str(dist_dir / "PicViewer-1.2.3.dmg"),
                ],
                commands[0],
            )

    def test_build_dmg_reads_version_from_pyproject(self) -> None:
        build_dmg = load_script("scripts/packaging/build_dmg.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "2.4.6"\n',
                encoding="utf-8",
            )

            self.assertEqual("2.4.6", build_dmg.read_project_version(root / "pyproject.toml"))

    def test_build_dmg_writes_sha256_checksum_next_to_dmg(self) -> None:
        build_dmg = load_script("scripts/packaging/build_dmg.py")
        dmg_bytes = b"deterministic dmg bytes"

        def fake_runner(command: list[str], **_: object) -> None:
            Path(command[-1]).write_bytes(dmg_bytes)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist_dir = root / "dist"
            app_dir = dist_dir / "PicViewer.app"
            app_dir.mkdir(parents=True)
            (app_dir / "Contents").mkdir()
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )

            dmg_path = build_dmg.build_dmg(
                project_root=root,
                env={"CONDA_DEFAULT_ENV": "PicViewer"},
                runner=fake_runner,
                platform="darwin",
                applications_linker=fake_applications_linker,
            )

            checksum_path = dist_dir / "PicViewer-1.2.3.dmg.sha256"
            expected_digest = hashlib.sha256(dmg_bytes).hexdigest()

            self.assertEqual(dist_dir / "PicViewer-1.2.3.dmg", dmg_path)
            self.assertTrue(checksum_path.exists())
            self.assertEqual(
                f"{expected_digest}  PicViewer-1.2.3.dmg\n",
                checksum_path.read_text(encoding="utf-8"),
            )

    def test_build_dmg_requires_existing_picviewer_app(self) -> None:
        build_dmg = load_script("scripts/packaging/build_dmg.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "build_app.py"):
                build_dmg.build_dmg(
                    project_root=root,
                    env={"CONDA_DEFAULT_ENV": "PicViewer"},
                    runner=lambda *_: None,
                    platform="darwin",
                )

    def test_build_dmg_requires_macos(self) -> None:
        build_dmg = load_script("scripts/packaging/build_dmg.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            (root / "dist" / "PicViewer.app").mkdir(parents=True)

            with self.assertRaisesRegex(RuntimeError, "macOS"):
                build_dmg.build_dmg(
                    project_root=root,
                    env={"CONDA_DEFAULT_ENV": "PicViewer"},
                    runner=lambda *_: None,
                    platform="linux",
                )

    def test_build_dmg_checks_conda_environment(self) -> None:
        build_dmg = load_script("scripts/packaging/build_dmg.py")

        with self.assertRaisesRegex(RuntimeError, "PicViewer"):
            build_dmg.ensure_conda_environment({"CONDA_DEFAULT_ENV": "base"})

        build_dmg.ensure_conda_environment({"CONDA_DEFAULT_ENV": "PicViewer"})

    def test_build_msi_creates_installer_from_existing_onedir_app(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")
        commands: list[list[str]] = []
        msi_bytes = b"deterministic msi bytes"

        def fake_runner(command: list[str], **_: object) -> None:
            commands.append(command)
            Path(command[command.index("-out") + 1]).write_bytes(msi_bytes)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist_dir = root / "dist"
            app_dir = dist_dir / "PicViewer"
            (app_dir / "_internal").mkdir(parents=True)
            (app_dir / "PicViewer.exe").write_bytes(b"exe")
            (app_dir / "_internal" / "runtime.dll").write_bytes(b"dll")
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )

            msi_path = build_msi.build_msi(
                project_root=root,
                env={"CONDA_DEFAULT_ENV": "PicViewer"},
                runner=fake_runner,
                platform="win32",
                wix_executable="wix-test",
                path_lookup=lambda _: "wix-test",
            )

            wxs_path = root / "build" / "msi" / "PicViewer.wxs"
            intermediate_dir = root / "build" / "msi" / "obj"
            wxs_text = wxs_path.read_text(encoding="utf-8")

            self.assertEqual(dist_dir / "PicViewer-1.2.3.msi", msi_path)
            self.assertIn('Scope="perMachine"', wxs_text)
            self.assertIn('Id="ProgramFiles64Folder"', wxs_text)
            self.assertIn('Id="ProgramMenuFolder"', wxs_text)
            self.assertIn('Id="DesktopFolder"', wxs_text)
            self.assertIn('Id="StartMenuShortcut"', wxs_text)
            self.assertIn('Id="DesktopShortcut"', wxs_text)
            self.assertIn(r"$(var.AppSourceDir)\PicViewer.exe", wxs_text)
            self.assertIn(r"$(var.AppSourceDir)\_internal\runtime.dll", wxs_text)
            self.assertEqual(
                [
                    "wix-test",
                    "build",
                    "-arch",
                    "x64",
                    "-define",
                    f"AppSourceDir={app_dir}",
                    "-define",
                    f"ProjectRoot={root}",
                    "-intermediateFolder",
                    str(intermediate_dir),
                    "-out",
                    str(dist_dir / "PicViewer-1.2.3.msi"),
                    str(wxs_path),
                ],
                commands[0],
            )

    def test_build_msi_can_pass_wix_eula_acceptance(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")
        commands: list[list[str]] = []
        msi_bytes = b"deterministic msi bytes"

        def fake_runner(command: list[str], **_: object) -> None:
            commands.append(command)
            Path(command[command.index("-out") + 1]).write_bytes(msi_bytes)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist_dir = root / "dist"
            app_dir = dist_dir / "PicViewer"
            app_dir.mkdir(parents=True)
            (app_dir / "PicViewer.exe").write_bytes(b"exe")
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )

            build_msi.build_msi(
                project_root=root,
                env={"CONDA_DEFAULT_ENV": "PicViewer"},
                runner=fake_runner,
                platform="win32",
                path_lookup=lambda _: "wix",
                accept_wix_eula=True,
            )

            self.assertEqual(["-acceptEula", "wix7"], commands[0][2:4])

    def test_build_msi_reports_wix_osmf_eula_failure(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        def fake_runner(command: list[str], **_: object) -> None:
            raise subprocess.CalledProcessError(
                returncode=1,
                cmd=command,
                stderr=(
                    "wix.exe : error WIX7015: You must accept the Open Source "
                    "Maintenance Fee (OSMF) EULA to use WiX Toolset v7."
                ),
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            app_dir = root / "dist" / "PicViewer"
            app_dir.mkdir(parents=True)
            (app_dir / "PicViewer.exe").write_bytes(b"exe")
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "--accept-wix-eula"):
                build_msi.build_msi(
                    project_root=root,
                    env={"CONDA_DEFAULT_ENV": "PicViewer"},
                    runner=fake_runner,
                    platform="win32",
                    path_lookup=lambda _: "wix",
                )

    def test_build_msi_reads_version_from_pyproject(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "2.4.6"\n',
                encoding="utf-8",
            )

            self.assertEqual("2.4.6", build_msi.read_project_version(root / "pyproject.toml"))

    def test_build_msi_rejects_non_msi_product_version(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        with self.assertRaisesRegex(RuntimeError, "MAJOR.MINOR.PATCH"):
            build_msi.validate_msi_version("1.2.3.4")

    def test_build_msi_writes_sha256_checksum_next_to_msi(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")
        msi_bytes = b"deterministic msi bytes"

        def fake_runner(command: list[str], **_: object) -> None:
            Path(command[command.index("-out") + 1]).write_bytes(msi_bytes)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dist_dir = root / "dist"
            app_dir = dist_dir / "PicViewer"
            app_dir.mkdir(parents=True)
            (app_dir / "PicViewer.exe").write_bytes(b"exe")
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.2.3"\n',
                encoding="utf-8",
            )

            msi_path = build_msi.build_msi(
                project_root=root,
                env={"CONDA_DEFAULT_ENV": "PicViewer"},
                runner=fake_runner,
                platform="win32",
                path_lookup=lambda _: "wix",
            )

            checksum_path = dist_dir / "PicViewer-1.2.3.msi.sha256"
            expected_digest = hashlib.sha256(msi_bytes).hexdigest()

            self.assertEqual(dist_dir / "PicViewer-1.2.3.msi", msi_path)
            self.assertTrue(checksum_path.exists())
            self.assertEqual(
                f"{expected_digest}  PicViewer-1.2.3.msi\n",
                checksum_path.read_text(encoding="utf-8"),
            )

    def test_build_msi_requires_existing_picviewer_app(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "build_app.py"):
                build_msi.build_msi(
                    project_root=root,
                    env={"CONDA_DEFAULT_ENV": "PicViewer"},
                    runner=lambda *_: None,
                    platform="win32",
                    path_lookup=lambda _: "wix",
                )

    def test_build_msi_requires_windows(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "picviewer"\nversion = "1.0.0"\n',
                encoding="utf-8",
            )
            app_dir = root / "dist" / "PicViewer"
            app_dir.mkdir(parents=True)
            (app_dir / "PicViewer.exe").write_bytes(b"exe")

            with self.assertRaisesRegex(RuntimeError, "Windows"):
                build_msi.build_msi(
                    project_root=root,
                    env={"CONDA_DEFAULT_ENV": "PicViewer"},
                    runner=lambda *_: None,
                    platform="linux",
                    path_lookup=lambda _: "wix",
                )

    def test_build_msi_checks_conda_environment(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        with self.assertRaisesRegex(RuntimeError, "PicViewer"):
            build_msi.ensure_conda_environment({"CONDA_DEFAULT_ENV": "base"})

        build_msi.ensure_conda_environment({"CONDA_DEFAULT_ENV": "PicViewer"})

    def test_build_msi_reports_missing_wix_cli(self) -> None:
        build_msi = load_script("scripts/packaging/build_msi.py")

        with self.assertRaisesRegex(RuntimeError, "WiX CLI"):
            build_msi.ensure_wix_executable("wix-missing", path_lookup=lambda _: None)
