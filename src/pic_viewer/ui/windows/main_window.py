"""Main window UI builder (layout, widgets, actions)."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from pic_viewer.app.services.analysis_view_service import AnalysisViewService
from pic_viewer.app.services.image_service import ImageService
from pic_viewer.ui.resources import styles
from pic_viewer.ui.resources.icons import icon_path
from pic_viewer.ui.widgets.histogram_clipping_label import HistogramClippingLabel
from pic_viewer.ui.widgets.detachable_tabs import DetachableTabWidget


class MainWindowUI:
    """根据 ui.md 规范构建主窗口UI（仅负责UI结构与控件命名）。"""

    # Fixed sizes are defined in logical pixels; Qt DPI scaling keeps proportions across screens.
    INFO_PANEL_HISTOGRAM_SIZE = QtCore.QSize(256, 100)
    INFO_PANEL_WAVEFORM_SIZE = QtCore.QSize(256, 256)
    INFO_PANEL_MIN_WIDTH = 320
    IMAGE_PANEL_MIN_WIDTH = 500
    METADATA_KEY_COLUMN_WIDTH = 112
    FILMSTRIP_ICON_SIDE = 72
    FILMSTRIP_MIN_ICON_SIDE = 48
    FILMSTRIP_ITEM_WIDTH = 108
    FILMSTRIP_ITEM_VERTICAL_PADDING = 18
    FILMSTRIP_HEIGHT = 140
    ANALYSIS_TOOLBAR_HEIGHT = 26
    ANALYSIS_TOOLBAR_ICON_SIZE = QtCore.QSize(16, 16)

    def setup_ui(self, main_window: QtWidgets.QMainWindow) -> None:
        self._main_window = main_window
        main_window.resize(1200, 800)
        main_window.setMinimumSize(900, 600)

        self.create_actions()
        self.create_menus()
        self.create_context_menus()
        self.create_widgets()
        self.create_layouts()
        self.apply_appearance_theme()
        self.retranslate_ui()

        self.actToggleInfoPanel.setChecked(True)
        self.actToggleAnalysisToolbar.setChecked(True)
        self.actToggleFilmstrip.setChecked(True)

    def _tr(self, text: str) -> str:
        return QtCore.QCoreApplication.translate("MainWindowUI", text)

    def create_actions(self) -> None:
        self.actOpenFile = QtGui.QAction(self._main_window)
        self.actOpenFile.setObjectName("actOpenFile")
        self.actOpenFolder = QtGui.QAction(self._main_window)
        self.actOpenFolder.setObjectName("actOpenFolder")
        self.actCloseTab = QtGui.QAction(self._main_window)
        self.actCloseTab.setObjectName("actCloseTab")
        self.actExit = QtGui.QAction(self._main_window)
        self.actExit.setObjectName("actExit")

        self.actZoomIn = QtGui.QAction(self._main_window)
        self.actZoomIn.setObjectName("actZoomIn")
        self.actZoomOut = QtGui.QAction(self._main_window)
        self.actZoomOut.setObjectName("actZoomOut")
        self.actFitToWindow = QtGui.QAction(self._main_window)
        self.actFitToWindow.setObjectName("actFitToWindow")
        self.actAppearanceLight = QtGui.QAction(self._main_window)
        self.actAppearanceLight.setObjectName("actAppearanceLight")
        self.actAppearanceLight.setCheckable(True)
        self.actAppearanceDark = QtGui.QAction(self._main_window)
        self.actAppearanceDark.setObjectName("actAppearanceDark")
        self.actAppearanceDark.setCheckable(True)

        self.actToggleInfoPanel = QtGui.QAction(self._main_window)
        self.actToggleInfoPanel.setObjectName("actToggleInfoPanel")
        self.actToggleInfoPanel.setCheckable(True)
        self.actToggleAnalysisToolbar = QtGui.QAction(self._main_window)
        self.actToggleAnalysisToolbar.setObjectName("actToggleAnalysisToolbar")
        self.actToggleAnalysisToolbar.setCheckable(True)
        self.actToggleFilmstrip = QtGui.QAction(self._main_window)
        self.actToggleFilmstrip.setObjectName("actToggleFilmstrip")
        self.actToggleFilmstrip.setCheckable(True)
        self.actToggleMetadataOverlay = QtGui.QAction(self._main_window)
        self.actToggleMetadataOverlay.setObjectName("actToggleMetadataOverlay")
        self.actToggleMetadataOverlay.setCheckable(True)
        self.actToggleMetadataOverlay.setChecked(True)
        self.actToggleCrossReferenceLine = QtGui.QAction(self._main_window)
        self.actToggleCrossReferenceLine.setObjectName("actToggleCrossReferenceLine")
        self.actToggleCrossReferenceLine.setCheckable(True)
        self.actToggleDiagonalReferenceLine = QtGui.QAction(self._main_window)
        self.actToggleDiagonalReferenceLine.setObjectName("actToggleDiagonalReferenceLine")
        self.actToggleDiagonalReferenceLine.setCheckable(True)
        self.actToggleThirdsReferenceLine = QtGui.QAction(self._main_window)
        self.actToggleThirdsReferenceLine.setObjectName("actToggleThirdsReferenceLine")
        self.actToggleThirdsReferenceLine.setCheckable(True)

        self.actAbout = QtGui.QAction(self._main_window)
        self.actAbout.setObjectName("actAbout")
        self.actThirdPartyLicenses = QtGui.QAction(self._main_window)
        self.actThirdPartyLicenses.setObjectName("actThirdPartyLicenses")

        self.actModeLuma = QtGui.QAction(self._main_window)
        self.actModeLuma.setObjectName("actModeLuma")
        self.actModeLuma.setCheckable(True)
        self.actModeRgb = QtGui.QAction(self._main_window)
        self.actModeRgb.setObjectName("actModeRgb")
        self.actModeRgb.setCheckable(True)

        self.actChannelAll = QtGui.QAction(self._main_window)
        self.actChannelAll.setObjectName("actChannelAll")
        self.actChannelAll.setCheckable(True)
        self.actChannelRed = QtGui.QAction(self._main_window)
        self.actChannelRed.setObjectName("actChannelRed")
        self.actChannelRed.setCheckable(True)
        self.actChannelGreen = QtGui.QAction(self._main_window)
        self.actChannelGreen.setObjectName("actChannelGreen")
        self.actChannelGreen.setCheckable(True)
        self.actChannelBlue = QtGui.QAction(self._main_window)
        self.actChannelBlue.setObjectName("actChannelBlue")
        self.actChannelBlue.setCheckable(True)
        self.actToggleUnderexposed = QtGui.QAction(self._main_window)
        self.actToggleUnderexposed.setObjectName("actToggleUnderexposed")
        self.actToggleUnderexposed.setCheckable(True)
        self.actToggleOverexposed = QtGui.QAction(self._main_window)
        self.actToggleOverexposed.setObjectName("actToggleOverexposed")
        self.actToggleOverexposed.setCheckable(True)
        self.actPeakHigh = QtGui.QAction(self._main_window)
        self.actPeakHigh.setObjectName("actPeakHigh")
        self.actPeakHigh.setCheckable(True)
        self.actPeakMedium = QtGui.QAction(self._main_window)
        self.actPeakMedium.setObjectName("actPeakMedium")
        self.actPeakMedium.setCheckable(True)
        self.actPeakLow = QtGui.QAction(self._main_window)
        self.actPeakLow.setObjectName("actPeakLow")
        self.actPeakLow.setCheckable(True)

        self.actionGroupMode = QtGui.QActionGroup(self._main_window)
        self.actionGroupMode.setExclusive(True)
        self.actionGroupMode.addAction(self.actModeLuma)
        self.actionGroupMode.addAction(self.actModeRgb)

        self.actionGroupChannel = QtGui.QActionGroup(self._main_window)
        self.actionGroupChannel.setExclusive(True)
        self.actionGroupChannel.addAction(self.actChannelAll)
        self.actionGroupChannel.addAction(self.actChannelRed)
        self.actionGroupChannel.addAction(self.actChannelGreen)
        self.actionGroupChannel.addAction(self.actChannelBlue)

        self.actionGroupAppearance = QtGui.QActionGroup(self._main_window)
        self.actionGroupAppearance.setExclusive(True)
        self.actionGroupAppearance.addAction(self.actAppearanceLight)
        self.actionGroupAppearance.addAction(self.actAppearanceDark)
        self.actAppearanceLight.triggered.connect(
            lambda _checked=False: self.apply_appearance_theme(styles.AppearanceTheme.LIGHT)
        )
        self.actAppearanceDark.triggered.connect(
            lambda _checked=False: self.apply_appearance_theme(styles.AppearanceTheme.DARK)
        )

        self.actModeLuma.setChecked(True)
        self.actChannelAll.setChecked(True)
        self._apply_analysis_action_icons()
        self._apply_shortcuts()

    def _apply_analysis_action_icons(
        self,
        theme: styles.AppearanceTheme = styles.AppearanceTheme.DARK,
    ) -> None:
        """Assign compact analysis toolbar icons to shared actions."""

        def themed_icon_name(default_name: str, on_light_name: str | None = None) -> str:
            if theme == styles.AppearanceTheme.LIGHT and on_light_name is not None:
                return on_light_name
            return default_name

        icon_by_action = {
            self.actModeLuma: themed_icon_name("analysis-luma.svg", "analysis-luma-on-light.svg"),
            self.actModeRgb: "analysis-rgb.svg",
            self.actChannelAll: "analysis-channel-all.svg",
            self.actChannelRed: "analysis-channel-red.svg",
            self.actChannelGreen: "analysis-channel-green.svg",
            self.actChannelBlue: "analysis-channel-blue.svg",
            self.actToggleUnderexposed: "analysis-underexposed.svg",
            self.actToggleOverexposed: "analysis-overexposed.svg",
            self.actPeakHigh: "analysis-peak-high.svg",
            self.actPeakMedium: "analysis-peak-medium.svg",
            self.actPeakLow: "analysis-peak-low.svg",
            self.actToggleCrossReferenceLine: themed_icon_name(
                "reference-line-cross.svg",
                "reference-line-cross-on-light.svg",
            ),
            self.actToggleDiagonalReferenceLine: themed_icon_name(
                "reference-line-diagonal.svg",
                "reference-line-diagonal-on-light.svg",
            ),
            self.actToggleThirdsReferenceLine: themed_icon_name(
                "reference-line-thirds.svg",
                "reference-line-thirds-on-light.svg",
            ),
            self.actToggleMetadataOverlay: themed_icon_name(
                "metadata-info.svg",
                "metadata-info-on-light.svg",
            ),
        }
        for action, file_name in icon_by_action.items():
            path = icon_path(file_name)
            if path.is_file():
                action.setIcon(QtGui.QIcon(str(path)))
                action.setIconVisibleInMenu(True)

    def _apply_shortcuts(self) -> None:
        """Assign platform-specific shortcuts for common menu actions."""

        # Qt swaps Ctrl/Meta on macOS by default, so "Ctrl" maps to Command there.
        modifier = "Ctrl"
        self.actOpenFile.setShortcut(QtGui.QKeySequence(f"{modifier}+O"))
        self.actOpenFolder.setShortcut(QtGui.QKeySequence(f"{modifier}+Shift+O"))
        self.actCloseTab.setShortcut(QtGui.QKeySequence("Esc"))
        self.actToggleInfoPanel.setShortcut(QtGui.QKeySequence(f"{modifier}+Right"))
        self.actToggleAnalysisToolbar.setShortcut(QtGui.QKeySequence(f"{modifier}+Up"))
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
        self.actPeakHigh.setShortcut(QtGui.QKeySequence("F3"))
        self.actPeakMedium.setShortcut(QtGui.QKeySequence("F2"))
        self.actPeakLow.setShortcut(QtGui.QKeySequence("F1"))

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
        self.menuView.addAction(self.actToggleMetadataOverlay)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actToggleInfoPanel)
        self.menuView.addAction(self.actToggleAnalysisToolbar)
        self.menuView.addAction(self.actToggleFilmstrip)
        self.menuAppearance = self.menuView.addMenu("")
        self.menuAppearance.setObjectName("menuAppearance")
        self.menuAppearance.addAction(self.actAppearanceLight)
        self.menuAppearance.addAction(self.actAppearanceDark)

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
        self.menuPseudoColor.addSeparator()
        self.menuFocusPeaking = self.menuPseudoColor.addMenu("")
        self.menuFocusPeaking.setObjectName("menuFocusPeaking")
        self.menuFocusPeaking.addAction(self.actPeakHigh)
        self.menuFocusPeaking.addAction(self.actPeakMedium)
        self.menuFocusPeaking.addAction(self.actPeakLow)

        self.menuReferenceLines = self.menuTools.addMenu("")
        self.menuReferenceLines.setObjectName("menuReferenceLines")
        self.menuReferenceLines.addAction(self.actToggleCrossReferenceLine)
        self.menuReferenceLines.addAction(self.actToggleDiagonalReferenceLine)
        self.menuReferenceLines.addAction(self.actToggleThirdsReferenceLine)

        self.menuHelp = menu_bar.addMenu("")
        self.menuHelp.setObjectName("menuHelp")
        self.menuHelp.addAction(self.actAbout)
        self.menuHelp.addAction(self.actThirdPartyLicenses)

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

        self.widgetAnalysisToolbar = QtWidgets.QFrame(self.central)
        self.widgetAnalysisToolbar.setObjectName("widgetAnalysisToolbar")
        self.widgetAnalysisToolbar.setFixedHeight(self.ANALYSIS_TOOLBAR_HEIGHT)
        self.widgetAnalysisToolbar.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        toolbar_layout = QtWidgets.QHBoxLayout(self.widgetAnalysisToolbar)
        toolbar_layout.setObjectName("layoutAnalysisToolbar")
        toolbar_layout.setContentsMargins(6, 2, 6, 2)
        toolbar_layout.setSpacing(2)

        self.buttonToolbarModeLuma = self._create_analysis_toolbar_button(
            "buttonToolbarModeLuma",
            self.actModeLuma,
        )
        self.buttonToolbarModeRgb = self._create_analysis_toolbar_button(
            "buttonToolbarModeRgb",
            self.actModeRgb,
        )
        self.buttonToolbarChannelAll = self._create_analysis_toolbar_button(
            "buttonToolbarChannelAll",
            self.actChannelAll,
        )
        self.buttonToolbarChannelRed = self._create_analysis_toolbar_button(
            "buttonToolbarChannelRed",
            self.actChannelRed,
        )
        self.buttonToolbarChannelGreen = self._create_analysis_toolbar_button(
            "buttonToolbarChannelGreen",
            self.actChannelGreen,
        )
        self.buttonToolbarChannelBlue = self._create_analysis_toolbar_button(
            "buttonToolbarChannelBlue",
            self.actChannelBlue,
        )
        self.buttonToolbarUnderexposed = self._create_analysis_toolbar_button(
            "buttonToolbarUnderexposed",
            self.actToggleUnderexposed,
        )
        self.buttonToolbarOverexposed = self._create_analysis_toolbar_button(
            "buttonToolbarOverexposed",
            self.actToggleOverexposed,
        )
        self.buttonToolbarPeakHigh = self._create_analysis_toolbar_button(
            "buttonToolbarPeakHigh",
            self.actPeakHigh,
        )
        self.buttonToolbarPeakMedium = self._create_analysis_toolbar_button(
            "buttonToolbarPeakMedium",
            self.actPeakMedium,
        )
        self.buttonToolbarPeakLow = self._create_analysis_toolbar_button(
            "buttonToolbarPeakLow",
            self.actPeakLow,
        )
        self.buttonToolbarCrossReferenceLine = self._create_analysis_toolbar_button(
            "buttonToolbarCrossReferenceLine",
            self.actToggleCrossReferenceLine,
        )
        self.buttonToolbarDiagonalReferenceLine = self._create_analysis_toolbar_button(
            "buttonToolbarDiagonalReferenceLine",
            self.actToggleDiagonalReferenceLine,
        )
        self.buttonToolbarThirdsReferenceLine = self._create_analysis_toolbar_button(
            "buttonToolbarThirdsReferenceLine",
            self.actToggleThirdsReferenceLine,
        )
        self.buttonToolbarMetadataOverlay = self._create_analysis_toolbar_button(
            "buttonToolbarMetadataOverlay",
            self.actToggleMetadataOverlay,
        )

        balance_size = self.buttonToolbarMetadataOverlay.minimumSize()
        toolbar_layout.addSpacerItem(
            QtWidgets.QSpacerItem(
                balance_size.width(),
                balance_size.height(),
                QtWidgets.QSizePolicy.Policy.Fixed,
                QtWidgets.QSizePolicy.Policy.Fixed,
            )
        )
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.buttonToolbarModeLuma)
        toolbar_layout.addWidget(self.buttonToolbarModeRgb)
        self._add_analysis_toolbar_separator(toolbar_layout)
        toolbar_layout.addWidget(self.buttonToolbarChannelAll)
        toolbar_layout.addWidget(self.buttonToolbarChannelRed)
        toolbar_layout.addWidget(self.buttonToolbarChannelGreen)
        toolbar_layout.addWidget(self.buttonToolbarChannelBlue)
        self._add_analysis_toolbar_separator(toolbar_layout)
        toolbar_layout.addWidget(self.buttonToolbarUnderexposed)
        toolbar_layout.addWidget(self.buttonToolbarOverexposed)
        self._add_analysis_toolbar_separator(toolbar_layout)
        toolbar_layout.addWidget(self.buttonToolbarPeakHigh)
        toolbar_layout.addWidget(self.buttonToolbarPeakMedium)
        toolbar_layout.addWidget(self.buttonToolbarPeakLow)
        self._add_analysis_toolbar_separator(toolbar_layout)
        toolbar_layout.addWidget(self.buttonToolbarCrossReferenceLine)
        toolbar_layout.addWidget(self.buttonToolbarDiagonalReferenceLine)
        toolbar_layout.addWidget(self.buttonToolbarThirdsReferenceLine)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.buttonToolbarMetadataOverlay)

        self.splitMain = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal, self.central)
        self.splitMain.setObjectName("splitMain")

        self.tabsImages = DetachableTabWidget("image", self.splitMain)
        self.tabsImages.setObjectName("tabsImages")
        self.tabsImages.setTabsClosable(True)
        self.tabsImages.setMovable(True)
        self.tabsImages.setMinimumWidth(self.image_panel_min_width)
        self.tabsImages.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        tab_bar = self.tabsImages.tabBar()
        tab_bar.setExpanding(False)
        tab_bar.setElideMode(QtCore.Qt.TextElideMode.ElideNone)

        self.scrollInfo = QtWidgets.QWidget(self.splitMain)
        self.scrollInfo.setObjectName("scrollInfo")
        self.scrollInfo.setMinimumWidth(self.info_panel_min_width)

        self.layoutInfo = QtWidgets.QVBoxLayout(self.scrollInfo)
        self.layoutInfo.setObjectName("layoutInfo")
        self.layoutInfo.setContentsMargins(8, 8, 8, 8)

        self.widgetAnalysisModeSummary = QtWidgets.QWidget(self.scrollInfo)
        self.widgetAnalysisModeSummary.setObjectName("widgetAnalysisModeSummary")
        self.widgetAnalysisModeSummary.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Fixed,
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
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.labelAnalysisModeValue.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.labelAnalysisChannelTitle = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelAnalysisChannelTitle.setObjectName("labelAnalysisChannelTitle")
        self.labelAnalysisChannelValue = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelAnalysisChannelValue.setObjectName("labelAnalysisChannelValue")
        self.labelAnalysisChannelValue.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.labelAnalysisChannelValue.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.labelPseudoColorTitle = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelPseudoColorTitle.setObjectName("labelPseudoColorTitle")
        self.labelPseudoColorValue = QtWidgets.QLabel(self.widgetAnalysisModeSummary)
        self.labelPseudoColorValue.setObjectName("labelPseudoColorValue")
        self.labelPseudoColorValue.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Preferred,
        )
        self.labelPseudoColorValue.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)

        summary_layout.addWidget(self.labelAnalysisModeTitle, 0, 0)
        summary_layout.addWidget(self.labelAnalysisModeValue, 0, 1)
        summary_layout.addWidget(self.labelAnalysisChannelTitle, 1, 0)
        summary_layout.addWidget(self.labelAnalysisChannelValue, 1, 1)
        summary_layout.addWidget(self.labelPseudoColorTitle, 2, 0)
        summary_layout.addWidget(self.labelPseudoColorValue, 2, 1)
        summary_layout.setColumnStretch(1, 1)
        self.layoutInfo.addWidget(self.widgetAnalysisModeSummary)

        self.tabsInfo = DetachableTabWidget("info", self.scrollInfo)
        self.tabsInfo.setObjectName("tabsInfo")
        self.tabsInfo.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.layoutInfo.addWidget(self.tabsInfo)

        self.tabAnalysis = QtWidgets.QWidget(self.tabsInfo)
        self.tabAnalysis.setObjectName("tabAnalysis")
        analysis_layout = QtWidgets.QVBoxLayout(self.tabAnalysis)
        analysis_layout.setContentsMargins(6, 6, 6, 6)
        analysis_layout.setSpacing(8)

        self.frameHistogramAnalysis = QtWidgets.QFrame(self.tabAnalysis)
        self.frameHistogramAnalysis.setObjectName("frameHistogramAnalysis")
        self.frameHistogramAnalysis.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frameHistogramAnalysis.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        hist_frame_layout = QtWidgets.QVBoxLayout(self.frameHistogramAnalysis)
        hist_frame_layout.setContentsMargins(8, 8, 8, 8)
        hist_frame_layout.setSpacing(0)
        self.widgetHistogram = HistogramClippingLabel("", self.frameHistogramAnalysis)
        self.widgetHistogram.setObjectName("widgetHistogram")
        self.widgetHistogram.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.widgetHistogram.setFixedSize(self.info_panel_histogram_size)
        self.widgetHistogram.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        hist_frame_layout.addWidget(self.widgetHistogram)
        analysis_layout.addWidget(
            self.frameHistogramAnalysis,
            0,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
        )

        self.frameWaveformAnalysis = QtWidgets.QFrame(self.tabAnalysis)
        self.frameWaveformAnalysis.setObjectName("frameWaveformAnalysis")
        self.frameWaveformAnalysis.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frameWaveformAnalysis.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        wave_frame_layout = QtWidgets.QVBoxLayout(self.frameWaveformAnalysis)
        wave_frame_layout.setContentsMargins(8, 8, 8, 8)
        wave_frame_layout.setSpacing(0)
        self.widgetWaveform = QtWidgets.QLabel("", self.frameWaveformAnalysis)
        self.widgetWaveform.setObjectName("widgetWaveform")
        self.widgetWaveform.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.widgetWaveform.setFixedSize(self.info_panel_waveform_size)
        self.widgetWaveform.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
        wave_frame_layout.addWidget(self.widgetWaveform)
        analysis_layout.addWidget(
            self.frameWaveformAnalysis,
            0,
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignTop,
        )
        analysis_layout.addStretch(1)
        self.tabsInfo.addTab(self.tabAnalysis, "")

        self.tabMetadata = QtWidgets.QWidget(self.tabsInfo)
        self.tabMetadata.setObjectName("tabMetadata")
        meta_layout = QtWidgets.QVBoxLayout(self.tabMetadata)
        self.tabsMetadata = QtWidgets.QTabWidget(self.tabMetadata)
        self.tabsMetadata.setObjectName("tabsMetadata")
        self.tabsMetadata.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

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

        self.frameFilmstrip = QtWidgets.QFrame(self.central)
        self.frameFilmstrip.setObjectName("frameFilmstrip")
        self.frameFilmstrip.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
        self.frameFilmstrip.setFixedHeight(self.FILMSTRIP_HEIGHT)
        self.frameFilmstrip.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        film_layout = QtWidgets.QVBoxLayout(self.frameFilmstrip)
        film_layout.setContentsMargins(8, 6, 8, 6)

        self.listFilmstrip = QtWidgets.QListWidget(self.frameFilmstrip)
        self.listFilmstrip.setObjectName("listFilmstrip")
        self.listFilmstrip.setFlow(QtWidgets.QListView.Flow.LeftToRight)
        self.listFilmstrip.setWrapping(False)
        self.listFilmstrip.setResizeMode(QtWidgets.QListView.ResizeMode.Adjust)
        self.listFilmstrip.setViewMode(QtWidgets.QListView.ViewMode.IconMode)
        self.listFilmstrip.setIconSize(QtCore.QSize(self.FILMSTRIP_ICON_SIDE, self.FILMSTRIP_ICON_SIDE))
        self.listFilmstrip.setUniformItemSizes(False)
        self.listFilmstrip.setWordWrap(False)
        self.listFilmstrip.setTextElideMode(QtCore.Qt.TextElideMode.ElideNone)
        self.listFilmstrip.setMovement(QtWidgets.QListView.Movement.Static)
        self.listFilmstrip.setSpacing(4)
        self.listFilmstrip.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.listFilmstrip.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        film_layout.addWidget(self.listFilmstrip)

        self.labelFilmstripSummary = QtWidgets.QLabel(self._main_window.statusBar())
        self.labelFilmstripSummary.setObjectName("labelFilmstripSummary")
        self.labelFilmstripSummary.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.labelFilmstripSummary.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self.labelFilmstripSummary.setVisible(False)
        self._main_window.statusBar().addPermanentWidget(self.labelFilmstripSummary)

    def filmstrip_item_size(self, icon_side: int | None = None, text: str = "") -> QtCore.QSize:
        """Return the filmstrip item size needed to display the full file name."""

        side = icon_side if icon_side is not None else self.FILMSTRIP_ICON_SIDE
        font_metrics = self.listFilmstrip.fontMetrics()
        font_height = font_metrics.height()
        text_width = font_metrics.horizontalAdvance(text) + 16 if text else 0
        width = max(self.FILMSTRIP_ITEM_WIDTH, side + 36, text_width)
        height = side + font_height + self.FILMSTRIP_ITEM_VERTICAL_PADDING
        return QtCore.QSize(width, height)

    def _create_analysis_toolbar_button(
        self,
        object_name: str,
        action: QtGui.QAction,
    ) -> QtWidgets.QToolButton:
        button = QtWidgets.QToolButton(self.widgetAnalysisToolbar)
        button.setObjectName(object_name)
        button.setAutoRaise(True)
        button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
        button.setIconSize(self.ANALYSIS_TOOLBAR_ICON_SIZE)
        button.setDefaultAction(action)
        button.setFixedSize(
            self.ANALYSIS_TOOLBAR_HEIGHT - 4,
            self.ANALYSIS_TOOLBAR_HEIGHT - 4,
        )
        return button

    def _add_analysis_toolbar_separator(self, layout: QtWidgets.QHBoxLayout) -> None:
        separator = QtWidgets.QFrame(self.widgetAnalysisToolbar)
        separator.setObjectName("separatorAnalysisToolbar")
        separator.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        separator.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        layout.addWidget(separator)

    def create_layouts(self) -> None:
        self.layoutMain = QtWidgets.QVBoxLayout(self.central)
        self.layoutMain.setObjectName("layoutMain")
        self.layoutMain.setContentsMargins(8, 8, 8, 8)
        self.layoutMain.setSpacing(8)

        self.layoutMain.addWidget(self.widgetAnalysisToolbar)
        self.layoutMain.addWidget(self.splitMain, 1)
        self.layoutMain.addWidget(self.frameFilmstrip)

        self.splitMain.setStretchFactor(0, 3)
        self.splitMain.setStretchFactor(1, 1)
        self.splitMain.setCollapsible(1, False)
        self.splitMain.setSizes(self.default_split_main_sizes())

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

    def apply_appearance_theme(
        self,
        theme: styles.AppearanceTheme | None = None,
    ) -> styles.AppearanceTheme:
        """Apply an appearance theme and synchronize the menu state."""

        applied_theme = styles.apply_stylesheet(self._main_window, theme)
        self._appearance_theme = applied_theme
        self._apply_analysis_action_icons(applied_theme)
        self._sync_appearance_actions(applied_theme)
        for tabs in (getattr(self, "tabsImages", None), getattr(self, "tabsInfo", None)):
            if hasattr(tabs, "apply_floating_stylesheet"):
                tabs.apply_floating_stylesheet(self._main_window.styleSheet())
        return applied_theme

    def _sync_appearance_actions(self, theme: styles.AppearanceTheme) -> None:
        light_blocker = QtCore.QSignalBlocker(self.actAppearanceLight)
        dark_blocker = QtCore.QSignalBlocker(self.actAppearanceDark)
        try:
            self.actAppearanceLight.setChecked(theme == styles.AppearanceTheme.LIGHT)
            self.actAppearanceDark.setChecked(theme == styles.AppearanceTheme.DARK)
        finally:
            del light_blocker
            del dark_blocker

    def _create_metadata_table(
        self, parent: QtWidgets.QWidget, object_name: str
    ) -> QtWidgets.QTableWidget:
        table = QtWidgets.QTableWidget(parent)
        table.setObjectName(object_name)
        table.setColumnCount(2)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.setWordWrap(False)
        table.setTextElideMode(QtCore.Qt.TextElideMode.ElideRight)
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, self.METADATA_KEY_COLUMN_WIDTH)
        table.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        return table

    def retranslate_ui(self) -> None:
        self._main_window.setWindowTitle(self._tr("PicViewer"))

        self.actOpenFile.setText(self._tr("Open Image..."))
        self.actOpenFolder.setText(self._tr("Open Folder..."))
        self.actCloseTab.setText(self._tr("Close Current Tab"))
        self.actExit.setText(self._tr("Exit"))
        self.actZoomIn.setText(self._tr("Zoom In"))
        self.actZoomOut.setText(self._tr("Zoom Out"))
        self.actFitToWindow.setText(self._tr("Fit to Window"))
        self.actAppearanceLight.setText(self._tr("Light"))
        self.actAppearanceDark.setText(self._tr("Dark"))
        self.actToggleInfoPanel.setText(self._tr("Info Panel"))
        self.actToggleAnalysisToolbar.setText(self._tr("Analysis Toolbar"))
        self.actToggleFilmstrip.setText(self._tr("Filmstrip"))
        self.actToggleMetadataOverlay.setText(self._tr("Show Metadata Overlay"))
        self.actToggleCrossReferenceLine.setText(self._tr("Cross Reference Line"))
        self.actToggleDiagonalReferenceLine.setText(self._tr("Diagonal Reference Line"))
        self.actToggleThirdsReferenceLine.setText(self._tr("Rule of Thirds Reference Line"))
        self.actAbout.setText(self._tr("About"))
        self.actThirdPartyLicenses.setText(self._tr("Third-Party License Information"))
        self.actModeLuma.setText(self._tr("Luma Mode"))
        self.actModeRgb.setText(self._tr("RGB Mode"))
        self.actChannelAll.setText(self._tr("All RGB Channels"))
        self.actChannelRed.setText(self._tr("Red Channel Only"))
        self.actChannelGreen.setText(self._tr("Green Channel Only"))
        self.actChannelBlue.setText(self._tr("Blue Channel Only"))
        self.actToggleUnderexposed.setText(self._tr("Show Underexposed"))
        self.actToggleOverexposed.setText(self._tr("Show Overexposed"))
        self.actPeakHigh.setText(self._tr("High"))
        self.actPeakMedium.setText(self._tr("Medium"))
        self.actPeakLow.setText(self._tr("Low"))
        self._sync_analysis_action_tooltips()

        self.menuFile.setTitle(self._tr("File"))
        self.menuView.setTitle(self._tr("View"))
        self.menuAppearance.setTitle(self._tr("Appearance"))
        self.menuReferenceLines.setTitle(self._tr("Reference Lines"))
        self.menuTools.setTitle(self._tr("Tools"))
        self.menuMode.setTitle(self._tr("Histogram/Waveform Mode"))
        self.menuChannel.setTitle(self._tr("RGB Channels"))
        self.menuPseudoColor.setTitle(self._tr("Pseudo Color"))
        self.menuFocusPeaking.setTitle(self._tr("Show Peaks"))
        self.menuHelp.setTitle(self._tr("Help"))

        self.tabsInfo.setTabText(self.tabsInfo.indexOf(self.tabAnalysis), self._tr("Analysis"))
        self.tabsInfo.setTabText(self.tabsInfo.indexOf(self.tabMetadata), self._tr("Metadata"))

        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataGeneral), self._tr("General"))
        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataExif), self._tr("Exif"))
        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataIptc), self._tr("IPTC"))
        self.tabsMetadata.setTabText(self.tabsMetadata.indexOf(self.tabMetadataTiff), self._tr("TIFF"))

        self.labelAnalysisModeTitle.setText(self._tr("Analysis Mode"))
        self.labelAnalysisModeValue.setText(self._tr("Luma Mode"))
        self.labelAnalysisChannelTitle.setText(self._tr("RGB Channels"))
        self.labelAnalysisChannelValue.setText(self._tr("Not Applicable"))
        self.labelPseudoColorTitle.setText(self._tr("Pseudo Color State"))
        self.labelPseudoColorValue.setText(
            self._tr("Underexposed: {under} / Overexposed: {over} / Peaks: {peaks}").format(
                under=self._tr("Off"),
                over=self._tr("Off"),
                peaks=self._tr("Off"),
            )
        )

        self.widgetHistogram.setText(self._tr("Histogram Placeholder"))
        self.widgetHistogram.set_triangle_tooltips(
            self._tr("Show/Hide Underexposed Areas"),
            self._tr("Show/Hide Overexposed Areas"),
        )
        self.widgetWaveform.setText(self._tr("Waveform Placeholder"))
        self._set_metadata_headers()

    def _sync_analysis_action_tooltips(self) -> None:
        """Keep icon-only analysis toolbar actions discoverable."""

        actions = (
            self.actModeLuma,
            self.actModeRgb,
            self.actChannelAll,
            self.actChannelRed,
            self.actChannelGreen,
            self.actChannelBlue,
            self.actToggleUnderexposed,
            self.actToggleOverexposed,
            self.actPeakHigh,
            self.actPeakMedium,
            self.actPeakLow,
            self.actToggleMetadataOverlay,
        )
        for action in actions:
            action.setToolTip(action.text())

    def _set_metadata_headers(self) -> None:
        headers = [self._tr("Key"), self._tr("Value")]
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
        self.statusBar().showMessage(QtCore.QCoreApplication.translate("MainWindow", "Ready"))

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self.controller.on_main_window_resized()
