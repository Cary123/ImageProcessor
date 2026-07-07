#!/usr/bin/env python3
"""Undo/redo history manager."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any

from PIL import Image

from image_processor.models.canvas_snapshot import CanvasSnapshot, LayerSnapshot


@dataclass
class HistoryEntry:
    """Snapshot of an image and optional layer state."""

    image: Image.Image
    description: str
    layers: list[LayerSnapshot] | None = None
    active_layer_index: int = 0
    checkerboard_size: int = 16

    def copy(self) -> HistoryEntry:
        return HistoryEntry(
            image=self.image.copy(),
            description=self.description,
            layers=[layer.copy() for layer in self.layers] if self.layers else None,
            active_layer_index=self.active_layer_index,
            checkerboard_size=self.checkerboard_size,
        )


class HistoryManager:
    """Keeps a bounded stack of history entries for undo/redo."""

    def __init__(self, max_size: int = 20):
        if max_size < 2:
            raise ValueError("max_size must be at least 2")
        self.max_size = max_size
        self._stack: deque[HistoryEntry] = deque()
        self._index = -1

    def push(
        self,
        image: Image.Image,
        description: str,
        *,
        layers: list[LayerSnapshot] | None = None,
        active_layer_index: int = 0,
        checkerboard_size: int = 16,
    ) -> None:
        """Save a snapshot of the current state."""
        while len(self._stack) > self._index + 1:
            self._stack.pop()

        self._stack.append(
            HistoryEntry(
                image=image.copy(),
                description=description,
                layers=[layer.copy() for layer in layers] if layers else None,
                active_layer_index=active_layer_index,
                checkerboard_size=checkerboard_size,
            )
        )
        self._index += 1

        while len(self._stack) > self.max_size:
            if len(self._stack) <= 1:
                break
            del self._stack[1]
            if self._index > 0:
                self._index -= 1

    def undo(self) -> HistoryEntry | None:
        if self._index <= 0:
            return None
        self._index -= 1
        return self._stack[self._index]

    def redo(self) -> HistoryEntry | None:
        if self._index >= len(self._stack) - 1:
            return None
        self._index += 1
        return self._stack[self._index]

    def current(self) -> HistoryEntry | None:
        if 0 <= self._index < len(self._stack):
            return self._stack[self._index]
        return None

    def original(self) -> Image.Image | None:
        if not self._stack:
            return None
        return self._stack[0].image

    def original_entry(self) -> HistoryEntry | None:
        if not self._stack:
            return None
        return self._stack[0]

    def can_undo(self) -> bool:
        return self._index > 0

    def can_redo(self) -> bool:
        return self._index < len(self._stack) - 1

    def clear(self) -> None:
        self._stack.clear()
        self._index = -1

    @property
    def current_description(self) -> str:
        entry = self.current()
        return entry.description if entry is not None else ""

    def entries(self) -> list[HistoryEntry]:
        return list(self._stack)

    def load_entries(self, entries: list[HistoryEntry], *, index: int | None = None) -> None:
        self._stack = deque(entries)
        self._index = len(self._stack) - 1 if index is None else max(0, min(index, len(self._stack) - 1))

    def to_canvas_snapshot(self, entry: HistoryEntry | None = None) -> CanvasSnapshot | None:
        target = entry or self.current()
        if target is None:
            return None
        if target.layers:
            return CanvasSnapshot(
                layers=[layer.copy() for layer in target.layers],
                active_layer_index=target.active_layer_index,
                checkerboard_size=target.checkerboard_size,
            )
        image = target.image
        return CanvasSnapshot(
            layers=[
                LayerSnapshot(
                    name="图片",
                    image=image.copy(),
                    x=-image.width // 2,
                    y=-image.height // 2,
                    metadata={"z": 0},
                )
            ],
            active_layer_index=0,
            checkerboard_size=target.checkerboard_size,
        )
