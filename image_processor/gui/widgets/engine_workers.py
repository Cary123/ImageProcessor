#!/usr/bin/env python3
"""Background workers for CPU-heavy image engine operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal

from image_processor.core.image_engine import EngineError, inpaint_image, resize_image


class EngineWorkerSignals(QObject):
    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)


class ResizeWorker(QRunnable):
    def __init__(self, image: Image.Image, options: dict[str, Any]) -> None:
        super().__init__()
        self.image = image.copy()
        self.options = options
        self.signals = EngineWorkerSignals()

    def run(self) -> None:
        try:
            result = resize_image(
                self.image,
                width=self.options.get("width") or None,
                height=self.options.get("height") or None,
                percentage=self.options.get("percentage") or None,
                interpolation=self.options.get("interpolation", "LANCZOS"),
            )
            self.signals.finished.emit(result)
        except EngineError as exc:
            self.signals.error.emit(str(exc))


class InpaintWorker(QRunnable):
    def __init__(self, image: Image.Image, options: dict[str, Any]) -> None:
        super().__init__()
        self.image = image.copy()
        self.options = options
        self.signals = EngineWorkerSignals()

    def run(self) -> None:
        try:
            result = inpaint_image(
                self.image,
                Path(self.options["mask_path"]),
                method=self.options.get("method", "NS"),
                radius=self.options.get("radius", 5),
            )
            self.signals.finished.emit(result)
        except EngineError as exc:
            self.signals.error.emit(str(exc))
