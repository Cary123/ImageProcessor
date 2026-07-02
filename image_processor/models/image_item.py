#!/usr/bin/env python3
"""Image data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from image_processor.core.history_manager import HistoryEntry, HistoryManager


@dataclass
class ImageItem:
    """Represents a loaded image in the application."""

    source_path: Path
    image: Image.Image
    metadata: dict[str, Any] = field(default_factory=dict)
    history: HistoryManager = field(default_factory=lambda: HistoryManager(max_size=20))

    def __post_init__(self) -> None:
        self.history.push(self.image, description="原始图片")

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    @property
    def size(self) -> tuple[int, int]:
        return self.image.size

    @property
    def mode(self) -> str:
        return self.image.mode

    @property
    def name(self) -> str:
        return self.source_path.name

    def clone(self) -> "ImageItem":
        return ImageItem(
            source_path=self.source_path,
            image=self.image.copy(),
            metadata=dict(self.metadata),
            history=HistoryManager(max_size=self.history.max_size),
        )

    def snapshot(self, description: str) -> "ImageItem":
        self.history.push(self.image, description=description)
        return self

    def replace(self, image: Image.Image, *, description: str = "编辑") -> "ImageItem":
        self.image = image
        self.snapshot(description)
        return self

    def undo(self) -> bool:
        entry = self.history.undo()
        if entry is None:
            return False
        self.image = entry.image.copy()
        return True

    def redo(self) -> bool:
        entry = self.history.redo()
        if entry is None:
            return False
        self.image = entry.image.copy()
        return True
