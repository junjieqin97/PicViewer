"""Build PicViewer source and wheel distributions."""

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


def python_executable() -> str:
    """Return the Python executable used for packaging commands."""

    return sys.executable


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def ensure_conda_environment(env: Optional[Mapping[str, str]] = None) -> None:
    """Ensure packaging runs inside the PicViewer conda environment."""

    current_env = (os.environ if env is None else env).get("CONDA_DEFAULT_ENV")
    if current_env != EXPECTED_CONDA_ENV:
        raise RuntimeError(
            f"Activate the {EXPECTED_CONDA_ENV} conda environment before packaging "
            f"(current: {current_env or 'not set'})."
        )


def remove_path(path: Path) -> None:
    """Remove a generated file or directory if it exists."""

    if path.is_dir():
        shutil.rmtree(path)
        logger.info("Removed directory: %s", path)
    elif path.exists():
        path.unlink()
        logger.info("Removed file: %s", path)


def clean_build_outputs(root: Path) -> None:
    """Remove generated Python packaging outputs."""

    remove_path(root / "dist")
    remove_path(root / "build")
    remove_path(root / "src" / "picviewer.egg-info")


def build_python_package(
    root: Path,
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., object] = subprocess.run,
) -> None:
    """Generate translation resources and build Python distributions."""

    ensure_conda_environment(env)
    build_qm_script = root / "scripts" / "i18n" / "build_qm.py"
    runner([python_executable(), str(build_qm_script)], cwd=root, check=True)
    clean_build_outputs(root)
    runner([python_executable(), "-m", "build"], cwd=root, check=True)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build PicViewer Python package artifacts.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=project_root(),
        help="Repository root. Defaults to the current PicViewer checkout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the Python package build command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        build_python_package(args.project_root.resolve())
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        logger.error("%s", exc)
        return 1

    logger.info("Python package artifacts written to: %s", args.project_root / "dist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
