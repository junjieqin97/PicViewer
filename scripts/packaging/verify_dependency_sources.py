"""Verify release dependency sources after conda-forge-first installation."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
from typing import Callable, Mapping, Optional, Sequence

try:
    from conda_cli import conda_executable
except ModuleNotFoundError:  # pragma: no cover - used when imported from tests
    from scripts.packaging.conda_cli import conda_executable

logger = logging.getLogger(__name__)

CONDA_FORGE_PACKAGES = (
    "pyside6",
    "qt6-main",
    "pyvips",
    "libvips",
    "rawpy",
    "opencv",
    "numpy",
    "pillow",
    "pillow-heif",
    "pillow-avif-plugin",
    "pyinstaller",
    "python-build",
    "twine",
    "tomli",
    "setuptools",
    "wheel",
    "pip",
)
PYPI_FALLBACK_PACKAGES = ("pyexiv2",)


def verify_active_environment(
    env: Optional[Mapping[str, str]] = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    """Load `conda list --json` output and verify dependency source channels."""

    result = runner(
        [conda_executable(env), "list", "--json"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    records = json.loads(result.stdout)
    verify_dependency_sources(records)


def verify_dependency_sources(records: Sequence[Mapping[str, object]]) -> None:
    """Verify release packages came from the expected package source."""

    indexed_records = {_normalized_name(record): record for record in records}

    for package_name in CONDA_FORGE_PACKAGES:
        record = _require_record(indexed_records, package_name)
        if not _is_conda_forge_record(record):
            raise RuntimeError(
                f"{package_name} must be installed from conda-forge, "
                f"but conda list reports channel {_record_channel(record)!r}."
            )

    for package_name in PYPI_FALLBACK_PACKAGES:
        record = _require_record(indexed_records, package_name)
        if not _is_pypi_record(record):
            raise RuntimeError(
                f"{package_name} must be installed from PyPI fallback, "
                f"but conda list reports channel {_record_channel(record)!r}."
            )


def _normalized_name(record: Mapping[str, object]) -> str:
    name = record.get("name")
    return str(name).lower()


def _require_record(records: Mapping[str, Mapping[str, object]], package_name: str) -> Mapping[str, object]:
    record = records.get(package_name.lower())
    if record is None:
        raise RuntimeError(f"Missing release dependency in conda list output: {package_name}.")
    return record


def _record_channel(record: Mapping[str, object]) -> str:
    return str(record.get("channel", "")).lower()


def _is_conda_forge_record(record: Mapping[str, object]) -> bool:
    channel = _record_channel(record)
    base_url = str(record.get("base_url", "")).lower()
    return "conda-forge" in channel or "conda-forge" in base_url


def _is_pypi_record(record: Mapping[str, object]) -> bool:
    channel = _record_channel(record)
    platform = str(record.get("platform", "")).lower()
    build_string = str(record.get("build_string", "")).lower()
    return channel == "pypi" or platform == "pypi" or build_string == "pypi_0"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(description="Verify release dependency source channels.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run dependency source verification."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parse_args(argv)

    try:
        verify_active_environment()
    except (RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        logger.error("%s", exc)
        return 1

    logger.info("Dependency source verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
