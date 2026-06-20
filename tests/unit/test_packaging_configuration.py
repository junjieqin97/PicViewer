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

    def test_runtime_image_backend_dependencies_are_declared(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        runtime_dependencies = pyproject.split("dependencies = [", maxsplit=1)[1].split(
            "]\n\n[project.optional-dependencies]",
            maxsplit=1,
        )[0]
        raw_extra = pyproject.split('raw = [', maxsplit=1)[1].split("]\n", maxsplit=1)[0]
        packaging_extra = pyproject.split("packaging = [", maxsplit=1)[1].split("]\n", maxsplit=1)[0]

        self.assertIn('"pyexiv2>=2.15.5,<3"', runtime_dependencies)
        self.assertIn('"pyvips>=3,<4"', runtime_dependencies)
        self.assertIn('"Pillow>=10.0"', runtime_dependencies)
        self.assertIn('"pillow-heif>=1,<2"', runtime_dependencies)
        self.assertIn('"pillow-avif-plugin>=1.5,<2"', runtime_dependencies)
        self.assertIn('"rawpy>=0.27.0"', raw_extra)
        self.assertIn('"rawpy>=0.27.0"', packaging_extra)
        self.assertIn('"pyvips>=3,<4"', packaging_extra)
        self.assertNotIn('"rawpy>=0.17"', pyproject)
        self.assertNotIn('"Pillow>=10.0"', packaging_extra)

    def test_manifest_includes_runtime_resources_and_release_files(self) -> None:
        manifest = (PROJECT_ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn("recursive-include src/pic_viewer/ui/resources/i18n *.ts *.qm", manifest)
        self.assertIn("recursive-include src/pic_viewer/ui/resources/styles *.qss", manifest)
        self.assertIn("recursive-include src/pic_viewer/ui/resources/icons *.svg *.png", manifest)
        self.assertIn("recursive-include packaging *.spec", manifest)
        self.assertIn("recursive-include packaging/icons *.ico *.icns", manifest)
        self.assertIn("recursive-include scripts *.py *.sh", manifest)

    def test_i18n_sources_include_display_color_space_label(self) -> None:
        i18n_dir = PROJECT_ROOT / "src" / "pic_viewer" / "ui" / "resources" / "i18n"
        en_ts = (i18n_dir / "picviewer_en.ts").read_text(encoding="utf-8")
        zh_ts = (i18n_dir / "picviewer_zh_CN.ts").read_text(encoding="utf-8")

        self.assertIn("<source>Display Color Space</source>", en_ts)
        self.assertIn("<source>Display Color Space</source>", zh_ts)
        self.assertIn("<translation>显示色彩空间</translation>", zh_ts)
        self.assertIn("<source>Image Color Space</source>", en_ts)
        self.assertIn("<source>Image Color Space</source>", zh_ts)
        self.assertIn("<translation>图片色彩空间</translation>", zh_ts)
        self.assertIn("<source>Specify Image Color Space</source>", en_ts)
        self.assertIn("<source>Specify Image Color Space</source>", zh_ts)
        self.assertIn("<translation>指定图片色彩空间</translation>", zh_ts)
        self.assertIn("<source>Rendering Intent</source>", en_ts)
        self.assertIn("<source>Rendering Intent</source>", zh_ts)
        self.assertIn("<translation>渲染意图</translation>", zh_ts)
        self.assertIn("<source>Analysis Sample Precision</source>", en_ts)
        self.assertIn("<source>Analysis Sample Precision</source>", zh_ts)
        self.assertIn("<translation>分析采样精度</translation>", zh_ts)
        self.assertIn("<source>8-bit/channel</source>", en_ts)
        self.assertIn("<source>16-bit/channel (if available)</source>", en_ts)
        self.assertIn("<source>Choose a local ICC...</source>", en_ts)
        self.assertIn("<source>Choose a local ICC...</source>", zh_ts)
        self.assertIn("<translation>选择本地 ICC...</translation>", zh_ts)
        self.assertIn("<source>Choose ICC Profile</source>", en_ts)
        self.assertIn("<source>ICC Profiles (*.icc *.icm)</source>", en_ts)
        self.assertIn("<source>Unable to Load ICC Profile</source>", en_ts)
        self.assertIn("<source>Unable to load ICC profile</source>", en_ts)
        for label in (
            "Perceptual",
            "Relative Colorimetric",
            "Saturation",
            "Absolute Colorimetric",
        ):
            self.assertIn(f"<source>{label}</source>", en_ts)
            self.assertIn(f"<source>{label}</source>", zh_ts)
        self.assertIn("<source>sRGB (default, no embedded ICC)</source>", en_ts)
        self.assertIn("<source>sRGB (fallback, ICC conversion failed)</source>", en_ts)
        self.assertIn("<source>{name} (specified, no embedded ICC)</source>", en_ts)
        self.assertIn("<source>{name} (specified fallback, ICC conversion failed)</source>", en_ts)

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
        metadata_packages = spec.split("RUNTIME_METADATA_PACKAGES = (", maxsplit=1)[1].split(")", maxsplit=1)[0]
        self.assertNotIn('"picviewer"', metadata_packages)
        for package_name in (
            "PySide6",
            "opencv-python",
            "numpy",
            "pyexiv2",
            "pyvips",
            "Pillow",
            "pillow-heif",
            "pillow-avif-plugin",
            "rawpy",
        ):
            self.assertIn(f'"{package_name}"', spec)
        self.assertNotIn('"PySide2"', spec)
        self.assertIn("_collect_runtime_metadata(RUNTIME_METADATA_PACKAGES)", spec)

    def test_pyinstaller_spec_collects_pyvips_runtime_and_excludes_pillow_imagecms(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn('collect_dynamic_libs("pyvips")', spec)
        self.assertIn('collect_submodules("pyvips")', spec)
        self.assertNotIn('"PIL.ImageCms"', spec)
        self.assertNotIn('"PIL._imagingcms"', spec)

    def test_pyinstaller_spec_collects_modern_pillow_image_plugins(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn('collect_dynamic_libs("pillow_heif")', spec)
        self.assertIn('collect_submodules("pillow_heif")', spec)
        self.assertIn('collect_dynamic_libs("pillow_avif")', spec)
        self.assertIn('collect_submodules("pillow_avif")', spec)

    def test_pyinstaller_spec_generates_picviewer_metadata_from_pyproject(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn("def _build_picviewer_metadata_datas(", spec)
        self.assertIn('metadata_dir = PROJECT_ROOT / "build" / "pyinstaller-metadata"', spec)
        self.assertIn('dist_info_dir = metadata_dir / f"picviewer-{version}.dist-info"', spec)
        self.assertIn('"Name: picviewer\\n"', spec)
        self.assertIn('"Version: {version}\\n"', spec)
        self.assertIn('return [(str(dist_info_dir / "METADATA"), dist_info_dir.name)]', spec)
        self.assertIn("datas += _build_picviewer_metadata_datas(APP_VERSION)", spec)

    def test_pyinstaller_spec_sets_macos_bundle_version_from_pyproject(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn('APP_VERSION = _read_project_version(PROJECT_ROOT / "pyproject.toml")', spec)
        self.assertIn("version=APP_VERSION", spec)
        self.assertIn('"CFBundleVersion": APP_VERSION', spec)

    def test_pyinstaller_spec_prunes_unused_qt_runtime_entries(self) -> None:
        spec = (PROJECT_ROOT / "packaging" / "pyinstaller" / "PicViewer.spec").read_text(encoding="utf-8")

        self.assertIn("filter_pyinstaller_analysis_toc", spec)
        self.assertIn("a.binaries = filter_pyinstaller_analysis_toc(a.binaries, sys.platform)", spec)
        self.assertIn("a.datas = filter_pyinstaller_analysis_toc(a.datas, sys.platform)", spec)

    def test_setup_py_delegates_metadata_to_pyproject(self) -> None:
        setup_py = (PROJECT_ROOT / "setup.py").read_text(encoding="utf-8")

        self.assertIn("setup()", setup_py)
        self.assertNotIn("install_requires=", setup_py)
        self.assertNotIn("extras_require=", setup_py)

    def test_desktop_release_workflow_publishes_dmg_and_msi_from_develop_merge(
        self,
    ) -> None:
        workflow_path = (
            PROJECT_ROOT
            / ".github"
            / "workflows"
            / "release-desktop.yml"
        )
        self.assertTrue(workflow_path.exists(), f"Missing workflow: {workflow_path}")
        workflow = workflow_path.read_text(encoding="utf-8")

        self.assertIn("pull_request:", workflow)
        self.assertIn("types:", workflow)
        self.assertIn("- closed", workflow)
        self.assertIn("- 'release-*'", workflow)
        self.assertIn("github.event.pull_request.merged == true", workflow)
        self.assertIn("github.event.pull_request.head.ref == 'develop'", workflow)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("release-metadata:", workflow)
        self.assertIn("build-macos:", workflow)
        self.assertIn("build-windows:", workflow)
        self.assertIn("publish-release:", workflow)
        self.assertIn("runs-on: macos-15", workflow)
        self.assertIn("runs-on: windows-2025", workflow)
        self.assertIn("shell: bash -el {0}", workflow)
        self.assertIn("shell: pwsh", workflow)
        self.assertIn("conda-incubator/setup-miniconda", workflow)
        self.assertIn("activate-environment: PicViewer", workflow)
        self.assertIn("python-version: \"3.10\"", workflow)
        self.assertIn("brew install inih", workflow)
        self.assertIn("QT_RUNTIME_VERSION: \"6.9.2\"", workflow)
        self.assertIn("RAWPY_VERSION: \"0.27.0\"", workflow)
        self.assertIn(
            'conda install -y -c conda-forge "pyside6=$QT_RUNTIME_VERSION" "qt6-main=$QT_RUNTIME_VERSION"',
            workflow,
        )
        self.assertIn(
            'conda install -y -c conda-forge "pyside6=$env:QT_RUNTIME_VERSION" "qt6-main=$env:QT_RUNTIME_VERSION"',
            workflow,
        )
        self.assertIn('python -m pip install -e ".[packaging]" "rawpy==$RAWPY_VERSION"', workflow)
        self.assertIn('python -m pip install -e ".[packaging]" "rawpy==$env:RAWPY_VERSION"', workflow)
        self.assertIn("$CONDA_PREFIX/lib/qt6/bin", workflow)
        self.assertIn("$env:CONDA_PREFIX", workflow)
        self.assertIn("Library\\bin", workflow)
        self.assertNotIn("conda install -y -c conda-forge pyside2", workflow)
        self.assertIn("actions/setup-dotnet@v4", workflow)
        self.assertIn("dotnet tool install --global wix", workflow)
        self.assertIn("python -m unittest discover -s tests/unit", workflow)
        self.assertIn("python scripts/packaging/build_app.py", workflow)
        self.assertIn("python scripts/packaging/build_dmg.py", workflow)
        self.assertIn("python scripts/packaging/build_msi.py --accept-wix-eula", workflow)
        self.assertIn("working-directory: dist", workflow)
        self.assertIn("shasum -a 256 -c *.dmg.sha256", workflow)
        self.assertIn("Get-FileHash", workflow)
        self.assertNotIn("shasum -a 256 -c dist/*.dmg.sha256", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertIn("actions/download-artifact@v4", workflow)
        self.assertIn("GH_REPO: ${{ github.repository }}", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("dist/PicViewer-$VERSION.dmg", workflow)
        self.assertIn("dist/PicViewer-$VERSION.dmg.sha256", workflow)
        self.assertIn("dist/PicViewer-$VERSION.msi", workflow)
        self.assertIn("dist/PicViewer-$VERSION.msi.sha256", workflow)
        self.assertIn("--target", workflow)
        self.assertIn("--generate-notes", workflow)
        self.assertNotIn("--clobber", workflow)

    def test_ci_documentation_describes_desktop_release_automation(self) -> None:
        ci_doc = (PROJECT_ROOT / "docs" / "ci.md").read_text(encoding="utf-8")
        packaging_doc = (PROJECT_ROOT / "docs" / "packaging.md").read_text(encoding="utf-8")

        self.assertIn("# Continuous Integration", ci_doc)
        self.assertIn("develop", ci_doc)
        self.assertIn("release-*", ci_doc)
        self.assertIn("macOS", ci_doc)
        self.assertIn("Apple Silicon", ci_doc)
        self.assertIn("arm64", ci_doc)
        self.assertIn("Qt/PySide6", ci_doc)
        self.assertIn("6.9.2", ci_doc)
        self.assertIn("rawpy", ci_doc)
        self.assertIn("0.27.0", ci_doc)
        self.assertIn("Windows", ci_doc)
        self.assertIn("MSI", ci_doc)
        self.assertIn("WiX", ci_doc)
        self.assertIn("--accept-wix-eula", ci_doc)
        self.assertIn("pyproject.toml", ci_doc)
        self.assertIn("v<version>", ci_doc)
        self.assertIn("PicViewer-<version>.dmg", ci_doc)
        self.assertIn("PicViewer-<version>.dmg.sha256", ci_doc)
        self.assertIn("PicViewer-<version>.msi", ci_doc)
        self.assertIn("PicViewer-<version>.msi.sha256", ci_doc)
        self.assertIn("does not overwrite", ci_doc)
        self.assertNotIn("GitHub Release automation", packaging_doc)
