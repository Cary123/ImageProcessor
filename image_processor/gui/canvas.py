#!/usr/bin/env python3
"""Image canvas with checkerboard background, zoom, and brush/eraser support."""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPixmap, QWheelEvent
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsScene, QGraphicsView

from image_processor.core.image_engine import create_checkerboard


class ImageCanvas(QGraphicsView):
    """Canvas that displays images on a checkerboard background."""

    zoom_changed = Signal(float)
    brush_applied = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAlignment(Qt.AlignCenter)
        self.setDragMode(QGraphicsView.ScrollHandDrag)

        self._checkerboard_size = 16
        self._current_pixmap_item: QGraphicsPixmapItem | None = None
        self._pil_image: Image.Image | None = None

        self._brush_mode: str | None = None
        self._brush_size = 20
        self._brush_hardness = 100
        self._original_image: Image.Image | None = None
        self._mask_image: Image.Image | None = None
        self._drawing = False
        self._last_point: tuple[int, int] | None = None

        self._set_checkerboard_background(512, 512)

    def _set_checkerboard_background(self, width: int, height: int) -> None:
        board = create_checkerboard(width, height, cell_size=self._checkerboard_size)
        self.scene.setBackgroundBrush(self._qbrush_from_pil(board))
        self.scene.setSceneRect(-width / 2, -height / 2, width, height)

    def _qbrush_from_pil(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGB"))
        height, width, _ = data.shape
        bytes_per_line = width * 3
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_image)

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)

    def set_image(self, image: Image.Image) -> None:
        self._pil_image = image
        if self._current_pixmap_item is not None:
            self.scene.removeItem(self._current_pixmap_item)

        pixmap = self._pil_to_pixmap(image)
        self._current_pixmap_item = self.scene.addPixmap(pixmap)
        self._current_pixmap_item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
        self._current_pixmap_item.setZValue(1)

        self._set_checkerboard_background(image.width, image.height)
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.zoom_changed.emit(self.transform().m11())

    def clear(self) -> None:
        if self._current_pixmap_item is not None:
            self.scene.removeItem(self._current_pixmap_item)
            self._current_pixmap_item = None
        self._pil_image = None
        self._set_checkerboard_background(512, 512)
        self._end_brush_session()

    def set_checkerboard_size(self, size: int) -> None:
        self._checkerboard_size = max(4, size)
        if self._pil_image is not None:
            self._set_checkerboard_background(self._pil_image.width, self._pil_image.height)

    def reset_zoom(self) -> None:
        self.resetTransform()
        if self._pil_image is not None:
            self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.zoom_changed.emit(self.transform().m11())

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._brush_mode is not None:
            return
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale(factor, factor)
        self.zoom_changed.emit(self.transform().m11())

    def set_brush_mode(self, mode: str | None) -> None:
        """Activate brush/eraser mode or None for normal navigation."""
        self._brush_mode = mode
        self._drawing = False
        self._last_point = None
        if mode is not None:
            self.setDragMode(QGraphicsView.NoDrag)
        else:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._end_brush_session()

    def set_brush_size(self, size: int) -> None:
        self._brush_size = max(1, size)

    def set_brush_hardness(self, hardness: int) -> None:
        self._brush_hardness = max(0, min(100, hardness))

    def start_brush_session(self, image: Image.Image, original_image: Image.Image) -> None:
        self._pil_image = image
        if original_image.size != image.size:
            self._original_image = original_image.resize(image.size, Image.Resampling.LANCZOS)
        else:
            self._original_image = original_image
        self._mask_image = Image.new("L", image.size, 0)
        self._drawing = False
        self._last_point = None
        self._update_brush_preview()

    def _end_brush_session(self) -> None:
        self._original_image = None
        self._mask_image = None
        self._drawing = False
        self._last_point = None

    def apply_brush(self) -> None:
        if self._pil_image is None or self._mask_image is None or self._original_image is None:
            return
        result = self._apply_mask(self._pil_image, self._original_image, self._mask_image)
        self._mask_image = Image.new("L", self._pil_image.size, 0)
        self._update_brush_preview()
        self.brush_applied.emit(result)

    def cancel_brush(self) -> None:
        self._mask_image = Image.new("L", self._pil_image.size, 0) if self._pil_image else None
        self._update_brush_preview()

    def _view_to_image_pos(self, view_pos) -> tuple[int, int] | None:
        if self._pil_image is None:
            return None
        scene_pos = self.mapToScene(view_pos)
        x = int(scene_pos.x() + self._pil_image.width / 2)
        y = int(scene_pos.y() + self._pil_image.height / 2)
        if 0 <= x < self._pil_image.width and 0 <= y < self._pil_image.height:
            return x, y
        return None

    def _image_brush_size(self) -> int:
        scale = self.transform().m11()
        if scale <= 0:
            scale = 1.0
        return max(1, int(self._brush_size / scale))

    def _create_brush_stamp(self, size: int) -> Image.Image:
        stamp = Image.new("L", (size * 2 + 1, size * 2 + 1), 0)
        draw = ImageDraw.Draw(stamp)
        hardness = self._brush_hardness / 100.0
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
        if self._mask_image is None:
            return

        size = self._image_brush_size()
        stamp = self._create_brush_stamp(size)

        x1, y1 = from_pos
        x2, y2 = to_pos
        distance = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(distance / (size / 2)) + 1)

        for step in range(steps + 1):
            t = step / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            paste_box = (x - size, y - size)
            self._mask_image.paste(stamp, paste_box, stamp)

        self._update_brush_preview()

    def _update_brush_preview(self) -> None:
        if self._pil_image is None or self._mask_image is None or self._original_image is None:
            return
        preview = self._apply_mask(self._pil_image, self._original_image, self._mask_image)
        if self._current_pixmap_item is not None:
            self.scene.removeItem(self._current_pixmap_item)
        pixmap = self._pil_to_pixmap(preview)
        self._current_pixmap_item = self.scene.addPixmap(pixmap)
        self._current_pixmap_item.setOffset(-pixmap.width() / 2, -pixmap.height() / 2)
        self._current_pixmap_item.setZValue(1)

    def _apply_mask(
        self,
        image: Image.Image,
        original: Image.Image,
        mask: Image.Image,
    ) -> Image.Image:
        result = image.copy()
        if self._brush_mode == "eraser":
            alpha = result.split()[3]
            alpha = ImageChops.multiply(alpha, ImageChops.invert(mask))
            result.putalpha(alpha)
        elif self._brush_mode == "brush":
            restored = Image.composite(original, result, mask)
            result = restored
        return result

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._brush_mode is not None and event.button() == Qt.LeftButton:
            self._drawing = True
            pos = self._view_to_image_pos(event.pos())
            if pos is not None:
                self._last_point = pos
                self._draw_stroke(pos, pos)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._brush_mode is not None and self._drawing:
            pos = self._view_to_image_pos(event.pos())
            if pos is not None and self._last_point is not None:
                self._draw_stroke(self._last_point, pos)
                self._last_point = pos
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._brush_mode is not None and event.button() == Qt.LeftButton:
            self._drawing = False
            self._last_point = None
            return
        super().mouseReleaseEvent(event)
