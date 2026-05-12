"""Main window UI builder (layout, widgets, actions)."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.ui.widgets.histogram_clipping_label import HistogramClippingLabel


class MainWindowUI:
    """根据 ui.md 规范构建主窗口UI（仅负责UI结构与控件命名）。"""

    # Fixed sizes are defined in logical pixels; Qt DPI scaling keeps proportions across screens.
    INFO_PANEL_HISTOGRAM_SIZE = QtCore.QSize(256, 100)
    INFO_PANEL_WAVEFORM_SIZE = QtCore.QSize(256, 256)
    INFO_PANEL_MIN_WIDTH = 320
    IMAGE_PANEL_MIN_WIDTH = 500
    METADATA_KEY_COLUMN_WIDTH = 112

    def setup_ui(self, main_window: QtWidgets.QMainWindow) -> None:
        self._main_window = main_window
        main_window.resize(1200, 800)
        main_window.setMinimumSize(900, 600)

        self.create_actions()
        self.create_menus()
        self.create_context_menus()
        self.create_widgets()
        self.create_layouts()
        self.retranslate_ui()

        self.actToggleInfoPanel.setChecked(True)
        self.actToggleFilmstrip.setChecked(True)

    def _tr(self, text: str) -> str:
        return QtCore.QCoreApplication.translate("MainWindowUI", text)

    def create_actions(self) -> None:
        self.actOpenFile = QtWidgets.QAction(self._main_window)
        self.actOpenFile.setObjectName("actOpenFile")
        self.actOpenFolder = QtWidgets.QAction(self._main_window)
        self.actOpenFolder.setObjectName("actOpenFolder")
        self.actCloseTab = QtWidgets.QAction(self._main_window)
        self.actCloseTab.setObjectName("actCloseTab")
        self.actExit = QtWidgets.QAction(self._main_window)
        self.actExit.setObjectName("actExit")

        self.actZoomIn = QtWidgets.QAction(self._main_window)
        self.actZoomIn.setObjectName("actZoomIn")
        self.actZoomOut = QtWidgets.QAction(self._main_window)
        self.actZoomOut.setObjectName("actZoomOut")
        self.actFitToWindow = QtWidgets.QAction(self._main_window)
        self.actFitToWindow.setObjectName("actFitToWindow")

        self.actToggleInfoPanel = QtWidgets.QAction(self._main_window)
        self.actToggleInfoPanel.setObjectName("actToggleInfoPanel")
        self.actToggleInfoPanel.setCheckable(True)
        self.actToggleFilmstrip = QtWidgets.QAction(self._main_window)
        self.actToggleFilmstrip.setObjectName("actToggleFilmstrip")
        self.actToggleFilmstrip.setCheckable(True)

        self.actAbout = QtWidgets.QAction(self._main_window)
        self.actAbout.setObjectName("actAbout")

        self.actModeLuma = QtWidgets.QAction(self._main_window)
        self.actModeLuma.setObjectName("actModeLuma")
        self.actModeLuma.setCheckable(True)
        self.actModeRgb = QtWidgets.QAction(self._main_window)
        self.actModeRgb.setObjectName("actModeRgb")
        self.actModeRgb.setCheckable(True)

        self.actChannelAll = QtWidgets.QAction(self._main_window)
        self.actChannelAll.setObjectName("actChannelAll")
        self.actChannelAll.setCheckable(True)
        self.actChannelRed = QtWidgets.QAction(self._main_window)
        self.actChannelRed.setObjectName("actChannelRed")
        self.actChannelRed.setCheckable(True)
        self.actChannelGreen = QtWidgets.QAction(self._main_window)
        self.actChannelGreen.setObjectName("actChannelGreen")
        self.actChannelGreen.setCheckable(True)
        self.actChannelBlue = QtWidgets.QAction(self._main_window)
        self.actChannelBlue.setObjectName("actChannelBlue")
        self.actChannelBlue.setCheckable(True)
        self.actToggleUnderexposed = QtWidgets.QAction(self._main_window)
        self.actToggleUnderexposed.setObjectName("actToggleUnderexposed")
        self.actToggleUnderexposed.setCheckable(True)
        self.actToggleOverexposed = QtWidgets.QAction(self._main_window)
        self.actToggleOverexposed.setObjectName("actToggleOverexposed")
        self.actToggleOverexposed.setCheckable(True)

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
        self.actCloseTab.setShortcut(QtGui.QKeySequence("Esc"))
        self.actToggleInfoPanel.setShortcut(QtGui.QKeySequence(f"{modifier}+Right"))
        self.actToggleFilmstrip.setShortcut(QtGui.QKeySequence(f"{modifier}+Down"))
        self.actZoomIn.setShortcut(QtGui.QKeySequence(f"{modifier}++"))
        self.actZoomOut.setShortcut(QtGui.QKeySequence(f"{modifier}+-"))
        self.actFitToWindow.setShortcut(QtGui.QKeySequence(f"{modifier}+0"))
        self.actModeLuma.setShortcut(QtGui.QKeySequence(f"{modifier}+L"))
        self.actModeRgb.setShortcut(QtGui.QKeySequence(f"{modifier}+K"))
        self.actChannelAll.setShortcut(QtGui.QKeySequence(f"{modifier}+K"))
        self.actChannelRed.setShortcut(QtGui.QKeySequence(f"{modifier}+R"))
        self.actChannelGreen.setShortcut(QtGui.QKeySequence(f"{modifier}+G"))
        self.actChannelBlue.setShortcut(QtGui.QKeySequence(f"{modifier}+B"))
        self.actToggleUnderexposed.setShortcut(QtGui.QKeySequence(f"{modifier}+Shift+P"))
        self.actToggleOverexposed.setShortcut(QtGui.QKeySequence(f"{modifier}+P"))

    def create_menus(self) -> None:
        menu_bar = self._main_window.menuBar()

        self.menuFile = menu_bar.addMenu("")
        self.menuFile.setObjectName("menuFile")
        self.menuFile.addAction(self.actOpenFile)
        self.menuFile.addAction(self.actOpenFolder)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actCloseTab)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actExit)

        self.menuView = menu_bar.addMenu("")
        self.menuView.setObjectName("menuView")
        self.menuView.addAction(self.actZoomIn)
        self.menuView.addAction(self.actZoomOut)
        self.menuView.addAction(self.actFitToWindow)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actToggleInfoPanel)
        self.menuView.addAction(self.actToggleFilmstrip)

        self.menuTools = menu_bar.addMenu("")
        self.menuTools.setObjectName("menuTools")
        self.menuMode = self.menuTools.addMenu("")
        self.menuMode.addAction(self.actModeLuma)
        self.menuMode.addAction(self.actModeRgb)

        self.menuChannel = self.menuTools.addMenu("")
        self.menuChannel.addAction(self.actChannelAll)
        self.menuChannel.addAction(self.actChannelRed)
        self.menuChannel.addAction(self.actChannelGreen)
        self.menuChannel.addAction(self.actChannelBlue)

        self.menuPseudoColor = self.menuTools.addMenu("")
        self.menuPseudoColor.setObjectName("menuPseudoColor")
        self.menuPseudoColor.addAction(self.actToggleUnderexposed)
        self.menuPseudoColor.addAction(self.actToggleOverexposed)

        self.menuHelp = menu_bar.addMenu("")
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.addAction(self.actAbout)

    def create_context_menus(self) -> None:
        """Create shared context menus for the image display area."""

        self.menuImageContext = QtWidgets.QMenu(self._main_window)
        self.menuImageContext.setObjectName("menuImageContext")
        self.menuImageContext.addAction(self.actZoomIn)
        self.menuImageContext.addAction(self.actZoomOut)
        self.menuImageContext.addSeparator()
        self.menuImageContext.addAction(self.actFitToWindow)

    def create_widgets(self) -> None:
        self.info_panel_histogram_size = QtCore.QSize(
            self.INFO_PANEL_HISTOGRAM_SIZE.width(),
            self.INFO_PANEL_HISTOGRAM_SIZE.height(),
        )
        self.info_panel_waveform_size = QtCore.QSize(
            self.INFO_PANEL_WAVEFORM_SIZE.width(),
            self.INFO_PANEL_WAVEFORM_SIZE.height(),
        )
        self.info_panel_min_width = int(self.INFO_PANEL_MIN_WIDTH)
        self.image_panel_min_width = int(self.IMAGE_PANEL_MIN_WIDTH)

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
        self.tabsImages.setMinimumWidth(self.image_panel_min_width)
        self.tabsImages.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        tab_bar = self.tabsImages.tabBar()
        tab_bar.setExpanding(False)
        self.tabsImages.setStyleSheet("QTabWidget#tabsImages::tab-bar { alignment: left; }")

        self.scrollInfo = QtWidgets.QWidget(self.splitMain)
        self.scrollInfo.setObjectName("scrollInfo")
        self.scrollInfo.setMinimumWidth(self.info_panel_min_width)

        self.layoutInfo = QtWidgets.QVBoxLayout(self.scrollInfo)
        self.layoutInfo.setObjectName("layoutInfo")
        self.layoutInfo.setContentsMargins(8, 8, 8, 8)

        self.widgetAnalysisModeSummary = QtWidgets.QWidget(self.scrollInfo)
        self.widgetAnalysisModeSummary.setObjectName("widgetAnalysisModeSummary")
        self.widgetAnalysisModeSummary.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Fixed,
        )
        summary_layout = QtWidgets.QGridLayout(self.widgetAnalysisModeSummary)
        summary_layout.setObjectName("layoutAnalysisModeSummary")
        summary_layout.setContentsMargins(4, 0, 4, 4)
        summary_layout.setHorizontalSpacing(8)
        summary_layout.setVerticalSpacing(2)

        self.labelAnalysisModeTitle = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelAnalysisModeTitle.setObjectName("labelAnalysisModeTitle")
        self.labelAnalysisModeValue = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelAnalysisModeValue.setObjectName("labelAnalysisModeValue")
        self.labelAnalysisModeValue.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.labelAnalysisModeValue.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.labelAnalysisChannelTitle = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelAnalysisChannelTitle.setObjectName("labelAnalysisChannelTitle")
        self.labelAnalysisChannelValue = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelAnalysisChannelValue.setObjectName("labelAnalysisChannelValue")
        self.labelAnalysisChannelValue.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )
        self.labelAnalysisChannelValue.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)

        summary_layout.addWidget(self.labelAnalysisModeTitle, 0, 0)
        summary_layout.addWidget(self.labelAnalysisModeValue, 0, 1)
        summary_layout.addWidget(self.labelAnalysisChannelTitle, 1, 0)
        summary_layout.addWidget(self.labelAnalysisChannelValue, 1, 1)
        summary_layout.setColumnStretch(1, 1)
        self.layoutInfo.addWidget(self.widgetAnalysisModeSummary)

        self.tabsInfo = QtWidgets.QTabWidget(self.scrollInfo)
        self.tabsInfo.setObjectName("tabsInfo")
        self.tabsInfo.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.layoutInfo.addWidget(self.tabsInfo)

        self.tabHistogram = QtWidgets.QWidget(self.tabsInfo)
        self.tabHistogram.setObjectName("tabHistogram")
        hist_layout = QtWidgets.QVBoxLayout(self.tabHistogram)
        hist_layout.setContentsMargins(6, 6, 6, 6)
        self.frameHistogramAnalysis = QtWidgets.QFrame(self.tabHistogram)
        self.frameHistogramAnalysis.setObjectName("frameHistogramAnalysis")
        self.frameHistogramAnalysis.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameHistogramAnalysis.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        hist_frame_layout = QtWidgets.QVBoxLayout(self.frameHistogramAnalysis)
        hist_frame_layout.setContentsMargins(8, 8, 8, 8)
        hist_frame_layout.setSpacing(0)
        self.widgetHistogram = HistogramClippingLabel("", self.frameHistogramAnalysis)
        self.widgetHistogram.setObjectName("widgetHistogram")
        self.widgetHistogram.setAlignment(QtCore.Qt.AlignCenter)
        self.widgetHistogram.setFixedSize(self.info_panel_histogram_size)
        self.widgetHistogram.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        hist_frame_layout.addWidget(self.widgetHistogram)
        hist_layout.addWidget(
            self.frameHistogramAnalysis,
            0,
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop,
        )
        self.tabsInfo.addTab(self.tabHistogram, "")

        self.tabWaveform = QtWidgets.QWidget(self.tabsInfo)
        self.tabWaveform.setObjectName("tabWaveform")
        wave_layout = QtWidgets.QVBoxLayout(self.tabWaveform)
        wave_layout.setContentsMargins(6, 6, 6, 6)
        self.frameWaveformAnalysis = QtWidgets.QFrame(self.tabWaveform)
        self.frameWaveformAnalysis.setObjectName("frameWaveformAnalysis")
        self.frameWaveformAnalysis.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frameWaveformAnalysis.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        wave_frame_layout = QtWidgets.QVBoxLayout(self.frameWaveformAnalysis)
        wave_frame_layout.setContentsMargins(8, 8, 8, 8)
        wave_frame_layout.setSpacing(0)
        self.widgetWaveform = QtWidgets.QLabel("", self.frameWaveformAnalysis)
        self.widgetWaveform.setObjectName("widgetWaveform")
        self.widgetWaveform.setAlignment(QtCore.Qt.AlignCenter)
        self.widgetWaveform.setFixedSize(self.info_panel_waveform_size)
        self.widgetWaveform.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        wave_frame_layout.addWidget(self.widgetWaveform)
        wave_layout.addWidget(
            self.frameWaveformAnalysis,
            0,
            QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop,
        )
        self.tabsInfo.addTab(self.tabWaveform, "")

        self.tabMetadata = QtWidgets.QWidget(self.tabsInfo)
        self.tabMetadata.setObjectName("tabMetadata")
        meta_layout = QtWidgets.QVBoxLayout(self.tabMetadata)
        self.tabsMetadata = QtWidgets.QTabWidget(self.tabMetadata)
        self.tabsMetadata.setObjectName("tabsMetadata")
        self.tabsMetadata.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.tabMetadataGeneral = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataGeneral.setObjectName("tabMetadataGeneral")
        general_layout = QtWidgets.QVBoxLayout(self.tabMetadataGeneral)
        self.tableMetadataGeneral = self._create_metadata_table(self.tabMetadataGeneral, "tableMetadataGeneral")
        general_layout.addWidget(self.tableMetadataGeneral)
        self.tabsMetadata.addTab(self.tabMetadataGeneral, "")

        self.tabMetadataExif = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataExif.setObjectName("tabMetadataExif")
        exif_layout = QtWidgets.QVBoxLayout(self.tabMetadataExif)
        self.tableMetadataExif = self._create_metadata_table(self.tabMetadataExif, "tableMetadataExif")
        exif_layout.addWidget(self.tableMetadataExif)
        self.tabsMetadata.addTab(self.tabMetadataExif, "")

        self.tabMetadataIptc = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataIptc.setObjectName("tabMetadataIptc")
        iptc_layout = QtWidgets.QVBoxLayout(self.tabMetadataIptc)
        self.tableMetadataIptc = self._create_metadata_table(self.tabMetadataIptc, "tableMetadataIptc")
        iptc_layout.addWidget(self.tableMetadataIptc)
        self.tabsMetadata.addTab(self.tabMetadataIptc, "")

        self.tabMetadataTiff = QtWidgets.QWidget(self.tabsMetadata)
        self.tabMetadataTiff.setObjectName("tabMetadataTiff")
        tiff_layout = QtWidgets.QVBoxLayout(self.tabMetadataTiff)
        self.tableMetadataTiff = self._create_metadata_table(self.tabMetadataTiff, "tableMetadataTiff")
        tiff_layout.addWidget(self.tableMetadataTiff)
        self.tabsMetadata.addTab(self.tabMetadataTiff, "")

        meta_layout.addWidget(self.tabsMetadata, 1)
        self.tabsInfo.addTab(self.tabMetadata, "")

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
        self.splitMain.setCollapsible(1, False)
        self.splitMain.setSizes(self.default_split_main_sizes())

        self.splitVertical.setStretchFactor(0, 3)
        self.splitVertical.setStretchFactor(1, 1)
        default_filmstrip = 140
        self.splitVertical.setSizes([max(self._main_window.height() - default_filmstrip, 1), default_filmstrip])

    def default_split_main_sizes(self, total_width: int | None = None) -> list[int]:
        """Return default splitter sizes for the image area and info panel."""

        info_width = max(self.info_panel_min_width, 300)
        base_width = total_width if total_width and total_width > 0 else self._main_window.width()
        if base_width <= 0:
            base_width = self._main_window.minimumWidth()
        if base_width <= 0:
            base_width = info_width + self.image_panel_min_width
        base_width = max(base_width, info_width + self.image_panel_min_width)
        image_width = max(base_width - info_width, self.image_panel_min_width)
        return [image_width, info_width]

    def _create_metadata_table(
        self, parent: QtWidgets.QWidget, object_name: str
    ) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(2)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setWordWrap(False)
        table.setTextElideMode(QtCore.Qt.ElideRight)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)
        table.setColumnWidth(0, self.METADATA_KEY_COLUMN_WIDTH)
        table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        return table

    def retranslate_ui(self) -> None:
        self._main_window.setWindowTitle(self._tr("PicViewer"))

        self.actOpenFile.setText(self._tr("打开图片…"))
        self.actOpenFolder.setText(self._tr("打开文件夹…"))
        self.actCloseTab.setText(self._tr("关闭当前标签"))
        self.actExit.setText(self._tr("退出"))
        self.actZoomIn.setText(self._tr("放大"))
        self.actZoomOut.setText(self._tr("缩小"))
        self.actFitToWindow.setText(self._tr("适配窗口"))
        self.actToggleInfoPanel.setText(self._tr("显示/隐藏信息区"))
        self.actToggleFilmstrip.setText(self._tr("显示/隐藏胶卷窗格"))
        self.actAbout.setText(self._tr("关于"))
        self.actModeLuma.setText(self._tr("明度模式"))
        self.actModeRgb.setText(self._tr("RGB模式"))
        self.actChannelAll.setText(self._tr("RGB全部通道"))
        self.actChannelRed.setText(self._tr("仅红通道"))
        self.actChannelGreen.setText(self._tr("仅绿通道"))
        self.actChannelBlue.setText(self._tr("仅蓝通道"))
        self.actToggleUnderexposed.setText(self._tr("显示欠曝"))
        self.actToggleOverexposed.setText(self._tr("显示过曝"))

        self.menuFile.setTitle(self._tr("文件"))
        self.menuView.setTitle(self._tr("查看"))
        self.menuTools.setTitle(self._tr("工具"))
        self.menuMode.setTitle(self._tr("直方图/波形图模式"))
        self.menuChannel.setTitle(self._tr("RGB通道"))
        self.menuPseudoColor.setTitle(self._tr("伪色"))
        self.menuHelp.setTitle(self._tr("帮助"))

        self.tabsInfo.setTabText(self.tabsInfo.indexOf(self.tabHistogram), self._tr("直方图"))
        self.tabsInfo.setTabText(self.tabsInfo.indexOf(self.tabWaveform), self._tr("波形图"))
        self.tabsInfo.setTabText(self.tabsInfo.indexOf(self.tabMetadata), self._tr("元数据"))

        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataGeneral), self._tr("通用"))
        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataExif), self._tr("Exif"))
        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataIptc), self._tr("IPTC"))
        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataTiff), self._tr("TIFF"))

        self.labelAnalysisModeTitle.setText(self._tr("分析模式"))
        self.labelAnalysisModeValue.setText(self._tr("明度模式"))
        self.labelAnalysisChannelTitle.setText(self._tr("RGB通道"))
        self.labelAnalysisChannelValue.setText(self._tr("不适用"))

        self.widgetHistogram.setText(self._tr("直方图占位图"))
        self.widgetHistogram.set_triangle_tooltips(
            self._tr("显示/隐藏欠曝区域"),
            self._tr("显示/隐藏过曝区域"),
        )
        self.widgetWaveform.setText(self._tr("波形图占位图"))
        self._set_metadata_headers()

    def _set_metadata_headers(self) -> None:
        headers = [self._tr("键"), self._tr("值")]
        self.tableMetadataGeneral.setHorizontalHeaderLabels(headers)
        self.tableMetadataExif.setHorizontalHeaderLabels(headers)
        self.tableMetadataIptc.setHorizontalHeaderLabels(headers)
        self.tableMetadataTiff.setHorizontalHeaderLabels(headers)


class MainWindow(QtWidgets.QMainWindow):
    """主窗口：装配 UI + Controller（避免在UI回调里写业务逻辑）。"""

    def __init__(self, image_service: ImageService, view_service: AnalysisViewService) -> None:
        super().__init__()
        self.ui = MainWindowUI()
        self.ui.setup_ui(self)

        from pic_viewer.controllers.main_controller import MainController

        self.controller = MainController(self, self.ui, image_service, view_service)
        self.statusBar().showMessage(QtCore.QCoreApplication.translate("MainWindow", "准备就绪"))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.controller.on_main_window_resized()
