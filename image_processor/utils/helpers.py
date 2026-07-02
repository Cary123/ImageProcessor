#!/usr/bin/env python3
"""General utility helpers."""

from __future__ import annotations

from pathlib import Path

from image_processor.core.image_engine import SUPPORTED_INPUT_EXTENSIONS


def collect_images(directory: Path) -> list[Path]:
    """Collect all supported image files in a directory, sorted by name."""
    directory = Path(directory).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory}")

    images = [
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
    ]
    return sorted(images)


def ensure_dir(path: Path) -> Path:
    path = Path(path).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_matting_model_available(model: str) -> bool:
    """Check whether a rembg model has already been downloaded."""
    model_dir = Path.home() / ".u2net"
    model_file = model_dir / f"{model}.onnx"
    return model_file.is_file()
