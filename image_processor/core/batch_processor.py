#!/usr/bin/env python3
"""Batch image processing."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from PIL import Image

from image_processor.core.image_engine import (
    EngineError,
    InterpolationMode,
    export_image,
    remove_background,
    resize_image,
)


class BatchResult:
    """Result of a single batch operation."""

    def __init__(self, source: Path, success: bool, output: Path | None = None, message: str = ""):
        self.source = source
        self.success = success
        self.output = output
        self.message = message


class BatchProcessor:
    """Processes images in parallel using a thread pool."""

    def __init__(self, max_workers: int | None = None):
        self.max_workers = max_workers
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def process_matting(
        self,
        paths: list[Path],
        output_dir: Path,
        *,
        model: str = "isnet-general-use",
        trim: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[BatchResult]:
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[BatchResult] = []
        total = len(paths)

        def process_one(path: Path) -> BatchResult:
            if self._cancelled:
                return BatchResult(path, False, message="Cancelled")
            try:
                image = remove_background(path, model=model, trim=trim)
                output_path = output_dir / f"{path.stem}_nobg.png"
                export_image(image, output_path, format="PNG")
                return BatchResult(path, True, output_path)
            except EngineError as exc:
                return BatchResult(path, False, message=str(exc))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[Future[BatchResult], Path] = {}
            for path in paths:
                future = executor.submit(process_one, path)
                futures[future] = path

            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results.append(result)
                if progress_callback:
                    progress_callback(index, total)

        return results

    def process_resize(
        self,
        paths: list[Path],
        output_dir: Path,
        *,
        width: int | None = None,
        height: int | None = None,
        percentage: float | None = None,
        interpolation: InterpolationMode = InterpolationMode.LANCZOS,
        format: str = "PNG",
        quality: int = 95,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> list[BatchResult]:
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[BatchResult] = []
        total = len(paths)

        def process_one(path: Path) -> BatchResult:
            if self._cancelled:
                return BatchResult(path, False, message="Cancelled")
            try:
                image = resize_image(path, width=width, height=height, percentage=percentage, interpolation=interpolation)
                ext = format.lower()
                output_path = output_dir / f"{path.stem}_resized.{ext}"
                export_image(image, output_path, format=format, quality=quality)
                return BatchResult(path, True, output_path)
            except EngineError as exc:
                return BatchResult(path, False, message=str(exc))

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: dict[Future[BatchResult], Path] = {}
            for path in paths:
                future = executor.submit(process_one, path)
                futures[future] = path

            for index, future in enumerate(as_completed(futures), start=1):
                result = future.result()
                results.append(result)
                if progress_callback:
                    progress_callback(index, total)

        return results
