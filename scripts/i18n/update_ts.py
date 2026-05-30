"""Update Qt ``.ts`` translation files from PicViewer Python sources."""

from __future__ import annotations

import argparse
import ast
import logging
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Callable, NamedTuple, Optional, Sequence
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

TRANSLATION_PATTERN = "picviewer_*.ts"
TARGET_TRANSLATION_FILES = ("picviewer_zh_CN.ts", "picviewer_en.ts")
LUPDATE_NAMES = ("pyside6-lupdate",)


class TranslationLocation(NamedTuple):
    """A source location for one translatable message."""

    filename: str
    line: int


class TranslationEntry:
    """A translatable message and all source locations where it appears."""

    def __init__(
        self,
        context: str,
        source: str,
        locations: Optional[list[TranslationLocation]] = None,
    ) -> None:
        self.context = context
        self.source = source
        self.locations = [] if locations is None else locations


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

    raise RuntimeError("Cannot find PySide6 lupdate. Install PySide6 tools or pass --lupdate explicitly.")


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


def literal_string(node: ast.AST) -> Optional[str]:
    """Return a string literal value from an AST node, if present."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


class TranslationExtractor(ast.NodeVisitor):
    """Extract PicViewer translation calls from Python source."""

    def __init__(self, filename: str) -> None:
        self._filename = filename
        self._class_stack: list[str] = []
        self.entries: list[TranslationEntry] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        self._extract_helper_call(node)
        self._extract_qt_translate_call(node)
        self.generic_visit(node)

    def _extract_helper_call(self, node: ast.Call) -> None:
        if not node.args:
            return

        source = literal_string(node.args[0])
        if source is None:
            return

        context = self._current_context()
        if context is None:
            return

        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "_tr" and isinstance(func.value, ast.Name):
            if func.value.id == "self":
                self._add_entry(context, source, node.lineno)
        elif isinstance(func, ast.Name) and func.id == "_tr":
            self._add_entry(context, source, node.lineno)

    def _extract_qt_translate_call(self, node: ast.Call) -> None:
        if len(node.args) < 2:
            return

        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "translate":
            return

        context = literal_string(node.args[0])
        source = literal_string(node.args[1])
        if context is None or source is None:
            return

        self._add_entry(context, source, node.lineno)

    def _current_context(self) -> Optional[str]:
        if not self._class_stack:
            return None
        return self._class_stack[-1]

    def _add_entry(self, context: str, source: str, line: int) -> None:
        self.entries.append(
            TranslationEntry(
                context=context,
                source=source,
                locations=[TranslationLocation(filename=self._filename, line=line)],
            )
        )


def extract_translation_entries(source_files: Sequence[Path]) -> list[TranslationEntry]:
    """Extract and de-duplicate translatable messages from Python sources."""

    ordered: list[TranslationEntry] = []
    by_key: dict[tuple[str, str], TranslationEntry] = {}
    for source_file in source_files:
        source_text = source_file.read_text(encoding="utf-8")
        tree = ast.parse(source_text, filename=str(source_file))
        extractor = TranslationExtractor(source_file.name)
        extractor.visit(tree)
        for entry in extractor.entries:
            key = (entry.context, entry.source)
            existing = by_key.get(key)
            if existing is None:
                by_key[key] = entry
                ordered.append(entry)
            else:
                existing.locations.extend(entry.locations)
    return ordered


def existing_translations(ts_file: Path) -> dict[tuple[str, str], tuple[str, dict[str, str]]]:
    """Return existing translations keyed by context and source text."""

    root = ET.parse(ts_file).getroot()
    translations: dict[tuple[str, str], tuple[str, dict[str, str]]] = {}
    for context in root.findall("context"):
        context_name = context.findtext("name")
        if context_name is None:
            continue
        for message in context.findall("message"):
            source = message.findtext("source")
            translation = message.find("translation")
            if source is None or translation is None:
                continue
            translations[(context_name, source)] = (translation.text or "", dict(translation.attrib))
    return translations


def ts_language(ts_file: Path) -> str:
    """Return the language attribute from an existing TS file."""

    return ET.parse(ts_file).getroot().get("language", "")


def group_entries_by_context(entries: Sequence[TranslationEntry]) -> dict[str, list[TranslationEntry]]:
    """Group extracted translation entries by context, preserving discovery order."""

    grouped: dict[str, list[TranslationEntry]] = {}
    for entry in entries:
        grouped.setdefault(entry.context, []).append(entry)
    return grouped


def default_translation(source: str, language: str) -> tuple[str, dict[str, str]]:
    """Return the default translation value for a newly discovered source."""

    if language.startswith("en"):
        return source, {}
    return "", {"type": "unfinished"}


def write_ts_file(ts_file: Path, entries: Sequence[TranslationEntry]) -> None:
    """Write one TS file while preserving existing translations where possible."""

    language = ts_language(ts_file)
    existing = existing_translations(ts_file)
    root = ET.Element("TS", {"version": "1.1", "language": language})

    for context_name, context_entries in group_entries_by_context(entries).items():
        context_element = ET.SubElement(root, "context")
        ET.SubElement(context_element, "name").text = context_name
        for entry in context_entries:
            message_element = ET.SubElement(context_element, "message")
            for location in entry.locations:
                ET.SubElement(
                    message_element,
                    "location",
                    {"filename": location.filename, "line": str(location.line)},
                )
            ET.SubElement(message_element, "source").text = entry.source
            translation_text, translation_attrs = existing.get(
                (entry.context, entry.source),
                default_translation(entry.source, language),
            )
            translation_element = ET.SubElement(message_element, "translation", translation_attrs)
            translation_element.text = translation_text

    ET.indent(root, space="    ")
    tree = ET.ElementTree(root)
    with ts_file.open("wb") as file:
        file.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        file.write(b"<!DOCTYPE TS>\n")
        tree.write(file, encoding="utf-8", xml_declaration=False)
        file.write(b"\n")


def update_ts_with_python(src_dir: Path, ts_dir: Path) -> list[Path]:
    """Update TS files using the built-in Python source extractor."""

    source_files = discover_python_files(src_dir)
    ts_files = discover_ts_files(ts_dir)
    ensure_required_translation_files(ts_files)
    entries = extract_translation_entries(source_files)

    updated_files: list[Path] = []
    for file_name in TARGET_TRANSLATION_FILES:
        target_file = ts_dir / file_name
        write_ts_file(target_file, entries)
        updated_files.append(target_file)
    return updated_files


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
    if lupdate is None:
        logger.info("Updating translation files with the built-in Python extractor: %s", translation_dir)
        return update_ts_with_python(source_dir, translation_dir)

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
        help="Optional path or command name for PySide6 lupdate. Defaults to the built-in Python extractor.",
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
