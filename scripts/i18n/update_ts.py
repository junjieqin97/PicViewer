"""Update Qt ``.ts`` translation files from PicViewer Python sources."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Callable, Optional, Sequence

logger = logging.getLogger(__name__)

TRANSLATION_PATTERN = "picviewer_*.ts"
TARGET_TRANSLATION_FILES = ("picviewer_zh_CN.ts", "picviewer_en.ts")
LUPDATE_NAMES = ("pyside6-lupdate", "lupdate")


def repository_root() -> Path:
    """Return the repository root for this script."""

    return Path(__file__).resolve().parents[2]


def project_root() -> Path:
    """Return the repository root for compatibility with other scripts."""

    return repository_root()


def default_source_dir(root: Optional[Path] = None) -> Path:
    """Return the default Python source directory."""

    base = repository_root() if root is None else root
    return base / "src" / "pic_viewer"


def default_translation_dir(root: Optional[Path] = None) -> Path:
    """Return the default translation source directory."""

    base = repository_root() if root is None else root
    return base / "src" / "pic_viewer" / "ui" / "resources" / "i18n"


def find_lupdate(
    explicit: Optional[str] = None,
    path_lookup: Callable[[str], Optional[str]] = shutil.which,
) -> str:
    """Resolve the Qt ``lupdate`` executable."""

    if explicit:
        return explicit

    for candidate in LUPDATE_NAMES:
        resolved = path_lookup(candidate)
        if resolved:
            return resolved

    raise RuntimeError("Cannot find Qt lupdate. Install PySide6 tools or ensure pyside6-lupdate is on PATH.")


def discover_python_files(src_dir: Path) -> list[Path]:
    """Return Python source files in deterministic order."""

    if not src_dir.is_dir():
        raise RuntimeError(f"Source directory does not exist: {src_dir}")

    files = sorted(src_dir.rglob("*.py"))
    if not files:
        raise RuntimeError(f"No Python source files found: {src_dir}")
    return files


def discover_ts_files(ts_dir: Path) -> list[Path]:
    """Return existing PicViewer translation source files."""

    if not ts_dir.is_dir():
        raise RuntimeError(f"Translation directory does not exist: {ts_dir}")

    files = sorted(ts_dir.glob(TRANSLATION_PATTERN))
    if not files:
        raise RuntimeError(f"No translation files found: {ts_dir / TRANSLATION_PATTERN}")
    return files


def ensure_required_translation_files(ts_files: Sequence[Path]) -> None:
    """Ensure the required target language files exist before updating."""

    existing_names = {ts_file.name for ts_file in ts_files}
    missing = [file_name for file_name in TARGET_TRANSLATION_FILES if file_name not in existing_names]
    if missing:
        raise RuntimeError(f"Missing required translation files: {', '.join(missing)}")


def transform_python_source(source: str) -> str:
    """Convert PicViewer translation helpers into forms recognized by lupdate."""

    transformed = re.sub(r"\bself\._tr\(", "self.tr(", source)
    return re.sub(r"\b_tr\(", "tr(", transformed)


def copy_shadow_sources(src_dir: Path, shadow_src_dir: Path, source_files: Sequence[Path]) -> list[Path]:
    """Copy transformed Python sources into the temporary shadow source tree."""

    shadow_files: list[Path] = []
    for source_file in source_files:
        relative_path = source_file.relative_to(src_dir)
        shadow_file = shadow_src_dir / relative_path
        shadow_file.parent.mkdir(parents=True, exist_ok=True)
        source_text = source_file.read_text(encoding="utf-8")
        shadow_file.write_text(transform_python_source(source_text), encoding="utf-8")
        shadow_files.append(shadow_file)
    return shadow_files


def copy_shadow_translations(ts_files: Sequence[Path], shadow_ts_dir: Path) -> None:
    """Copy existing translation files into the temporary shadow tree."""

    shadow_ts_dir.mkdir(parents=True, exist_ok=True)
    for ts_file in ts_files:
        shutil.copy2(ts_file, shadow_ts_dir / ts_file.name)


def update_ts(
    project_root: Optional[Path] = None,
    src_dir: Optional[Path] = None,
    ts_dir: Optional[Path] = None,
    lupdate: Optional[str] = None,
    runner: Callable[..., object] = subprocess.run,
) -> list[Path]:
    """Update PicViewer translation source files with Qt ``lupdate``."""

    root = project_root if project_root is not None else repository_root()
    source_dir = src_dir if src_dir is not None else default_source_dir(root)
    translation_dir = ts_dir if ts_dir is not None else default_translation_dir(root)
    source_files = discover_python_files(source_dir)
    ts_files = discover_ts_files(translation_dir)
    ensure_required_translation_files(ts_files)
    executable = find_lupdate(lupdate)

    with tempfile.TemporaryDirectory() as temp_dir:
        shadow_src_dir = Path(temp_dir) / "src" / "pic_viewer"
        shadow_ts_dir = shadow_src_dir / "ui" / "resources" / "i18n"
        copy_shadow_translations(ts_files, shadow_ts_dir)
        shadow_sources = copy_shadow_sources(source_dir, shadow_src_dir, source_files)
        shadow_targets = [shadow_ts_dir / file_name for file_name in TARGET_TRANSLATION_FILES]
        command = [executable, "-noobsolete", *(str(path) for path in shadow_sources), "-ts"]
        command.extend(str(path) for path in shadow_targets)
        logger.info("Updating translation files in: %s", translation_dir)
        runner(command, check=True)

        updated_files: list[Path] = []
        for file_name in TARGET_TRANSLATION_FILES:
            target_file = translation_dir / file_name
            shutil.copy2(shadow_ts_dir / file_name, target_file)
            updated_files.append(target_file)
        return updated_files


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Update PicViewer Qt .ts translation files.")
    parser.add_argument(
        "--project-root",
        type=Path,
        default=repository_root(),
        help="Repository root. Defaults to the current PicViewer checkout.",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=None,
        help="Directory containing PicViewer Python source files. Defaults to <project-root>/src/pic_viewer.",
    )
    parser.add_argument(
        "--ts-dir",
        type=Path,
        default=None,
        help="Directory containing picviewer_*.ts files. Defaults to <project-root>/src/pic_viewer/ui/resources/i18n.",
    )
    parser.add_argument(
        "--lupdate",
        default=None,
        help="Path or command name for Qt lupdate.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the translation update command."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args(argv)

    try:
        updated_files = update_ts(
            project_root=args.project_root.resolve(),
            src_dir=args.src_dir,
            ts_dir=args.ts_dir,
            lupdate=args.lupdate,
        )
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        logger.error("%s", exc)
        return 1

    for ts_file in updated_files:
        logger.info("Updated: %s", ts_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
