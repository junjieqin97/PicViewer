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
python scripts/packaging/install_release_dependencies.py
python scripts/packaging/verify_dependency_sources.py
```

The `packaging` optional dependency group remains in `pyproject.toml` for pip
users and package metadata, but release builds do not use it to resolve the
desktop packaging environment.

PicViewer uses `pyexiv2` as the runtime metadata backend, pyvips/libvips as
the runtime color management backend, and Pillow image plugins for AVIF/HEIF
decoding. These are installed with the base package. `pyexiv2` includes native
Exiv2 runtime files in its wheels, while pyvips requires a matching native
libvips runtime with LittleCMS support. Desktop release builds use a
conda-forge-first dependency policy: all dependencies available from
conda-forge are installed with conda, and PyPI is used only for the explicit
`pyexiv2` fallback because `pyexiv2` is not available on conda-forge for the
current macOS arm64 and Windows x64 release targets.

Some package names differ between PyPI metadata and conda-forge release
dependencies:

- `PySide6` -> `pyside6`
- `opencv-python` -> `opencv`
- `Pillow` -> `pillow`
- `build` -> `python-build`

For desktop release builds, do not let pip resolve PicViewer's runtime
dependencies. Install conda-forge dependencies and the PyPI-only fallback with
the release dependency script, then verify the resulting sources:

```bash
python scripts/packaging/install_release_dependencies.py
python scripts/packaging/verify_dependency_sources.py
python scripts/packaging/verify_pyvips_runtime.py --environment
```

This prevents pip from replacing conda-forge packages such as pyvips, OpenCV,
Pillow plugins, rawpy, and PyInstaller with PyPI wheels during release builds.
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

Generating translation source files uses the built-in Python extractor by default:

```bash
python scripts/i18n/update_ts.py
```

If a local PySide6 `lupdate` wrapper is available and should be used explicitly, pass it with `--lupdate /path/to/pyside6-lupdate`.

Generating translation resources requires Qt's `lrelease` command to be available in `PATH`. If the local `lrelease` command has a different name, use:

```bash
python scripts/i18n/build_qm.py --lrelease /path/to/lrelease
```

When neither `pyside6-lrelease` nor `lrelease` is in `PATH`, `build_qm.py` also searches common Qt tool directories under the active conda prefix, including `$CONDA_PREFIX/lib/qt6/bin`, `$CONDA_PREFIX/Library/bin`, and the PySide6 package directory. The legacy `~/.conda/envs/PicViewer/Lib/site-packages/PySide6` location is still checked last for older local setups.

Application icon resources are generated from `src/pic_viewer/ui/resources/icons/picviewer.svg` as the primary source:

```bash
python scripts/packaging/generate_icons.py
```

Icon PNG generation requires librsvg's `rsvg-convert` command:

```bash
conda install -c conda-forge librsvg
```

The script generates the runtime PNG size family with `rsvg-convert`, then generates Windows `.ico`
and macOS `.icns` from those PNGs. On macOS, it calls `iconutil` first and falls back to Pillow for
generating `.icns` if `iconutil` is unavailable. Pillow is already a runtime dependency because the
app keeps it as a fallback decoder and plugin host. The script does not fall back to QtSvg for PNG
generation because QtSvg does not support the `<clipPath>` element used by the PicViewer SVG master.

## Python Package Mode

Build command:

```bash
python scripts/packaging/build_python_package.py
```

The script performs the following steps:

- Verify that the current conda environment name is `PicViewer`.
- Generate `src/pic_viewer/ui/resources/i18n/*.qm`.
- Clean old `dist/`, `build/`, and `src/picviewer.egg-info/`.
- Run `python -m build --no-isolation`, with artifacts written to `dist/`.

The no-isolation build is intentional. The release dependency script installs
`setuptools`, `wheel`, and `python-build` from conda-forge first, so the build
step must not create a pip-resolved isolated build environment.

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

PyInstaller uses `onedir` mode. The Windows artifact is `dist/PicViewer/`, and the macOS artifact is `dist/PicViewer.app`. Windows uses `packaging/icons/picviewer.ico` as the application icon, and macOS uses `packaging/icons/picviewer.icns`. The app version installs `rawpy` through the `packaging` extra by default, providing RAW support for ordinary users. The spec packages the `rawpy` runtime core explicitly by keeping `rawpy`, `rawpy._rawpy`, and `rawpy._version`.
The spec also collects `pyexiv2` submodules, `pyexiv2` dynamic libraries,
pyvips submodules, pyvips/libvips dynamic libraries, Pillow HEIF/AVIF plugin
modules and dynamic libraries, and macOS Homebrew `inih` dynamic libraries so
Exiv2 metadata reading, ICC color conversion, and modern image decoding work in
packaged apps. Pillow ImageCms hidden imports are intentionally not collected.
`rawpy.enhance` and its optional `skimage`/`scipy` image-enhancement chain are
also intentionally excluded because PicViewer decodes RAW files through
`rawpy.imread(...).postprocess(...)` and does not use rawpy enhancement helpers.
The spec generates PicViewer's own package metadata for the About dialog from `pyproject.toml` and sets the macOS bundle version from the same source.

The PyInstaller spec prunes unused PySide6 runtime entries after dependency
analysis. It keeps QtCore, QtGui, QtWidgets, QtDBus, and QtSvg because the app
uses Qt widgets and SVG toolbar icons. It removes QtNetwork, Qt network
information plugins, TLS plugins, non-native platform plugins on macOS and
Windows, non-SVG image format plugins, and unused Qt translation files. Linux
platform plugins are not pruned so X11 and Wayland compatibility remains
controlled by the Qt runtime. On macOS, `build_app.py` post-processes the
generated app bundle by replacing top-level GLib runtime dylibs used by
pyvips/libvips with the active conda environment's `lib/` copies, then re-signs
the bundle. This prevents PyInstaller from leaving top-level `libglib`,
`libintl`, or `libpcre2` symlinks to OpenCV's private bundled copies, which can
be older than the libvips runtime and break ICC conversion. Other pruning only
applies to Qt runtime entries and the unused rawpy optional enhancement chain;
OpenCV, rawpy's core runtime, pyexiv2, pyvips/libvips, Pillow image plugins, and
PicViewer resources are left unchanged.

After building the PyInstaller app, verify that the bundle still contains
conda-forge pyvips metadata and native libvips/LittleCMS runtime files:

```bash
# Windows:
python scripts/packaging/verify_pyvips_runtime.py --bundle dist/PicViewer

# macOS:
python scripts/packaging/verify_pyvips_runtime.py --bundle dist/PicViewer.app
```

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
python scripts/packaging/install_release_dependencies.py
python scripts/packaging/verify_dependency_sources.py
python -m unittest discover -s tests/unit
python scripts/packaging/build_python_package.py
python -m zipfile -l dist/*.whl
python scripts/packaging/verify_pyvips_runtime.py --environment
python scripts/packaging/build_app.py
# Windows:
python scripts/packaging/verify_pyvips_runtime.py --bundle dist/PicViewer
python scripts/packaging/build_msi.py
cd dist
certutil -hashfile PicViewer-0.1.0.msi SHA256
cd ..
# macOS:
python scripts/packaging/verify_pyvips_runtime.py --bundle dist/PicViewer.app
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
