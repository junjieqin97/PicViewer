from __future__ import annotations

import importlib
import unittest

from PySide6 import QtWidgets
import shiboken6


class QtTestUtilsTests(unittest.TestCase):
    """Validate shared Qt test lifecycle helpers."""

    def test_qt_widget_test_case_flushes_deferred_delete_after_cleanups(self) -> None:
        try:
            from tests.unit.qt_test_utils import QtWidgetTestCase
        except ModuleNotFoundError as exc:
            self.fail(f"Missing shared Qt widget test base: {exc}")

        cleaned_widgets: list[QtWidgets.QWidget] = []

        class ProbeTest(QtWidgetTestCase):
            def runTest(self) -> None:
                widget = QtWidgets.QWidget()
                cleaned_widgets.append(widget)
                self.addCleanup(widget.deleteLater)

        result = unittest.TestResult()
        ProbeTest().run(result)

        self.assertEqual([], result.errors)
        self.assertEqual([], result.failures)
        self.assertFalse(shiboken6.isValid(cleaned_widgets[0]))

    def test_qt_widget_tests_use_shared_cleanup_base(self) -> None:
        try:
            from tests.unit.qt_test_utils import QtWidgetTestCase
        except ModuleNotFoundError as exc:
            self.fail(f"Missing shared Qt widget test base: {exc}")

        qt_test_cases = (
            ("test_about_dialog", "AboutDialogTests"),
            ("test_analysis_toolbar", "AnalysisToolbarTests"),
            ("test_app_icon_resources", "AppIconResourceTests"),
            ("test_combo_popup_delegate", "ComboPopupItemDelegateTests"),
            ("test_display_color_space_controller", "DisplayColorSpaceControllerTests"),
            ("test_image_display_label", "ImageDisplayLabelTests"),
            ("test_image_load_states", "ImageLoadStateTests"),
            ("test_image_load_states", "InfoPanelLoadStateTests"),
            ("test_image_qt", "ImageQtColorSpaceTests"),
            ("test_main_controller_clipping_toggle", "MainControllerClippingToggleTests"),
            ("test_main_controller_reference_lines", "MainControllerReferenceLineTests"),
            ("test_main_window_reference_lines", "MainWindowReferenceLineTests"),
            ("test_main_window_shortcuts", "MainWindowShortcutTests"),
            ("test_main_window_tabs", "MainWindowTabsTests"),
            ("test_show_in_folder_action", "ShowInFolderActionTests"),
            ("test_third_party_license_dialog", "ThirdPartyLicenseDialogTests"),
            ("test_ui_styles", "UiStylesTests"),
            ("test_zoom_feedback", "MainControllerZoomFeedbackTests"),
        )

        for module_name, class_name in qt_test_cases:
            with self.subTest(test_case=f"{module_name}.{class_name}"):
                module = importlib.import_module(f"tests.unit.{module_name}")
                test_case = getattr(module, class_name)

                self.assertTrue(
                    issubclass(test_case, QtWidgetTestCase),
                    f"{module_name}.{class_name} must inherit QtWidgetTestCase.",
                )


if __name__ == "__main__":
    unittest.main()
