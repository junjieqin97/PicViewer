"""Verify that release builds use conda-forge pyvips/libvips runtime files."""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import logging
import os
from pathlib import Path
import sys
from typing import Optional, Sequence

logger = logging.getLogger(__name__)

PYVIPS_DIST_INFO_PATTERN = "pyvips-*.dist-info"


def verify_environment(
    site_packages: Optional[Path] = None,
    *,
    conda_prefix: Optional[Path] = None,
    platform: str = sys.platform,
) -> None:
    """Verify active environment pyvips metadata and native libvips files."""

    if site_packages is None:
        site_packages = _active_site_packages()
    if conda_prefix is None:
        conda_prefix_text = os.environ.get("CONDA_PREFIX")
        if not conda_prefix_text:
            raise RuntimeError("CONDA_PREFIX is required to verify the pyvips runtime.")
        conda_prefix = Path(conda_prefix_text)

    dist_info = _find_pyvips_dist_info(site_packages)
    _verify_conda_pyvips_metadata(dist_info)
    _require_environment_native_files(site_packages, conda_prefix, platform)


def verify_bundle(bundle_path: Path, *, platform: str = sys.platform) -> None:
    """Verify a PyInstaller bundle contains conda pyvips and libvips files."""

    bundle_root = Path(bundle_path)
    if not bundle_root.exists():
        raise RuntimeError(f"Bundle path does not exist: {bundle_root}.")

    dist_info = _find_pyvips_dist_info(bundle_root, recursive=True)
    _verify_conda_pyvips_metadata(dist_info)
    _require_bundle_native_files(bundle_root, platform)


def _active_site_packages() -> Path:
    distribution = importlib_metadata.distribution("pyvips")
    return Path(distribution.locate_file(""))


def _find_pyvips_dist_info(root: Path, recursive: bool = False) -> Path:
    pattern = f"**/{PYVIPS_DIST_INFO_PATTERN}" if recursive else PYVIPS_DIST_INFO_PATTERN
    matches = sorted(
        (path for path in root.glob(pattern) if path.is_dir()),
        key=lambda path: len(path.parts),
    )
    if not matches:
        raise RuntimeError(f"Cannot find pyvips dist-info under {root}.")
    return matches[0]


def _verify_conda_pyvips_metadata(dist_info: Path) -> None:
    installer = _read_dist_info_text(dist_info, "INSTALLER").strip().lower()
    if installer != "conda":
        raise RuntimeError(
            f"pyvips must be installed by conda, but {dist_info / 'INSTALLER'} contains {installer!r}."
        )

    wheel_text = _read_dist_info_text(dist_info, "WHEEL")
    root_is_purelib = _wheel_field(wheel_text, "Root-Is-Purelib").lower()
    if root_is_purelib != "false":
        raise RuntimeError("pyvips must not be a pure Python wheel in release builds.")


def _read_dist_info_text(dist_info: Path, file_name: str) -> str:
    path = dist_info / file_name
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Cannot read pyvips metadata file: {path}.") from exc


def _wheel_field(wheel_text: str, field_name: str) -> str:
    prefix = f"{field_name}:"
    for line in wheel_text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix).strip()
    raise RuntimeError(f"pyvips WHEEL metadata is missing {field_name}.")


def _require_environment_native_files(site_packages: Path, conda_prefix: Path, platform: str) -> None:
    if platform == "win32":
        library_bin = conda_prefix / "Library" / "bin"
        _require_any(site_packages, "_libvips*.pyd", "pyvips native extension")
        _require_any(library_bin, "vips-*.dll", "libvips DLL")
        _require_any(library_bin, "lcms2.dll", "LittleCMS DLL")
        return

    if platform == "darwin":
        conda_lib = conda_prefix / "lib"
        _require_any(site_packages, "_libvips*.so", "pyvips native extension")
        _require_any(conda_lib, "libvips*.dylib", "libvips dylib")
        _require_any(conda_lib, "liblcms2*.dylib", "LittleCMS dylib")
        return

    logger.info("Skipping platform-specific pyvips native file checks for %s.", platform)


def _require_bundle_native_files(bundle_root: Path, platform: str) -> None:
    if platform == "win32":
        internal = bundle_root / "_internal"
        _require_any(internal, "_libvips*.pyd", "bundled pyvips native extension")
        _require_any(internal, "vips-*.dll", "bundled libvips DLL")
        _require_any(internal, "lcms2.dll", "bundled LittleCMS DLL")
        return

    if platform == "darwin":
        _require_any(bundle_root, "**/_libvips*.so", "bundled pyvips native extension")
        _require_any(bundle_root, "**/libvips*.dylib", "bundled libvips dylib")
        _require_any(bundle_root, "**/liblcms2*.dylib", "bundled LittleCMS dylib")
        return

    logger.info("Skipping platform-specific bundled pyvips native file checks for %s.", platform)


def _require_any(root: Path, pattern: str, description: str) -> None:
    if any(root.glob(pattern)):
        return
    raise RuntimeError(f"Cannot find {description}: {root / pattern}.")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Verify conda pyvips/libvips runtime files.")
    parser.add_argument(
        "--environment",
        action="store_true",
        help="Verify the active conda environment's pyvips/libvips runtime.",
    )
    parser.add_argument(
        "--bundle",
        type=Path,
        help="Verify a PyInstaller app bundle or onedir output.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run pyvips runtime verification checks."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    if not args.environment and args.bundle is None:
        logger.error("Pass --environment or --bundle.")
        return 1

    try:
        if args.environment:
            verify_environment()
        if args.bundle is not None:
            verify_bundle(args.bundle)
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 1

    logger.info("pyvips/libvips runtime verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
