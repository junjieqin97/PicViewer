# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import shutil
import sys
import warnings

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib

from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
WINDOWS_ICON = PROJECT_ROOT / "packaging" / "icons" / "picviewer.ico"
MACOS_ICON = PROJECT_ROOT / "packaging" / "icons" / "picviewer.icns"
HOMEBREW_INIH_DYLIBS = (
    Path("/opt/homebrew/opt/inih/lib/libINIReader.0.dylib"),
    Path("/opt/homebrew/opt/inih/lib/libinih.0.dylib"),
)
RUNTIME_METADATA_PACKAGES = (
    "PySide6",
    "opencv-python",
    "numpy",
    "pyexiv2",
    "pyvips",
    "Pillow",
    "pillow-heif",
    "pillow-avif-plugin",
    "rawpy",
)
OPTIONAL_METADATA_PACKAGES = {"rawpy"}
RAWPY_RUNTIME_MODULES = (
    "rawpy",
    "rawpy._rawpy",
    "rawpy._version",
)
EXCLUDED_OPTIONAL_RAWPY_MODULES = (
    "rawpy.enhance",
    "skimage",
    "scipy",
)
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC_ROOT))

from scripts.packaging.pyinstaller_filters import filter_pyinstaller_analysis_toc


def _read_project_version(pyproject_path: Path) -> str:
    """Read the app version from pyproject.toml for packaged artifacts."""

    with pyproject_path.open("rb") as file_obj:
        pyproject = tomllib.load(file_obj)

    version = pyproject.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Cannot read project.version from {pyproject_path}.")
    return version


APP_VERSION = _read_project_version(PROJECT_ROOT / "pyproject.toml")


def _existing_dylib_binaries(paths, target_dir):
    return [(str(path), target_dir) for path in paths if path.exists()]


def _collect_runtime_metadata(package_names):
    metadata_datas = []
    for package_name in package_names:
        try:
            metadata_datas += copy_metadata(package_name)
        except Exception as exc:
            if package_name not in OPTIONAL_METADATA_PACKAGES:
                raise
            warnings.warn(f"Skipping optional package metadata for {package_name}: {exc}")
    return metadata_datas


def _build_picviewer_metadata_datas(version: str):
    """Build PicViewer metadata from pyproject.toml instead of installed state."""

    metadata_dir = PROJECT_ROOT / "build" / "pyinstaller-metadata"
    if metadata_dir.exists():
        shutil.rmtree(metadata_dir)
    dist_info_dir = metadata_dir / f"picviewer-{version}.dist-info"
    dist_info_dir.mkdir(parents=True)
    (dist_info_dir / "METADATA").write_text(
        "".join(
            (
                "Metadata-Version: 2.1\n",
                "Name: picviewer\n",
                f"Version: {version}\n",
            )
        ),
        encoding="utf-8",
    )
    return [(str(dist_info_dir / "METADATA"), dist_info_dir.name)]


datas = collect_data_files(
    "pic_viewer",
    includes=[
        "ui/resources/i18n/*.ts",
        "ui/resources/i18n/*.qm",
        "ui/resources/styles/*.qss",
        "ui/resources/icons/*.svg",
        "ui/resources/icons/*.png",
        "assets/licenses/*.txt",
    ],
)
datas += _collect_runtime_metadata(RUNTIME_METADATA_PACKAGES)
datas += _build_picviewer_metadata_datas(APP_VERSION)

binaries = []
hiddenimports = []
try:
    binaries += collect_dynamic_libs("pyexiv2")
    if sys.platform == "darwin":
        binaries += _existing_dylib_binaries(HOMEBREW_INIH_DYLIBS, "pyexiv2/lib")
    hiddenimports += collect_submodules("pyexiv2")
except Exception:
    hiddenimports.append("pyexiv2")

try:
    binaries += collect_dynamic_libs("pyvips")
    hiddenimports += collect_submodules("pyvips")
except Exception:
    hiddenimports.append("pyvips")

hiddenimports += list(RAWPY_RUNTIME_MODULES)

try:
    binaries += collect_dynamic_libs("pillow_heif")
    hiddenimports += collect_submodules("pillow_heif")
except Exception:
    hiddenimports.append("pillow_heif")

try:
    binaries += collect_dynamic_libs("pillow_avif")
    hiddenimports += collect_submodules("pillow_avif")
except Exception:
    hiddenimports.append("pillow_avif")

a = Analysis(
    [str(SRC_ROOT / "pic_viewer" / "main.py")],
    pathex=[str(SRC_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=list(EXCLUDED_OPTIONAL_RAWPY_MODULES),
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
a.binaries = filter_pyinstaller_analysis_toc(a.binaries, sys.platform)
a.datas = filter_pyinstaller_analysis_toc(a.datas, sys.platform)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PicViewer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(WINDOWS_ICON) if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PicViewer",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="PicViewer.app",
        icon=str(MACOS_ICON),
        bundle_identifier="com.picviewer.app",
        version=APP_VERSION,
        info_plist={"CFBundleVersion": APP_VERSION},
    )
