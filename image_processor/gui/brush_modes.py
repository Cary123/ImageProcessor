#!/usr/bin/env python3
"""Brush stamp generators inspired by classic paint programs."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

BRUSH_STYLES: dict[str, str] = {
    "round": "毛笔",
    "crayon": "蜡笔",
    "marker": "马克笔",
    "watercolor": "水彩",
    "airbrush": "喷枪",
    "pencil": "铅笔",
}

_STYLE_HINTS: dict[str, str] = {
    "round": "边缘柔和的圆形画笔，硬度可调节。",
    "crayon": "带颗粒质感的蜡笔效果，适合涂鸦和纹理。",
    "marker": "颜色饱满、边缘略软的马克笔效果。",
    "watercolor": "低浓度叠加的水彩效果，适合晕染。",
    "airbrush": "渐变喷雾效果，适合柔和过渡。",
    "pencil": "边缘锐利的铅笔线条，适合勾线。",
}


def style_label(style_id: str) -> str:
    return BRUSH_STYLES.get(style_id, style_id)


def style_hint(style_id: str) -> str:
    return _STYLE_HINTS.get(style_id, "")


def uses_hardness(style_id: str) -> bool:
    return style_id in ("round", "marker", "pencil")


def uses_opacity(style_id: str) -> bool:
    return style_id in ("round", "crayon", "marker", "watercolor", "airbrush", "pencil")


def _round_stamp(size: int, hardness: float) -> Image.Image:
    stamp = Image.new("L", (size * 2 + 1, size * 2 + 1), 0)
    draw = ImageDraw.Draw(stamp)
    for radius in range(size, -1, -1):
        ratio = radius / size if size > 0 else 0
        intensity = int(255 * (1 - ratio * (1 - hardness)))
        intensity = max(0, min(255, intensity))
        draw.ellipse(
            [size - radius, size - radius, size + radius, size + radius],
            fill=intensity,
        )
    return stamp


def create_brush_stamp(
    size: int,
    *,
    style: str = "round",
    hardness: float = 1.0,
    opacity: float = 1.0,
) -> Image.Image:
    """Build a grayscale brush stamp for the given style."""
    size = max(1, size)
    opacity = max(0.05, min(1.0, opacity))
    hardness = max(0.0, min(1.0, hardness))

    if style == "round":
        stamp = _round_stamp(size, hardness)
    elif style == "marker":
        stamp = _round_stamp(size, max(0.85, hardness))
    elif style == "pencil":
        stamp = _round_stamp(max(1, int(size * 0.75)), max(0.95, hardness))
        if stamp.size[0] < size * 2 + 1:
            canvas = Image.new("L", (size * 2 + 1, size * 2 + 1), 0)
            offset = (canvas.size[0] - stamp.size[0]) // 2
            canvas.paste(stamp, (offset, offset))
            stamp = canvas
    elif style == "watercolor":
        stamp = _round_stamp(size, 0.15)
    elif style == "airbrush":
        stamp = _round_stamp(size, 0.08)
    elif style == "crayon":
        stamp = _round_stamp(size, 0.55)
        data = np.array(stamp, dtype=np.float32)
        rng = np.random.default_rng(size * 7919 + int(hardness * 100))
        grain = rng.integers(120, 256, size=data.shape, dtype=np.int32)
        data = data * grain / 255.0
        data[data < 35] = 0
        stamp = Image.fromarray(np.clip(data, 0, 255).astype(np.uint8), mode="L")
    else:
        stamp = _round_stamp(size, hardness)

    if opacity < 1.0:
        data = (np.array(stamp, dtype=np.float32) * opacity).astype(np.uint8)
        stamp = Image.fromarray(data, mode="L")
    return stamp
