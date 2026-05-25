"""Build Qt ``.qm`` translation files from PicViewer ``.ts`` files."""

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

TRANSLATION_PATTERN = "picviewer_*.ts"
CONDA_ENV_NAME = "PicViewer"
LRELEASE_NAMES = ("pyside6-lrelease", "lrelease")


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def default_translation_dir(root: Optional[Path] = None) -> Path:
    """Return the source translation directory."""

    base = project_root() if root is None else root
    return base / "src" / "pic_viewer" / "ui" / "resources" / "i18n"


def default_pyside6_tools_dir() -> Path:
    """Return the PySide6 tool directory in the default PicViewer conda env."""

    return (
        Path.home()
        / ".conda"
        / "envs"
        / CONDA_ENV_NAME
        / "Lib"
        / "site-packages"
        / "PySide6"
    )


def _site_packages_dir(prefix: Path) -> Path:
    """Return the platform-specific site-packages directory for a Python prefix."""

    if os.name == "nt":
        return prefix / "Lib" / "site-packages"
    return (
        prefix
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
    )


def _unique_paths(paths: Sequence[Path]) -> list[Path]:
    """Return paths without duplicates while preserving lookup order."""

    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path)
        if key not in seen:
            unique.append(path)
            seen.add(key)
    return unique


def default_lrelease_tool_dirs(env: Optional[Mapping[str, str]] = None) -> list[Path]:
    """Return fallback directories that can contain Qt lrelease executables.

    Conda-forge Qt packages may keep Qt command-line tools under the active
    environment prefix instead of exposing every executable on PATH.
    """

    current_env = os.environ if env is None else env
    prefixes: list[Path] = []
    conda_prefix = current_env.get("CONDA_PREFIX")
    if conda_prefix:
        prefixes.append(Path(conda_prefix))
    prefixes.append(Path(sys.prefix))

    tool_dirs: list[Path] = []
    for prefix in _unique_paths(prefixes):
        tool_dirs.extend(
            [
                prefix / "bin",
                prefix / "Scripts",
                prefix / "Library" / "bin",
                prefix / "lib" / "qt6" / "bin",
                prefix / "Library" / "lib" / "qt6" / "bin",
                _site_packages_dir(prefix) / "PySide6",
            ]
        )
    tool_dirs.append(default_pyside6_tools_dir())
    return _unique_paths(tool_dirs)


def lrelease_file_candidates(name: str) -> list[str]:
    """Return platform-appropriate executable file names for ``lrelease``."""

    if os.name == "nt" and not name.lower().endswith(".exe"):
        return [name, f"{name}.exe"]
    return [name]


def find_lrelease(
    explicit: Optional[str] = None,
    path_lookup: Callable[[str], Optional[str]] = shutil.which,
    pyside6_tools_dir: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
) -> str:
    """Resolve the Qt ``lrelease`` executable.

    Args:
        explicit: User-provided executable path or command name.
        path_lookup: Lookup function used for tests and PATH resolution.
        pyside6_tools_dir: Fallback PySide6 tools directory.
        env: Environment mapping used to resolve the active conda prefix.

    Returns:
        The executable path or command name to run.

    Raises:
        RuntimeError: If no ``lrelease`` executable can be found.
    """

    if explicit:
        return explicit

    for candidate in LRELEASE_NAMES:
        resolved = path_lookup(candidate)
        if resolved:
            return resolved

    search_dirs = (
        [pyside6_tools_dir]
        if pyside6_tools_dir is not None
        else default_lrelease_tool_dirs(env)
    )
    for tools_dir in search_dirs:
        for candidate in LRELEASE_NAMES:
            for file_name in lrelease_file_candidates(candidate):
                executable = tools_dir / file_name
                if executable.is_file():
                    return str(executable)

    searched = ", ".join(str(path) for path in search_dirs)
    raise RuntimeError(
        "Cannot find Qt lrelease. Install Qt/PySide6 tools, ensure lrelease is on "
        f"PATH, or place it in one of: {searched}."
    )


def discover_ts_files(ts_dir: Path) -> list[Path]:
    """Return translation source files in deterministic order."""

    if not ts_dir.is_dir():
        raise RuntimeError(f"Translation directory does not exist: {ts_dir}")

    files = sorted(ts_dir.glob(TRANSLATION_PATTERN))
    if not files:
        raise RuntimeError(f"No translation files found: {ts_dir / TRANSLATION_PATTERN}")
    return files


def build_qm(
    ts_dir: Path,
    out_dir: Path,
    lrelease: Optional[str] = None,
    runner: Callable[..., object] = subprocess.run,
) -> list[Path]:
    """Generate ``.qm`` files for every PicViewer translation source file."""

    executable = find_lrelease(lrelease)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    for ts_file in discover_ts_files(ts_dir):
        qm_file = out_dir / f"{ts_file.stem}.qm"
        command = [executable, str(ts_file), "-qm", str(qm_file)]
        logger.info("Generating translation: %s", qm_file)
        runner(command, check=True)
        generated.append(qm_file)

    return generated


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Build PicViewer Qt .qm translation files.")
    parser.add_argument(
        "--ts-dir",
        type=Path,
        default=default_translation_dir(),
        help="Directory containing picviewer_*.ts files.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Directory where generated .qm files are written. Defaults to --ts-dir.",
    )
    parser.add_argument(
        "--lrelease",
        default=None,
        help="Path or command name for Qt lrelease.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the translation build command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)
    out_dir = args.ts_dir if args.out_dir is None else args.out_dir

    try:
        generated = build_qm(args.ts_dir, out_dir, lrelease=args.lrelease)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        logger.error("%s", exc)
        return 1

    for qm_file in generated:
        logger.info("Generated: %s", qm_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
