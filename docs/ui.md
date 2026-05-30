# PicViewer UI Design Specification

## 0. General Rules (Mandatory)

- Implement the UI structure and component names strictly according to this document; do not add or remove areas, buttons, or panels without authorization.
- Do not use absolute positioning with `move()`/`resize()`; all layouts must be based on `QVBoxLayout`/`QHBoxLayout`/`QGridLayout`/`QSplitter`.
- All visible areas must adapt to window resizing: the left + center image area and the right info area resize with the window; the bottom filmstrip keeps a fixed height.
- UI component styles must be defined uniformly in `src/pic_viewer/ui/resources/styles/*.qss` files; do not hardcode colors, borders, spacing, or other styles in Python code via `setStyleSheet(...)` or string constants.

## 1. Main Window Layout Structure (Information Architecture)

The main window uses a typical four-area structure:

```text
[QMainWindow: MainWindow]
  ├─  MenuBar (top, entry point for all features)
  └─ CentralWidget (vertical VBox layout)
       ├─ AnalysisToolbar (top lightweight analysis toolbar, hideable)           [fixed height]
       ├─ TopContentArea (horizontal Splitter: left/center image area + right info area) [expand]
       └─ FilmstripArea (bottom filmstrip pane)                                  [fixed height]
```

### 1.1 Top: MenuBar

- Use `QMainWindow.menuBar()`.
- The menu bar is the entry point for all features.
- It must contain at least these top-level menus (names must be consistent):
  - File: Open Image, Open Folder, Close Current Tab, Exit
  - View: Zoom, Fit to Window, Show Metadata Overlay (checkable, checked = visible), Info Panel (checkable, checked = visible), Analysis Toolbar (checkable, checked = visible), Filmstrip Pane (checkable, checked = visible), Appearance (Light/Dark, mutually exclusive)
  - Tools: Histogram/Waveform options + pseudo color options + reference line options
    - Pseudo Color: Show Underexposed (checkable), Show Overexposed (checkable), Show Peaking (High/Medium/Low, checkable, three levels are mutually exclusive and clicking the current level turns it off)
    - Reference Lines: Crosshair Reference Line, Diagonal Reference Line, Rule-of-Thirds Grid Reference Line (all checkable; can be toggled independently and displayed as overlays together)
  - Help: About, Third-Party Library License Information
- In the `Third-Party Library License Information` dialog, recognizable license names must be displayed as hyperlinks; clicking a license name opens a read-only dialog showing the original English text of that license.
- Requirement: create and name each menu item with `QAction` (see "Component Checklist").

## 2. Central Area (CentralWidget)

`CentralWidget` uses `QVBoxLayout` and contains three blocks from top to bottom:

- Top lightweight analysis toolbar `widgetAnalysisToolbar` (fixed height, hideable)
- Upper content area `splitMain` (occupies remaining space, resizable)
- Bottom filmstrip pane `filmstrip` (fixed height)

### 2.1 Top Lightweight Analysis Toolbar (AnalysisToolbar)

- Widget: `widgetAnalysisToolbar`
- Position: below the menu bar and above `splitMain`, spanning the full width of the `CentralWidget`.
- Behavior:
  - Visible by default; can be hidden/shown through `View > Analysis Toolbar`.
  - The toolbar is a shortcut entry point for menu actions and does not replace the menu bar; luma/RGB, RGB channels, pseudo color, and reference line features must still remain in the `Tools` menu.
  - Toolbar buttons must reuse the corresponding `QAction` objects to ensure the menu, shortcuts, and toolbar states stay synchronized.
- Visual:
  - Fixed low height, recommended to be no more than 30 logical pixels.
  - Button groups must be horizontally centered inside the toolbar.
  - Buttons show only small icons and no text; feature descriptions are provided through tooltips.
  - Recommended icon size is no more than 18 x 18 logical pixels.
- Tool buttons must include:
  - Luma Mode, RGB Mode
  - All RGB Channels, Red Channel Only, Green Channel Only, Blue Channel Only
  - Show Underexposed, Show Overexposed
  - Show Peaking High/Medium/Low
  - Crosshair Reference Line, Diagonal Reference Line, Rule-of-Thirds Grid Reference Line
  - Show Metadata Overlay
- The Show Metadata Overlay button is pinned to the far right side of the toolbar. The centered analysis button group must remain visually centered by reserving equal space on the left side.
- The Show Metadata Overlay button is enabled by default. When enabled, the current image shows up to three metadata lines at the upper-left corner of the actual displayed image: camera/lens, exposure settings, and resolution. The camera name combines camera maker and camera model when both are available. Missing metadata fields are omitted instead of shown as placeholders. The text is drawn in semi-transparent white.

## 3. Upper Content Area: Image Tabs + Right Info Area (QSplitter)

Use `QSplitter(Qt.Horizontal)` with two sections:

- Left side (more precisely: left + center) = image display area (tab-browser style)
- Right side = info area (analysis / metadata; the analysis section contains the histogram and waveform)

Constraint: the right info area width is adjustable by default; when the main window is resized, the image display area expands first.

### 3.1 Image Display Area (Tabbed Image Viewer)

- Widget: `tabsImages: DetachableTabWidget` (`QTabWidget` subclass)
- Behavior:
- Add a new tab for each opened image.
- Each tab corresponds to one image; the tab title must be the image file name (including extension).
- The tab label group in the image display area's tab bar must be left-aligned (arranged by content width, not stretched evenly to fill the width; blank space remains on the right).
- Tabs are closable: `tabsImages.setTabsClosable(True)`; the close button closes the current image tab.
- Tabs are detachable: dragging an image tab out of the image tab bar opens it in a separate floating window.
- A detached image tab remains an open image and stays synchronized with the filmstrip, zoom actions, pseudo-color overlays, metadata overlay, and right-side information refresh.
- A detached image floating window uses the native window frame and title only; it must not add a second internal tab header.
- Closing a detached image floating window returns the tab to `tabsImages`; it must not close the image. `Close Current Tab` remains the only shortcut/menu action that closes the image and removes its filmstrip item.
- Closing the main window closes all detached image floating windows as part of application shutdown.
- Detached image tabs can only be dropped back into `tabsImages`; they must not be accepted by the info tab widget.
- Switching tabs synchronizes: right info area content + selected item in the bottom filmstrip.
- When no image is open, the center of the image area displays prompts for "Open Image..." and "Open Folder...", along with the corresponding platform shortcuts.
- Tab content structure (inside each tab):
- `ImageViewWidget` (recommended to use `QGraphicsView + QGraphicsScene`, or use `QLabel` as a placeholder)
- Specification: each tab should contain only one main display control; do not stack additional buttons/toolbars inside the tab (all tool entries are in the menu bar).
- Naming rules:
- The display control inside a tab is named `viewImage` (if using `QGraphicsView`) or `lblImage` (if using `QLabel` as a placeholder).
- Context menu: right-clicking in the `image display area` opens a context menu containing `Zoom In`, `Zoom Out`, and `Fit to Window`; their behavior must remain consistent with the `top menu bar` actions. See `5.2 MenuBar Actions`.
- Mouse wheel: scrolling up in the `image display area` performs `Zoom In`, and scrolling down performs `Zoom Out`; the implementation must reuse the zoom logic from the `top menu bar`.

### 3.2 Right Info Area (Info Panel)

The right info area is a non-scrollable panel containing two top-level information categories: analysis and metadata. The "Analysis" panel combines the histogram and waveform to reduce tab switching when viewing analysis information. Histogram and waveform content are displayed at fixed sizes, while the metadata area adaptively fills the info area. Sizes are defined in logical pixels and automatically scale with DPI to keep proportions consistent across different resolutions.

- Container: `scrollInfo: QWidget` (outer layer is not scrollable)
- Content layout: `layoutInfo: QVBoxLayout`
- The top of the info area must display a lightweight summary: current analysis mode, RGB channel, pseudo color state (underexposed/overexposed toggles, peaking level).

Inside the info area, use `DetachableTabWidget` (`QTabWidget` subclass):

- Widget: `tabsInfo: DetachableTabWidget`
- Two tabs (titles must be consistent):
  - `tabAnalysis` title: Analysis
  - `tabMetadata` title: Metadata
- `Analysis` and `Metadata` tabs are detachable: dragging either top-level info tab out of `tabsInfo` opens it in a separate floating window.
- A detached info floating window uses the native window frame and title only; it must not add a second internal tab header.
- Closing a detached info floating window returns the tab to `tabsInfo`; it must not remove the analysis or metadata content.
- Closing the main window closes all detached info floating windows as part of application shutdown.
- Returning a detached info tab must make the right info panel visible if it was hidden.
- Detached info tabs can only be dropped back into `tabsInfo`; they must not be accepted by the image tab widget.
- Nested metadata tabs (`General`, `Exif`, `IPTC`, `TIFF`) remain regular tabs and are not detachable in this version.

Each info tab is first implemented with placeholder controls (the metadata table may scroll internally):

- Analysis: `tabAnalysis` uses a vertical layout and displays the histogram and waveform from top to bottom; both analysis charts should be centered horizontally and aligned near the top.
- Histogram: `widgetHistogram` (may initially be a `QLabel` with "Histogram Placeholder")
  - Fixed display size: height 100 x width 256 (logical pixels)
  - Clickable small triangles must be displayed in the upper-left and upper-right corners of the histogram:
    - The upper-left triangle toggles the `underexposed` warning: underexposed areas are displayed on the main image with a semi-transparent `green` pseudo-color overlay.
    - The upper-right triangle toggles the `overexposed` warning: overexposed areas are displayed on the main image with a semi-transparent `red` pseudo-color overlay.
  - The underexposed/overexposed triangle state is shared globally (the current toggle state is preserved after switching images).
- Waveform: `widgetWaveform` (may initially be a `QLabel` with "Waveform Placeholder")
  - Fixed display size: height 256 x width 256 (logical pixels)
- Metadata: `tableMetadata: QTableWidget` (two columns: Key/Value; a `QLabel` placeholder is also allowed, but a table is recommended)
  - The metadata container height adaptively fills the info area, and its width follows the info area; the internal table may scroll.

Constraint: the right info area must not affect the minimum usable space of the main image display area. The recommended default width is 320-420 px and should be draggable for adjustment.
At the same time, the splitter must enforce a minimum width to prevent the info area from becoming too narrow to display fixed-size content completely.

## 4. Bottom Filmstrip Pane (FilmstripArea)

The bottom area is a Lightroom-style filmstrip: a horizontal thumbnail list. Clicking an item switches the currently displayed image.

- Container: `frameFilmstrip: QFrame` (or `QWidget`)
- Fixed height: `h=140`; height adjustment by vertical dragging is not supported.
- Internal control: choose one of the following two implementations (1 is recommended):
  1. `listFilmstrip: QListWidget` (horizontal layout)
     - `setFlow(QListView.LeftToRight)`
     - `setWrapping(False)`
     - `setResizeMode(QListView.Adjust)`
     - `setViewMode(QListView.IconMode)`
     - `setIconSize(QSize(72, 72))`
     - Supports a horizontal scrollbar
  2. `tableFilmstrip: QTableWidget` (not recommended unless a more complex layout is needed)
- Behavior:
- When an image is opened, add one item to the filmstrip (thumbnail + file name, or no displayed text; this must be clearly specified).
- Clicking a filmstrip item:
- If the corresponding image tab exists: switch to that tab.
- If it does not exist (theoretically should not happen): ignore or TODO.
- When switching tabs: synchronize the selected item in the filmstrip.
- When the filmstrip pane is hidden, the right side of the status bar must display a current file summary in the format `Current: {name} ({index}/{total})`;
  `name` is the full file name, and the tooltip displays the full path. When the filmstrip pane is shown again or there is no current image, this summary must be hidden.
- Selected state requirement: clearly visible (system default selection style may be used first).

## 5. Component Checklist (Must Be Created One by One and Named Consistently)

### 5.1 MainWindow & Layout

- `MainWindow: QMainWindow`
- `central: QWidget`
- `layoutMain: QVBoxLayout`
- `splitMain: QSplitter(Qt.Horizontal)`
- `tabsImages: DetachableTabWidget`
- `scrollInfo: QWidget`
- `layoutInfo: QVBoxLayout`
- `widgetAnalysisToolbar: QWidget` or `QFrame`
- `buttonToolbarModeLuma: QToolButton`
- `buttonToolbarModeRgb: QToolButton`
- `buttonToolbarChannelAll: QToolButton`
- `buttonToolbarChannelRed: QToolButton`
- `buttonToolbarChannelGreen: QToolButton`
- `buttonToolbarChannelBlue: QToolButton`
- `buttonToolbarUnderexposed: QToolButton`
- `buttonToolbarOverexposed: QToolButton`
- `buttonToolbarPeakHigh: QToolButton`
- `buttonToolbarPeakMedium: QToolButton`
- `buttonToolbarPeakLow: QToolButton`
- `buttonToolbarCrossReferenceLine: QToolButton`
- `buttonToolbarDiagonalReferenceLine: QToolButton`
- `buttonToolbarThirdsReferenceLine: QToolButton`
- `buttonToolbarMetadataOverlay: QToolButton`
- `tabsInfo: DetachableTabWidget`
- `tabAnalysis: QWidget`
- `tabMetadata: QWidget`
- `frameFilmstrip: QFrame`
- `listFilmstrip: QListWidget`
- `labelFilmstripSummary: QLabel` (right side of the status bar; displays the current file summary when the filmstrip pane is hidden)

### 5.2 MenuBar Actions (skeleton first)

Top-level menus: `menuFile` `menuView` `menuTools` `menuHelp`
Submenus: `menuAppearance`
Actions (names must be consistent; copy may mix Chinese and English, but consistency is recommended):

- `actOpenFile`: Open Image...
- `actOpenFolder`: Open Folder...
- `actCloseTab`: Close Current Tab
- `actExit`: Exit
- `actZoomIn`: Zoom In
- `actZoomOut`: Zoom Out
- `actFitToWindow`: Fit to Window
- `actAppearanceLight`: Light (checkable, mutually exclusive with Dark)
- `actAppearanceDark`: Dark (checkable, mutually exclusive with Light)
- `actToggleInfoPanel`: Info Panel (checkable, checked = visible)
- `actToggleAnalysisToolbar`: Analysis Toolbar (checkable, checked = visible)
- `actToggleFilmstrip`: Filmstrip Pane (checkable, checked = visible)
- `actToggleMetadataOverlay`: Show Metadata Overlay (checkable, checked = visible)
- `actToggleUnderexposed`: Show Underexposed (checkable)
- `actToggleOverexposed`: Show Overexposed (checkable)
- `actPeakHigh`: High (checkable, focus peaking high level)
- `actPeakMedium`: Medium (checkable, focus peaking medium level)
- `actPeakLow`: Low (checkable, focus peaking low level)
- `actToggleCrossReferenceLine`: Crosshair Reference Line (checkable)
- `actToggleDiagonalReferenceLine`: Diagonal Reference Line (checkable)
- `actToggleThirdsReferenceLine`: Rule-of-Thirds Grid Reference Line (checkable)
- `actAbout`: About
- `actThirdPartyLicenses`: Third-Party Library License Information

## 6. Shortcuts

- Common features in the menu bar must have shortcuts.
- Shortcuts must support cross-platform use (`Windows`/`Linux`/`MacOS`).

Shortcuts for common features must be set as follows:

| Feature               | Shortcut (Windows/Linux) | Shortcut (MacOS)        |
| --------------------- | ------------------------ | ----------------------- |
| Open Image            | `Ctrl + O`               | `Command + O`           |
| Open Folder           | `Shift + Ctrl + O`       | `Shift + Command + O`   |
| Close Current Tab     | `Esc`                    | `Esc`                   |
| Info Panel            | `Ctrl + Right Arrow`     | `Command + Right Arrow` |
| Analysis Toolbar      | `Ctrl + Up Arrow`        | `Command + Up Arrow`    |
| Filmstrip Pane        | `Ctrl + Down Arrow`      | `Command + Down Arrow`  |
| Zoom In               | `Ctrl + +`               | `Command + +`           |
| Zoom Out              | `Ctrl + -`               | `Command + -`           |
| Fit to Window         | `Ctrl + 0`               | `Command + 0`           |
| Luma Mode             | `Ctrl + L`               | `Command + L`           |
| RGB Mode              | `Ctrl + K`               | `Command + K`           |
| All RGB Channels      | `Ctrl + K`               | `Command + K`           |
| Red Channel Only      | `Ctrl + R`               | `Command + R`           |
| Green Channel Only    | `Ctrl + G`               | `Command + G`           |
| Blue Channel Only     | `Ctrl + B`               | `Command + B`           |
| Show Underexposed     | `Shift + Ctrl + P`       | `Shift + Command + P`   |
| Show Overexposed      | `Ctrl + P`               | `Command + P`           |
| Show Peaking (High)   | `F3`                     | `F3`                    |
| Show Peaking (Medium) | `F2`                     | `F2`                    |
| Show Peaking (Low)    | `F1`                     | `F1`                    |

## 7. Interaction Rules (Synchronization Relationships That Must Be Implemented)

- Open Image => add a new tab + add a new filmstrip item + automatically switch to that tab.
- Switch image tab => update the right info area (placeholder update first) + update the selected filmstrip item; the currently selected image triggers full parsing in the background (histogram/waveform/metadata).
- Click filmstrip item => switch to the corresponding tab.
- Close tab => synchronously remove the corresponding filmstrip item; if the closed tab is the current tab, switch to an adjacent tab and synchronize updates.
- Open Folder => first load fast previews for each image concurrently, then perform full parsing on demand (when selected).

Performance constraint: background image loading uses a thread pool with a default maximum concurrency of 8.

Note: this version allows "placeholder refresh" in the right info area, but the interface `update_info_for_image(image_path)` must be preserved.

## 8. Code Structure Requirements (Delivery Format, Avoid UI Disorder)

Code must be output according to the following structure (or an equivalent split):

- `ui/windows/main_window.py`
- `class MainWindowUI:`
- `setup_ui(main_window)`
- `create_actions()`
- `create_menus()`
- `create_widgets()`
- `create_layouts()`
- `controllers/main_controller.py`
- Responsible for signals and slots: opening/closing tabs, tab-filmstrip synchronization, menu `QAction` binding
- `main.py`
- Startup entry point

Do not write business logic inside UI files; TODO/placeholder implementations are allowed in the controller first.

## 9. Acceptance Checklist (Codex Self-Check)

- The UI structure is strictly: MenuBar + (top AnalysisToolbar) + (upper Splitter) + (bottom Filmstrip).
- The image display area is a `QTabWidget`, and each tab title = file name.
- The right info area contains two tabs: Analysis/Metadata; the Analysis tab displays both the histogram and waveform at the same time (placeholders are acceptable).
- The bottom filmstrip is a horizontal thumbnail list, and clicking an item switches tabs.
- Tabs and filmstrip selected states are synchronized bidirectionally.
- The tab titles in the `image display area` are left-aligned (the tab label group is left-aligned and not stretched evenly to fill the width).
- No absolute positioning with `move()`/`resize()`.
- The `right info area` and `bottom filmstrip pane` can be hidden.
- Image file names are displayed in full in the `tab title`, `bottom filmstrip`, and hidden-filmstrip status summary.
- When the mouse pointer is at the boundary between the `image display area` and the `right info area`, the pointer `style` must automatically change to a `double arrow` (that is, a `move arrow`).
- Hovering the mouse over the `image display area` should immediately change the pointer to a `hand`, and holding the mouse button should allow dragging to pan a zoomed image.
