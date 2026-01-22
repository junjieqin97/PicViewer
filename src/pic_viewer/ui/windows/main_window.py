"""Backwards-compatible import for the main window.

ui.md 规范要求使用 `pic_viewer.ui.main_window`；这里保留旧路径避免其他代码引用出错。
"""

from pic_viewer.ui.main_window import MainWindow
