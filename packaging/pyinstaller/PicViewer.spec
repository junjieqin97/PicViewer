# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
WINDOWS_ICON = PROJECT_ROOT / "packaging" / "icons" / "picviewer.ico"
MACOS_ICON = PROJECT_ROOT / "packaging" / "icons" / "picviewer.icns"
sys.path.insert(0, str(SRC_ROOT))

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

binaries = []
hiddenimports = []
try:
    binaries += collect_dynamic_libs("pyexiv2")
    hiddenimports += collect_submodules("pyexiv2")
except Exception:
    hiddenimports.append("pyexiv2")

try:
    hiddenimports += collect_submodules("rawpy")
except Exception:
    hiddenimports.append("rawpy")

a = Analysis(
    [str(SRC_ROOT / "pic_viewer" / "main.py")],
    pathex=[str(SRC_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
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
    )
