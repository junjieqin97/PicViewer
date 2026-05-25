# PicViewer Packaging Plan

## Goals

PicViewer supports two release modes:

- Python package: generate `sdist` and `wheel`; after installation, advanced users can run `python -m pic_viewer` or `picviewer`.
- Desktop app and installer: use PyInstaller to build distributable apps natively on Windows/macOS, and generate MSI or DMG packages by platform; ordinary users do not need to understand the Python environment.

This phase does not include code signing, notarization, auto-updates, or PyPI upload automation.

## Prerequisites

All Python commands must be run after entering the project conda environment:

```bash
conda activate PicViewer
```

The `PicViewer` environment must use Python 3.10. The project GUI binding is PySide6. Python remains pinned to 3.10 for this release line to avoid changing the interpreter and GUI binding at the same time.

To rebuild the environment, use:

```bash
conda create -n PicViewer python=3.10
conda activate PicViewer
pip install -e ".[packaging]"
```

Packaging tools are installed through optional dependencies:

```bash
pip install ".[packaging]"
```

PicViewer uses `pyexiv2` as the runtime metadata backend. It is installed
with the base package and includes native Exiv2 runtime files in its wheels.
Packaging builds must keep those native files bundled with the application.
On macOS, if importing `pyexiv2` reports a missing `libINIReader.0.dylib`,
install the native dependency with `brew install inih` before building.

Windows MSI builds require WiX Toolset to be installed, and the `wix` command must be available in `PATH`. If the command is not in `PATH`, specify the path to `wix.exe` with `--wix` when running the script.

WiX Toolset v7 and later may report `WIX7015` before the first build, indicating that the OSMF EULA must be accepted. First read and confirm the requirements at <https://wixtoolset.org/osmf/>, then choose one of the following approaches:

```bash
wix eula accept wix7
```

Or explicitly pass the acceptance option in a one-off build command:

```bash
python scripts/packaging/build_msi.py --accept-wix-eula
```

`--accept-wix-eula` passes `-acceptEula wix7` to WiX and should only be used after the WiX OSMF EULA requirements have been confirmed.

Generating translation source files requires the PySide6 `pyside6-lupdate` command to be available in `PATH`. Generating translation resources requires Qt's `lrelease` command to be available in `PATH`. If the local `lrelease` command has a different name, use:

```bash
python scripts/i18n/build_qm.py --lrelease /path/to/lrelease
```

When neither `pyside6-lrelease` nor `lrelease` is in `PATH`, `build_qm.py` also searches common Qt tool directories under the active conda prefix, including `$CONDA_PREFIX/lib/qt6/bin`, `$CONDA_PREFIX/Library/bin`, and the PySide6 package directory. The legacy `~/.conda/envs/PicViewer/Lib/site-packages/PySide6` location is still checked last for older local setups.

Application icon resources are generated from `src/pic_viewer/ui/resources/icons/picviewer.svg` as the primary source:

```bash
python scripts/packaging/generate_icons.py
```

The script generates the runtime PNG size family, Windows `.ico`, and macOS `.icns`. On macOS, it calls `iconutil` first and falls back to Pillow for generating `.icns` if `iconutil` is unavailable.

## Python Package Mode

Build command:

```bash
python scripts/packaging/build_python_package.py
```

The script performs the following steps:

- Verify that the current conda environment name is `PicViewer`.
- Generate `src/pic_viewer/ui/resources/i18n/*.qm`.
- Clean old `dist/`, `build/`, and `src/picviewer.egg-info/`.
- Run `python -m build`, with artifacts written to `dist/`.

The release package includes QSS, TS, and QM resources. After installation, it supports:

```bash
python -m pic_viewer
picviewer
```

RAW support remains optional for pip users:

```bash
pip install "picviewer[raw]"
```

## PyInstaller App Mode

Build command:

```bash
python scripts/packaging/build_app.py
```

The script performs the following steps:

- Verify that the current conda environment name is `PicViewer`.
- Generate `.qm` translation resources.
- Invoke PyInstaller with `packaging/pyinstaller/PicViewer.spec`.
- Output native platform artifacts to `dist/`.

PyInstaller uses `onedir` mode. The Windows artifact is `dist/PicViewer/`, and the macOS artifact is `dist/PicViewer.app`. Windows uses `packaging/icons/picviewer.ico` as the application icon, and macOS uses `packaging/icons/picviewer.icns`. The app version installs and collects `rawpy` through the `packaging` extra by default, providing RAW support for ordinary users.
The spec also collects `pyexiv2` submodules, `pyexiv2` dynamic libraries, and macOS Homebrew `inih` dynamic libraries so Exiv2 metadata reading works in packaged apps.
The spec generates PicViewer's own package metadata for the About dialog from `pyproject.toml` and sets the macOS bundle version from the same source.

The PyInstaller spec prunes unused PySide6 runtime entries after dependency
analysis. It keeps QtCore, QtGui, QtWidgets, QtDBus, and QtSvg because the app
uses Qt widgets and SVG toolbar icons. It removes QtNetwork, Qt network
information plugins, TLS plugins, non-native platform plugins on macOS and
Windows, non-SVG image format plugins, and unused Qt translation files. Linux
platform plugins are not pruned so X11 and Wayland compatibility remains
controlled by the Qt runtime. The pruning only applies to Qt runtime entries;
OpenCV, rawpy, pyexiv2, and PicViewer resources are left unchanged.

After building, inspect the packaged Qt runtime with platform-specific file
listing tools. On macOS, for example:

```bash
find dist/PicViewer.app/Contents/Frameworks -name 'libQt6*.dylib' -print
find dist/PicViewer.app/Contents/Frameworks/PySide6/Qt/plugins -type f -print
find dist/PicViewer.app/Contents/Resources/PySide6/Qt/translations -type f -print
```

Cross-building is not supported: the Windows app must be built on Windows, and the macOS app must be built on macOS.

## Windows MSI Mode

Build command:

```bash
python scripts/packaging/build_msi.py
```

The script performs the following steps:

- Verify that the current conda environment name is `PicViewer`.
- Verify that the current platform is Windows.
- Verify that the WiX CLI is available.
- Read the version number from `pyproject.toml`; the version must follow Windows Installer's numeric `MAJOR.MINOR.PATCH` format.
- Verify that `dist/PicViewer/PicViewer.exe` already exists; if it does not, run `python scripts/packaging/build_app.py` first.
- Generate a temporary WiX source file, `build/msi/PicViewer.wxs`, from the actual file tree under `dist/PicViewer/`.
- Use WiX to build an x64, per-machine MSI, with the installation directory set to `C:\Program Files\PicViewer`.
- Create `PicViewer` shortcuts in the Start menu and on the desktop.
- Generate a SHA256 checksum file next to the MSI, with the file name `*.msi.sha256`.

The MSI artifact is written to `dist/PicViewer-version.msi`, for example `dist/PicViewer-0.1.0.msi`.
The SHA256 checksum file is written to `dist/PicViewer-version.msi.sha256`, with content in the format `SHA256  MSI file name`.

If the WiX command is not named `wix`, use:

```bash
python scripts/packaging/build_msi.py --wix C:\Path\To\wix.exe
```

If using WiX v7 and no user-level or machine-level EULA acceptance has been saved yet, you can also use:

```bash
python scripts/packaging/build_msi.py --accept-wix-eula
```

## macOS DMG Mode

Build command:

```bash
python scripts/packaging/build_dmg.py
```

The script performs the following steps:

- Verify that the current conda environment name is `PicViewer`.
- Verify that the current platform is macOS.
- Read the version number from `pyproject.toml`.
- Verify that `dist/PicViewer.app` already exists; if it does not, run `python scripts/packaging/build_app.py` first.
- Copy `dist/PicViewer.app` to a temporary staging directory.
- Create an `Applications -> /Applications` shortcut in the staging directory so users can install by dragging.
- Use macOS built-in `hdiutil` to generate a compressed DMG.
- Generate a SHA256 checksum file next to the DMG, with the file name `*.dmg.sha256`.

The DMG artifact is written to `dist/PicViewer-version.dmg`, for example `dist/PicViewer-0.1.0.dmg`.
The SHA256 checksum file is written to `dist/PicViewer-version.dmg.sha256`, with content in the format `SHA256  DMG file name`.

## Release Checklist

```bash
conda activate PicViewer
python --version  # Should output Python 3.10.x
python -m unittest discover -s tests/unit
python scripts/packaging/build_python_package.py
python -m zipfile -l dist/*.whl
python scripts/packaging/build_app.py
# Windows:
python scripts/packaging/build_msi.py
cd dist
certutil -hashfile PicViewer-0.1.0.msi SHA256
cd ..
# macOS:
python scripts/packaging/build_dmg.py
cd dist
shasum -a 256 -c *.dmg.sha256
cd ..
```

When checking wheel contents, the following files should be visible:

- `pic_viewer/ui/resources/styles/main.qss`
- `pic_viewer/ui/resources/icons/picviewer.svg`
- `pic_viewer/ui/resources/icons/picviewer-256.png`
- `pic_viewer/ui/resources/i18n/picviewer_zh_CN.qm`
- `pic_viewer/ui/resources/i18n/picviewer_en.qm`

App verification should cover at least:

- Starting with the default language.
- Starting with `PICVIEWER_LANG=zh_CN`.
- Explicitly verifying the English source fallback with `PICVIEWER_LANG=en` when needed.
- Opening ordinary JPG/PNG images.
- Opening RAW images.
- Confirming that Exif/IPTC metadata appears in the Metadata tab for images that contain it.
- Confirming that `--developer-mode` can write development logs.
