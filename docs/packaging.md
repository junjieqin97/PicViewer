# PicViewer 打包方案

## 目标

PicViewer 支持两种发布模式：

- Python 包：生成 `sdist` 和 `wheel`，专业用户安装后可执行 `python -m pic_viewer` 或 `picviewer`。
- 桌面 App：使用 PyInstaller 在 Windows/macOS 本机构建可分发 App，普通用户无需了解 Python 环境。

本阶段不包含代码签名、公证、DMG/MSI 安装器、自动更新或 PyPI 上传自动化。

## 前置条件

所有 Python 命令必须先进入项目 conda 环境：

```bash
conda activate PicViewer
```

打包工具通过可选依赖安装：

```bash
pip install ".[packaging]"
```

生成翻译资源需要 Qt 的 `lrelease` 命令位于 `PATH`。若本机命令名不同，可直接使用：

```bash
python scripts/i18n/build_qm.py --lrelease /path/to/lrelease
```

## Python 包模式

构建命令：

```bash
python scripts/packaging/build_python_package.py
```

脚本会执行以下步骤：

- 校验当前 conda 环境名为 `PicViewer`。
- 生成 `src/pic_viewer/ui/resources/i18n/*.qm`。
- 清理旧的 `dist/`、`build/`、`src/picviewer.egg-info/`。
- 执行 `python -m build`，产物输出到 `dist/`。

发布包包含 QSS、TS、QM 资源。安装后支持：

```bash
python -m pic_viewer
picviewer
```

RAW 支持对 pip 用户保持可选：

```bash
pip install "picviewer[raw]"
```

## PyInstaller App 模式

构建命令：

```bash
python scripts/packaging/build_app.py
```

脚本会执行以下步骤：

- 校验当前 conda 环境名为 `PicViewer`。
- 生成 `.qm` 翻译资源。
- 使用 `packaging/pyinstaller/PicViewer.spec` 调用 PyInstaller。
- 在 `dist/` 输出平台本机产物。

PyInstaller 使用 `onedir` 模式。Windows 产物为 `dist/PicViewer/`，macOS 产物为 `dist/PicViewer.app`。App 版本默认通过 `packaging` extra 安装并收集 `rawpy`，面向普通用户提供 RAW 支持。

不支持交叉构建：Windows App 必须在 Windows 构建，macOS App 必须在 macOS 构建。

## 发布检查清单

```bash
conda activate PicViewer
python -m unittest discover -s tests/unit
python scripts/packaging/build_python_package.py
python -m zipfile -l dist/*.whl
python scripts/packaging/build_app.py
```

检查 wheel 内容时，应能看到：

- `pic_viewer/ui/resources/styles/main.qss`
- `pic_viewer/ui/resources/i18n/picviewer_zh_CN.qm`
- `pic_viewer/ui/resources/i18n/picviewer_en.qm`

App 验证至少覆盖：

- 默认语言启动。
- `PICVIEWER_LANG=en` 启动。
- 打开普通 JPG/PNG 图片。
- 打开 RAW 图片。
- `--developer-mode` 能写入开发日志。
