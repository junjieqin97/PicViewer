# PicViewer项目UI设计规范

## 0. 总则（必须遵守）

- 严格按本说明实现 UI 结构与组件命名；不得擅自新增/删减区域、按钮、面板。
- 禁止使用 move()/resize() 绝对定位；所有布局必须基于 QVBoxLayout/QHBoxLayout/QGridLayout/QSplitter。
- 所有可视区域必须可随窗口缩放自适应：左+中图片区、右侧信息区随窗口变化；底部胶卷条固定高度。
- UI 组件样式必须统一定义在 `src/pic_viewer/ui/resources/styles/*.qss` 文件中；禁止在 Python 代码中通过 `setStyleSheet(...)` 或字符串常量硬编码颜色、边框、间距等样式。

## 1. 主窗口布局结构（信息架构）

主窗口采用典型四区结构：

```text
[QMainWindow: MainWindow]
  ├─ MenuBar (顶部，所有功能入口)
  └─ CentralWidget (垂直布局 VBox)
       ├─ AnalysisToolbar (顶部轻量分析工具栏，可隐藏)                 [fixed height]
       ├─ TopContentArea (水平分割 Splitter: 左/中图片区  + 右侧信息区)  [expand]
       └─ FilmstripArea (底部胶卷窗格)                                [fixed height]
```

### 1.1 顶部：菜单栏（MenuBar）

- 采用 QMainWindow.menuBar()。
- 菜单栏作为所有功能入口（本版本先提供菜单结构骨架，具体 QAction 回调可留空或 TODO）。
- 至少包含这些顶层菜单（名称必须一致）：
    - 文件(File)：打开图片、打开文件夹、关闭当前标签、退出
    - 查看(View)：缩放、适配窗口、信息区（checkable，勾选=显示）、分析工具栏（checkable，勾选=显示）、胶卷窗格（checkable，勾选=显示）
    - 工具(Tools)：直方图/波形图选项 + 伪色选项
      - 伪色(Pseudo Color)：显示欠曝（checkable）、显示过曝（checkable）、显示峰值（高/中/低，checkable，三档互斥且点击当前档关闭）
    - 帮助(Help)：关于
- 要求：每个菜单项用 QAction 创建并命名（见“组件清单”）。

## 2. 中央区域（CentralWidget）

CentralWidget 使用 QVBoxLayout，自上而下三块：

- 顶部轻量分析工具栏 widgetAnalysisToolbar（固定高度，可隐藏）
- 上部内容区 splitMain（占据剩余空间，可伸缩）
- 下部胶卷窗格 filmstrip（固定高度）

### 2.1 顶部轻量分析工具栏（AnalysisToolbar）

- 控件：widgetAnalysisToolbar
- 位置：菜单栏下方、splitMain 上方，横跨整个 CentralWidget 顶部。
- 行为：
  - 默认显示；可通过 `查看(View) > 分析工具栏` 隐藏/显示。
  - 工具栏是菜单动作的快捷入口，不替代菜单栏；明度/RGB、RGB通道、伪色相关功能仍必须保留在 `工具(Tools)` 菜单中。
  - 工具栏按钮必须复用对应 QAction，确保菜单、快捷键、工具栏状态同步。
- 视觉：
  - 固定低高度，建议不超过 30 逻辑像素。
  - 按钮组必须在工具栏中水平居中显示。
  - 按钮只显示小图标，不显示文字；功能说明通过 tooltip 提供。
  - 图标建议尺寸不超过 18×18 逻辑像素。
- 工具按钮必须包含：
  - 明度模式、RGB模式
  - RGB全部通道、仅红通道、仅绿通道、仅蓝通道
  - 显示欠曝、显示过曝
  - 显示峰值高/中/低

## 3. 上部内容区：图片标签页 + 右侧信息区（QSplitter）

使用 QSplitter(Qt.Horizontal)，左右两块：

- 左侧（更准确说：左+中）= 图片显示区（Tab 浏览器式）
- 右侧 = 信息区（分析 / 元数据；分析内包含直方图和波形图）

约束：默认右侧信息区可调整宽度；主窗口缩放时，图片显示区优先扩展。

### 3.1 图片显示区（Tabbed Image Viewer）

- 控件：tabsImages: QTabWidget
- 行为：
- 每打开一张图片，新增一个 Tab。
- 每个 Tab 对应一张图片；Tab 标题必须是图片文件名（含扩展名）。
- 图片显示区 Tab 栏的标签组必须左对齐显示（按内容宽度排列，不均分铺满，空白留在右侧）。
- Tab 可关闭：tabsImages.setTabsClosable(True)；关闭按钮关闭当前图片 Tab。
- 切换 Tab 会同步更新：右侧信息区内容 + 底部胶卷选中项。
- 当没有打开图片时，图片区中央显示“打开图片…”和“打开文件夹…”提示，并展示对应平台快捷键。
- Tab 内容结构（每个 tab 内部）：
- ImageViewWidget（建议用 QGraphicsView + QGraphicsScene 或 QLabel 占位）
- 规范：tab 内只放一个主显示控件，不要堆额外按钮/工具条（工具入口全部在菜单栏）。
- 命名规则：
- Tab 内的显示控件命名为 viewImage（如果用 QGraphicsView）或 lblImage（如果用 QLabel 占位）。
- 右键菜单：在`图片显示区`右键可以打开右键菜单，右键菜单下有`放大`、`缩小`、`适配窗口`功能（功能实现保持和`顶部菜单栏`中的一致，详见`5.2 MenuBar Actions`）

### 3.2 右侧信息区（Info Panel）

右侧信息区是一个不可滚动面板，包含两类一级信息：分析、元数据。其中“分析”面板合并显示直方图和波形图，以减少查看分析信息时的 Tab 切换成本；直方图和波形图内容固定尺寸显示，元数据区自适应填充信息区；尺寸以逻辑像素定义，DPI 自动缩放，确保不同分辨率下占比一致。

- 容器：scrollInfo: QWidget（外层不滚动）
- 内容布局：layoutInfo: QVBoxLayout
- 信息区顶部必须显示轻量摘要：当前分析模式、RGB 通道、伪色状态（欠曝/过曝开关、峰值档位）。

信息区内部使用 QTabWidget：

- 控件：tabsInfo: QTabWidget
- 两个 Tab（标题必须一致）：
  - tabAnalysis 标题：分析
  - tabMetadata 标题：元数据

每个信息 Tab 内部先用占位控件实现（元数据表允许内部滚动）：

- 分析：tabAnalysis 使用垂直布局，按从上到下顺序显示直方图和波形图，两个分析图都应居中且靠顶部排列
- 直方图：widgetHistogram（可先是 QLabel “Histogram Placeholder”）
  - 固定显示尺寸：高 100 × 宽 256（逻辑像素）
  - 直方图左上角和右上角必须显示可点击小三角形：
    - 左上角三角形切换`欠曝`预警：在主图中以`绿色`伪色半透明叠加显示欠曝区域
    - 右上角三角形切换`过曝`预警：在主图中以`红色`伪色半透明叠加显示过曝区域
  - 欠曝/过曝三角形状态为全局共享（切换图片后保持当前开关状态）
- 波形图：widgetWaveform（可先是 QLabel “Waveform Placeholder”）
  - 固定显示尺寸：高 256 × 宽 256（逻辑像素）
- 元数据：tableMetadata: QTableWidget（两列：Key/Value；或 QLabel 占位也可，但推荐表格）
  - 元数据容器高度自适应填充信息区，宽度随信息区；内部表格可滚动

约束：右侧信息区不得影响主图显示区的最小可用空间；默认宽度建议 320~420px，且可拖拽调整；
同时必须限制分割条最小宽度，避免信息区过窄导致固定内容无法完整显示。

## 4. 底部胶卷窗格（FilmstripArea）

底部为类似 Lightroom 的胶卷条：横向缩略图列表，点击切换当前显示图片。

- 容器：frameFilmstrip: QFrame（或 QWidget）
- 固定高度：h=140，不支持通过上下拖动调节高度
- 内部控件：二选一实现（推荐 1）
  1. listFilmstrip: QListWidget（横向排列）
     - setFlow(QListView.LeftToRight)
     - setWrapping(False)
     - setResizeMode(QListView.Adjust)
     - setViewMode(QListView.IconMode)
     - setIconSize(QSize(72, 72))
     - 支持水平滚动条
  2. tableFilmstrip: QTableWidget（不推荐，除非你要更复杂布局）
- 行为：
- 每打开一张图片，在胶卷条新增一个 item（缩略图 + 文件名或不显示文字都可以，但需明确）。
- 点击胶卷条 item：
- 如果该图片 Tab 存在：切换到对应 Tab。
- 如果不存在（理论上不应该）：忽略或 TODO。
- 切换 Tab 时：胶卷条选中项同步变化。
- 当胶卷窗格被隐藏时，状态栏右侧必须显示当前文件摘要，格式为 `Current: {name} ({index}/{total})`；
  其中 `name` 沿用 Tab/胶卷条的长文件名截断规则，tooltip 显示完整路径。胶卷窗格重新显示或没有当前图片时，该摘要必须隐藏。
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
- widgetAnalysisToolbar: QWidget 或 QFrame
- buttonToolbarModeLuma: QToolButton
- buttonToolbarModeRgb: QToolButton
- buttonToolbarChannelAll: QToolButton
- buttonToolbarChannelRed: QToolButton
- buttonToolbarChannelGreen: QToolButton
- buttonToolbarChannelBlue: QToolButton
- buttonToolbarUnderexposed: QToolButton
- buttonToolbarOverexposed: QToolButton
- buttonToolbarPeakHigh: QToolButton
- buttonToolbarPeakMedium: QToolButton
- buttonToolbarPeakLow: QToolButton
- tabsInfo: QTabWidget
- tabAnalysis: QWidget
- tabMetadata: QWidget
- frameFilmstrip: QFrame
- listFilmstrip: QListWidget
- labelFilmstripSummary: QLabel（状态栏右侧，胶卷窗格隐藏时显示当前文件摘要）

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
- actToggleInfoPanel：信息区（可 checkable，勾选=显示）
- actToggleAnalysisToolbar：分析工具栏（可 checkable，勾选=显示）
- actToggleFilmstrip：胶卷窗格（可 checkable，勾选=显示）
- actToggleUnderexposed：显示欠曝（可 checkable）
- actToggleOverexposed：显示过曝（可 checkable）
- actPeakHigh：高（可 checkable，焦点峰值高档）
- actPeakMedium：中（可 checkable，焦点峰值中档）
- actPeakLow：低（可 checkable，焦点峰值低档）
- actAbout：关于

## 6. 快捷键

- 菜单栏上的常用功能必须具备有快捷键
- 快捷键必须支持跨平台（`Windows`/`Linux`/`MacOS`）

常用功能的快捷键需要按照如下键位设置：

| 功能        | 快捷键（Windows/Linux） | 快捷键（MacOS）            | 是否已实现 |
|-----------|--------------------|-----------------------|-------|
| 打开图片      | `Ctrl + O`         | `Command + O`         | 已实现   |
| 打开文件夹     | `Shift + Ctrl + O` | `Shift + Command + O` | 已实现   |
| 关闭当前标签    | `Esc`              | `Esc`                 | 已实现   |
| 信息区       | `Ctrl + →`         | `Command + →`         | 已实现   |
| 分析工具栏     | `Ctrl + ↑`         | `Command + ↑`         | 已实现   |
| 胶卷窗格      | `Ctrl + ↓`         | `Command + ↓`         | 已实现   |
| 放大        | `Ctrl + +`         | `Command + +`         | 已实现   |
| 缩小        | `Ctrl + -`         | `Command + -`         | 已实现   |
| 适配窗口      | `Ctrl + 0`         | `Command + 0`         | 已实现   |
| 明度模式      | `Ctrl + L`         | `Command + L`         | 已实现   |
| RGB模式     | `Ctrl + K`         | `Command + K`         | 已实现   |
| RGB全部通道   | `Ctrl + K`         | `Command + K`         | 已实现   |
| 仅红通道      | `Ctrl + R`         | `Command + R`         | 已实现   |
| 仅绿通道      | `Ctrl + G`         | `Command + G`         | 已实现   |
| 仅蓝通道      | `Ctrl + B`         | `Command + B`         | 已实现   |
| 显示欠曝      | `Shift + Ctrl + P` | `Shift + Command + P` | 已实现   |
| 显示过曝      | `Ctrl + P`         | `Command + P`         | 已实现   |
| 显示峰值（高）  | `F3`               | `F3`                  | 已实现   |
| 显示峰值（中）  | `F2`               | `F2`                  | 已实现   |
| 显示峰值（低）  | `F1`               | `F1`                  | 已实现   |

## 7. 交互规则（必须实现的同步关系）

- 打开图片 => 新增 Tab + 新增胶卷 item + 自动切到该 Tab。
- 切换图片 Tab => 更新右侧信息（先占位更新）+ 更新胶卷选中项；当前选中图片在后台触发完整解析（直方图/波形图/元数据）。
- 点击胶卷 item => 切换到对应 Tab。
- 关闭 Tab => 同步移除对应胶卷 item；如果关闭的是当前 Tab，则切换到相邻 Tab 并同步更新。
- 打开文件夹 => 先并发加载每张图的快速预览，再按需（选中时）进行完整解析。

性能约束：后台图片加载使用线程池，默认最大并发数为 8。

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

- UI 结构严格为：MenuBar + (顶部 AnalysisToolbar) + (上部 Splitter) + (底部 Filmstrip)
- 图片显示区为 QTabWidget，Tab 标题=文件名
- 右侧信息区包含：分析/元数据 两个 Tab；分析 Tab 内同时显示直方图和波形图（占位可）
- 底部胶卷条横向缩略图列表，可点击切换 Tab
- Tab 与胶卷选中态双向同步
- `图片显示区` 的 Tab 标题左对齐（标签组靠左，不均分铺满）
- 无绝对定位 move()/resize()
- `右侧信息区`和`底部胶卷窗格`可隐藏。
- 若图片的文件名超过15个字符，则在`Tab标题`和`底部胶卷条`上显示的文件名按此规则显示：只显示开头的5个字符和末尾的5个字符，中间的字符用3个点号替代。
- 当鼠标指针位于`图片显示区`和`右侧信息区`交界处时，鼠标指针的`样式`要自动变成`双箭头`（即`移动箭头`）。
- 鼠标悬停在`图片显示区`应立即变成`手形`，按住可以拖拽平移放大后的图片。
