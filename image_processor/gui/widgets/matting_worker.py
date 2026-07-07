#!/usr/bin/env python3
"""Thread-safe worker for background removal."""

from __future__ import annotations

from typing import Any

from PIL import Image
from PySide6.QtCore import QObject, QRunnable, Signal

from image_processor.core.image_engine import EngineError, remove_background


class MattingWorkerSignals(QObject):
    """Signals emitted by the matting worker."""

    progress = Signal(int)
    finished = Signal(object)
    error = Signal(str)


class MattingWorker(QRunnable):
    """Runs background removal in a thread pool."""

    def __init__(self, image: Image.Image, options: dict[str, Any]) -> None:
        super().__init__()
        self.image = image.copy()
        self.options = options
        self.signals = MattingWorkerSignals()

    def run(self) -> None:
        try:

            def progress_callback(value: float) -> None:
                self.signals.progress.emit(int(value * 100))

            result = remove_background(
                self.image,
                model=self.options.get("model", "isnet-general-use"),
                trim=self.options.get("trim", False),
                trim_padding=self.options.get("trim_padding", 0),
                alpha_matting=self.options.get("alpha_matting", False),
                progress_callback=progress_callback,
            )
            self.signals.finished.emit(result)
        except EngineError as exc:
            self.signals.error.emit(str(exc))
