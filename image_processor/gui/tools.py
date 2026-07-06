#!/usr/bin/env python3
"""Interactive tools for the image canvas."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageDraw
from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem, QGraphicsPolygonItem, QGraphicsRectItem

if TYPE_CHECKING:
    from image_processor.gui.canvas import ImageCanvas


class Tool(ABC):
    """Base class for canvas tools."""

    id = "tool"
    cursor = Qt.ArrowCursor
    use_mask = False

    def __init__(self, canvas: "ImageCanvas") -> None:
        self.canvas = canvas
        self.active = False

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False

    def mouse_press(self, event) -> bool:
        return False

    def mouse_move(self, event) -> bool:
        return False

    def mouse_release(self, event) -> bool:
        return False

    def key_press(self, event) -> bool:
        return False

    def key_release(self, event) -> bool:
        return False

    def paint(self, painter: QPainter) -> None:
        pass

    def _view_to_image_pos(self, view_pos: QPoint) -> tuple[int, int] | None:
        layer = self.canvas.active_layer()
        if layer is None:
            return None
        scene_pos = self.canvas.mapToScene(view_pos)
        x = int(scene_pos.x() - layer.x)
        y = int(scene_pos.y() - layer.y)
        if 0 <= x < layer.width and 0 <= y < layer.height:
            return x, y
        return None

    def _emit_image_changed(self) -> None:
        self.canvas.image_changed.emit(self.canvas.export_image())


class NavigatorTool(Tool):
    id = "navigator"
    cursor = Qt.OpenHandCursor

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self._panning = False
        self._last_pos: QPoint | None = None

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            self._panning = True
            self._last_pos = event.pos()
            self.canvas.setCursor(Qt.ClosedHandCursor)
            return True
        return False

    def mouse_move(self, event) -> bool:
        if self._panning and self._last_pos is not None:
            delta = event.pos() - self._last_pos
            self.canvas.horizontalScrollBar().setValue(
                self.canvas.horizontalScrollBar().value() - delta.x()
            )
            self.canvas.verticalScrollBar().setValue(
                self.canvas.verticalScrollBar().value() - delta.y()
            )
            self._last_pos = event.pos()
            return True
        return False

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._panning:
            self._panning = False
            self._last_pos = None
            self.canvas.setCursor(self.cursor)
            return True
        return False


class BrushBaseTool(Tool):
    """Base class for brush and eraser."""

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self.cursor = Qt.BlankCursor
        self._drawing = False
        self._last_point: tuple[int, int] | None = None
        self._cursor_item: QGraphicsEllipseItem | None = None

    def activate(self) -> None:
        super().activate()
        self._ensure_cursor_item()

    def deactivate(self) -> None:
        super().deactivate()
        self._remove_cursor_item()

    def _ensure_cursor_item(self) -> None:
        if self._cursor_item is None:
            self._cursor_item = QGraphicsEllipseItem()
            pen = QPen(Qt.white)
            pen.setWidth(2)
            self._cursor_item.setPen(pen)
            self._cursor_item.setBrush(Qt.NoBrush)
            self._cursor_item.setZValue(1000)
            self._cursor_item.setVisible(False)
            self.canvas.scene.addItem(self._cursor_item)
        self._update_cursor_position()

    def _remove_cursor_item(self) -> None:
        if self._cursor_item is not None:
            self.canvas.scene.removeItem(self._cursor_item)
            self._cursor_item = None

    def _update_cursor_position(self, view_pos: QPoint | None = None) -> None:
        if self._cursor_item is None:
            return
        if view_pos is None:
            view_pos = self.canvas.mapFromGlobal(self.canvas.cursor().pos())
        if not self.canvas.viewport().rect().contains(view_pos):
            self._cursor_item.setVisible(False)
            return
        scene_pos = self.canvas.mapToScene(view_pos)
        radius = max(1, self.canvas._brush_size / 2)
        self._cursor_item.setRect(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            radius * 2,
            radius * 2,
        )
        self._cursor_item.setVisible(True)

    def _image_brush_size(self) -> int:
        """Brush radius in image pixels, matching the on-canvas cursor circle."""
        return max(1, round(self.canvas._brush_size / 2))

    def _create_brush_stamp(self, size: int) -> Image.Image:
        stamp = Image.new("L", (size * 2 + 1, size * 2 + 1), 0)
        draw = ImageDraw.Draw(stamp)
        hardness = self.canvas._brush_hardness / 100.0
        for radius in range(size, -1, -1):
            ratio = radius / size if size > 0 else 0
            intensity = int(255 * (1 - ratio * (1 - hardness)))
            intensity = max(0, min(255, intensity))
            draw.ellipse(
                [size - radius, size - radius, size + radius, size + radius],
                fill=intensity,
            )
        return stamp

    def _draw_stroke(self, from_pos: tuple[int, int], to_pos: tuple[int, int]) -> None:
        layer = self.canvas.active_layer()
        if layer is None or layer.image is None:
            return
        size = self._image_brush_size()
        stamp = self._create_brush_stamp(size)

        x1, y1 = from_pos
        x2, y2 = to_pos
        distance = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(distance / (size / 2)) + 1)

        mask = Image.new("L", layer.image.size, 0)
        for step in range(steps + 1):
            t = step / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            paste_box = (x - size, y - size)
            mask.paste(stamp, paste_box, stamp)

        result = self._apply_mask(layer.image, mask)
        layer.image = result
        layer.update_pixmap(self.canvas.scene)

    def _apply_mask(self, image: Image.Image, mask: Image.Image) -> Image.Image:
        result = image.copy()
        if self.id == "eraser":
            alpha = result.split()[3]
            alpha = ImageChops.multiply(alpha, ImageChops.invert(mask))
            result.putalpha(alpha)
        elif self.id == "brush":
            color = self.canvas.foreground_color()
            overlay = Image.new("RGBA", image.size, (color.red(), color.green(), color.blue(), 255))
            result = Image.composite(overlay, result, mask)
        return result

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            pos = self._view_to_image_pos(event.pos())
            if pos is not None:
                self._drawing = True
                self._last_point = pos
                self._draw_stroke(pos, pos)
            return True
        return False

    def mouse_move(self, event) -> bool:
        self._update_cursor_position(event.pos())
        if self._drawing and self._last_point is not None:
            pos = self._view_to_image_pos(event.pos())
            if pos is not None:
                self._draw_stroke(self._last_point, pos)
                self._last_point = pos
        return True

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            self._last_point = None
            self._emit_image_changed()
            return True
        return False


class EraserTool(BrushBaseTool):
    id = "eraser"


class BrushTool(BrushBaseTool):
    id = "brush"


class RectangleSelectTool(Tool):
    id = "rect_select"
    cursor = Qt.CrossCursor

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self._selecting = False
        self._start_point: QPoint | None = None
        self._rect_item: QGraphicsRectItem | None = None

    def activate(self) -> None:
        super().activate()
        if self._rect_item is None:
            self._rect_item = QGraphicsRectItem()
            pen = QPen(Qt.DashLine)
            pen.setColor(Qt.blue)
            pen.setWidth(2)
            self._rect_item.setPen(pen)
            self._rect_item.setZValue(1000)
            self.canvas.scene.addItem(self._rect_item)
        self._update_rect()

    def deactivate(self) -> None:
        super().deactivate()
        if self._rect_item is not None:
            self.canvas.scene.removeItem(self._rect_item)
            self._rect_item = None

    def _update_rect(self) -> None:
        if self._rect_item is None:
            return
        selection = self.canvas.selection_rect
        if selection is None:
            self._rect_item.setVisible(False)
            return
        left, top, right, bottom = selection
        self._rect_item.setRect(QRectF(left, top, right - left, bottom - top))
        self._rect_item.setVisible(True)

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            self._selecting = True
            self._start_point = event.pos()
            scene_pos = self.canvas.mapToScene(event.pos())
            self.canvas.selection_rect = (scene_pos.x(), scene_pos.y(), scene_pos.x(), scene_pos.y())
            self._update_rect()
            return True
        return False

    def mouse_move(self, event) -> bool:
        if self._selecting and self._start_point is not None:
            start_scene = self.canvas.mapToScene(self._start_point)
            current_scene = self.canvas.mapToScene(event.pos())
            left = min(start_scene.x(), current_scene.x())
            top = min(start_scene.y(), current_scene.y())
            right = max(start_scene.x(), current_scene.x())
            bottom = max(start_scene.y(), current_scene.y())
            self.canvas.selection_rect = (left, top, right, bottom)
            self._update_rect()
            return True
        return False

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            self._start_point = None
            return True
        return False


class FreeSelectTool(Tool):
    id = "free_select"
    cursor = Qt.CrossCursor

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self._selecting = False
        self._points: list[QPointF] = []
        self._polygon_item: QGraphicsPolygonItem | None = None

    def activate(self) -> None:
        super().activate()
        if self._polygon_item is None:
            self._polygon_item = QGraphicsPolygonItem()
            pen = QPen(Qt.DashLine)
            pen.setColor(Qt.blue)
            pen.setWidth(2)
            self._polygon_item.setPen(pen)
            self._polygon_item.setZValue(1000)
            self.canvas.scene.addItem(self._polygon_item)

    def deactivate(self) -> None:
        super().deactivate()
        if self._polygon_item is not None:
            self.canvas.scene.removeItem(self._polygon_item)
            self._polygon_item = None

    def _update_polygon(self) -> None:
        if self._polygon_item is None or not self._points:
            if self._polygon_item is not None:
                self._polygon_item.setVisible(False)
            return
        self._polygon_item.setPolygon(QPolygonF(self._points))
        self._polygon_item.setVisible(True)

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            self._selecting = True
            scene_pos = self.canvas.mapToScene(event.pos())
            self._points = [scene_pos]
            self._update_polygon()
            return True
        return False

    def mouse_move(self, event) -> bool:
        if self._selecting:
            scene_pos = self.canvas.mapToScene(event.pos())
            self._points.append(scene_pos)
            self._update_polygon()
            return True
        return False

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._selecting:
            self._selecting = False
            if self._points:
                self.canvas.selection_polygon = [p.toPoint() for p in self._points]
            return True
        return False


class CropTool(Tool):
    id = "crop"
    cursor = Qt.CrossCursor

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self._dragging = False
        self._handle: str | None = None
        self._start_rect: tuple[float, float, float, float] | None = None
        self._start_pos: QPoint | None = None
        self._rect_item: QGraphicsRectItem | None = None
        self._handle_items: list[QGraphicsRectItem] = []
        self._shift_pressed = False

    def activate(self) -> None:
        super().activate()
        if self._rect_item is None:
            self._rect_item = QGraphicsRectItem()
            pen = QPen(Qt.red)
            pen.setWidth(2)
            self._rect_item.setPen(pen)
            self._rect_item.setZValue(1000)
            self.canvas.scene.addItem(self._rect_item)
        self._clear_handles()
        for _ in range(8):
            handle = QGraphicsRectItem()
            handle.setRect(-4, -4, 8, 8)
            pen = QPen(Qt.black)
            pen.setWidth(1)
            handle.setPen(pen)
            handle.setBrush(Qt.white)
            handle.setZValue(1001)
            self.canvas.scene.addItem(handle)
            self._handle_items.append(handle)
        self._update_display()

    def deactivate(self) -> None:
        super().deactivate()
        if self._rect_item is not None:
            self.canvas.scene.removeItem(self._rect_item)
            self._rect_item = None
        self._clear_handles()

    def _clear_handles(self) -> None:
        for handle in self._handle_items:
            self.canvas.scene.removeItem(handle)
        self._handle_items.clear()

    def _update_display(self) -> None:
        rect = self.canvas.crop_rect
        if rect is None or self._rect_item is None:
            if self._rect_item is not None:
                self._rect_item.setVisible(False)
            for handle in self._handle_items:
                handle.setVisible(False)
            return
        left, top, right, bottom = rect
        self._rect_item.setRect(left, top, right - left, bottom - top)
        self._rect_item.setVisible(True)

        handles = [
            (left, top),
            ((left + right) / 2, top),
            (right, top),
            (right, (top + bottom) / 2),
            (right, bottom),
            ((left + right) / 2, bottom),
            (left, bottom),
            (left, (top + bottom) / 2),
        ]
        for handle, (x, y) in zip(self._handle_items, handles):
            handle.setPos(x, y)
            handle.setVisible(True)

    def _hit_handle(self, scene_pos: QPointF) -> str | None:
        if self.canvas.crop_rect is None:
            return None
        left, top, right, bottom = self.canvas.crop_rect
        handles = {
            "nw": (left, top),
            "n": ((left + right) / 2, top),
            "ne": (right, top),
            "e": (right, (top + bottom) / 2),
            "se": (right, bottom),
            "s": ((left + right) / 2, bottom),
            "sw": (left, bottom),
            "w": (left, (top + bottom) / 2),
        }
        for name, (hx, hy) in handles.items():
            if abs(scene_pos.x() - hx) <= 8 and abs(scene_pos.y() - hy) <= 8:
                return name
        if left <= scene_pos.x() <= right and top <= scene_pos.y() <= bottom:
            return "move"
        return None

    def _constrain_proportional(
        self,
        start_rect: tuple[float, float, float, float],
        new_rect: tuple[float, float, float, float],
        handle: str,
    ) -> tuple[float, float, float, float]:
        left, top, right, bottom = new_rect
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            return start_rect
        sx, sy, sr, sb = start_rect
        start_width = sr - sx
        start_height = sb - sy
        ratio = start_width / start_height if start_height > 0 else 1.0

        if handle in {"nw", "se"}:
            if width / height > ratio:
                width = height * ratio
            else:
                height = width / ratio
            if handle == "nw":
                left = right - width
                top = bottom - height
            else:
                right = left + width
                bottom = top + height
        elif handle in {"ne", "sw"}:
            if width / height > ratio:
                width = height * ratio
            else:
                height = width / ratio
            if handle == "ne":
                right = left + width
                top = bottom - height
            else:
                left = right - width
                bottom = top + height
        return left, top, right, bottom

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            scene_pos = self.canvas.mapToScene(event.pos())
            handle = self._hit_handle(scene_pos)
            if handle is not None:
                self._dragging = True
                self._handle = handle
                self._start_rect = self.canvas.crop_rect
                self._start_pos = event.pos()
                self._shift_pressed = event.modifiers() & Qt.ShiftModifier
                return True
            layer = self.canvas.active_layer()
            if layer is not None:
                self.canvas.crop_rect = (
                    layer.x,
                    layer.y,
                    layer.x + layer.width,
                    layer.y + layer.height,
                )
                self._update_display()
                return True
        return False

    def mouse_move(self, event) -> bool:
        if not self._dragging or self._start_rect is None or self._start_pos is None:
            scene_pos = self.canvas.mapToScene(event.pos())
            handle = self._hit_handle(scene_pos)
            if handle == "move":
                self.canvas.setCursor(Qt.SizeAllCursor)
            elif handle:
                self.canvas.setCursor(Qt.CrossCursor)
            else:
                self.canvas.setCursor(self.cursor)
            return False

        delta = self.canvas.mapToScene(event.pos()) - self.canvas.mapToScene(self._start_pos)
        sx, sy, sr, sb = self._start_rect
        left, top, right, bottom = sx, sy, sr, sb

        if self._handle == "move":
            left = sx + delta.x()
            top = sy + delta.y()
            right = sr + delta.x()
            bottom = sb + delta.y()
        elif self._handle == "nw":
            left = min(sx + delta.x(), sr - 1)
            top = min(sy + delta.y(), sb - 1)
        elif self._handle == "n":
            top = min(sy + delta.y(), sb - 1)
        elif self._handle == "ne":
            right = max(sr + delta.x(), sx + 1)
            top = min(sy + delta.y(), sb - 1)
        elif self._handle == "e":
            right = max(sr + delta.x(), sx + 1)
        elif self._handle == "se":
            right = max(sr + delta.x(), sx + 1)
            bottom = max(sb + delta.y(), sy + 1)
        elif self._handle == "s":
            bottom = max(sb + delta.y(), sy + 1)
        elif self._handle == "sw":
            left = min(sx + delta.x(), sr - 1)
            bottom = max(sb + delta.y(), sy + 1)
        elif self._handle == "w":
            left = min(sx + delta.x(), sr - 1)

        new_rect = (left, top, right, bottom)
        shift = event.modifiers() & Qt.ShiftModifier
        if shift:
            new_rect = self._constrain_proportional(self._start_rect, new_rect, self._handle)
        self.canvas.crop_rect = new_rect
        self.canvas.crop_rect_changed.emit(new_rect)
        self._update_display()
        return True

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._handle = None
            self._start_rect = None
            self._start_pos = None
            return True
        return False


class CloneStampTool(Tool):
    id = "clone_stamp"
    cursor = Qt.BlankCursor

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self._source_point: tuple[int, int] | None = None
        self._drawing = False
        self._last_point: tuple[int, int] | None = None
        self._source_indicator: QGraphicsEllipseItem | None = None
        self._cursor_item: QGraphicsEllipseItem | None = None

    def activate(self) -> None:
        super().activate()
        if self._source_indicator is None:
            self._source_indicator = QGraphicsEllipseItem()
            pen = QPen(Qt.green)
            pen.setWidth(2)
            self._source_indicator.setPen(pen)
            self._source_indicator.setBrush(Qt.NoBrush)
            self._source_indicator.setZValue(1000)
            self.canvas.scene.addItem(self._source_indicator)
        if self._cursor_item is None:
            self._cursor_item = QGraphicsEllipseItem()
            pen = QPen(Qt.white)
            pen.setWidth(2)
            self._cursor_item.setPen(pen)
            self._cursor_item.setBrush(Qt.NoBrush)
            self._cursor_item.setZValue(1001)
            self._cursor_item.setVisible(False)
            self.canvas.scene.addItem(self._cursor_item)

    def deactivate(self) -> None:
        super().deactivate()
        if self._source_indicator is not None:
            self.canvas.scene.removeItem(self._source_indicator)
            self._source_indicator = None
        if self._cursor_item is not None:
            self.canvas.scene.removeItem(self._cursor_item)
            self._cursor_item = None

    def _update_cursor(self, view_pos: QPoint) -> None:
        if self._cursor_item is None:
            return
        if not self.canvas.viewport().rect().contains(view_pos):
            self._cursor_item.setVisible(False)
            return
        scene_pos = self.canvas.mapToScene(view_pos)
        radius = max(1, self.canvas._brush_size / 2)
        self._cursor_item.setRect(
            scene_pos.x() - radius,
            scene_pos.y() - radius,
            radius * 2,
            radius * 2,
        )
        self._cursor_item.setVisible(True)

    def _update_source_indicator(self) -> None:
        if self._source_indicator is None or self._source_point is None:
            return
        layer = self.canvas.active_layer()
        if layer is None:
            return
        x = self._source_point[0] + layer.x
        y = self._source_point[1] + layer.y
        radius = max(1, self.canvas._brush_size / 2)
        self._source_indicator.setRect(x - radius, y - radius, radius * 2, radius * 2)
        self._source_indicator.setVisible(True)

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                pos = self._view_to_image_pos(event.pos())
                if pos is not None:
                    self._source_point = pos
                    self._update_source_indicator()
                return True
            pos = self._view_to_image_pos(event.pos())
            if pos is not None and self._source_point is not None:
                self._drawing = True
                self._last_point = pos
                self._stamp(pos)
            return True
        return False

    def mouse_move(self, event) -> bool:
        self._update_cursor(event.pos())
        if self._drawing and self._last_point is not None:
            pos = self._view_to_image_pos(event.pos())
            if pos is not None:
                self._stamp(pos)
                self._last_point = pos
        return True

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._drawing:
            self._drawing = False
            self._last_point = None
            self._emit_image_changed()
            return True
        return False

    def _stamp(self, target: tuple[int, int]) -> None:
        if self._source_point is None:
            return
        layer = self.canvas.active_layer()
        if layer is None:
            return
        size = max(1, round(self.canvas._brush_size / 2))
        sx, sy = self._source_point
        tx, ty = target
        dx = tx - sx
        dy = ty - sy
        source = layer.image.copy()
        mask = Image.new("L", layer.image.size, 0)
        stamp = Image.new("L", (size * 2 + 1, size * 2 + 1), 255)
        mask.paste(stamp, (tx - size, ty - size))
        shifted = source.transform(
            source.size,
            Image.Transform.AFFINE,
            (1, 0, dx, 0, 1, dy),
            resample=Image.Resampling.BILINEAR,
        )
        result = Image.composite(shifted, layer.image, mask)
        layer.image = result
        layer.update_pixmap(self.canvas.scene)


class MoveTool(Tool):
    id = "move"
    cursor = Qt.SizeAllCursor

    def __init__(self, canvas: "ImageCanvas") -> None:
        super().__init__(canvas)
        self._moving = False
        self._start_pos: QPoint | None = None
        self._start_layer_pos: tuple[int, int] | None = None
        self._layer: Any = None

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            scene_pos = self.canvas.mapToScene(event.pos())
            layer = self.canvas._layers.layer_at(scene_pos.x(), scene_pos.y())
            if layer is None:
                layer = self.canvas.active_layer()
            if layer is not None:
                self._moving = True
                self._start_pos = event.pos()
                self._start_layer_pos = (layer.x, layer.y)
                self._layer = layer
                self.canvas._layers.set_active_layer(layer)
                return True
        return False

    def mouse_move(self, event) -> bool:
        if self._moving and self._start_pos is not None and self._start_layer_pos is not None and self._layer is not None:
            delta = self.canvas.mapToScene(event.pos()) - self.canvas.mapToScene(self._start_pos)
            self._layer.move(
                int(self._start_layer_pos[0] + delta.x()),
                int(self._start_layer_pos[1] + delta.y()),
            )
            return True
        return False

    def mouse_release(self, event) -> bool:
        if event.button() == Qt.LeftButton and self._moving:
            self._moving = False
            self._start_pos = None
            self._start_layer_pos = None
            self._layer = None
            self._emit_image_changed()
            return True
        return False


class EyedropperTool(Tool):
    id = "eyedropper"
    cursor = Qt.CrossCursor

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            pos = self._view_to_image_pos(event.pos())
            if pos is not None:
                layer = self.canvas.active_layer()
                if layer is not None and layer.image is not None:
                    x, y = pos
                    pixel = layer.image.getpixel((x, y))
                    if len(pixel) == 4:
                        r, g, b, a = pixel
                    else:
                        r, g, b = pixel
                        a = 255
                    self.canvas.color_picked.emit(QColor(r, g, b, a))
            return True
        return False


class PaintBucketTool(Tool):
    id = "paint_bucket"
    cursor = Qt.PointingHandCursor

    def mouse_press(self, event) -> bool:
        if event.button() == Qt.LeftButton:
            pos = self._view_to_image_pos(event.pos())
            if pos is not None:
                layer = self.canvas.active_layer()
                if layer is not None and layer.image is not None:
                    x, y = pos
                    color = self.canvas.foreground_color()
                    fill = (color.red(), color.green(), color.blue(), 255)
                    image = layer.image.copy()
                    ImageDraw.floodfill(image, (x, y), fill, border=None)
                    layer.image = image
                    layer.update_pixmap(self.canvas.scene)
                    self._emit_image_changed()
            return True
        return False
