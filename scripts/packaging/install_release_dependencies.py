"""Install release dependencies with conda-forge first and PyPI fallback last."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Mapping, Optional, Sequence

try:
    from conda_cli import conda_executable
except ModuleNotFoundError:  # pragma: no cover - used when imported from tests
    from scripts.packaging.conda_cli import conda_executable

logger = logging.getLogger(__name__)

EXPECTED_CONDA_ENV = "PicViewer"
DEFAULT_QT_RUNTIME_VERSION = "6.11.1"
DEFAULT_PYVIPS_VERSION = "3.1.1"
DEFAULT_LIBVIPS_VERSION = "8.18.2"
DEFAULT_RAWPY_VERSION = "0.27.0"
PYEXIV2_FALLBACK_SPEC = "pyexiv2>=2.15.5,<3"


def python_executable() -> str:
    """Return the Python executable used for pip commands."""

    return sys.executable


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def ensure_conda_environment(env: Optional[Mapping[str, str]] = None) -> None:
    """Ensure release dependency installation runs inside the PicViewer conda env."""

    current_env = (os.environ if env is None else env).get("CONDA_DEFAULT_ENV")
    if current_env != EXPECTED_CONDA_ENV:
        raise RuntimeError(
            f"Activate the {EXPECTED_CONDA_ENV} conda environment before installing "
            f"release dependencies (current: {current_env or 'not set'})."
        )


def release_conda_packages(env: Optional[Mapping[str, str]] = None) -> list[str]:
    """Return conda-forge package specs for release builds."""

    source_env = os.environ if env is None else env
    qt_version = source_env.get("QT_RUNTIME_VERSION", DEFAULT_QT_RUNTIME_VERSION)
    pyvips_version = source_env.get("PYVIPS_VERSION", DEFAULT_PYVIPS_VERSION)
    libvips_version = source_env.get("LIBVIPS_VERSION", DEFAULT_LIBVIPS_VERSION)
    rawpy_version = source_env.get("RAWPY_VERSION", DEFAULT_RAWPY_VERSION)

    return [
        f"pyside6={qt_version}",
        f"qt6-main={qt_version}",
        f"pyvips={pyvips_version}",
        f"libvips={libvips_version}",
        f"rawpy={rawpy_version}",
        "opencv>=4.7,<5",
        "numpy>=1.23",
        "pillow>=10.0",
        "pillow-heif>=1,<2",
        "pillow-avif-plugin>=1.5,<2",
        "pyinstaller>=6.0",
        "python-build>=1.2",
        "twine>=5.0",
        "tomli>=2.0",
        "setuptools>=68.0",
        "wheel",
        "pip",
    ]


def install_release_dependencies(
    root: Path,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    """Install conda-forge release dependencies, then the PyPI-only fallback."""

    ensure_conda_environment(env)
    conda_command = [
        conda_executable(env),
        "install",
        "-y",
        "--override-channels",
        "-c",
        "conda-forge",
        *release_conda_packages(env),
    ]
    runner(conda_command, cwd=root, check=True)
    runner(
        [
            python_executable(),
            "-m",
            "pip",
            "install",
            "--no-deps",
            PYEXIV2_FALLBACK_SPEC,
        ],
        cwd=root,
        check=True,
    )
    runner(
        [
            python_executable(),
            "-m",
            "pip",
            "install",
            "-e",
            str(root),
            "--no-deps",
        ],
        cwd=root,
        check=True,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Install PicViewer release dependencies.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root(),
        help="Repository root. Defaults to the current PicViewer checkout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run release dependency installation."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        install_release_dependencies(args.project_root.resolve())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        logger.error("%s", exc)
        return 1

    logger.info("Release dependencies installed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
