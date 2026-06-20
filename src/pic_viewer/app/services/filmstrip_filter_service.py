"""Business rules for filtering the Filmstrip image list."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pic_viewer.app.dto.filmstrip_filter import (
    FilmstripFilterCriteria,
    FilmstripFilterItem,
    FilmstripFilterOptions,
)
from pic_viewer.app.dto.metadata import ImageMetadata
from pic_viewer.app.services.metadata_summary_service import camera_display_name, lens_display_name

UNKNOWN_CAMERA_LABEL = "Unknown Camera"
UNKNOWN_LENS_LABEL = "Unknown Lens"


class FilmstripFilterService:
    """Build and evaluate filter metadata for Filmstrip items."""

    def build_initial_item(self, path: Path) -> FilmstripFilterItem:
        """Build a filter item before metadata scanning has completed."""

        return FilmstripFilterItem(
            path=path,
            extension=self.normalize_extension(path.suffix),
        )

    def build_item_from_metadata(self, path: Path, metadata: ImageMetadata) -> FilmstripFilterItem:
        """Build a filter item from metadata-only or full image load metadata."""

        camera = camera_display_name(metadata) or UNKNOWN_CAMERA_LABEL
        lens = lens_display_name(metadata) or UNKNOWN_LENS_LABEL
        return FilmstripFilterItem(
            path=path,
            extension=self.normalize_extension(path.suffix),
            camera=camera,
            lens=lens,
            metadata_loaded=True,
        )

    def matches(self, item: FilmstripFilterItem, criteria: FilmstripFilterCriteria) -> bool:
        """Return True when an item satisfies all selected filter criteria."""

        if criteria.extension and item.extension != self.normalize_extension(criteria.extension):
            return False
        if criteria.camera and item.camera != criteria.camera:
            return False
        if criteria.lens and item.lens != criteria.lens:
            return False
        return True

    def build_options(self, items: Iterable[FilmstripFilterItem]) -> FilmstripFilterOptions:
        """Build sorted, deduplicated filter options from known item metadata."""

        materialized = tuple(items)
        return FilmstripFilterOptions(
            extensions=self._sorted_unique(item.extension for item in materialized if item.extension),
            cameras=self._sorted_unique(
                item.camera for item in materialized if item.metadata_loaded and item.camera
            ),
            lenses=self._sorted_unique(
                item.lens for item in materialized if item.metadata_loaded and item.lens
            ),
        )

    @staticmethod
    def normalize_extension(extension: str) -> str:
        """Normalize file suffix comparisons to lower case with a leading dot."""

        cleaned = extension.strip().lower()
        if not cleaned:
            return ""
        return cleaned if cleaned.startswith(".") else f".{cleaned}"

    @staticmethod
    def _sorted_unique(values: Iterable[str | None]) -> tuple[str, ...]:
        present = {value for value in values if value}
        return tuple(sorted(present, key=lambda value: value.casefold()))
