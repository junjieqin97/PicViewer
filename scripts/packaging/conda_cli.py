"""Resolve the conda CLI for release packaging subprocess calls."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys
from typing import Callable, Mapping, Optional

PathLookup = Callable[[str], Optional[str]]


def conda_executable(
    env: Optional[Mapping[str, str]] = None,
    platform: Optional[str] = None,
    path_lookup: PathLookup = shutil.which,
) -> str:
    """Return a conda executable path suitable for direct subprocess use.

    PowerShell activation can expose `conda` as a shell function that Python's
    subprocess module cannot execute directly. Prefer conda's own environment
    variables, then fall back to PATH lookup for local environments.
    """

    source_env = os.environ if env is None else env
    explicit_executable = source_env.get("CONDA_EXE")
    if explicit_executable:
        return explicit_executable

    current_platform = sys.platform if platform is None else platform
    conda_root = source_env.get("CONDA")
    if conda_root:
        candidate = _conda_executable_from_root(Path(conda_root), current_platform)
        if candidate is not None:
            return str(candidate)

    resolved = path_lookup("conda")
    if resolved:
        return resolved

    raise RuntimeError(
        "Cannot find conda executable. Activate a conda environment or set "
        "CONDA_EXE/CONDA before running release packaging scripts."
    )


def _conda_executable_from_root(conda_root: Path, platform: str) -> Optional[Path]:
    """Return the first existing conda executable under a conda root."""

    for candidate in _conda_root_candidates(conda_root, platform):
        if candidate.exists():
            return candidate
    return None


def _conda_root_candidates(conda_root: Path, platform: str) -> tuple[Path, ...]:
    """Return platform-specific conda executable candidates."""

    if platform.startswith("win"):
        return (
            conda_root / "Scripts" / "conda.exe",
            conda_root / "condabin" / "conda.exe",
            conda_root / "condabin" / "conda.bat",
        )

    return (
        conda_root / "bin" / "conda",
        conda_root / "condabin" / "conda",
    )
