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
  - View: Zoom, Fit to Window, Show Metadata Overlay (checkable, checked = visible), Info Panel (checkable, checked = visible), Analysis Toolbar (checkable, checked = visible), Filmstrip Pane (checkable, checked = visible), Appearance (Light/Dark, mutually exclusive), Canvas Color (Pure White/18% Middle Gray/Deep Neutral Gray/Near-Black Neutral Gray/Pure Black, mutually exclusive and ordered from light to dark)
  - Tools: Histogram/Waveform options + pseudo color options + reference line options
    - Pseudo Color: Show Underexposed (checkable), Show Overexposed (checkable), Show Peaking (High/Medium/Low, checkable, three levels are mutually exclusive and clicking the current level turns it off)
    - Reference Lines: Crosshair Reference Line, Diagonal Reference Line, Rule-of-Thirds Grid Reference Line (all checkable; can be toggled independently and displayed as overlays together)
    - Color Readouts: Add Color Readout, Delete Color Readout (checkable tool modes; activating one deactivates the other, and clicking the active tool again exits the mode), Delete All Readouts (clears all readouts from the current image only)
    - Color Readouts Type: RGBL, HSB, HSL, Lab (mutually exclusive global session setting; RGBL is selected by default)
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
  - Add Color Readout, Delete Color Readout, Delete All Readouts
  - Show Metadata Overlay
- The Show Metadata Overlay button is pinned to the far right side of the toolbar. The centered analysis button group must remain visually centered by reserving equal space on the left side.
- The Show Metadata Overlay button is enabled by default. When enabled, the current image shows up to three metadata lines at the upper-left corner of the actual displayed image: camera/lens, exposure settings, and resolution. The camera name combines camera maker and camera model when both are available. Missing metadata fields are omitted instead of shown as placeholders. The text is drawn in semi-transparent white.
- The Add Color Readout, Delete Color Readout, and Delete All Readouts buttons reuse the corresponding `Tools > Color Readouts` actions. Add mode uses a plus-style cursor over the analyzed image and can add multiple persistent labels. Delete mode uses a minus-style cursor and removes a readout only when the user clicks an existing readout label. Delete All Readouts is a one-shot action that clears all readouts from the current image only. `Tools > Color Readouts Type` globally selects RGBL, HSB, HSL, or Lab for all existing and future labels during the current session. RGBL labels retain four unprefixed red, green, blue, and luma integer values with the existing channel colors. HSB/HSL labels use three prefixed values (`H n°`, `S n%`, and `B n%` or `L n%`). Lab labels use three prefixed integer D65 CIE L\*a\*b\* values (`L n`, `a n`, and `b n`). HSB, HSL, and Lab values use theme-aware neutral text. Labels use the active light/dark appearance style with a nearly transparent background.

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
- Loading state: while the selected image is still loading its full display payload, the image tab shows only centered `Loading...` text. Fast preview images must not be rendered inside the image tab; they are used only for the bottom filmstrip thumbnails.
- Naming rules:
- The display control inside a tab is named `viewImage` (if using `QGraphicsView`) or `lblImage` (if using `QLabel` as a placeholder).
- Context menu: right-clicking in the `image display area` opens a context menu containing `Zoom In`, `Zoom Out`, `Fit to Window`, and `Show in Folder`; zoom behavior must remain consistent with the `top menu bar` actions, and `Show in Folder` opens the current image's parent directory. See `5.2 MenuBar Actions`.
- Mouse wheel: scrolling up in the `image display area` performs `Zoom In`, and scrolling down performs `Zoom Out`; the implementation must reuse the zoom logic from the `top menu bar`.
- Canvas color: the area surrounding a loaded image uses an achromatic RGB background independent of the Light/Dark appearance theme. `View > Canvas Color` lists its options from light to dark: `Pure White` (`#FFFFFF`), `18% Middle Gray` (`#777777`), `Deep Neutral Gray` (`#202020`), `Near-Black Neutral Gray` (`#101010`), and `Pure Black` (`#000000`). `Deep Neutral Gray` is selected by default. The selection applies immediately to attached and detached image views, remains active when the appearance theme changes, and is kept only for the current application session. Empty, loading, and error states continue to use their appearance-theme backgrounds.

### 3.2 Right Info Area (Info Panel)

The right info area is a non-scrollable panel containing two top-level information categories: analysis and metadata. The "Analysis" panel combines the histogram and waveform to reduce tab switching when viewing analysis information. Histogram and waveform content are displayed at fixed sizes, while the metadata area adaptively fills the info area. Sizes are defined in logical pixels and automatically scale with DPI to keep proportions consistent across different resolutions.

- Container: `scrollInfo: QWidget` (outer layer is not scrollable)
- Content layout: `layoutInfo: QVBoxLayout`
- The top of the info area must start with `tabsInfo`; no separate summary panel is shown above the info tabs.

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

- Analysis: `tabAnalysis` contains a borderless `scrollAnalysis: QScrollArea` whose vertical scrollbar appears only when needed and whose horizontal scrollbar is disabled. The outer `scrollInfo` panel remains non-scrollable. `scrollAnalysis` owns a resizable `analysisScrollContent` widget with a vertical layout. From top to bottom, that layout displays the current source image color space status, the `Analysis Sample Precision` selector, a `Specify Image Color Space` selector, the `Rendering Intent` selector, the `Display Color Space` selector, the histogram, and the waveform. Both analysis charts remain centered horizontally, aligned near the top, and keep their fixed logical sizes. At short supported window heights, including `900 x 600`, users scroll only the Analysis page to reach the complete waveform. Analysis field titles and the source color-space value wrap when the available width is insufficient so their full text remains readable without horizontal scrolling.
  - `Analysis Sample Precision` uses `8-bit/channel` and `16-bit/channel (if available)`; `8-bit/channel` is selected by default. Choosing 16-bit preserves 16-bit/channel analysis only when the ICC-converted display source is 16-bit. 8-bit sources remain 8-bit and are not artificially expanded.
  - `Specify Image Color Space` uses `sRGB`, `Display P3`, `Adobe RGB (1998)`, `ProPhoto RGB`, startup-loaded system ICC profiles when supported, and `Choose a local ICC...`; `sRGB` is selected by default. System ICC profiles are inserted after the built-in presets and before the chooser entry. `Choose a local ICC...` opens a file dialog for `.icc` and `.icm` files, validates the profile, inserts the selected local profile before the chooser entry, and keeps it only for the current application session. It is a global fallback source color space selector used only when no embedded ICC profile is present, the embedded ICC profile cannot be read, or embedded ICC conversion fails. It is disabled with a gray style and blank visible text when the current image has a valid embedded ICC profile. For RAW images, it is disabled with a gray style and fixed visible text `ProPhoto RGB`; this per-image display state does not change the global fallback selection. It is restored to the selected fallback value when fallback, loading, failed, or empty states enable it again.
  - `Rendering Intent` uses `Perceptual`, `Relative Colorimetric`, `Saturation`, and `Absolute Colorimetric`; `Perceptual` is selected by default. It is a global ICC gamut mapping selector used for image-to-display-space conversion.
  - `Display Color Space` uses `sRGB`, `Display P3`, `Adobe RGB (1998)`, `ProPhoto RGB`, startup-loaded system ICC profiles when supported, and `Choose a local ICC...`; `sRGB` is selected by default. System ICC profiles are inserted after the built-in presets and before the chooser entry. `Choose a local ICC...` opens the same `.icc`/`.icm` file dialog, validates the profile, inserts the selected local profile before the chooser entry, and keeps it only for the current application session.
- Histogram: `widgetHistogram` (may initially be a `QLabel` with "Histogram Placeholder")
  - Fixed display size: height 100 x width 256 (logical pixels)
  - Above the histogram widget, `widgetPixelSampleValues` displays four numeric labels from left to right:
    - `labelPixelRedValue`: red channel value, shown in red.
    - `labelPixelGreenValue`: green channel value, shown in green.
    - `labelPixelBlueValue`: blue channel value, shown in blue.
    - `labelPixelLumaValue`: luma value, shown in white.
  - The four labels default to `-1`. When the mouse pointer is over the active analyzed image, they display the RGB and luma values for the image pixel under the pointer. When the pointer is outside the image, all four labels return to `-1`.
  - The luma readout uses the same luma definition as the luma histogram. When the luma value is not `-1`, the histogram displays a black vertical marker at that luma position.
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
- Lightweight filter toolbar: `widgetFilmstripFilterToolbar` sits above the thumbnail list and contains three single-select combo boxes:
  - `comboFilmstripExtensionFilter`: filters by file extension case-insensitively; suffixes are displayed in normalized lowercase form such as `.jpg`.
  - `comboFilmstripCameraFilter`: filters by camera model.
  - `comboFilmstripLensFilter`: filters by lens model.
  Each combo has an all-inclusive first item: `All Extensions`, `All Cameras`, and `All Lenses`.
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
- Filmstrip filters combine with AND semantics and only hide/show Filmstrip items. They must not close image tabs, cancel image loads, or remove cached image data.
- Camera and lens filter candidates are populated from metadata-only background scans and from full image load metadata. Missing or unreadable camera/lens metadata is grouped as `Unknown Camera` or `Unknown Lens`.
- If the current image is excluded by a newly selected filter and at least one image still matches, the current image switches to the first matching Filmstrip item. If no image matches, the Filmstrip selection is cleared and the current image view remains open.
- When the filmstrip pane is hidden, the right side of the status bar must display a current file summary in the format `Current: {name} ({index}/{total})`;
  `name` is the full file name, `index` and `total` count only currently visible filtered Filmstrip items, and the tooltip displays the full path. When the filmstrip pane is shown again or there is no current visible image, this summary must be hidden.
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
- `buttonToolbarAddColorReadout: QToolButton`
- `buttonToolbarDeleteColorReadout: QToolButton`
- `buttonToolbarDeleteAllColorReadouts: QToolButton`
- `buttonToolbarMetadataOverlay: QToolButton`
- `tabsInfo: DetachableTabWidget`
- `tabAnalysis: QWidget`
- `scrollAnalysis: QScrollArea`
- `analysisScrollContent: QWidget`
- `tabMetadata: QWidget`
- `widgetImageColorSpace: QWidget`
- `labelImageColorSpaceTitle: QLabel`
- `labelImageColorSpaceValue: QLabel`
- `widgetSpecifiedImageColorSpace: QWidget`
- `labelSpecifiedImageColorSpaceTitle: QLabel`
- `comboSpecifiedImageColorSpace: QComboBox`
- `widgetRenderingIntent: QWidget`
- `labelRenderingIntentTitle: QLabel`
- `comboRenderingIntent: QComboBox`
- `widgetDisplayColorSpace: QWidget`
- `labelDisplayColorSpaceTitle: QLabel`
- `comboDisplayColorSpace: QComboBox`
- `widgetPixelSampleValues: QWidget`
- `labelPixelRedValue: QLabel`
- `labelPixelGreenValue: QLabel`
- `labelPixelBlueValue: QLabel`
- `labelPixelLumaValue: QLabel`
- `frameFilmstrip: QFrame`
- `widgetFilmstripFilterToolbar: QWidget`
- `comboFilmstripExtensionFilter: QComboBox`
- `comboFilmstripCameraFilter: QComboBox`
- `comboFilmstripLensFilter: QComboBox`
- `listFilmstrip: QListWidget`
- `labelFilmstripSummary: QLabel` (right side of the status bar; displays the current file summary when the filmstrip pane is hidden)

### 5.2 MenuBar Actions (skeleton first)

Top-level menus: `menuFile` `menuView` `menuTools` `menuHelp`
Submenus: `menuAppearance` `menuCanvasColor`
Tools submenus: `menuColorReadouts` `menuColorReadoutsType`
Actions (names must be consistent; copy may mix Chinese and English, but consistency is recommended):

- `actOpenFile`: Open Image...
- `actOpenFolder`: Open Folder...
- `actCloseTab`: Close Current Tab
- `actExit`: Exit
- `actZoomIn`: Zoom In
- `actZoomOut`: Zoom Out
- `actFitToWindow`: Fit to Window
- `actShowInFolder`: Show in Folder (image context menu only)
- `actAppearanceLight`: Light (checkable, mutually exclusive with Dark)
- `actAppearanceDark`: Dark (checkable, mutually exclusive with Light)
- `actCanvasColorPureWhite`: Pure White (checkable, mutually exclusive with the other canvas colors)
- `actCanvasColorMiddleGray18`: 18% Middle Gray (checkable, mutually exclusive with the other canvas colors)
- `actCanvasColorDeepNeutral`: Deep Neutral Gray (checkable, mutually exclusive with the other canvas colors; selected by default)
- `actCanvasColorNearBlack`: Near-Black Neutral Gray (checkable, mutually exclusive with the other canvas colors)
- `actCanvasColorPureBlack`: Pure Black (checkable, mutually exclusive with the other canvas colors)
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
- `actAddColorReadout`: Add Color Readout (checkable)
- `actDeleteColorReadout`: Delete Color Readout (checkable)
- `actDeleteAllColorReadouts`: Delete All Readouts
- `actColorReadoutTypeRgbl`: RGBL (checkable, selected by default)
- `actColorReadoutTypeHsb`: HSB (checkable)
- `actColorReadoutTypeHsl`: HSL (checkable)
- `actColorReadoutTypeLab`: Lab (checkable)
- `actAbout`: About
- `actThirdPartyLicenses`: Third-Party Library License Information

## 6. Shortcuts

- Common features in the menu bar must have shortcuts.
- Shortcuts must support cross-platform use (`Windows`/`Linux`/`MacOS`).

Shortcuts for common features must be set as follows:

| Feature                       | Shortcut (Windows/Linux) | Shortcut (MacOS)        |
|-------------------------------|--------------------------|-------------------------|
| Open Image                    | `Ctrl + O`               | `Command + O`           |
| Open Folder                   | `Shift + Ctrl + O`       | `Shift + Command + O`   |
| Close Current Tab             | `Esc`                    | `Esc`                   |
| Show Metadata Overlay         | `Ctrl + I`               | `Command + I`           |
| Info Panel                    | `Ctrl + Right Arrow`     | `Command + Right Arrow` |
| Analysis Toolbar              | `Ctrl + Up Arrow`        | `Command + Up Arrow`    |
| Filmstrip Pane                | `Ctrl + Down Arrow`      | `Command + Down Arrow`  |
| Zoom In                       | `Ctrl + =`               | `Command + =`           |
| Zoom Out                      | `Ctrl + -`               | `Command + -`           |
| Fit to Window                 | `Ctrl + 0`               | `Command + 0`           |
| Luma Mode                     | `Ctrl + L`               | `Command + L`           |
| RGB Mode                      | `Ctrl + K`               | `Command + K`           |
| All RGB Channels              | `Ctrl + K`               | `Command + K`           |
| Red Channel Only              | `Ctrl + R`               | `Command + R`           |
| Green Channel Only            | `Ctrl + G`               | `Command + G`           |
| Blue Channel Only             | `Ctrl + B`               | `Command + B`           |
| Show Underexposed             | `Shift + Ctrl + P`       | `Shift + Command + P`   |
| Show Overexposed              | `Ctrl + P`               | `Command + P`           |
| Show Peaking (Low)            | `F1`                     | `F1`                    |
| Show Peaking (Medium)         | `F2`                     | `F2`                    |
| Show Peaking (High)           | `F3`                     | `F3`                    |
| Cross Reference Line          | `F5`                     | `F5`                    |
| Diagonal Reference Line       | `F6`                     | `F6`                    |
| Rule of Thirds Reference Line | `F7`                     | `F7`                    |
| Add Color Readout             | `Ctrl + ]`               | `Command + ]`           |
| Delete Color Readout          | `Ctrl + [`               | `Command + [`           |
| Delete All Readouts           | `Shift + Ctrl + [`       | `Shift + Command + [`   |

## 7. Interaction Rules (Synchronization Relationships That Must Be Implemented)

- Open Image => add a new tab + add a new filmstrip item + automatically switch to that tab.
- Switch image tab => update the right info area (placeholder update first) + update the selected filmstrip item; the currently selected image triggers full parsing in the background (histogram/waveform/metadata).
- Click filmstrip item => switch to the corresponding tab.
- Close tab => synchronously remove the corresponding filmstrip item; if the closed tab is the current tab, switch to an adjacent tab and synchronize updates.
- Open Folder => first load fast previews for each image concurrently for the filmstrip, then perform full parsing on demand (when selected). The selected image tab remains in the centered `Loading...` state until the full display payload is available.

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
- A loaded image is surrounded by the selected neutral canvas color in both appearance themes; switching the appearance theme preserves the canvas selection, and detached image views update immediately.
- Image file names are displayed in full in the `tab title`, `bottom filmstrip`, and hidden-filmstrip status summary.
- When the mouse pointer is at the boundary between the `image display area` and the `right info area`, the pointer `style` must automatically change to a `double arrow` (that is, a `move arrow`).
- Hovering the mouse over the `image display area` should immediately change the pointer to a `hand`, and holding the mouse button should allow dragging to pan a zoomed image.
- When Add Color Readout is active, hovering over a loaded analyzed image uses a plus-style cursor, and left-clicking a displayed image pixel adds a persistent readout label for that image. When Delete Color Readout is active, hovering uses a minus-style cursor, and left-clicking a readout label deletes only that label. Delete All Readouts clears every readout for the current image only and leaves other images' readouts unchanged. If the current image is not fully loaded, all Color Readouts actions are disabled. If the current image has no readouts, Delete Color Readout and Delete All Readouts are disabled, and Delete Color Readout mode is cleared.
- Color Readouts Type remains selectable when no image is loaded. RGBL is selected on startup, and changing to RGBL, HSB, HSL, or Lab immediately updates every existing fixed readout label across attached and detached image views without changing the hover sample display.
