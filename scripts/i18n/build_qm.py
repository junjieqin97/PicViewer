"""Build Qt ``.qm`` translation files from PicViewer ``.ts`` files."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Optional, Sequence

logger = logging.getLogger(__name__)

TRANSLATION_PATTERN = "picviewer_*.ts"


def project_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def default_translation_dir(root: Optional[Path] = None) -> Path:
    """Return the source translation directory."""

    base = project_root() if root is None else root
    return base / "src" / "pic_viewer" / "ui" / "resources" / "i18n"


def find_lrelease(
    explicit: Optional[str] = None,
    path_lookup: Callable[[str], Optional[str]] = shutil.which,
) -> str:
    """Resolve the Qt ``lrelease`` executable.

    Args:
        explicit: User-provided executable path or command name.
        path_lookup: Lookup function used for tests and PATH resolution.

    Returns:
        The executable path or command name to run.

    Raises:
        RuntimeError: If no ``lrelease`` executable can be found.
    """

    if explicit:
        return explicit

    for candidate in ("lrelease", "lrelease-qt5"):
        resolved = path_lookup(candidate)
        if resolved:
            return resolved

    raise RuntimeError(
        "Cannot find Qt lrelease. Install Qt/PyQt tools and ensure lrelease is on PATH."
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
