from __future__ import annotations

import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from pic_viewer.app.services.app_metadata_service import load_app_metadata, resolve_app_version  # noqa: E402


class AppMetadataServiceTests(unittest.TestCase):
    def test_resolve_app_version_reads_project_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            (project_root / "pyproject.toml").write_text(
                '\n'.join(
                    (
                        "[project]",
                        'name = "picviewer"',
                        'version = "9.8.7"',
                        "",
                    )
                ),
                encoding="utf-8",
            )

            version = resolve_app_version(project_root=project_root)

        self.assertEqual("9.8.7", version)

    def test_resolve_app_version_matches_current_pyproject(self) -> None:
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        version = resolve_app_version(project_root=PROJECT_ROOT)

        self.assertIn(f'version = "{version}"', pyproject)

    def test_load_app_metadata_uses_picviewer_defaults(self) -> None:
        metadata = load_app_metadata(project_root=PROJECT_ROOT)

        self.assertEqual("PicViewer", metadata.name)
        self.assertEqual("junjieqin", metadata.copyright_owner)
        self.assertEqual(resolve_app_version(project_root=PROJECT_ROOT), metadata.version)

    def test_resolve_app_version_falls_back_to_package_metadata_for_invalid_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            (project_root / "pyproject.toml").write_text("[project]\nversion =\n", encoding="utf-8")

            with (
                self.assertLogs("pic_viewer.app.services.app_metadata_service", level="ERROR") as logs,
                patch("pic_viewer.app.services.app_metadata_service.metadata.version", return_value="2.3.4"),
            ):
                version = resolve_app_version(project_root=project_root)

        self.assertEqual("2.3.4", version)
        self.assertTrue(any("Failed to parse pyproject metadata" in message for message in logs.output))


if __name__ == "__main__":
    unittest.main()
