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
from image_processor.models.canvas_snapshot import CanvasSnapshot, LayerSnapshot


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

    def update_pixmap(self, scene: QGraphicsScene, *, image_changed: bool = True) -> None:
        if self.item is None:
            self.item = QGraphicsPixmapItem()
            self.item.setOffset(self.x, self.y)
            scene.addItem(self.item)
        if image_changed:
            data = np.ascontiguousarray(self.image.convert("RGBA"))
            self._pixmap_buffer = data
            height, width, _ = data.shape
            bytes_per_line = width * 4
            q_image = QImage(
                self._pixmap_buffer.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_RGBA8888,
            ).copy()
            pixmap = QPixmap.fromImage(q_image)
            self.item.setPixmap(pixmap)
        self.item.setOffset(self.x, self.y)
        self.item.setOpacity(self.opacity)
        self.item.setVisible(self.visible)
        self.item.setZValue(self.metadata.get("z", 0))

    def refresh_visual(self) -> None:
        """Update Qt item opacity/visibility/offset without rebuilding pixmap."""
        if self.item is None:
            return
        self.item.setOffset(self.x, self.y)
        self.item.setOpacity(self.opacity)
        self.item.setVisible(self.visible)
        self.item.setZValue(self.metadata.get("z", 0))

    def remove_from_scene(self, scene: QGraphicsScene) -> None:
        if self.item is not None:
            scene.removeItem(self.item)
            self.item = None

    def contains(self, scene_x: float, scene_y: float) -> bool:
        return self.x <= scene_x < self.x + self.width and self.y <= scene_y < self.y + self.height


class LayerManager:
    """Manages the stack of layers for a canvas."""

    def __init__(self, scene: QGraphicsScene) -> None:
        self.scene = scene
        self.layers: list[Layer] = []
        self._checkerboard_layer: Layer | None = None
        self._checkerboard_size = 16
        self._checkerboard_color1 = (255, 255, 255)
        self._checkerboard_color2 = (229, 231, 235)
        self._selected_layer: Layer | None = None

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
        if self._selected_layer is layer:
            self._selected_layer = None

    def image_layers(self) -> list[Layer]:
        return [layer for layer in self.layers if not layer.metadata.get("is_checkerboard")]

    def reorder_image_layers(self, new_order: list[int]) -> None:
        """Reorder image layers according to the given index permutation."""
        image_layers = self.image_layers()
        if not image_layers or not new_order:
            return
        try:
            reordered = [image_layers[i] for i in new_order]
        except IndexError:
            return
        self.layers = [self._checkerboard_layer] + reordered if self._checkerboard_layer is not None else reordered
        self._refresh_z_values()

    def set_active_layer(self, layer: Layer | None) -> None:
        if layer is None or layer in self.layers:
            self._selected_layer = layer

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
        self._selected_layer = None

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
        if self._selected_layer is not None and self._selected_layer.visible:
            return self._selected_layer
        for layer in reversed(self.layers):
            if not layer.metadata.get("is_checkerboard") and layer.visible:
                return layer
        return None

    def layer_at(self, scene_x: float, scene_y: float) -> Layer | None:
        for layer in reversed(self.image_layers()):
            if layer.visible and layer.contains(scene_x, scene_y):
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

    def capture_snapshot(self, *, active_layer_index: int = 0, checkerboard_size: int = 16) -> CanvasSnapshot:
        layers = [
            LayerSnapshot(
                name=layer.name,
                image=layer.image.copy(),
                x=layer.x,
                y=layer.y,
                opacity=layer.opacity,
                visible=layer.visible,
                locked=layer.locked,
                metadata=dict(layer.metadata),
            )
            for layer in self.image_layers()
        ]
        return CanvasSnapshot(
            layers=layers,
            active_layer_index=max(0, min(active_layer_index, len(layers) - 1)) if layers else 0,
            checkerboard_size=checkerboard_size,
        )

    def restore_snapshot(self, snapshot: CanvasSnapshot) -> None:
        for layer in list(self.layers):
            layer.remove_from_scene(self.scene)
        self.layers.clear()
        self._checkerboard_layer = None
        self._selected_layer = None

        if not snapshot.layers:
            return

        bounds_left = min(layer.x for layer in snapshot.layers)
        bounds_top = min(layer.y for layer in snapshot.layers)
        bounds_right = max(layer.x + layer.image.width for layer in snapshot.layers)
        bounds_bottom = max(layer.y + layer.image.height for layer in snapshot.layers)
        width = max(1, bounds_right - bounds_left)
        height = max(1, bounds_bottom - bounds_top)
        self.set_checkerboard(
            width,
            height,
            cell_size=snapshot.checkerboard_size,
            x=bounds_left,
            y=bounds_top,
        )
        self.set_scene_rect(width, height)

        for index, layer_state in enumerate(snapshot.layers):
            layer = Layer(
                name=layer_state.name,
                image=layer_state.image.copy(),
                x=layer_state.x,
                y=layer_state.y,
                opacity=layer_state.opacity,
                visible=layer_state.visible,
                locked=layer_state.locked,
                metadata=dict(layer_state.metadata),
            )
            self.add_layer(layer)
            if index == snapshot.active_layer_index:
                self._selected_layer = layer
