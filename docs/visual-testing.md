# Visual regression checks

Run the principal-layout checks from the repository root:

```bash
conda activate PicViewer
python -m tests.visual.run
```

The independent runner checks all 32 combinations of 900 x 600 / 1200 x 800,
light / dark appearance, English / Simplified Chinese, empty / loaded state,
and 1x / 2x device pixel ratio. It exits nonzero if any case fails and continues
after individual failures. Each case has its own process and a 60-second timeout.
Do not run with Python optimization (`-O` or `PYTHONOPTIMIZE`), which disables
the assertions; the runner explicitly rejects this configuration.

## Environment and fixtures

Use the existing Python 3.10 Conda environment and project dependencies. Qt's
`lrelease` tool must be available through that environment. The runner compiles
the repository's real TS files into a temporary directory and installs the
requested translator before creating the window. Missing Chinese translations
or missing glyphs in checked text fail the run rather than silently falling
back to English. Install an OS Chinese font if glyph checks fail (for example,
PingFang SC on macOS, Microsoft YaHei on Windows, or Noto Sans CJK on Linux).

The runner selects Qt's offscreen platform and Fusion style to reduce host
window-manager variation. It sets the scale factor before QApplication creation,
clears conflicting scaling overrides, and verifies actual DPR, physical capture
dimensions, and loaded pixmap DPR. Host fonts are retained so unsupported fonts
are visible as failures. A native menu bar is disabled for the test window so
menus are included in captures on macOS as well.

Production MainWindowUI, MainController, image analysis and rendering are used.
Only background image/metadata scheduling and external I/O are isolated. A small
deterministic NumPy portrait and fixed metadata exercise the real load-result
delivery path, charts, metadata table, and Filmstrip without disk image fixtures,
system ICC discovery, or optional decoder backends.

## Assertions and evidence

- Check exact window sizes, toolbar/Filmstrip heights, control containment,
  non-overlapping chrome, filter alignment, and scroll-reachable Analysis fields
  and charts. Scrolling inside Analysis is intentional, not a clipping failure.
- Check state text fit, glyph support, painted ink and 4.5:1 contrast against
  the composited window background. Channel-colored pixel readouts are checked
  for fit separately. Long status/selector strings must retain full tooltips
  without growing beyond their available space.
- Check extra rendered focus-colored pixels with and without keyboard focus,
  and unchanged geometry, for tool buttons, push buttons, combo boxes, tab bars,
  metadata tables and Filmstrip items. Table/list checks also capture the current
  item independently of its container border. Hue tolerances accommodate dashed
  border anti-aliasing at both DPIs.
- Sample actual canvas pixels outside the portrait, checking the documented
  default and all five canvas selections before and after appearance changes.

Failures save `window.png`, `control.png`, `diagnostics.json`, and `worker.log`
under `build/visual-regression/<case>/`. Setup failures may have no window to
capture; crashes and timeouts still produce worker logs. Diagnostics include the
case parameters, Qt/QPA versions, font, DPR, current control and widget geometry.
`results.json` summarizes the current run. This directory is already covered by
the repository's `build/` ignore rule; images and QM files are not committed.

To capture passing scenes for manual review, or rerun one case:

```bash
python -m tests.visual.run --capture --output build/visual-review
python -m tests.visual.run --case 900x600-light-zh_CN-loaded-2x
python -m unittest tests.unit.test_visual_assertions tests.unit.test_visual_runner -v
python -m unittest discover -s tests/unit
```

Use a fresh `--output` directory when retaining evidence from multiple runs;
previous case artifacts are not deleted automatically. Negative-control unit
tests verify rejection of clipped geometry, unreadable contrast, absent focus,
wrong canvas colors, failed workers and timed-out workers.

## Coverage limits

These checks use rendered assertions, not whole-window golden images. They do
not detect every cosmetic change, replace human design review, or certify native
window-manager behavior, monitor ICC output, fractional DPI, detached-window
dragging, or every image codec. Loading/error transitions and detached-window
behavior remain covered by the existing unit tests. No release workflow is
changed; run this entry point explicitly when reviewing UI changes.
