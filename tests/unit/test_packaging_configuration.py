from __future__ import annotations

from pathlib import Path
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class PackagingConfigurationTests(unittest.TestCase):
    """Validate release metadata needed by pip and PyInstaller packaging."""

    def test_pyproject_defines_picviewer_console_script(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("[project.scripts]", pyproject)
        self.assertIn('picviewer = "pic_viewer.main:main"', pyproject)

    def test_pyproject_declares_packaging_extra(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("packaging = [", pyproject)
        self.assertIn('"build', pyproject)
        self.assertIn('"twine', pyproject)
        self.assertIn('"pyinstaller', pyproject)
        self.assertIn('"tomli>=2.0; python_version < \\"3.11\\""', pyproject)

    def test_metadata_backend_dependencies_are_declared_in_correct_groups(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        runtime_dependencies = pyproject.split("dependencies = [", maxsplit=1)[1].split(
            "]\n\n[project.optional-dependencies]",
            maxsplit=1,
        )[0]
        packaging_extra = pyproject.split("packaging = [", maxsplit=1)[1].split("]\n", maxsplit=1)[0]

        self.assertIn('"pyexiv2>=2.15.5,<3"', runtime_dependencies)
        self.assertNotIn('"Pillow>=10.0"', runtime_dependencies)
        self.assertIn('"Pillow>=10.0"', packaging_extra)

    def test_manifest_includes_runtime_resources_and_release_files(self) -> None:
        manifest = (PROJECT_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("recursive-include src/pic_viewer/ui/resources/i18n *.ts *.qm", manifest)
        self.assertIn("recursive-include src/pic_viewer/ui/resources/styles *.qss", manifest)
        self.assertIn("recursive-include src/pic_viewer/ui/resources/icons *.svg *.png", manifest)
        self.assertIn("recursive-include packaging *.spec", manifest)
        self.assertIn("recursive-include packaging/icons *.ico *.icns", manifest)
        self.assertIn("recursive-include scripts *.py *.sh", manifest)

    def test_pyproject_includes_icon_package_data(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn('"ui/resources/icons/*.svg"', pyproject)
        self.assertIn('"ui/resources/icons/*.png"', pyproject)

    def test_pyinstaller_spec_configures_platform_icons(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn('WINDOWS_ICON = PROJECT_ROOT / "packaging" / "icons" / "picviewer.ico"', spec)
        self.assertIn('MACOS_ICON = PROJECT_ROOT / "packaging" / "icons" / "picviewer.icns"', spec)
        self.assertIn('icon=str(WINDOWS_ICON) if sys.platform == "win32" else None', spec)
        self.assertIn("icon=str(MACOS_ICON)", spec)
        self.assertNotIn("icon=None", spec)

    def test_pyinstaller_spec_collects_pyexiv2_native_runtime(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn("collect_dynamic_libs", spec)
        self.assertIn('collect_submodules("pyexiv2")', spec)
        self.assertIn('collect_dynamic_libs("pyexiv2")', spec)

    def test_pyinstaller_spec_collects_pyexiv2_inih_runtime(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn("HOMEBREW_INIH_DYLIBS", spec)
        self.assertIn("libINIReader.0.dylib", spec)
        self.assertIn("libinih.0.dylib", spec)
        self.assertIn("_existing_dylib_binaries(HOMEBREW_INIH_DYLIBS", spec)
        self.assertIn('"pyexiv2/lib"', spec)

    def test_setup_py_delegates_metadata_to_pyproject(self) -> None:
        setup_py = (PROJECT_ROOT / "setup.py").read_text(encoding="utf-8")

        self.assertIn("setup()", setup_py)
        self.assertNotIn("install_requires=", setup_py)
        self.assertNotIn("extras_require=", setup_py)
