"""DTOs for Filmstrip filtering state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FilmstripFilterCriteria:
    """Selected Filmstrip filter values.

    Attributes:
        extension: Optional file suffix filter, including the leading dot.
        camera: Optional camera model display value.
        lens: Optional lens model display value.
    """

    extension: str | None = None
    camera: str | None = None
    lens: str | None = None


@dataclass(frozen=True)
class FilmstripFilterItem:
    """Filterable metadata associated with one opened image path."""

    path: Path
    extension: str
    camera: str | None = None
    lens: str | None = None
    metadata_loaded: bool = False


@dataclass(frozen=True)
class FilmstripFilterOptions:
    """Available values shown by Filmstrip filter combo boxes."""

    extensions: tuple[str, ...]
    cameras: tuple[str, ...]
    lenses: tuple[str, ...]
