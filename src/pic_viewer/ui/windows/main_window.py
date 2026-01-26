"""Main window UI builder (layout, widgets, actions)."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService


class MainWindowUI:
    """根据 ui.md 规范构建主窗口UI（仅负责UI结构与控件命名）。"""

    def setup_ui(self, main_window: QtWidgets.QMainWindow) -> None:
        self._main_window = main_window
        main_window.setWindowTitle("PicViewer")
        main_window.resize(1200, 800)
        main_window.setMinimumSize(900, 600)

        self.create_actions()
        self.create_menus()
        self.create_widgets()
        self.create_layouts()

        self.actToggleInfoPanel.setChecked(True)
        self.actToggleFilmstrip.setChecked(True)

    def create_actions(self) -> None:
        self.actOpenFile = QtWidgets.QAction("打开图片…", self._main_window)
        self.actOpenFile.setObjectName("actOpenFile")
        self.actOpenFolder = QtWidgets.QAction("打开文件夹…", self._main_window)
        self.actOpenFolder.setObjectName("actOpenFolder")
        self.actCloseTab = QtWidgets.QAction("关闭当前标签", self._main_window)
        self.actCloseTab.setObjectName("actCloseTab")
        self.actExit = QtWidgets.QAction("退出", self._main_window)
        self.actExit.setObjectName("actExit")

        self.actZoomIn = QtWidgets.QAction("放大", self._main_window)
        self.actZoomIn.setObjectName("actZoomIn")
        self.actZoomOut = QtWidgets.QAction("缩小", self._main_window)
        self.actZoomOut.setObjectName("actZoomOut")
        self.actFitToWindow = QtWidgets.QAction("适配窗口", self._main_window)
        self.actFitToWindow.setObjectName("actFitToWindow")

        self.actToggleInfoPanel = QtWidgets.QAction("显示/隐藏信息区", self._main_window)
        self.actToggleInfoPanel.setObjectName("actToggleInfoPanel")
        self.actToggleInfoPanel.setCheckable(True)
        self.actToggleFilmstrip = QtWidgets.QAction("显示/隐藏胶卷窗格", self._main_window)
        self.actToggleFilmstrip.setObjectName("actToggleFilmstrip")
        self.actToggleFilmstrip.setCheckable(True)

        self.actAbout = QtWidgets.QAction("关于", self._main_window)
        self.actAbout.setObjectName("actAbout")

        self.actModeLuma = QtWidgets.QAction("明度模式", self._main_window)
        self.actModeLuma.setObjectName("actModeLuma")
        self.actModeLuma.setCheckable(True)
        self.actModeRgb = QtWidgets.QAction("RGB模式", self._main_window)
        self.actModeRgb.setObjectName("actModeRgb")
        self.actModeRgb.setCheckable(True)

        self.actChannelAll = QtWidgets.QAction("RGB全部通道", self._main_window)
        self.actChannelAll.setObjectName("actChannelAll")
        self.actChannelAll.setCheckable(True)
        self.actChannelRed = QtWidgets.QAction("仅红通道", self._main_window)
        self.actChannelRed.setObjectName("actChannelRed")
        self.actChannelRed.setCheckable(True)
        self.actChannelGreen = QtWidgets.QAction("仅绿通道", self._main_window)
        self.actChannelGreen.setObjectName("actChannelGreen")
        self.actChannelGreen.setCheckable(True)
        self.actChannelBlue = QtWidgets.QAction("仅蓝通道", self._main_window)
        self.actChannelBlue.setObjectName("actChannelBlue")
        self.actChannelBlue.setCheckable(True)

        self.actionGroupMode = QtWidgets.QActionGroup(self._main_window)
        self.actionGroupMode.setExclusive(True)
        self.actionGroupMode.addAction(self.actModeLuma)
        self.actionGroupMode.addAction(self.actModeRgb)

        self.actionGroupChannel = QtWidgets.QActionGroup(self._main_window)
        self.actionGroupChannel.setExclusive(True)
        self.actionGroupChannel.addAction(self.actChannelAll)
        self.actionGroupChannel.addAction(self.actChannelRed)
        self.actionGroupChannel.addAction(self.actChannelGreen)
        self.actionGroupChannel.addAction(self.actChannelBlue)

        self.actModeLuma.setChecked(True)
        self.actChannelAll.setChecked(True)
        self._apply_shortcuts()

    def _apply_shortcuts(self) -> None:
        """Assign platform-specific shortcuts for common menu actions."""

        # Qt swaps Ctrl/Meta on macOS by default, so "Ctrl" maps to Command there.
        modifier = "Ctrl"
        self.actOpenFile.setShortcut(QtGui.QKeySequence(f"{modifier}+O"))
        self.actOpenFolder.setShortcut(QtGui.QKeySequence(f"{modifier}+Shift+O"))
        self.actToggleInfoPanel.setShortcut(QtGui.QKeySequence(f"{modifier}+Right"))
        self.actToggleFilmstrip.setShortcut(QtGui.QKeySequence(f"{modifier}+Down"))
        self.actZoomIn.setShortcut(QtGui.QKeySequence(f"{modifier}++"))
        self.actZoomOut.setShortcut(QtGui.QKeySequence(f"{modifier}+-"))
        self.actFitToWindow.setShortcut(QtGui.QKeySequence(f"{modifier}+0"))

    def create_menus(self) -> None:
        menu_bar = self._main_window.menuBar()

        self.menuFile = menu_bar.addMenu("文件(File)")
        self.menuFile.setObjectName("menuFile")
        self.menuFile.addAction(self.actOpenFile)
        self.menuFile.addAction(self.actOpenFolder)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actCloseTab)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actExit)

        self.menuView = menu_bar.addMenu("查看(View)")
        self.menuView.setObjectName("menuView")
        self.menuView.addAction(self.actZoomIn)
        self.menuView.addAction(self.actZoomOut)
        self.menuView.addAction(self.actFitToWindow)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actToggleInfoPanel)
        self.menuView.addAction(self.actToggleFilmstrip)

        self.menuTools = menu_bar.addMenu("工具(Tools)")
        self.menuTools.setObjectName("menuTools")
        self.menuMode = self.menuTools.addMenu("直方图/波形图模式")
        self.menuMode.addAction(self.actModeLuma)
        self.menuMode.addAction(self.actModeRgb)

        self.menuChannel = self.menuTools.addMenu("RGB通道")
        self.menuChannel.addAction(self.actChannelAll)
        self.menuChannel.addAction(self.actChannelRed)
        self.menuChannel.addAction(self.actChannelGreen)
        self.menuChannel.addAction(self.actChannelBlue)

        self.menuHelp = menu_bar.addMenu("帮助(Help)")
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.addAction(self.actAbout)

    def create_widgets(self) -> None:
        self.central = QtWidgets.QWidget(self._main_window)
        self.central.setObjectName("central")
        self._main_window.setCentralWidget(self.central)

        self.splitVertical = QtWidgets.QSplitter(QtCore.Qt.Vertical, self.central)
        self.splitVertical.setObjectName("splitVertical")

        self.splitMain = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self.splitVertical)
        self.splitMain.setObjectName("splitMain")

        self.tabsImages = QtWidgets.QTabWidget(self.splitMain)
        self.tabsImages.setObjectName("tabsImages")
        self.tabsImages.setTabsClosable(True)
        self.tabsImages.setMovable(True)

        self.scrollInfo = QtWidgets.QScrollArea(self.splitMain)
        self.scrollInfo.setObjectName("scrollInfo")
        self.scrollInfo.setWidgetResizable(True)

        self.panelInfo = QtWidgets.QWidget(self.scrollInfo)
        self.panelInfo.setObjectName("panelInfo")
        self.layoutInfo = QtWidgets.QVBoxLayout(self.panelInfo)
        self.layoutInfo.setObjectName("layoutInfo")
        self.layoutInfo.setContentsMargins(8, 8, 8, 8)

        self.tabsInfo = QtWidgets.QTabWidget(self.panelInfo)
        self.tabsInfo.setObjectName("tabsInfo")
        self.layoutInfo.addWidget(self.tabsInfo)
        self.scrollInfo.setWidget(self.panelInfo)

        self.tabHistogram = QtWidgets.QWidget(self.tabsInfo)
        self.tabHistogram.setObjectName("tabHistogram")
        hist_layout = QtWidgets.QVBoxLayout(self.tabHistogram)
        self.widgetHistogram = QtWidgets.QLabel("Histogram Placeholder", self.tabHistogram)
        self.widgetHistogram.setObjectName("widgetHistogram")
        self.widgetHistogram.setAlignment(QtCore.Qt.AlignCenter)
        hist_layout.addWidget(self.widgetHistogram)
        self.tabsInfo.addTab(self.tabHistogram, "直方图")

        self.tabWaveform = QtWidgets.QWidget(self.tabsInfo)
        self.tabWaveform.setObjectName("tabWaveform")
        wave_layout = QtWidgets.QVBoxLayout(self.tabWaveform)
        self.widgetWaveform = QtWidgets.QLabel("Waveform Placeholder", self.tabWaveform)
        self.widgetWaveform.setObjectName("widgetWaveform")
        self.widgetWaveform.setAlignment(QtCore.Qt.AlignCenter)
        wave_layout.addWidget(self.widgetWaveform)
        self.tabsInfo.addTab(self.tabWaveform, "波形图")

        self.tabMetadata = QtWidgets.QWidget(self.tabsInfo)
        self.tabMetadata.setObjectName("tabMetadata")
        meta_layout = QtWidgets.QVBoxLayout(self.tabMetadata)
        self.tabsMetadata = QtWidgets.QTabWidget(self.tabMetadata)
        self.tabsMetadata.setObjectName("tabsMetadata")

        self.tabMetadataGeneral = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataGeneral.setObjectName("tabMetadataGeneral")
        general_layout = QtWidgets.QVBoxLayout(self.tabMetadataGeneral)
        self.tableMetadataGeneral = self._create_metadata_table(self.tabMetadataGeneral, "tableMetadataGeneral")
        general_layout.addWidget(self.tableMetadataGeneral)
        self.tabsMetadata.addTab(self.tabMetadataGeneral, "通用")

        self.tabMetadataExif = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataExif.setObjectName("tabMetadataExif")
        exif_layout = QtWidgets.QVBoxLayout(self.tabMetadataExif)
        self.tableMetadataExif = self._create_metadata_table(self.tabMetadataExif, "tableMetadataExif")
        exif_layout.addWidget(self.tableMetadataExif)
        self.tabsMetadata.addTab(self.tabMetadataExif, "Exif")

        self.tabMetadataIptc = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataIptc.setObjectName("tabMetadataIptc")
        iptc_layout = QtWidgets.QVBoxLayout(self.tabMetadataIptc)
        self.tableMetadataIptc = self._create_metadata_table(self.tabMetadataIptc, "tableMetadataIptc")
        iptc_layout.addWidget(self.tableMetadataIptc)
        self.tabsMetadata.addTab(self.tabMetadataIptc, "IPTC")

        self.tabMetadataTiff = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataTiff.setObjectName("tabMetadataTiff")
        tiff_layout = QtWidgets.QVBoxLayout(self.tabMetadataTiff)
        self.tableMetadataTiff = self._create_metadata_table(self.tabMetadataTiff, "tableMetadataTiff")
        tiff_layout.addWidget(self.tableMetadataTiff)
        self.tabsMetadata.addTab(self.tabMetadataTiff, "TIFF")

        meta_layout.addWidget(self.tabsMetadata)
        self.tabsInfo.addTab(self.tabMetadata, "元数据")

        self.frameFilmstrip = QtWidgets.QFrame(self.splitVertical)
        self.frameFilmstrip.setObjectName("frameFilmstrip")
        self.frameFilmstrip.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameFilmstrip.setMinimumHeight(100)
        film_layout = QtWidgets.QVBoxLayout(self.frameFilmstrip)
        film_layout.setContentsMargins(8, 6, 8, 6)

        self.listFilmstrip = QtWidgets.QListWidget(self.frameFilmstrip)
        self.listFilmstrip.setObjectName("listFilmstrip")
        self.listFilmstrip.setFlow(QtWidgets.QListView.LeftToRight)
        self.listFilmstrip.setWrapping(False)
        self.listFilmstrip.setResizeMode(QtWidgets.QListView.Adjust)
        self.listFilmstrip.setViewMode(QtWidgets.QListView.IconMode)
        self.listFilmstrip.setIconSize(QtCore.QSize(96, 96))
        self.listFilmstrip.setMovement(QtWidgets.QListView.Static)
        self.listFilmstrip.setSpacing(6)
        self.listFilmstrip.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.listFilmstrip.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        film_layout.addWidget(self.listFilmstrip)

    def create_layouts(self) -> None:
        self.layoutMain = QtWidgets.QVBoxLayout(self.central)
        self.layoutMain.setObjectName("layoutMain")
        self.layoutMain.setContentsMargins(8, 8, 8, 8)
        self.layoutMain.setSpacing(8)

        self.layoutMain.addWidget(self.splitVertical, 1)

        self.splitMain.setStretchFactor(0, 3)
        self.splitMain.setStretchFactor(1, 1)
        self.splitMain.setSizes([1, 380])

        self.splitVertical.setStretchFactor(0, 3)
        self.splitVertical.setStretchFactor(1, 1)
        default_filmstrip = 140
        self.splitVertical.setSizes([max(self._main_window.height() - default_filmstrip, 1), default_filmstrip])

    def _create_metadata_table(
        self, parent: QtWidgets.QWidget, object_name: str
    ) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Key", "Value"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.horizontalHeader().setStretchLastSection(True)
        return table


class MainWindow(QtWidgets.QMainWindow):
    """主窗口：装配 UI + Controller（避免在UI回调里写业务逻辑）。"""

    def __init__(self, image_service: ImageService, view_service: AnalysisViewService) -> None:
        super().__init__()
        self.ui = MainWindowUI()
        self.ui.setup_ui(self)

        from pic_viewer.controllers.main_controller import MainController

        self.controller = MainController(self, self.ui, image_service, view_service)
        self.statusBar().showMessage("准备就绪")

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.controller.on_main_window_resized()
