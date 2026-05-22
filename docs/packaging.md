# PicViewer 打包方案

## 目标

PicViewer 支持两类发布模式：

- Python 包：生成 `sdist` 和 `wheel`，专业用户安装后可执行 `python -m pic_viewer` 或 `picviewer`。
- 桌面 App 与安装器：使用 PyInstaller 在 Windows/macOS 本机构建可分发 App，并按平台生成 MSI 或 DMG，普通用户无需了解 Python 环境。

本阶段不包含代码签名、公证、自动更新或 PyPI 上传自动化。

## 前置条件

所有 Python 命令必须先进入项目 conda 环境：

```bash
conda activate PicViewer
```

`PicViewer` 环境必须使用 Python 3.10。项目 GUI 绑定为 PySide2，PySide2 不支持 Python 3.11 及以上版本。

如需重建环境，可使用：

```bash
conda create -n PicViewer python=3.10
conda activate PicViewer
pip install -e ".[packaging]"
```

打包工具通过可选依赖安装：

```bash
pip install ".[packaging]"
```

Windows MSI 构建需要安装 WiX Toolset，并确保 `wix` 命令位于 `PATH`。如果命令不在 `PATH`，可在执行脚本时通过 `--wix` 指定 `wix.exe` 路径。

WiX Toolset v7 及以上版本在首次构建前可能会报错 `WIX7015`，提示需要接受 OSMF EULA。请先阅读并确认
<https://wixtoolset.org/osmf/> 中的要求，然后选择一种方式处理：

```bash
wix eula accept wix7
```

或在单次构建命令中显式传递接受参数：

```bash
python scripts/packaging/build_msi.py --accept-wix-eula
```

`--accept-wix-eula` 会向 WiX 传递 `-acceptEula wix7`，只应在已经确认 WiX OSMF EULA 要求后使用。

生成翻译源文件需要 PySide2 的 `pyside2-lupdate` 命令位于 `PATH`。生成翻译资源需要 Qt 的
`lrelease` 命令位于 `PATH`。若本机 `lrelease` 命令名不同，可直接使用：

```bash
python scripts/i18n/build_qm.py --lrelease /path/to/lrelease
```

当 `lrelease` 和 `lrelease-qt5` 都不在 `PATH` 中时，`build_qm.py` 也会在
`~/.conda/envs/PicViewer/Lib/site-packages/PySide2` 下查找这些工具。

应用图标资源由 `src/pic_viewer/ui/resources/icons/picviewer.svg` 作为主源生成：

```bash
python scripts/packaging/generate_icons.py
```

脚本会生成运行时 PNG 尺寸族、Windows `.ico` 和 macOS `.icns`。macOS 会优先调用 `iconutil`，不可用时回退到 Pillow 生成 `.icns`。

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

PyInstaller 使用 `onedir` 模式。Windows 产物为 `dist/PicViewer/`，macOS 产物为 `dist/PicViewer.app`。Windows 使用 `packaging/icons/picviewer.ico`，macOS 使用 `packaging/icons/picviewer.icns` 作为应用图标。App 版本默认通过 `packaging` extra 安装并收集 `rawpy`，面向普通用户提供 RAW 支持。

不支持交叉构建：Windows App 必须在 Windows 构建，macOS App 必须在 macOS 构建。

## Windows MSI 模式

构建命令：

```bash
python scripts/packaging/build_msi.py
```

脚本会执行以下步骤：

- 校验当前 conda 环境名为 `PicViewer`。
- 校验当前平台为 Windows。
- 校验 WiX CLI 可用。
- 从 `pyproject.toml` 读取版本号，版本号必须符合 Windows Installer 的 `MAJOR.MINOR.PATCH` 数字格式。
- 校验 `dist/PicViewer/PicViewer.exe` 已存在；若不存在，应先运行 `python scripts/packaging/build_app.py`。
- 根据 `dist/PicViewer/` 的实际文件树生成临时 WiX 源文件 `build/msi/PicViewer.wxs`。
- 使用 WiX 构建 x64、per-machine MSI，安装目录为 `C:\Program Files\PicViewer`。
- 在开始菜单和桌面创建 `PicViewer` 快捷方式。
- 在 MSI 同级目录生成 SHA256 校验文件，文件名为 `*.msi.sha256`。

MSI 产物输出到 `dist/PicViewer-版本号.msi`，例如 `dist/PicViewer-0.1.0.msi`。
SHA256 校验文件输出到 `dist/PicViewer-版本号.msi.sha256`，内容格式为 `SHA256  MSI文件名`。

如果 WiX 命令不叫 `wix`，可使用：

```bash
python scripts/packaging/build_msi.py --wix C:\Path\To\wix.exe
```

如果使用 WiX v7 且尚未做过按用户/机器保存的 EULA 接受，也可使用：

```bash
python scripts/packaging/build_msi.py --accept-wix-eula
```

## macOS DMG 模式

构建命令：

```bash
python scripts/packaging/build_dmg.py
```

脚本会执行以下步骤：

- 校验当前 conda 环境名为 `PicViewer`。
- 校验当前平台为 macOS。
- 从 `pyproject.toml` 读取版本号。
- 校验 `dist/PicViewer.app` 已存在；若不存在，应先运行 `python scripts/packaging/build_app.py`。
- 将 `dist/PicViewer.app` 复制到临时 staging 目录。
- 在 staging 目录中创建 `Applications -> /Applications` 捷径，方便用户拖拽安装。
- 使用 macOS 自带 `hdiutil` 生成压缩 DMG。
- 在 DMG 同级目录生成 SHA256 校验文件，文件名为 `*.dmg.sha256`。

DMG 产物输出到 `dist/PicViewer-版本号.dmg`，例如 `dist/PicViewer-0.1.0.dmg`。
SHA256 校验文件输出到 `dist/PicViewer-版本号.dmg.sha256`，内容格式为 `SHA256  DMG文件名`。

## 发布检查清单

```bash
conda activate PicViewer
python --version  # 应输出 Python 3.10.x
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

检查 wheel 内容时，应能看到：

- `pic_viewer/ui/resources/styles/main.qss`
- `pic_viewer/ui/resources/icons/picviewer.svg`
- `pic_viewer/ui/resources/icons/picviewer-256.png`
- `pic_viewer/ui/resources/i18n/picviewer_zh_CN.qm`
- `pic_viewer/ui/resources/i18n/picviewer_en.qm`

App 验证至少覆盖：

- 默认语言启动。
- `PICVIEWER_LANG=zh_CN` 启动。
- 必要时用 `PICVIEWER_LANG=en` 显式验证英文 source 回退。
- 打开普通 JPG/PNG 图片。
- 打开 RAW 图片。
- `--developer-mode` 能写入开发日志。
