"""Build the PicViewer desktop application with PyInstaller."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

EXPECTED_CONDA_ENV = "PicViewer"
APP_BUNDLE_NAME = "PicViewer.app"
WINDOWS_APP_DIR_NAME = "PicViewer"
WINDOWS_CV2_CONFIG = """import os

BINARIES_PATHS = [
    os.path.abspath(os.path.join(LOADER_DIR, os.pardir))
] + BINARIES_PATHS
"""
WINDOWS_CV2_CONFIG_3 = """import os

PYTHON_EXTENSIONS_PATHS = [
    os.path.join(LOADER_DIR, "python-3")
] + PYTHON_EXTENSIONS_PATHS
"""
MACOS_LIBVIPS_RUNTIME_DYLIBS = (
    "libglib-2.0.0.dylib",
    "libgobject-2.0.0.dylib",
    "libgmodule-2.0.0.dylib",
    "libgio-2.0.0.dylib",
    "libintl.8.dylib",
    "libpcre2-8.0.dylib",
)


def python_executable() -> str:
    """Return the Python executable used for packaging commands."""

    return sys.executable


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def ensure_conda_environment(env: Optional[Mapping[str, str]] = None) -> None:
    """Ensure PyInstaller runs inside the PicViewer conda environment."""

    current_env = (os.environ if env is None else env).get("CONDA_DEFAULT_ENV")
    if current_env != EXPECTED_CONDA_ENV:
        raise RuntimeError(
            f"Activate the {EXPECTED_CONDA_ENV} conda environment before packaging "
            f"(current: {current_env or 'not set'})."
        )


def normalize_windows_cv2_runtime_config(
    app_path: Path,
    platform: str = sys.platform,
) -> bool:
    """Rewrite conda OpenCV loader paths to the bundled Windows app layout."""

    if platform != "win32":
        return False

    cv2_dir = app_path / "_internal" / "cv2"
    extension_path = cv2_dir / "python-3" / "cv2.pyd"
    if not extension_path.is_file():
        raise RuntimeError(f"Missing bundled OpenCV extension: {extension_path}.")

    _write_text_if_changed(cv2_dir / "config.py", WINDOWS_CV2_CONFIG)
    _write_text_if_changed(cv2_dir / "config-3.py", WINDOWS_CV2_CONFIG_3)
    logger.info("Normalized Windows OpenCV runtime config: %s", cv2_dir)
    return True


def _write_text_if_changed(path: Path, content: str) -> bool:
    try:
        existing = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing bundled OpenCV loader config: {path}.") from exc
    except OSError as exc:
        raise RuntimeError(f"Cannot read bundled OpenCV loader config: {path}.") from exc

    if existing == content:
        return False

    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise RuntimeError(f"Cannot write bundled OpenCV loader config: {path}.") from exc
    return True


def normalize_macos_libvips_runtime_dylibs(
    app_path: Path,
    conda_prefix: Path,
    platform: str = sys.platform,
) -> bool:
    """Replace macOS libvips GLib runtime symlinks with conda dylib copies."""

    if platform != "darwin":
        return False

    frameworks_dir = app_path / "Contents" / "Frameworks"
    if not frameworks_dir.is_dir():
        raise RuntimeError(f"Missing app Frameworks directory: {frameworks_dir}.")

    changed = False
    conda_lib_dir = conda_prefix / "lib"
    for library_name in MACOS_LIBVIPS_RUNTIME_DYLIBS:
        source = conda_lib_dir / library_name
        target = frameworks_dir / library_name
        if not source.exists():
            if target.is_symlink():
                raise RuntimeError(f"Missing conda runtime library required by libvips: {source}.")
            continue
        if not target.exists() and not target.is_symlink():
            continue

        if target.is_symlink() or not _same_file_bytes(source, target):
            if target.is_dir() and not target.is_symlink():
                raise RuntimeError(f"Cannot replace directory with runtime dylib: {target}.")
            target.unlink()
            shutil.copy2(source, target)
            changed = True
            logger.info("Normalized macOS libvips runtime dylib: %s", target)
    return changed


def _same_file_bytes(first: Path, second: Path) -> bool:
    try:
        return first.read_bytes() == second.read_bytes()
    except OSError:
        return False


def resign_macos_app_bundle(
    app_path: Path,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    """Re-sign a macOS app bundle after post-processing native libraries."""

    runner(["codesign", "--force", "--sign", "-", "--deep", str(app_path)], check=True)


def build_app(
    project_root: Path,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., object] = subprocess.run,
    platform: str = sys.platform,
) -> None:
    """Generate translations and build the platform-native PyInstaller app."""

    ensure_conda_environment(env)
    build_qm_script = project_root / "scripts" / "i18n" / "build_qm.py"
    spec_file = project_root / "packaging" / "pyinstaller" / "PicViewer.spec"
    command_env = os.environ.copy()
    if env is not None:
        command_env.update(env)
    command_env["PYINSTALLER_CONFIG_DIR"] = str(project_root / "build" / "pyinstaller-cache")

    runner([python_executable(), str(build_qm_script)], cwd=project_root, check=True)
    runner(
        [
            python_executable(),
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(spec_file),
        ],
        cwd=project_root,
        env=command_env,
        check=True,
    )
    if platform == "win32":
        app_path = project_root / "dist" / WINDOWS_APP_DIR_NAME
        normalize_windows_cv2_runtime_config(app_path, platform)
    if platform == "darwin":
        conda_prefix = Path(command_env.get("CONDA_PREFIX") or sys.prefix)
        app_path = project_root / "dist" / APP_BUNDLE_NAME
        if normalize_macos_libvips_runtime_dylibs(app_path, conda_prefix, platform):
            resign_macos_app_bundle(app_path, runner)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build the PicViewer desktop app.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root(),
        help="Repository root. Defaults to the current PicViewer checkout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the PyInstaller build command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        build_app(args.project_root.resolve())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        logger.error("%s", exc)
        return 1

    logger.info("Desktop app artifacts written to: %s", args.project_root / "dist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
