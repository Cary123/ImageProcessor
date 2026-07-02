#!/usr/bin/env python3
"""Image canvas with layers, tools, checkerboard background, and zoom support."""

from __future__ import annotations

from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPainter, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from image_processor.gui.layers import Layer, LayerManager
from image_processor.gui.tools import (
    BrushTool,
    CloneStampTool,
    CropTool,
    EraserTool,
    FreeSelectTool,
    MoveTool,
    NavigatorTool,
    RectangleSelectTool,
    Tool,
)
from image_processor.gui.widgets.grid_overlay import GridOverlay


class ImageCanvas(QGraphicsView):
    """Canvas that displays image layers and supports interactive tools."""

    zoom_changed = Signal(float)
    cursor_moved = Signal(int, int)
    brush_applied = Signal(object)
    crop_rect_changed = Signal(tuple)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAlignment(Qt.AlignCenter)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)

        self._layers = LayerManager(self.scene)
        self._checkerboard_size = 16

        self._current_tool_id: str | None = None
        self._tool: Tool | None = None
        self._tools: dict[str, Tool] = {}
        self._init_tools()

        self._brush_size = 20
        self._brush_hardness = 100
        self._brush_original: Image.Image | None = None

        self.selection_rect: tuple[float, float, float, float] | None = None
        self.selection_polygon: list[QPoint] | None = None
        self.crop_rect: tuple[float, float, float, float] | None = None
        self._clipboard_layer: Image.Image | None = None

        self._empty_layer = Layer(
            name="默认",
            image=Image.new("RGBA", (512, 512), (0, 0, 0, 0)),
        )
        self._grid_overlay = GridOverlay()
        self.scene.addItem(self._grid_overlay)
        self._grid_options: dict[str, Any] = {"visible": False, "rows": 4, "cols": 4}

        self._layers.set_checkerboard(512, 512, cell_size=self._checkerboard_size)
        self._center_on_checkerboard()

    def _init_tools(self) -> None:
        self._tools = {
            "navigator": NavigatorTool(self),
            "brush": BrushTool(self),
            "eraser": EraserTool(self),
            "rect_select": RectangleSelectTool(self),
            "free_select": FreeSelectTool(self),
            "crop": CropTool(self),
            "clone_stamp": CloneStampTool(self),
            "move": MoveTool(self),
        }

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)

    def _center_on_checkerboard(self) -> None:
        rect = self.scene.sceneRect()
        self.fitInView(rect, Qt.KeepAspectRatio)
        self.zoom_changed.emit(self.transform().m11())

    def set_image(self, image: Image.Image) -> None:
        self._layers.clear()
        self._brush_original = image.copy()
        layer = Layer(
            name="图片",
            image=image,
            x=-image.width // 2,
            y=-image.height // 2,
            metadata={"z": 0},
        )
        self._layers.add_layer(layer)
        self._layers.set_checkerboard(
            image.width,
            image.height,
            cell_size=self._checkerboard_size,
            x=-image.width // 2,
            y=-image.height // 2,
        )
        self._layers.set_scene_rect(image.width, image.height)
        self._update_grid_overlay()
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.zoom_changed.emit(self.transform().m11())
        self._set_tool("navigator")

    def clear(self) -> None:
        self._layers.clear()
        self._brush_original = None
        self.selection_rect = None
        self.selection_polygon = None
        self.crop_rect = None
        self._layers.set_checkerboard(512, 512, cell_size=self._checkerboard_size)
        self._layers.set_scene_rect(512, 512)
        self._update_grid_overlay()
        self._center_on_checkerboard()
        self._set_tool("navigator")

    def active_layer(self) -> Layer | None:
        return self._layers.active_image_layer()

    def _update_grid_overlay(self) -> None:
        layer = self.active_layer()
        if layer is None:
            self._grid_overlay.set_rect(0, 0, 0, 0)
            return
        self._grid_overlay.set_rect(layer.x, layer.y, layer.width, layer.height)
        self._grid_overlay.set_grid(self._grid_options.get("rows", 4), self._grid_options.get("cols", 4))
        self._grid_overlay.set_visible(self._grid_options.get("visible", False))

    def set_grid_options(self, options: dict[str, Any]) -> None:
        self._grid_options = {
            "visible": options.get("visible", False),
            "rows": max(1, options.get("rows", 4)),
            "cols": max(1, options.get("cols", 4)),
        }
        self._update_grid_overlay()

    def set_checkerboard_size(self, size: int) -> None:
        self._checkerboard_size = max(4, size)
        self._layers.set_checkerboard_size(self._checkerboard_size)

    def reset_zoom(self) -> None:
        self.resetTransform()
        if self.active_layer() is not None:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        else:
            self._center_on_checkerboard()
        self.zoom_changed.emit(self.transform().m11())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._current_tool_id in ("brush", "eraser", "clone_stamp"):
            return
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)
        self.zoom_changed.emit(self.transform().m11())

    def set_brush_mode(self, mode: str | None) -> None:
        if mode == "brush":
            self._set_tool("brush")
        elif mode == "eraser":
            self._set_tool("eraser")
        else:
            self._set_tool("navigator")

    def set_brush_size(self, size: int) -> None:
        self._brush_size = max(1, size)

    def set_brush_hardness(self, hardness: int) -> None:
        self._brush_hardness = max(0, min(100, hardness))

    def start_brush_session(self, image: Image.Image, original_image: Image.Image) -> None:
        self._layers.clear()
        self._brush_original = original_image.copy()
        if original_image.size != image.size:
            self._brush_original = original_image.resize(image.size, Image.Resampling.LANCZOS)
        layer = Layer(
            name="图片",
            image=image.copy(),
            x=-image.width // 2,
            y=-image.height // 2,
            metadata={"z": 0},
        )
        self._layers.add_layer(layer)
        self._layers.set_checkerboard(
            image.width,
            image.height,
            cell_size=self._checkerboard_size,
            x=-image.width // 2,
            y=-image.height // 2,
        )
        self._layers.set_scene_rect(image.width, image.height)

    def _end_brush_session(self) -> None:
        self._brush_original = None

    def apply_brush(self) -> None:
        layer = self.active_layer()
        if layer is not None:
            self.brush_applied.emit(layer.image.copy())

    def cancel_brush(self) -> None:
        layer = self.active_layer()
        if layer is not None and self._brush_original is not None:
            layer.image = self._brush_original.copy()
            layer.update_pixmap(self.scene)

    def _set_tool(self, tool_id: str) -> None:
        if tool_id not in self._tools:
            return
        if self._tool is not None:
            self._tool.deactivate()
        self._current_tool_id = tool_id
        self._tool = self._tools[tool_id]
        self._tool.activate()
        self.setCursor(self._tool.cursor)

    def set_tool(self, tool_id: str) -> None:
        self._set_tool(tool_id)

    def current_tool(self) -> str | None:
        return self._current_tool_id

    def copy_selection(self) -> None:
        layer = self.active_layer()
        if layer is None:
            return
        if self.selection_rect is not None:
            left, top, right, bottom = self.selection_rect
            left = int(left - layer.x)
            top = int(top - layer.y)
            right = int(right - layer.x)
            bottom = int(bottom - layer.y)
            left = max(0, left)
            top = max(0, top)
            right = min(layer.width, right)
            bottom = min(layer.height, bottom)
            if right > left and bottom > top:
                self._clipboard_layer = layer.image.crop((left, top, right, bottom))
        elif self.selection_polygon is not None and len(self.selection_polygon) > 2:
            # Convert polygon to a mask and crop to its bounding box.
            poly = [(int(p.x() - layer.x), int(p.y() - layer.y)) for p in self.selection_polygon]
            mask = Image.new("L", layer.image.size, 0)
            draw = ImageDraw.Draw(mask)
            draw.polygon(poly, fill=255)
            bbox = mask.getbbox()
            if bbox is not None:
                cropped = layer.image.crop(bbox)
                mask_crop = mask.crop(bbox)
                result = Image.new("RGBA", cropped.size, (0, 0, 0, 0))
                result.paste(cropped, (0, 0), mask_crop)
                self._clipboard_layer = result

    def paste_selection(self) -> Image.Image | None:
        if self._clipboard_layer is None:
            return None
        pasted = self._clipboard_layer.copy()
        self._layers.add_layer(
            Layer(
                name="粘贴",
                image=pasted,
                x=-pasted.width // 2,
                y=-pasted.height // 2,
                metadata={"z": 1},
            )
        )
        return pasted

    def get_crop_box(self) -> tuple[int, int, int, int] | None:
        if self.crop_rect is None:
            return None
        layer = self.active_layer()
        if layer is None:
            return None
        left, top, right, bottom = self.crop_rect
        left = int(left - layer.x)
        top = int(top - layer.y)
        right = int(right - layer.x)
        bottom = int(bottom - layer.y)
        left = max(0, left)
        top = max(0, top)
        right = min(layer.width, right)
        bottom = min(layer.height, bottom)
        if right <= left or bottom <= top:
            return None
        return left, top, right, bottom

    def refresh_crop_tool(self) -> None:
        tool = self._tools.get("crop")
        if isinstance(tool, CropTool):
            tool._update_display()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._tool is not None and self._tool.mouse_press(event):
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._emit_cursor_position(event.pos())
        if self._tool is not None and self._tool.mouse_move(event):
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._tool is not None and self._tool.mouse_release(event):
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Control:
            if self._current_tool_id == "clone_stamp":
                self.setCursor(Qt.CrossCursor)
        if self._tool is not None and self._tool.key_press(event):
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key_Control:
            if self._current_tool_id in ("brush", "eraser", "clone_stamp"):
                self.setCursor(self._tool.cursor)
        super().keyReleaseEvent(event)

    def _emit_cursor_position(self, view_pos: QPoint) -> None:
        layer = self.active_layer()
        if layer is None:
            self.cursor_moved.emit(-1, -1)
            return
        scene_pos = self.mapToScene(view_pos)
        x = int(scene_pos.x() - layer.x)
        y = int(scene_pos.y() - layer.y)
        if 0 <= x < layer.width and 0 <= y < layer.height:
            self.cursor_moved.emit(x, y)
        else:
            self.cursor_moved.emit(-1, -1)

    def export_image(self) -> Image.Image:
        return self._layers.export_merged_image()

    def add_layer(self, image: Image.Image, *, name: str = "图层", x: int = 0, y: int = 0) -> None:
        self._layers.add_layer(Layer(name=name, image=image, x=x, y=y, metadata={"z": 1}))
