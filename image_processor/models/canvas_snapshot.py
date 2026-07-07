#!/usr/bin/env python3
"""Serializable canvas / layer state for undo and project persistence."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PIL import Image


@dataclass
class LayerSnapshot:
    """Immutable layer state."""

    name: str
    image: Image.Image
    x: int
    y: int
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def copy(self) -> LayerSnapshot:
        return LayerSnapshot(
            name=self.name,
            image=self.image.copy(),
            x=self.x,
            y=self.y,
            opacity=self.opacity,
            visible=self.visible,
            locked=self.locked,
            metadata=dict(self.metadata),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "opacity": self.opacity,
            "visible": self.visible,
            "locked": self.locked,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], image: Image.Image) -> LayerSnapshot:
        return cls(
            name=data.get("name", "图层"),
            image=image,
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            opacity=float(data.get("opacity", 1.0)),
            visible=bool(data.get("visible", True)),
            locked=bool(data.get("locked", False)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class CanvasSnapshot:
    """Full editable canvas state."""

    layers: list[LayerSnapshot]
    active_layer_index: int = 0
    checkerboard_size: int = 16

    def copy(self) -> CanvasSnapshot:
        return CanvasSnapshot(
            layers=[layer.copy() for layer in self.layers],
            active_layer_index=self.active_layer_index,
            checkerboard_size=self.checkerboard_size,
        )

    def merged_image(self) -> Image.Image:
        if not self.layers:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))

        left = min(layer.x for layer in self.layers)
        top = min(layer.y for layer in self.layers)
        right = max(layer.x + layer.image.width for layer in self.layers)
        bottom = max(layer.y + layer.image.height for layer in self.layers)
        width = max(1, right - left)
        height = max(1, bottom - top)
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        for layer in self.layers:
            if not layer.visible:
                continue
            paste_x = layer.x - left
            paste_y = layer.y - top
            if layer.opacity >= 0.999:
                if layer.image.mode == "RGBA":
                    canvas.paste(layer.image, (paste_x, paste_y), layer.image)
                else:
                    canvas.paste(layer.image, (paste_x, paste_y))
                continue
            overlay = layer.image.convert("RGBA")
            alpha = overlay.split()[3]
            alpha = alpha.point(lambda value: int(value * layer.opacity))
            overlay.putalpha(alpha)
            canvas.paste(overlay, (paste_x, paste_y), overlay)
        return canvas
