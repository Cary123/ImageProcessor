#!/usr/bin/env python3
"""Core image processing engine."""

from __future__ import annotations

import math
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image, ImageDraw
from rembg import new_session, remove
from rembg.sessions import sessions_names

SUPPORTED_INPUT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}
SUPPORTED_EXPORT_FORMATS = {"PNG", "JPEG", "WEBP", "BMP", "TIFF"}
DEFAULT_MODEL = "isnet-general-use"
AVAILABLE_MODELS = sessions_names


class InterpolationMode(str, Enum):
    """Pillow interpolation modes."""

    LANCZOS = "LANCZOS"
    BILINEAR = "BILINEAR"
    NEAREST = "NEAREST"
    BICUBIC = "BICUBIC"


class EngineError(Exception):
    """Raised when image processing fails."""


class UnsupportedFormatError(EngineError):
    """Raised when an unsupported image format is encountered."""


def _pil_interpolation(mode: InterpolationMode) -> int:
    mapping = {
        InterpolationMode.LANCZOS: Image.Resampling.LANCZOS,
        InterpolationMode.BILINEAR: Image.Resampling.BILINEAR,
        InterpolationMode.NEAREST: Image.Resampling.NEAREST,
        InterpolationMode.BICUBIC: Image.Resampling.BICUBIC,
    }
    return mapping[mode]


def validate_image_path(path: Path) -> Path:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise EngineError(f"Image file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        raise UnsupportedFormatError(f"Unsupported image format: {path}")
    return path


def load_image(path: Path) -> Image.Image:
    path = validate_image_path(path)
    try:
        return Image.open(path).convert("RGBA")
    except OSError as exc:
        raise EngineError(f"Failed to open image '{path}': {exc}") from exc


def trim_transparent(image: Image.Image, padding: int = 0) -> Image.Image:
    bbox = image.getbbox()
    if bbox is None:
        return image

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def remove_background(
    image: Image.Image | Path,
    *,
    model: str = DEFAULT_MODEL,
    alpha_matting: bool = False,
    alpha_matting_foreground_threshold: int = 240,
    alpha_matting_background_threshold: int = 10,
    alpha_matting_erode_size: int = 10,
    post_process_mask: bool = False,
    only_mask: bool = False,
    trim: bool = False,
    trim_padding: int = 0,
    progress_callback: Callable[[float], None] | None = None,
) -> Image.Image:
    if isinstance(image, Path):
        image = load_image(image)

    if progress_callback:
        progress_callback(0.05)

    try:
        session = new_session(model)
    except Exception as exc:
        raise EngineError(f"Failed to load rembg model '{model}': {exc}") from exc

    if progress_callback:
        progress_callback(0.1)

    buffer = BytesIO()
    image.convert("RGBA").save(buffer, format="PNG")
    input_bytes = buffer.getvalue()

    if progress_callback:
        progress_callback(0.2)

    try:
        result = remove(
            input_bytes,
            session=session,
            alpha_matting=alpha_matting,
            alpha_matting_foreground_threshold=alpha_matting_foreground_threshold,
            alpha_matting_background_threshold=alpha_matting_background_threshold,
            alpha_matting_erode_size=alpha_matting_erode_size,
            post_process_mask=post_process_mask,
            only_mask=only_mask,
        )
    except Exception as exc:
        raise EngineError(f"Background removal failed: {exc}") from exc

    if progress_callback:
        progress_callback(0.85)

    if isinstance(result, bytes):
        output_image = Image.open(BytesIO(result)).convert("RGBA")
    else:
        output_image = result.convert("RGBA")

    if only_mask:
        output_image = output_image.convert("L")

    if trim and not only_mask:
        output_image = trim_transparent(output_image, padding=trim_padding)

    if progress_callback:
        progress_callback(1.0)

    return output_image


def merge_layers(images: list[Image.Image | Path]) -> Image.Image:
    if len(images) < 2:
        raise EngineError("At least 2 images are required to merge")

    layers = [img if isinstance(img, Image.Image) else load_image(img) for img in images]
    width, height = layers[0].size

    for index, layer in enumerate(layers[1:], start=2):
        if layer.size != (width, height):
            raise EngineError(
                f"Image size mismatch: layer 1 is {width}x{height}, "
                f"but layer {index} is {layer.width}x{layer.height}"
            )

    merged = layers[0].copy()
    for layer in layers[1:]:
        merged = Image.alpha_composite(merged, layer)

    return merged


def resize_image(
    image: Image.Image | Path,
    *,
    width: int | None = None,
    height: int | None = None,
    percentage: float | None = None,
    interpolation: InterpolationMode = InterpolationMode.LANCZOS,
) -> Image.Image:
    if isinstance(image, Path):
        image = load_image(image)

    if percentage is not None and percentage > 0:
        width = int(image.width * percentage / 100)
        height = int(image.height * percentage / 100)
    elif width is not None and height is None:
        ratio = width / image.width
        height = int(image.height * ratio)
    elif height is not None and width is None:
        ratio = height / image.height
        width = int(image.width * ratio)
    elif width is None or height is None:
        raise EngineError("Provide width, height, or percentage for resize")

    if width <= 0 or height <= 0:
        raise EngineError("Target dimensions must be positive")

    return image.resize((width, height), _pil_interpolation(interpolation))


def export_image(
    image: Image.Image,
    output_path: Path,
    *,
    format: str | None = None,
    quality: int = 95,
    optimize: bool = True,
) -> Path:
    output_path = Path(output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format is None:
        format = output_path.suffix.lstrip(".").upper() or "PNG"

    format = format.upper()
    if format not in SUPPORTED_EXPORT_FORMATS:
        raise UnsupportedFormatError(f"Unsupported export format: {format}")

    save_kwargs: dict[str, object] = {"optimize": optimize}
    if format == "JPEG":
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        save_kwargs["quality"] = max(1, min(100, quality))
    elif format == "WEBP":
        save_kwargs["quality"] = max(1, min(100, quality))
        save_kwargs["method"] = 6

    image.save(output_path, format=format, **save_kwargs)
    return output_path


def crop_image(
    image: Image.Image | Path,
    box: tuple[int, int, int, int],
) -> Image.Image:
    if isinstance(image, Path):
        image = load_image(image)

    left, top, right, bottom = box
    left = max(0, left)
    top = max(0, top)
    right = min(image.width, right)
    bottom = min(image.height, bottom)

    if right <= left or bottom <= top:
        raise EngineError(f"Invalid crop region: {box}")

    return image.crop((left, top, right, bottom))


def rotate_image(
    image: Image.Image | Path,
    angle: float,
    *,
    expand: bool = True,
    resample: InterpolationMode = InterpolationMode.BILINEAR,
) -> Image.Image:
    if isinstance(image, Path):
        image = load_image(image)

    return image.rotate(
        angle,
        expand=expand,
        resample=_pil_interpolation(resample),
    )


def flip_image(
    image: Image.Image | Path,
    *,
    horizontal: bool = False,
    vertical: bool = False,
) -> Image.Image:
    if isinstance(image, Path):
        image = load_image(image)

    if horizontal:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if vertical:
        image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return image


def inpaint_image(
    image: Image.Image | Path,
    mask: Image.Image | Path,
    *,
    radius: int = 3,
    method: str = "NS",
) -> Image.Image:
    """Remove selected region using OpenCV inpainting.

    Args:
        image: Source image.
        mask: Mask where non-zero pixels mark the region to inpaint.
        radius: Radius of a circular neighborhood of each point inpainted.
        method: Inpainting method: "NS" (Navier-Stokes) or "TELEA" (Fast Marching).
    """
    if isinstance(image, Path):
        image = load_image(image)
    if isinstance(mask, Path):
        mask = Image.open(mask).convert("L")

    image_rgb = image.convert("RGB")
    cv_image = cv2.cvtColor(np.array(image_rgb), cv2.COLOR_RGB2BGR)
    cv_mask = np.array(mask.convert("L"))

    if cv_mask.shape[:2] != cv_image.shape[:2]:
        raise EngineError("Mask size must match image size")

    cv_mask = cv2.threshold(cv_mask, 1, 255, cv2.THRESH_BINARY)[1]
    if cv2.countNonZero(cv_mask) == 0:
        raise EngineError("Mask is empty; nothing to inpaint")

    flag = cv2.INPAINT_NS if method == "NS" else cv2.INPAINT_TELEA
    result = cv2.inpaint(cv_image, cv_mask, radius, flag)

    result_rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    output = Image.fromarray(result_rgb)

    if image.mode == "RGBA":
        alpha = image.split()[3]
        output.putalpha(alpha)

    return output


def create_checkerboard(
    width: int,
    height: int,
    cell_size: int = 16,
    color1: tuple[int, int, int] = (255, 255, 255),
    color2: tuple[int, int, int] = (229, 231, 235),
) -> Image.Image:
    if cell_size <= 0:
        raise EngineError("Cell size must be positive")

    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(0, height, cell_size):
        for x in range(0, width, cell_size):
            box = (x, y, min(x + cell_size, width), min(y + cell_size, height))
            is_even = ((x // cell_size) + (y // cell_size)) % 2 == 0
            draw.rectangle(box, fill=color1 if is_even else color2)
    return image


def _optimal_grid(n: int) -> tuple[int, int]:
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    return rows, cols


def create_sprite_sheet(
    images: list[Image.Image | Path],
    *,
    cols: int | None = None,
    spacing: int = 0,
    padding: int = 0,
    sort_by: str = "name",
) -> tuple[Image.Image, dict[str, dict[str, object]]]:
    if not images:
        raise EngineError("At least one image is required to create a sprite sheet")

    if sort_by == "name":
        images = sorted(images, key=lambda img: str(img) if isinstance(img, Path) else str(id(img)))

    layers = [img if isinstance(img, Image.Image) else load_image(img) for img in images]

    if padding > 0:
        padded_layers: list[Image.Image] = []
        for original in layers:
            canvas = Image.new(
                "RGBA",
                (original.width + padding * 2, original.height + padding * 2),
                (0, 0, 0, 0),
            )
            canvas.paste(original, (padding, padding), original)
            padded_layers.append(canvas)
        layers = padded_layers

    if cols is None:
        rows, cols = _optimal_grid(len(layers))
    else:
        cols = max(1, cols)
        rows = math.ceil(len(layers) / cols)

    col_widths = [0] * cols
    row_heights = [0] * rows

    for index, layer in enumerate(layers):
        row, col = divmod(index, cols)
        col_widths[col] = max(col_widths[col], layer.width)
        row_heights[row] = max(row_heights[row], layer.height)

    sprite_width = sum(col_widths) + spacing * (cols - 1)
    sprite_height = sum(row_heights) + spacing * (rows - 1)
    sprite = Image.new("RGBA", (sprite_width, sprite_height), (0, 0, 0, 0))

    frames: dict[str, dict[str, object]] = {}
    y = 0
    for row in range(rows):
        x = 0
        for col in range(cols):
            index = row * cols + col
            if index < len(layers):
                layer = layers[index]
                paste_x = x + (col_widths[col] - layer.width) // 2
                paste_y = y + (row_heights[row] - layer.height) // 2
                sprite.paste(layer, (paste_x, paste_y), layer)

                name = f"frame_{index:03d}"
                frames[name] = {
                    "frame": {"x": paste_x, "y": paste_y, "w": layer.width, "h": layer.height},
                    "rotated": False,
                    "trimmed": False,
                    "sourceSize": {"w": layer.width, "h": layer.height},
                }
            x += col_widths[col] + spacing
        y += row_heights[row] + spacing

    return sprite, frames
