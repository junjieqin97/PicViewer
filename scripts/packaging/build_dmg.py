"""Build a macOS DMG from the existing PicViewer.app bundle."""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Optional, Sequence

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python 3.9/3.10.
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

logger = logging.getLogger(__name__)

EXPECTED_CONDA_ENV = "PicViewer"
APP_NAME = "PicViewer"


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def ensure_conda_environment(env: Optional[Mapping[str, str]] = None) -> None:
    """Ensure DMG packaging runs inside the PicViewer conda environment."""

    current_env = (os.environ if env is None else env).get("CONDA_DEFAULT_ENV")
    if current_env != EXPECTED_CONDA_ENV:
        raise RuntimeError(
            f"Activate the {EXPECTED_CONDA_ENV} conda environment before packaging "
            f"(current: {current_env or 'not set'})."
        )


def ensure_macos(platform: str = sys.platform) -> None:
    """Ensure the DMG build is running on macOS."""

    if platform != "darwin":
        raise RuntimeError("DMG packaging is only supported on macOS.")


def read_project_version(pyproject_path: Path) -> str:
    """Read the project version from pyproject.toml."""

    with pyproject_path.open("rb") as file_obj:
        pyproject = tomllib.load(file_obj)

    version = pyproject.get("project", {}).get("version")
    if not isinstance(version, str) or not version:
        raise RuntimeError(f"Cannot read project.version from {pyproject_path}.")
    return version


def remove_path(path: Path) -> None:
    """Remove a generated file, directory, or symlink if it exists."""

    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        logger.info("Removed directory: %s", path)
    elif path.exists() or path.is_symlink():
        path.unlink()
        logger.info("Removed file: %s", path)


def ensure_app_bundle(app_path: Path) -> None:
    """Ensure the PyInstaller app bundle exists before creating a DMG."""

    if not app_path.is_dir():
        raise RuntimeError(
            f"Missing app bundle: {app_path}. Run python scripts/packaging/build_app.py first."
        )


def create_applications_symlink(link_path: Path) -> None:
    """Create the Applications shortcut expected in a macOS DMG."""

    link_path.symlink_to("/Applications", target_is_directory=True)


def stage_dmg_contents(
    root: Path,
    app_path: Path,
    applications_linker: Callable[[Path], None] = create_applications_symlink,
) -> Path:
    """Prepare the DMG staging directory with the app and Applications shortcut."""

    staging_dir = root / "build" / "dmg" / "staging"
    remove_path(staging_dir)
    staging_dir.mkdir(parents=True, exist_ok=True)

    shutil.copytree(app_path, staging_dir / f"{APP_NAME}.app", symlinks=True)
    applications_linker(staging_dir / "Applications")
    return staging_dir


def write_sha256_checksum(dmg_path: Path) -> Path:
    """Write a SHA256 checksum file next to a generated DMG.

    Args:
        dmg_path: Path to the DMG file to hash.

    Returns:
        Path to the generated checksum file.

    Raises:
        RuntimeError: If the DMG cannot be read or the checksum file cannot be
            written.
    """

    checksum_path = dmg_path.with_name(f"{dmg_path.name}.sha256")
    sha256 = hashlib.sha256()

    try:
        with dmg_path.open("rb") as file_obj:
            for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
                sha256.update(chunk)

        checksum_path.write_text(
            f"{sha256.hexdigest()}  {dmg_path.name}\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise RuntimeError(
            f"Cannot write SHA256 checksum for DMG: {dmg_path}."
        ) from exc

    logger.info("SHA256 checksum written to: %s", checksum_path)
    return checksum_path


def build_dmg(
    project_root: Path,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., object] = subprocess.run,
    platform: str = sys.platform,
    applications_linker: Callable[[Path], None] = create_applications_symlink,
) -> Path:
    """Create a compressed macOS DMG from dist/PicViewer.app."""

    ensure_conda_environment(env)
    ensure_macos(platform)

    dist_dir = project_root / "dist"
    app_path = dist_dir / f"{APP_NAME}.app"
    ensure_app_bundle(app_path)

    version = read_project_version(project_root / "pyproject.toml")
    dmg_path = dist_dir / f"{APP_NAME}-{version}.dmg"
    staging_dir = stage_dmg_contents(project_root, app_path, applications_linker)

    runner(
        [
            "hdiutil",
            "create",
            "-volname",
            APP_NAME,
            "-srcfolder",
            str(staging_dir),
            "-ov",
            "-format",
            "UDZO",
            str(dmg_path),
        ],
        cwd=project_root,
        check=True,
    )
    write_sha256_checksum(dmg_path)
    return dmg_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build the PicViewer macOS DMG.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root(),
        help="Repository root. Defaults to the current PicViewer checkout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the DMG build command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        dmg_path = build_dmg(args.project_root.resolve())
    except (RuntimeError, subprocess.CalledProcessError, OSError) as exc:
        logger.error("%s", exc)
        return 1

    logger.info("DMG artifact written to: %s", dmg_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
