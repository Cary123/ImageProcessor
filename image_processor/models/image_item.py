#!/usr/bin/env python3
"""Image data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image

from image_processor.core.history_manager import HistoryEntry, HistoryManager
from image_processor.models.canvas_snapshot import CanvasSnapshot, LayerSnapshot


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

    def clone(self) -> ImageItem:
        return ImageItem(
            source_path=self.source_path,
            image=self.image.copy(),
            metadata=dict(self.metadata),
            history=HistoryManager(max_size=self.history.max_size),
        )

    def replace(
        self,
        image: Image.Image,
        *,
        description: str = "编辑",
        layers: list[LayerSnapshot] | None = None,
        active_layer_index: int = 0,
        checkerboard_size: int = 16,
    ) -> ImageItem:
        self.image = image
        self.history.push(
            image,
            description,
            layers=layers,
            active_layer_index=active_layer_index,
            checkerboard_size=checkerboard_size,
        )
        return self

    def replace_from_snapshot(self, snapshot: CanvasSnapshot, *, description: str = "编辑") -> ImageItem:
        merged = snapshot.merged_image()
        return self.replace(
            merged,
            description=description,
            layers=[layer.copy() for layer in snapshot.layers],
            active_layer_index=snapshot.active_layer_index,
            checkerboard_size=snapshot.checkerboard_size,
        )

    def undo(self) -> HistoryEntry | None:
        return self.history.undo()

    def redo(self) -> HistoryEntry | None:
        return self.history.redo()
