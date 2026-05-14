"""Build the PicViewer desktop application with PyInstaller."""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

EXPECTED_CONDA_ENV = "PicViewer"


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


def build_app(
    project_root: Path,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., object] = subprocess.run,
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
