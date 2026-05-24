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

    def test_pyproject_declares_gplv3_license(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")

        self.assertIn('license = "GPL-3.0-only"', pyproject)
        self.assertIn("GNU GENERAL PUBLIC LICENSE", license_text)
        self.assertIn("Version 3, 29 June 2007", license_text)

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

    def test_pyinstaller_spec_collects_runtime_dependency_metadata(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn("copy_metadata", spec)
        self.assertIn("RUNTIME_METADATA_PACKAGES", spec)
        for package_name in ("PySide2", "opencv-python", "numpy", "pyexiv2", "rawpy"):
            self.assertIn(f'"{package_name}"', spec)
        self.assertIn("_collect_runtime_metadata(RUNTIME_METADATA_PACKAGES)", spec)

    def test_setup_py_delegates_metadata_to_pyproject(self) -> None:
        setup_py = (PROJECT_ROOT / "setup.py").read_text(encoding="utf-8")

        self.assertIn("setup()", setup_py)
        self.assertNotIn("install_requires=", setup_py)
        self.assertNotIn("extras_require=", setup_py)

    def test_macos_release_workflow_publishes_dmg_from_develop_merge(self) -> None:
        workflow = (
            PROJECT_ROOT
            / ".github"
            / "workflows"
            / "release-macos.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertIn("types:", workflow)
        self.assertIn("- closed", workflow)
        self.assertIn("- 'release-*'", workflow)
        self.assertIn("github.event.pull_request.merged == true", workflow)
        self.assertIn("github.event.pull_request.head.ref == 'develop'", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("runs-on: macos-15", workflow)
        self.assertIn("shell: bash -el {0}", workflow)
        self.assertIn("conda-incubator/setup-miniconda", workflow)
        self.assertIn("activate-environment: PicViewer", workflow)
        self.assertIn("python-version: \"3.10\"", workflow)
        self.assertIn("brew install inih", workflow)
        self.assertIn("conda install -y -c conda-forge pyside2", workflow)
        self.assertIn("python -m unittest discover -s tests/unit", workflow)
        self.assertIn("python scripts/packaging/build_app.py", workflow)
        self.assertIn("python scripts/packaging/build_dmg.py", workflow)
        self.assertIn("working-directory: dist", workflow)
        self.assertIn("shasum -a 256 -c *.dmg.sha256", workflow)
        self.assertNotIn("shasum -a 256 -c dist/*.dmg.sha256", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("dist/PicViewer-$VERSION.dmg", workflow)
        self.assertIn("dist/PicViewer-$VERSION.dmg.sha256", workflow)
        self.assertIn("--target", workflow)
        self.assertIn("--generate-notes", workflow)
        self.assertNotIn("--clobber", workflow)

    def test_ci_documentation_describes_macos_release_automation(self) -> None:
        ci_doc = (PROJECT_ROOT / "docs" / "ci.md").read_text(encoding="utf-8")
        packaging_doc = (PROJECT_ROOT / "docs" / "packaging.md").read_text(encoding="utf-8")

        self.assertIn("# Continuous Integration", ci_doc)
        self.assertIn("develop", ci_doc)
        self.assertIn("release-*", ci_doc)
        self.assertIn("macOS", ci_doc)
        self.assertIn("Apple Silicon", ci_doc)
        self.assertIn("arm64", ci_doc)
        self.assertIn("pyproject.toml", ci_doc)
        self.assertIn("v<version>", ci_doc)
        self.assertIn("PicViewer-<version>.dmg", ci_doc)
        self.assertIn("PicViewer-<version>.dmg.sha256", ci_doc)
        self.assertIn("does not overwrite", ci_doc)
        self.assertNotIn("GitHub Release automation", packaging_doc)
