#!/usr/bin/env python3
"""Undo/redo history manager."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Generic, TypeVar

from PIL import Image

T = TypeVar("T")


@dataclass
class HistoryEntry:
    """Snapshot of an image state."""

    image: Image.Image
    description: str


class HistoryManager(Generic[T]):
    """Keeps a bounded stack of history entries for undo/redo."""

    def __init__(self, max_size: int = 20):
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self.max_size = max_size
        self._stack: deque[HistoryEntry] = deque()
        self._index = -1

    def push(self, image: Image.Image, description: str) -> None:
        """Save a snapshot of the current image."""
        # Remove any redo states after the current index.
        while len(self._stack) > self._index + 1:
            self._stack.pop()

        self._stack.append(HistoryEntry(image=image.copy(), description=description))
        self._index += 1

        if len(self._stack) > self.max_size:
            self._stack.popleft()
            self._index -= 1

    def undo(self) -> HistoryEntry | None:
        """Return the previous state, or None if at the beginning."""
        if self._index <= 0:
            return None
        self._index -= 1
        return self._stack[self._index]

    def redo(self) -> HistoryEntry | None:
        """Return the next state, or None if at the end."""
        if self._index >= len(self._stack) - 1:
            return None
        self._index += 1
        return self._stack[self._index]

    def can_undo(self) -> bool:
        return self._index > 0

    def can_redo(self) -> bool:
        return self._index < len(self._stack) - 1

    def clear(self) -> None:
        self._stack.clear()
        self._index = -1

    @property
    def current_description(self) -> str:
        if 0 <= self._index < len(self._stack):
            return self._stack[self._index].description
        return ""
