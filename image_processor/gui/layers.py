#!/usr/bin/env python3
"""Layer model and manager for the image canvas."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QBrush, QImage, QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene

from image_processor.core.image_engine import create_checkerboard


@dataclass
class Layer:
    """A single layer in the image editor."""

    name: str
    image: Image.Image
    x: int = 0
    y: int = 0
    opacity: float = 1.0
    visible: bool = True
    locked: bool = False
    item: QGraphicsPixmapItem | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def copy(self) -> "Layer":
        return Layer(
            name=self.name,
            image=self.image.copy(),
            x=self.x,
            y=self.y,
            opacity=self.opacity,
            visible=self.visible,
            locked=self.locked,
            metadata=dict(self.metadata),
        )

    def move(self, x: int, y: int) -> None:
        self.x = x
        self.y = y
        if self.item is not None:
            self.item.setOffset(x, y)

    def update_pixmap(self, scene: QGraphicsScene) -> None:
        if self.item is None:
            self.item = QGraphicsPixmapItem()
            self.item.setOffset(self.x, self.y)
            scene.addItem(self.item)
        data = np.array(self.image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(q_image)
        self.item.setPixmap(pixmap)
        self.item.setOffset(self.x, self.y)
        self.item.setOpacity(self.opacity)
        self.item.setVisible(self.visible)
        self.item.setZValue(self.metadata.get("z", 0))

    def remove_from_scene(self, scene: QGraphicsScene) -> None:
        if self.item is not None:
            scene.removeItem(self.item)
            self.item = None


class LayerManager:
    """Manages the stack of layers for a canvas."""

    def __init__(self, scene: QGraphicsScene) -> None:
        self.scene = scene
        self.layers: list[Layer] = []
        self._checkerboard_layer: Layer | None = None
        self._checkerboard_size = 16
        self._checkerboard_color1 = (255, 255, 255)
        self._checkerboard_color2 = (229, 231, 235)

    def add_layer(self, layer: Layer, *, index: int | None = None) -> None:
        if index is None:
            self.layers.append(layer)
        else:
            self.layers.insert(index, layer)
        self._refresh_z_values()
        layer.update_pixmap(self.scene)

    def remove_layer(self, layer: Layer) -> None:
        layer.remove_from_scene(self.scene)
        if layer in self.layers:
            self.layers.remove(layer)

    def set_checkerboard(
        self,
        width: int,
        height: int,
        cell_size: int = 16,
        color1: tuple[int, int, int] = (255, 255, 255),
        color2: tuple[int, int, int] = (229, 231, 235),
        x: int = 0,
        y: int = 0,
    ) -> None:
        self._checkerboard_size = max(4, cell_size)
        self._checkerboard_color1 = color1
        self._checkerboard_color2 = color2
        board = create_checkerboard(
            width,
            height,
            cell_size=self._checkerboard_size,
            color1=color1,
            color2=color2,
        )
        if self._checkerboard_layer is None:
            self._checkerboard_layer = Layer(
                name="棋盘格背景",
                image=board,
                x=x,
                y=y,
                metadata={"z": -1000, "is_checkerboard": True},
            )
            self.add_layer(self._checkerboard_layer, index=0)
        else:
            self._checkerboard_layer.image = board
            self._checkerboard_layer.move(x, y)
            self._checkerboard_layer.update_pixmap(self.scene)

    def set_checkerboard_size(self, size: int) -> None:
        self._checkerboard_size = max(4, size)
        if self._checkerboard_layer is not None:
            self.set_checkerboard(
                self._checkerboard_layer.width,
                self._checkerboard_layer.height,
                self._checkerboard_size,
                self._checkerboard_color1,
                self._checkerboard_color2,
                x=self._checkerboard_layer.x,
                y=self._checkerboard_layer.y,
            )

    def _refresh_z_values(self) -> None:
        for index, layer in enumerate(self.layers):
            z = layer.metadata.get("z", index)
            layer.metadata["z"] = z
            if layer.item is not None:
                layer.item.setZValue(z)

    def clear(self) -> None:
        for layer in self.layers:
            layer.remove_from_scene(self.scene)
        self.layers.clear()
        self._checkerboard_layer = None

    def image_rect(self) -> tuple[int, int, int, int] | None:
        """Return bounding box of all non-background layers."""
        rects = [
            (layer.x, layer.y, layer.x + layer.width, layer.y + layer.height)
            for layer in self.layers
            if not layer.metadata.get("is_checkerboard")
        ]
        if not rects:
            return None
        left = min(r[0] for r in rects)
        top = min(r[1] for r in rects)
        right = max(r[2] for r in rects)
        bottom = max(r[3] for r in rects)
        return left, top, right, bottom

    def active_image_layer(self) -> Layer | None:
        for layer in reversed(self.layers):
            if not layer.metadata.get("is_checkerboard") and layer.visible:
                return layer
        return None

    def set_scene_rect(self, width: int, height: int, *, centered: bool = True) -> None:
        if centered:
            self.scene.setSceneRect(-width / 2, -height / 2, width, height)
        else:
            self.scene.setSceneRect(0, 0, width, height)

    def export_merged_image(self) -> Image.Image:
        """Merge all visible non-background layers into a single image."""
        rect = self.image_rect()
        if rect is None:
            return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        left, top, right, bottom = rect
        width = right - left
        height = bottom - top
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for layer in self.layers:
            if layer.visible and not layer.metadata.get("is_checkerboard"):
                paste_x = layer.x - left
                paste_y = layer.y - top
                if layer.image.mode == "RGBA":
                    canvas.paste(layer.image, (paste_x, paste_y), layer.image)
                else:
                    canvas.paste(layer.image, (paste_x, paste_y))
        return canvas
