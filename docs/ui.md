# PicViewer项目UI设计规范

## 0. 总则（必须遵守）

- 严格按本说明实现 UI 结构与组件命名；不得擅自新增/删减区域、按钮、面板。
- 禁止使用 move()/resize() 绝对定位；所有布局必须基于 QVBoxLayout/QHBoxLayout/QGridLayout/QSplitter。
- 所有可视区域必须可随窗口缩放自适应：左+中图片区、右侧信息区随窗口变化；底部胶卷条固定高度。

## 1. 主窗口布局结构（信息架构）

主窗口采用典型四区结构：

```text
[QMainWindow: MainWindow]
  ├─ MenuBar (顶部，所有功能入口)
  └─ CentralWidget (垂直布局 VBox)
       ├─ TopContentArea (水平分割 Splitter: 左/中图片区  + 右侧信息区)  [expand]
       └─ FilmstripArea (底部胶卷窗格)                                [fixed height]
```

### 1.1 顶部：菜单栏（MenuBar）

- 采用 QMainWindow.menuBar()。
- 菜单栏作为所有功能入口（本版本先提供菜单结构骨架，具体 QAction 回调可留空或 TODO）。
- 至少包含这些顶层菜单（名称必须一致）：
  - 文件(File)：打开图片、打开文件夹、关闭当前标签、退出
  - 查看(View)：缩放、适配窗口、显示/隐藏右侧信息区、显示/隐藏胶卷窗格
  - 工具(Tools)：直方图/波形图选项（可先放占位）
  - 帮助(Help)：关于
- 要求：每个菜单项用 QAction 创建并命名（见“组件清单”）。

## 2. 中央区域（CentralWidget）

CentralWidget 使用 QVBoxLayout，上下两块：

- 上部内容区 splitMain（占据剩余空间，可伸缩）
- 下部胶卷窗格 filmstrip（固定高度）

## 3. 上部内容区：图片标签页 + 右侧信息区（QSplitter）

使用 QSplitter(Qt.Horizontal)，左右两块：

- 左侧（更准确说：左+中）= 图片显示区（Tab 浏览器式）
- 右侧 = 信息区（直方图 / 波形图 / 元数据）

约束：默认右侧信息区可调整宽度；主窗口缩放时，图片显示区优先扩展。

### 3.1 图片显示区（Tabbed Image Viewer）

- 控件：tabsImages: QTabWidget
- 行为：
- 每打开一张图片，新增一个 Tab。
- 每个 Tab 对应一张图片；Tab 标题必须是图片文件名（含扩展名）。
- Tab 可关闭：tabsImages.setTabsClosable(True)；关闭按钮关闭当前图片 Tab。
- 切换 Tab 会同步更新：右侧信息区内容 + 底部胶卷选中项。
- Tab 内容结构（每个 tab 内部）：
- ImageViewWidget（建议用 QGraphicsView + QGraphicsScene 或 QLabel 占位）
- 规范：tab 内只放一个主显示控件，不要堆额外按钮/工具条（工具入口全部在菜单栏）。
- 命名规则：
- Tab 内的显示控件命名为 viewImage（如果用 QGraphicsView）或 lblImage（如果用 QLabel 占位）。

### 3.2 右侧信息区（Info Panel）

右侧信息区是一个不可滚动面板，包含三类信息：直方图、波形图、元数据（内容固定尺寸显示，避免拖动分割条时实时渲染；尺寸以逻辑像素定义，DPI 自动缩放，确保不同分辨率下占比一致）。

- 容器：scrollInfo: QWidget（外层不滚动）
- 内容布局：layoutInfo: QVBoxLayout

信息区内部使用 QTabWidget 或 QToolBox（二选一，推荐 QTabWidget）：

- 控件：tabsInfo: QTabWidget
- 三个 Tab（标题必须一致）：
  - tabHistogram 标题：直方图
  - tabWaveform 标题：波形图
  - tabMetadata 标题：元数据

每个信息 Tab 内部先用占位控件实现（元数据表允许内部滚动）：

- 直方图：widgetHistogram（可先是 QLabel “Histogram Placeholder”）
  - 固定显示尺寸：高 100 × 宽 256（逻辑像素）
- 波形图：widgetWaveform（可先是 QLabel “Waveform Placeholder”）
  - 固定显示尺寸：高 256 × 宽 256（逻辑像素）
- 元数据：tableMetadata: QTableWidget（两列：Key/Value；或 QLabel 占位也可，但推荐表格）
  - 元数据容器固定高度 320（逻辑像素），宽度随信息区；内部表格可滚动

约束：右侧信息区不得影响主图显示区的最小可用空间；默认宽度建议 320~420px，且可拖拽调整；
同时必须限制分割条最小宽度，避免信息区过窄导致固定内容无法完整显示。

## 4. 底部胶卷窗格（FilmstripArea）

底部为类似 Lightroom 的胶卷条：横向缩略图列表，点击切换当前显示图片。

- 容器：frameFilmstrip: QFrame（或 QWidget）
- 固定高度：建议 h=140（允许你后续改，但先固定）
- 内部控件：二选一实现（推荐 1）
  1. listFilmstrip: QListWidget（横向排列）
     - setFlow(QListView.LeftToRight)
     - setWrapping(False)
     - setResizeMode(QListView.Adjust)
     - setViewMode(QListView.IconMode)
     - setIconSize(QSize(96, 96))（占位）
     - 支持水平滚动条
  2. tableFilmstrip: QTableWidget（不推荐，除非你要更复杂布局）
- 行为：
- 每打开一张图片，在胶卷条新增一个 item（缩略图 + 文件名或不显示文字都可以，但需明确）。
- 点击胶卷条 item：
- 如果该图片 Tab 存在：切换到对应 Tab。
- 如果不存在（理论上不应该）：忽略或 TODO。
- 切换 Tab 时：胶卷条选中项同步变化。
- 选中态要求：清晰可见（可先使用系统默认选中样式）。

## 5. 组件清单（必须逐一创建 & 命名一致）

### 5.1 MainWindow & Layout

- MainWindow: QMainWindow
- central: QWidget
- layoutMain: QVBoxLayout
- splitMain: QSplitter(Qt.Horizontal)
- tabsImages: QTabWidget
- scrollInfo: QWidget
- layoutInfo: QVBoxLayout
- tabsInfo: QTabWidget
- frameFilmstrip: QFrame
- listFilmstrip: QListWidget

5.2 MenuBar Actions（先骨架）
顶层菜单：menuFile menuView menuTools menuHelp
Actions（命名必须一致，文案可中英混排但建议一致）：

- actOpenFile：打开图片…
- actOpenFolder：打开文件夹…
- actCloseTab：关闭当前标签
- actExit：退出
- actZoomIn：放大
- actZoomOut：缩小
- actFitToWindow：适配窗口
- actToggleInfoPanel：显示/隐藏信息区（可 checkable）
- actToggleFilmstrip：显示/隐藏胶卷窗格（可 checkable）
- actAbout：关于

## 6. 快捷键

- 菜单栏上的常用功能必须具备有快捷键
- 快捷键必须支持跨平台（`Windows`/`Linux`/`MacOS`）

常用功能的快捷键需要按照如下键位设置：

| 功能              | 快捷键（Windows/Linux） | 快捷键（MacOS）       | 是否已实现 |
| ----------------- | ----------------------- | --------------------- | ---------- |
| 打开图片          | `Ctrl + O`              | `Command + O`         | 已实现     |
| 打开文件夹        | `Shift + Ctrl + O`      | `Shift + Command + O` | 已实现     |
| 显示/隐藏信息区   | `Ctrl + →`              | `Command + →`         | 已实现     |
| 显示/隐藏胶卷窗格 | `Ctrl + ↓`              | `Command + ↓`         | 已实现     |
| 放大              | `Ctrl + +`              | `Command + +`         | 已实现     |
| 缩小              | `Ctrl + -`              | `Command + -`         | 已实现     |
| 适配窗口          | `Ctrl + 0`              | `Command + 0`         | 已实现     |

## 7. 交互规则（必须实现的同步关系）

- 打开图片 => 新增 Tab + 新增胶卷 item + 自动切到该 Tab。
- 切换 Tab => 更新右侧信息（先占位更新）+ 更新胶卷选中项。
- 点击胶卷 item => 切换到对应 Tab。
- 关闭 Tab => 同步移除对应胶卷 item；如果关闭的是当前 Tab，则切换到相邻 Tab 并同步更新。

说明：右侧信息区本版允许“占位刷新”，但必须保留接口 update_info_for_image(image_path)。

## 8. 代码结构要求（交付格式，避免 UI 变乱）

必须按以下结构输出代码（或等价拆分）：

- ui/windows/main_window.py
- class MainWindowUI:
- setup_ui(main_window)
- create_actions()
- create_menus()
- create_widgets()
- create_layouts()
- controllers/main_controller.py
- 负责信号槽：打开/关闭 Tab、Tab-胶卷同步、菜单 QAction 绑定
- main.py
- 启动入口

UI 文件内禁止写业务逻辑；controller 里可以先用 TODO/占位实现。

## 9. 验收清单（Codex 自检）

- UI 结构严格为：MenuBar + (上部 Splitter) + (底部 Filmstrip)
- 图片显示区为 QTabWidget，Tab 标题=文件名
- 右侧信息区包含：直方图/波形图/元数据 三个 Tab（占位可）
- 底部胶卷条横向缩略图列表，可点击切换 Tab
- Tab 与胶卷选中态双向同步
- 无绝对定位 move()/resize()
- `右侧信息区`和`底部胶卷窗格`可隐藏。
- 若图片的文件名超过15个字符，则在`Tab标题`和`底部胶卷条`上显示的文件名按此规则显示：只显示开头的5个字符和末尾的5个字符，中间的字符用3个点号替代。
- 当鼠标指针位于`图片显示区`和`右侧信息区`交界处，或位于`图片显示区`和`底部胶卷窗格`的交界处时，鼠标指针的`样式`要自动变成`双箭头`（即`移动箭头`）。
- 鼠标悬停在`图片显示区`应立即变成`手形`，按住可以拖拽平移放大后的图片。
