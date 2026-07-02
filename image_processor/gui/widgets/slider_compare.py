#!/usr/bin/env python3
"""Sliding before/after image comparison widget."""

from __future__ import annotations

import numpy as np
from PIL import Image
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPaintEvent, QPainter, QPixmap
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class SliderCompareWidget(QWidget):
    """Widget showing a draggable divider between before and after images."""

    divider_changed = Signal(int)

    def __init__(self, before: Image.Image, after: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.before = before.convert("RGBA")
        self.after = after.convert("RGBA")
        self._before_pixmap = self._pil_to_pixmap(self.before)
        self._after_pixmap = self._pil_to_pixmap(self.after)
        self._divider_x = self.width() // 2
        self._dragging = False

        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        data = np.array(image.convert("RGBA"))
        height, width, _ = data.shape
        bytes_per_line = width * 4
        q_image = QImage(data.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
        return QPixmap.fromImage(q_image)

    def resizeEvent(self, event) -> None:
        self._divider_x = self.width() // 2
        super().resizeEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        if painter.isActive():
            widget_width = self.width()
            widget_height = self.height()

            after_scaled = self._after_pixmap.scaled(
                widget_width, widget_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            before_scaled = self._before_pixmap.scaled(
                widget_width, widget_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

            x_offset = (widget_width - after_scaled.width()) // 2
            y_offset = (widget_height - after_scaled.height()) // 2

            painter.drawPixmap(x_offset, y_offset, after_scaled)

            divider_x = max(0, min(self._divider_x, widget_width))
            clip_rect = before_scaled.rect()
            clip_rect.setWidth(divider_x - x_offset)
            painter.setClipRect(x_offset, y_offset, divider_x - x_offset, before_scaled.height())
            painter.drawPixmap(x_offset, y_offset, before_scaled)
            painter.setClipRect(event.rect())

            pen = painter.pen()
            pen.setWidth(2)
            pen.setColor(Qt.white)
            painter.setPen(pen)
            painter.drawLine(divider_x, y_offset, divider_x, y_offset + after_scaled.height())

            painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._divider_x = event.pos().x()
            self.divider_changed.emit(self._divider_x)
            self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._divider_x = max(0, min(event.pos().x(), self.width()))
            self.divider_changed.emit(self._divider_x)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._dragging = False


class SliderCompareDialog(QDialog):
    """Dialog for sliding before/after comparison."""

    def __init__(self, before: Image.Image, after: Image.Image, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("滑动对比")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        hint = QLabel("拖动白色分隔线对比原图和处理后效果")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        self.compare_widget = SliderCompareWidget(before, after, self)
        layout.addWidget(self.compare_widget, 1)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
