#!/usr/bin/env python3
"""Non-destructive grid overlay for the image canvas."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QWidget


class GridOverlay(QGraphicsItem):
    """A grid overlay that divides an image into equal cells."""

    def __init__(self, parent: QGraphicsItem | None = None) -> None:
        super().__init__(parent)
        self._rect = (0.0, 0.0, 1.0, 1.0)
        self._rows = 4
        self._cols = 4
        self._color = Qt.red
        self._visible = False
        self.setZValue(2000)

    def set_rect(self, x: float, y: float, width: float, height: float) -> None:
        self._rect = (x, y, width, height)
        self.update()

    def set_grid(self, rows: int, cols: int) -> None:
        self._rows = max(1, rows)
        self._cols = max(1, cols)
        self.update()

    def set_visible(self, visible: bool) -> None:
        self._visible = visible
        self.setVisible(visible)
        self.update()

    def set_color(self, color: Qt.GlobalColor) -> None:
        self._color = color
        self.update()

    def boundingRect(self) -> object:
        from PySide6.QtCore import QRectF
        x, y, w, h = self._rect
        return QRectF(x, y, w, h)

    def paint(self, painter: QPainter, _option, _widget: QWidget | None) -> None:
        if not self._visible:
            return
        x, y, width, height = self._rect
        if width <= 0 or height <= 0:
            return

        pen = QPen(self._color)
        pen.setWidth(1)
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)

        for col in range(1, self._cols):
            px = x + width * col / self._cols
            painter.drawLine(int(px), int(y), int(px), int(y + height))

        for row in range(1, self._rows):
            py = y + height * row / self._rows
            painter.drawLine(int(x), int(py), int(x + width), int(py))

        painter.drawRect(int(x), int(y), int(width), int(height))
