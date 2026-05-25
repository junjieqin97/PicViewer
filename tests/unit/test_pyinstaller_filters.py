from __future__ import annotations

import unittest

from scripts.packaging.pyinstaller_filters import filter_pyinstaller_analysis_toc


def _entry(destination: str) -> tuple[str, str, str]:
    return (destination, f"/source/{destination}", "BINARY")


def _destinations(entries: list[tuple[str, str, str]]) -> set[str]:
    return {entry[0] for entry in entries}


class PyInstallerFilterTests(unittest.TestCase):
    """Validate conservative PySide6 runtime pruning for packaged apps."""

    def test_filter_removes_unused_qt_network_runtime(self) -> None:
        entries = [
            _entry("PySide6/QtCore.cpython-310-darwin.so"),
            _entry("PySide6/QtNetwork.cpython-310-darwin.so"),
            _entry("libQt6Core.6.dylib"),
            _entry("libQt6Network.6.dylib"),
            _entry("pyexiv2/lib/exiv2api.so"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="darwin")

        self.assertEqual(
            {
                "PySide6/QtCore.cpython-310-darwin.so",
                "libQt6Core.6.dylib",
                "pyexiv2/lib/exiv2api.so",
            },
            _destinations(filtered),
        )

    def test_filter_removes_qt_network_and_tls_plugins(self) -> None:
        entries = [
            _entry("PySide6/Qt/plugins/networkinformation/libqscnetworkreachability.dylib"),
            _entry("PySide6/Qt/plugins/networkinformation/libqglib.dylib"),
            _entry("PySide6/Qt/plugins/tls/libqcertonlybackend.dylib"),
            _entry("PySide6/Qt/plugins/tls/libqopensslbackend.dylib"),
            _entry("PySide6/Qt/plugins/tls/libqsecuretransportbackend.dylib"),
            _entry("cv2/cv2.abi3.so"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="darwin")

        self.assertEqual({"cv2/cv2.abi3.so"}, _destinations(filtered))

    def test_filter_keeps_only_native_macos_platform_plugin(self) -> None:
        entries = [
            _entry("PySide6/Qt/plugins/platforms/libqcocoa.dylib"),
            _entry("PySide6/Qt/plugins/platforms/libqminimal.dylib"),
            _entry("PySide6/Qt/plugins/platforms/libqoffscreen.dylib"),
            _entry("PySide6/Qt/plugins/styles/libqmacstyle.dylib"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="darwin")

        self.assertEqual(
            {
                "PySide6/Qt/plugins/platforms/libqcocoa.dylib",
                "PySide6/Qt/plugins/styles/libqmacstyle.dylib",
            },
            _destinations(filtered),
        )

    def test_filter_keeps_only_windows_platform_plugin_on_windows(self) -> None:
        entries = [
            _entry("PySide6/Qt/plugins/platforms/qwindows.dll"),
            _entry("PySide6/Qt/plugins/platforms/qminimal.dll"),
            _entry("PySide6/Qt/plugins/platforms/qoffscreen.dll"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="win32")

        self.assertEqual({"PySide6/Qt/plugins/platforms/qwindows.dll"}, _destinations(filtered))

    def test_filter_keeps_linux_platform_plugins(self) -> None:
        entries = [
            _entry("PySide6/Qt/plugins/platforms/libqxcb.so"),
            _entry("PySide6/Qt/plugins/platforms/libqwayland-egl.so"),
            _entry("PySide6/Qt/plugins/platforms/libqoffscreen.so"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="linux")

        self.assertEqual(entries, filtered)

    def test_filter_keeps_only_svg_icon_and_image_plugins(self) -> None:
        entries = [
            _entry("PySide6/Qt/plugins/iconengines/libqsvgicon.dylib"),
            _entry("PySide6/Qt/plugins/imageformats/libqsvg.dylib"),
            _entry("PySide6/Qt/plugins/imageformats/libqjpeg.dylib"),
            _entry("PySide6/Qt/plugins/imageformats/libqgif.dylib"),
            _entry("PySide6/Qt/plugins/imageformats/libqtiff.dylib"),
            _entry("PySide6/Qt/plugins/imageformats/libqwebp.dylib"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="darwin")

        self.assertEqual(
            {
                "PySide6/Qt/plugins/iconengines/libqsvgicon.dylib",
                "PySide6/Qt/plugins/imageformats/libqsvg.dylib",
            },
            _destinations(filtered),
        )

    def test_filter_keeps_only_supported_qt_translations(self) -> None:
        entries = [
            _entry("PySide6/Qt/translations/qtbase_zh_CN.qm"),
            _entry("PySide6/Qt/translations/qt_zh_CN.qm"),
            _entry("PySide6/Qt/translations/qtbase_en.qm"),
            _entry("PySide6/Qt/translations/qt_en.qm"),
            _entry("PySide6/Qt/translations/qt_help_zh_CN.qm"),
            _entry("PySide6/Qt/translations/qtbase_de.qm"),
            _entry("PySide6/Qt/translations/qt_fr.qm"),
            _entry("pic_viewer/ui/resources/i18n/picviewer_zh_CN.qm"),
        ]

        filtered = filter_pyinstaller_analysis_toc(entries, platform="darwin")

        self.assertEqual(
            {
                "PySide6/Qt/translations/qtbase_zh_CN.qm",
                "PySide6/Qt/translations/qt_zh_CN.qm",
                "PySide6/Qt/translations/qtbase_en.qm",
                "PySide6/Qt/translations/qt_en.qm",
                "pic_viewer/ui/resources/i18n/picviewer_zh_CN.qm",
            },
            _destinations(filtered),
        )
