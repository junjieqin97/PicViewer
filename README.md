# PicViewer

![](./src/pic_viewer/ui/resources/icons/picviewer-64.png)

> A desktop photo viewer for common image formats, modern formats such as AVIF/WebP/HEIF/HEIC, and camera RAW files.

## Installation and Startup

On Windows, you can install it via the winget:

```bash
winget install PicViewer
```

Run from development source:

```bash
conda activate PicViewer
python -m pic_viewer.main
```

Run after installing as a Python package:

```bash
pip install picviewer
python -m pic_viewer
picviewer
```

Professional users who need RAW support can install:

```bash
pip install "picviewer[raw]"
```

## Packaging

Activate the project environment before release:

```bash
conda activate PicViewer
python scripts/packaging/install_release_dependencies.py
python scripts/packaging/verify_dependency_sources.py
```

Build the Python source distribution and wheel:

```bash
python scripts/packaging/build_python_package.py
```

Build native PyInstaller apps for Windows/macOS:

```bash
python scripts/packaging/build_app.py
```

For detailed rules, see [docs/packaging.md](docs/packaging.md).

## Notes

- High-DPI support is enabled: the image display area and analysis charts in the info panel render according to DPR.

## Internationalization (Simplified Chinese/English)

- Language priority: `PICVIEWER_LANG` > system language > `zh_CN`.
- Supported values:
  - Chinese: `zh` / `zh_CN` / `zh-CN`
  - English: `en` / `en_US` / `en-GB`
- Runtime switching is not supported; the language is determined when the application starts.

### Environment Variable Examples

```bash
PICVIEWER_LANG=en python -m pic_viewer.main
PICVIEWER_LANG=en python -m pic_viewer
```

### Fallback Rules

- If English is selected but `picviewer_en.qm` cannot be found at runtime, the application automatically falls back to Chinese and continues startup.
- By default, the source repository commits only `.ts` files; `.qm` files are generated during CI/packaging.

### Translation File Maintenance

```bash
# Update ts files from Python source code
python scripts/i18n/update_ts.py

# Generate qm files from ts files (defaults to output under src/pic_viewer/ui/resources/i18n)
python scripts/i18n/build_qm.py
```

For more conventions, see [docs/i18n.md](docs/i18n.md).

## Logging

- Default mode: logs are output to the console.
- Developer mode: logs are output to `~/.PicViewer/logs/picviewer.log`; each file is capped at 5 MB, with 5 rotating backups retained.
- The log level is still controlled by `PICVIEWER_LOG_LEVEL`; the default value is `INFO`.

### Developer Mode Examples

```bash
python -m pic_viewer.main --developer-mode
python -m pic_viewer --developer-mode
PICVIEWER_LOG_LEVEL=DEBUG python -m pic_viewer.main --developer-mode
```
