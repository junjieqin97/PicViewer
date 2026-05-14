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

    def test_manifest_includes_runtime_resources_and_release_files(self) -> None:
        manifest = (PROJECT_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("recursive-include src/pic_viewer/ui/resources/i18n *.ts *.qm", manifest)
        self.assertIn("recursive-include src/pic_viewer/ui/resources/styles *.qss", manifest)
        self.assertIn("recursive-include packaging *.spec", manifest)
        self.assertIn("recursive-include scripts *.py *.sh", manifest)

    def test_setup_py_delegates_metadata_to_pyproject(self) -> None:
        setup_py = (PROJECT_ROOT / "setup.py").read_text(encoding="utf-8")

        self.assertIn("setup()", setup_py)
        self.assertNotIn("install_requires=", setup_py)
        self.assertNotIn("extras_require=", setup_py)
