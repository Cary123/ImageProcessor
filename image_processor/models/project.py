#!/usr/bin/env python3
"""Project data model for save/load."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from image_processor.core.history_manager import HistoryEntry, HistoryManager
from image_processor.models.image_item import ImageItem


@dataclass
class ProjectImageData:
    """Serializable data for a single image item."""

    source_path: Path
    metadata: dict[str, Any]
    history_entries: list[tuple[str, Image.Image]] = field(default_factory=list)

    def to_item(self) -> ImageItem:
        """Restore an ImageItem from this data."""
        if not self.history_entries:
            raise ValueError("Project image has no history entries")

        _, current_image = self.history_entries[-1]
        item = ImageItem(
            source_path=self.source_path,
            image=current_image.copy(),
            metadata=dict(self.metadata),
        )
        item.history.clear()
        entries = [
            HistoryEntry(image=image.copy(), description=description)
            for description, image in self.history_entries
        ]
        item.history.load_entries(entries)
        return item


@dataclass
class Project:
    """A project containing multiple image items and UI state."""

    current_index: int
    images: list[ProjectImageData]
    version: str = "1.0"

    def __post_init__(self) -> None:
        if self.current_index < 0 or self.current_index >= len(self.images):
            self.current_index = 0 if self.images else -1
