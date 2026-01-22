# PicViewer项目开发计划

* 正在开发一个桌面端的照片预览工具，支持打开JPG、PNG、TIFF等常见的图片格式文件，同时支持打开各种相机的RAW文件。

## 基本功能

* 使用该照片预览工具打开照片后，支持显示该照片对应的`直方图`、`波形图`、`元数据`。
* `直方图`和`波形图`支持在`明度模式`和`RGB模式`之间切换，默认显示的是`明度模式`。
* `直方图`和`波形图`在`RGB模式`下，支持在同时显示RGB三个通道和只显示其中一个通道之间切换。
* `元数据`可以像`MacOS`的`预览App`那样显示`通用`、`Exif`、`IPTC`、`TIFF`四种类型的`元数据`，默认显示的是`通用`。

## 技术框架

* 采用的技术框架是Python + OpenCV + PyQt5。

## 文件结构

该项目所有文件需要严格遵循如下结构。

```text
PicViewer/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ pic_viewer/
│     ├─ __init__.py
│     ├─ main.py                 # 程序入口（创建App、装配依赖、启动主窗口）
│     │
│     ├─ ui/                     # 视图层：窗口、控件、资源、UI状态
│     │  ├─ __init__.py
│     │  ├─ windows/             # 主窗口/对话框/页面
│     │  ├─ widgets/             # 可复用组件
│     │  ├─ presenters/          # (可选) MVP/MVVM 的展示逻辑 / view-model
│     │  └─ resources/           # 图标、qss/css、图片、字体、翻译文件等
│     │
│     ├─ app/                    # 应用层：用例编排（“点击按钮后要做什么”）
│     │  ├─ __init__.py
│     │  ├─ services/            # 应用服务/用例（例如：导入文件、生成报告）
│     │  ├─ commands/            # (可选) 命令对象、撤销/重做
│     │  └─ dto/                 # (可选) 跨层数据结构（避免domain对象直出到UI）
│     │
│     ├─ domain/                 # 领域层：核心业务模型与规则（尽量不依赖GUI/IO）
│     │  ├─ __init__.py
│     │  ├─ models/              # 实体、值对象
│     │  ├─ rules/               # 校验规则、计算逻辑
│     │  └─ ports/               # 抽象接口（Repository、Gateway、Clock等）
│     │
│     ├─ infra/                  # 基础设施层：domain ports 的具体实现
│     │  ├─ __init__.py
│     │  ├─ persistence/         # sqlite/sqlalchemy/文件存储等
│     │  ├─ network/             # http/grpc/websocket等
│     │  ├─ system/              # OS相关：剪贴板、通知、开机自启
│     │  └─ adapters/            # 第三方SDK封装
│     │
│     ├─ config/                 # 配置与环境
│     │  ├─ __init__.py
│     │  ├─ settings.py          # 统一读取配置（env/ini/yaml）
│     │  └─ logging.yaml
│     │
│     ├─ common/                 # 通用工具：不会反向依赖业务
│     │  ├─ __init__.py
│     │  ├─ errors.py            # 自定义异常
│     │  ├─ event_bus.py         # (可选) 事件总线
│     │  ├─ i18n.py              # (可选) 国际化辅助
│     │  └─ utils.py
│     │
│     └─ assets/                 # (可选) 静态资源集中管理（也可放ui/resources）
│
├─ tests/
│  ├─ unit/                      # domain/app 层单元测试
│  ├─ integration/               # infra 集成测试
│  └─ e2e/                       # (可选) UI自动化
│
├─ scripts/                      # 开发脚本（格式化、打包、生成版本号等）
└─ packaging/                    # PyInstaller/Briefcase/cx_Freeze 打包相关
   ├─ pyinstaller.spec
   └─ icons/
```
